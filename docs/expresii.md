# Expresii Power Automate și catalogul de mesaje

> Sursa de adevăr pentru expresiile din fluxuri. Numele acțiunilor sunt cele din ghidurile `docs/flux*_pas_cu_pas.md`.
> Secțiunea pentru Flux 2 se completează în Faza 7.

## Flux 1 — `BG_Flux1_Cerere`

### Expresii de bază

| Scop | Expresie |
|---|---|
| Cod CC din opțiunea Forms | `first(split(outputs('Date_Formular')?['centru_cost'], ' '))` |
| Config ca obiect (`Select_Config`, mod text) | `concat('"', item()?['Title'], '":"', item()?['Valoare'], '"')` |
| Config ca obiect (`cfg`) | `json(concat('{', join(body('Select_Config'), ','), '}'))` |
| ID cerere | `concat('PR-', formatDateTime(utcNow(), 'yyyy'), '-', formatNumber(outputs('Create_Cerere')?['body/ID'], '0000'))` |
| Firma ANAF (null dacă nu există) | `first(body('Parse_ANAF')?['found'])` |
| Curs BNR pentru moneda cererii | `float(xpath(xml(body('HTTP_BNR')), concat('string(//*[local-name()=''Rate''][@currency=''', outputs('Cerere')?['moneda'], '''])')))` |
| Data cursului | `xpath(xml(body('HTTP_BNR')), 'string(//*[local-name()=''Cube'']/@date)')` |
| Curs de rezervă | `float(outputs('cfg')?[concat('curs_fallback_', outputs('Cerere')?['moneda'])])` |
| Valoare_RON, 2 zecimale | `float(formatNumber(mul(float(outputs('Cerere')?['valoare']), variables('varCurs')), '0.00', 'en-US'))` |
| Rând de buget | `first(outputs('Get_Buget')?['body/value'])` |
| Peste buget | `greater(outputs('Valoare_RON'), coalesce(outputs('Buget')?['Ramas_RON'], 1000000000))` |
| Listă → text pe linii | `join(variables('varErori'), decodeUriComponent('%0A'))` |
| Dată afișată în email | `convertTimeZone(utcNow(), 'UTC', 'GTB Standard Time', 'dd.MM.yyyy HH:mm')` |

### Aprobări (Faza 5)

| Scop | Expresie |
|---|---|
| CFO necesar | `or(outputs('Peste_Buget'), greater(outputs('Valoare_RON'), float(outputs('cfg')?['prag_cfo_ron'])))` |
| Aprobatorul pasului curent | `variables('varAprobatori')[variables('varIdx')]` |
| Oprirea buclei | `or(variables('varRespins'), greaterOrEquals(variables('varIdx'), length(variables('varAprobatori'))))` |
| Rezultatul pasului (sigur și la timeout) | `if(equals(actions('Aprobare')?['outputs']?['body']?['outcome'], 'Approve'), 'Aprobat', if(equals(actions('Aprobare')?['status'], 'TimedOut'), 'Expirat', 'Respins'))` |
| Cine a răspuns | `coalesce(actions('Aprobare')?['outputs']?['body']?['responses']?[0]?['responder']?['email'], variables('varAprobatori')[variables('varIdx')])` |
| Angajat nou | `float(formatNumber(add(float(coalesce(body('Get_Buget_Curent')?['Angajat_RON'], 0)), outputs('Valoare_RON')), '0.00', 'en-US'))` |
| Jurnal → listă HTML | `join(split(trim(replace(variables('varJurnal'), '- Pas', 'Pas')), decodeUriComponent('%0A')), '</li><li>')` |

### Export (`BG_Export`)

| Scop | Expresie |
|---|---|
| Filtru OData cu condiții opționale | vezi `docs/export_pas_cu_pas.md` §2.2 |
| Coloană Alegere din Get items | `item()?['Moneda']?['Value']` |
| CSV cu BOM (diacritice în Excel) | `concat(decodeUriComponent('%EF%BB%BF'), body('Create_CSV'))` |
| Suma unei coloane dintr-un array | `xpath(xml(json(concat('{"r":{"w":', string(body('Select_Export')), '}}'))), 'sum(/r/w/Valoare_RON)')` |

### Formatul răspunsurilor Forms (verificat 2026-11-21)
- Data: `2026-11-30` (ISO, `yyyy-MM-dd`), deși în formular se afișează `dd.MM.yyyy`.
- Evaluare: șir (`"3"`). Alegere: textul complet al opțiunii (`IT – Tehnologie`).
- Textul liber poate începe cu spațiu, de aceea `titlu` și `justificare` trec prin `trim()`.

### Tehnici folosite și de ce
- **`Date_Formular` → `Cerere`**: întrebările Forms au ID-uri generate. Se mapează o singură dată, prin jetoane, iar restul fluxului folosește chei stabile. Toate valorile din `Cerere` sunt șiruri, ca JSON-ul să rămână valid. Conversia se face la utilizare.
- **Fără `if()` cu ramuri care pot eșua**: în loc de `if(empty(x), 0, int(x))` se normalizează la text (`'0'`) și se convertește după. La buget se folosește `coalesce`, fiindcă `and()` nu se oprește la primul `false`.
- **Fallback BNR**: `Cond_BNR_OK` rulează după `HTTP_BNR` și pe *a eșuat / a expirat*, apoi verifică `actions('HTTP_BNR')?['status']`.

### Catalogul de mesaje

| Cod | Tip | Când | Mesaj (exemplu) |
|---|---|---|---|
| V1 | eroare | CUI absent la ANAF | `[V1] CUI 99999999 nu figurează în baza ANAF.` |
| V2 | eroare | `statusInactivi = true` | `[V2] Furnizorul X SRL (CUI 123) este declarat inactiv fiscal.` |
| V2b | eroare | `dataRadiere` completată | `[V2b] Furnizorul X SRL (CUI 123) este radiat din data de 2024-05-10.` |
| V3 | eroare | Valoare_RON ≤ 0 sau > `valoare_max_ron` | `[V3] Valoarea de 612.300,00 RON este în afara intervalului acceptat: peste 0 și cel mult 500.000 RON.` |
| V4 | eroare | data < azi + `zile_min_avans` | `[V4] Data necesară 21.11.2026 este prea apropiată. Data minimă acceptată este 25.11.2026 (5 zile de la depunere).` |
| V5 | eroare | nu există rând în Bugete | `[V5] Nu există buget pentru IT/MKT în 2026-11.` |
| W1 | avertisment | Valoare_RON > Ramas_RON | `[W1] Valoarea de 52.000,00 RON depășește bugetul rămas de 47.200,00 RON pentru 2026-11_IT_SW. Se solicită și aprobarea CFO.` |
| W2 | avertisment | HW + OPEX + ≥ `prag_capex_ron` | `[W2] Hardware de 3.000,00 RON încadrat ca OPEX (prag 2500 RON): posibilă imobilizare — verificați încadrarea CAPEX.` |
| W3 | avertisment | `scpTVA = false` | `[W3] Furnizorul ASOCIATIA X nu este înregistrat în scopuri de TVA.` |
| W4 | avertisment | BNR indisponibil | `[W4] Cursul BNR nu a putut fi obținut; s-a folosit cursul de rezervă din Config (1 EUR = 5.3459 RON).` |
| A1 | respingere | aprobator respinge | `Respinsă la pasul 2/3 – Controlling de x@ase.ro: „Birotica pentru T1 e deja acoperită.”` |
| A2 | respingere | aprobare expirată (7 zile) | `Termenul de aprobare a expirat (7 zile) la pasul 1/3 – Manager centru de cost (x@ase.ro).` |
| E1 | informare export | niciun rezultat | `Nicio cerere aprobată în intervalul selectat.` |
