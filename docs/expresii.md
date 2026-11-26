# Expresii Power Automate și catalogul de mesaje

> Sursa de adevăr pentru expresiile din fluxuri. Numele acțiunilor sunt cele din ghidurile `docs/flux*_pas_cu_pas.md`.
> Flux 2: secțiunea de la final (Faza 7). Rândurile marcate „de confirmat” se actualizează după primele rulări.

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

## Flux 2 — `BG_Flux2_Import`

### Citirea fișierului

| Scop | Expresie |
|---|---|
| Doar `.json`, nu din `Procesate` (condiții de declanșare) | `@endsWith(toLower(triggerOutputs()?['body/{FilenameWithExtension}']), '.json')` și `@not(contains(toLower(triggerOutputs()?['body/{Path}']), 'procesate'))` |
| Conținut ca text, din obiect sau base64, fără BOM (`Fisier_Text`) | `replace(if(empty(body('Get_file_content')?['$content']), string(body('Get_file_content')), base64ToString(coalesce(body('Get_file_content')?['$content'], ''))), decodeUriComponent('%EF%BB%BF'), '')` |
| Text → obiect (`Fisier_JSON`; eșuează la JSON corupt) | `json(outputs('Fisier_Text'))` |
| Rulare_ID | `workflow()?['run']?['name']` |

**Varianta întoarsă de `Get_file_content` pentru `.json`** (verificat 2026-11-25): **obiect JSON deja parsat** (`Content-Type: application/json`), fără `$content`. `Fisier_Text` merge pe ramura `string(body(...))`. Ramura base64 rămâne pentru fișierele pe care SharePoint nu le poate parsa (de ex. JSON corupt, TC-F2-04). Sumele întregi vin fără zecimale (`51750`, `-1500`).

### Validarea rândului

| Scop | Expresie |
|---|---|
| Format lună AAAA-LL, sigur pe orice text | `and(equals(length(l), 7), equals(substring(concat(l, '_______'), 4, 1), '-'), isInt(substring(concat(l, '_______'), 0, 4)), contains(createArray('01', …, '12'), substring(concat(l, '_______'), 5, 2)))` |
| Câmpuri lipsă ca listă | `join(split(trim(concat(if(empty(luna), 'luna ', ''), …)), ' '), ', ')` |
| Sumă numerică fără eroare | `float(if(isFloat(s), s, '0'))` |
| Primul test care pică (`Cod_Eroare`) | `if(…, 'LIPSA', if(…, 'LUNA', … if(contains(variables('varChei'), cheie), 'DUP', ''))))` |
| Sumă RON | `float(formatNumber(mul(outputs('Suma_Num'), float(variables('varCursuri')?[moneda])), '0.00', 'en-US'))` |

**Regula de bază:** Power Automate evaluează toate argumentele unei expresii, inclusiv ramura neluată a lui `if` și toți termenii lui `and`. Orice funcție care poate eșua (`substring`, `float`, `int`) primește o intrare care nu poate fi greșită: text umplut sau `'0'` în locul valorii invalide.

### Sume și agregări

| Scop | Expresie |
|---|---|
| Suma aprobată pe cheie (array gol → 0) | `float(formatNumber(float(xpath(xml(json(concat('{"r":{"v":', string(body('Select_Valori')), '}}'))), 'sum(/r/v)')), '0.00', 'en-US'))` |
| Maverick | `max(0, float(formatNumber(sub(suma_ron, outputs('Aprobat_RON')), '0.00', 'en-US')))` |
| Dicționar cheie → maverick | `setProperty(variables('varMav'), cheie, outputs('Maverick_RON'))`, prin `Mav_Map` → `Set_varMav` |
| Maverick pe toată luna (pentru `Analiza_CC`) | `json(concat('{', join(body('Select_Mav_Luna'), ','), '}'))`, din `Realizat_Lunar` filtrat pe lună. Nu din `varMav`, care are doar rândurile fișierului curent |
| Total pe CC dintr-o coloană | `float(formatNumber(float(xpath(xml(json(concat('{"r":{"c":', string(body('Select_Categorii')), '}}'))), 'sum(/r/c/buget)')), '0.00', 'en-US'))` |
| Varianță % | `float(formatNumber(div(mul(outputs('Varianta_RON'), 100), max(outputs('Buget_CC'), 0.01)), '0.00', 'en-US'))` |
| Modul (nu există `abs`) | `max(x, mul(x, -1))` |
| Alerta după regulă | `if(lessOrEquals(modul, 5), 'Verde', if(lessOrEquals(modul, float(outputs('cfg')?['prag_alerta_pct'])), 'Galben', 'Roșu'))` |

**Suma xpath pe array gol / cu un element** (verificat 2026-11-25, punctul de control C): corectă în toate cazurile. HR/TRN (0 cereri) → `0`, cheile cu 1 cerere → valoarea ei, cheile cu 2 cereri → suma. `compare_results.py`: 62/62 verificări OK pe Realizat_Lunar. Nu e nevoie de tratare separată.

**Export CSV din SharePoint:** numerele vin în format RO (`51.750,00`), iar datele ca `25.11.2026 16:08`. `compare_results.py` le citește pe ambele.

### AI

| Scop | Expresie |
|---|---|
| Corpul cererii Groq, fără escapare manuală | `setProperty(setProperty(json('{"temperature":0.2,"response_format":{"type":"json_object"}}'), 'model', …), 'messages', createArray(setProperty(json('{"role":"system"}'), 'content', outputs('System_Prompt')), setProperty(json('{"role":"user"}'), 'content', string(outputs('User_AI')))))` |
| Răspunsul, cu sedila corectată | `replace(replace(replace(replace(body('HTTP_Groq')?['choices']?[0]?['message']?['content'], 'ţ', 'ț'), 'ş', 'ș'), 'Ţ', 'Ț'), 'Ş', 'Ș')` |
| Necesită revizuire | `not(equals(body('Parse_AI')?['nivel_alerta'], outputs('Alerta_Regula')))` |
| Valoare dintr-o acțiune care poate fi omisă | `actions('Parse_AI')?['outputs']?['body']?['comentariu']` |
| Id-ul rândului din Analize_AI (creat sau existent) | `coalesce(first(outputs('Get_Analiza')?['body/value'])?['ID'], actions('Create_Analiza')?['outputs']?['body']?['ID'])` |

### Tratarea erorilor

| Scop | Expresie |
|---|---|
| Acțiunile eșuate din `Scope_Try` | *Filtrare matrice* pe `result('Scope_Try')`, cu `item()?['status']` = `Failed` |
| Numele acțiunii | `coalesce(first(body('Filter_Esec'))?['name'], 'necunoscută')` |
| Mesajul tehnic | `coalesce(first(body('Filter_Esec'))?['error']?['message'], first(body('Filter_Esec'))?['outputs']?['body']?['error']?['message'], 'fără detalii')` |

### Catalogul de mesaje Flux 2

Mesajele de rând sunt identice cu cele din `scripts/reference_pipeline.py`, ca `scripts/compare_results.py` să le compare literal.

| Cod | Tip_Eroare | Mesaj (exemplu) |
|---|---|---|
| LIPSA | Câmp lipsă | `Rândul 5 (2026-10_IT_HW): lipsesc câmpurile obligatorii suma, moneda.` |
| LUNA | Format lună | `Rândul 17: luna „10/2026” are format greșit; formatul corect este AAAA-LL (ex. 2026-10).` |
| TIP | Tip invalid | `Rândul 3 (2026-10_MKT_SRV): suma „abc” nu este un număr.` |
| SUMA | Valoare în afara domeniului | `Rândul 14 (2026-10_OPS_BIR): suma -1500 nu este validă; se acceptă doar valori mai mari decât 0.` |
| MONEDA | Valoare în afara domeniului | `Rândul 6 (2026-10_OPS_BIR): moneda „GBP” nu este acceptată; valori permise: RON, EUR, USD.` |
| CC | Cod necunoscut | `Rândul 9 (2026-10_LOG_SRV): centrul de cost „LOG” nu există în nomenclator. Coduri valide: IT, MKT, OPS, HR, SAL.` |
| CAT | Cod necunoscut | `Rândul 2 (2026-10_IT_XX): categoria „XX” nu există în nomenclator. Coduri valide: HW, SW, SRV, TRN, MKT, BIR.` |
| DUP | Duplicat | `Rândul 22 (2026-10_IT_SW): înregistrare duplicat — cheia a apărut deja la rândul 1; rândul a fost ignorat.` |
| AI | — (Analize_AI) | `Analiza AI pentru HR a eșuat (HTTP 429 – limită de cereri). Calculele sunt salvate; analiza poate fi reluată.` Variante: `HTTP 401 – cheie API invalidă`, `serviciul AI nu a răspuns în timp util`, `răspunsul AI nu respectă formatul JSON așteptat` |
| F-JSON | — (email de eșec) | `Fișierul „x.json” nu este un JSON valid (verificați acoladele, ghilimelele și virgulele). Nicio înregistrare nu a fost importată.` |
| F-STRUCT | — (email de eșec) | `Fișierul „x.json” nu are structura așteptată: lista „inregistrari” lipsește sau este goală. Nicio înregistrare nu a fost importată.` |
| F-ALT | — (email de eșec) | `Importul fișierului „x.json” a eșuat la pasul Upsert_Realizat. Rândurile procesate până la eroare au rămas salvate; după corectare, reîncărcați fișierul (importul nu creează dubluri).` |
