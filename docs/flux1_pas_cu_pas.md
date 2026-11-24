# Flux 1 — `BG_Flux1_Cerere`, pas cu pas

> Pașii 0–8: Faza 4 (până la „În aprobare”). Pașii 9–12: Faza 5 (bucla de aprobare, „Aprobată” / „Respinsă”, angajarea în buget, timeout), adăugați **la finalul ramurii „Nu” a lui `Cond_Erori`**, după `Teams_In_Aprobare`.
> Denumirile din interfață sunt în română, cu originalul englezesc în paranteză. Dacă nu găsești o acțiune după numele românesc, caut-o după cel englezesc.
> Numele acțiunilor (`Cerere`, `HTTP_ANAF` …) **trebuie redenumite exact așa**, fiindcă expresiile le folosesc. Redenumirea: clic pe titlul acțiunii, în panoul din dreapta.

## Convenții folosite în ghid

- **Actualizare element** (*Update item*): **întotdeauna** apeși întâi **Advanced parameters → Clear all**, apoi adaugi din lista *Advanced parameters* doar câmpurile din tabelul pasului. Altfel câmpurile Alegere/Da-Nu precompletate suprascriu datele.

- **fx** = deschizi editorul de expresii (iconița *fx* sau „Inserare expresie”), lipești expresia, apoi **Adăugare** (*Add*).
- **Lipire directă** = lipești textul în câmp, fără fx. Fragmentele `@{...}` din text sunt expresii: după lipire și salvare, ar trebui să devină „jetoane” colorate. Dacă după **Salvare** (*Save*) rămân text simplu, șterge fragmentul și inserează expresia dintre acolade prin **fx**.
- **Notă BPMN**: pe acțiunile principale, adaugi din meniul **…** → **Adăugare notă** (*Add a note*) ID-ul elementului BPMN dat în ghid, ca fiecare acțiune să poată fi legată de diagramă.
- **Condiție** (*Condition*): în stânga pui expresia prin **fx**, operatorul **este egal cu** (*is equal to*), iar în dreapta tot prin **fx**, `true`. Așa compari un boolean cu un boolean, nu cu textul „true”.

## Harta fluxului

```
Trigger Forms → Get_response_details → Date_Formular → Cerere
→ Get_Config → Select_Config → cfg → 8 × Inițializare variabilă
→ Create_Cerere → Set_varIdCerere → Set_ID_Cerere → Log_Noua
→ Scope_Validare [ANAF: V1 V2 V2b W3 │ BNR: curs (+W4) │ V3 │ V4 │ Buget: V5 W1 W2]
→ Cond_Erori
     ├─ Da: Upd_Respinsa → Log_Respinsa → email → Teams → Terminate
     └─ Nu: Upd_In_Aprobare → Log_In_Aprobare → email → Teams
            → Necesita_CFO → Set_varAprobatori → Roluri
            → Do_until_Aprobare [Aprobare → Decizie → Append_Jurnal → Upd_Aprobari → Log_Pas
                                 → Cond_Aprobat_Pas (Nu: varRespins, varMotiv) → Increment_varIdx]
            → Cond_Respins
                 ├─ Da: Upd_Respinsa_Aprobare → Log → email → Teams → Terminate
                 └─ Nu: Upd_Aprobata → Get_Buget_Curent → Angajat_Nou → Ramas_Nou → Upd_Buget → Log → email → Teams
```

---

## Pasul 0 — Pregătiri

### 0.1 ID-urile Teams în Config
1. În Teams, în echipa BudgetGuard, la canalul în care vrei notificările (de exemplu **General**): **…** → **Obțineți linkul către canal** (*Get link to channel*) → **Copiere**.
2. Linkul arată așa:
   `https://teams.microsoft.com/l/channel/19%3aABC...%40thread.tacv2/General?groupId=1111-2222-...&tenantId=...`
   - **`teams_channel_id`** = bucata dintre `/channel/` și următorul `/`, **decodificată**: `%3a` → `:` și `%40` → `@`. Rezultă ceva de forma `19:ABC...@thread.tacv2`.
   - **`teams_team_id`** = valoarea lui `groupId=` (un GUID), fără `&tenantId...`.
3. Le scrii în lista **Config**, la cheile `teams_team_id` și `teams_channel_id`.

### 0.2 Config pentru echipa de 2
Verifică în **Config** că `aprobator_1..3`, `aprobator_cfo` și `email_echipa` au adrese ASE reale. `mod_demo` rămâne `false`.

---

## Pasul 1 — Formularul „BudgetGuard – Cerere de achiziție”

În **forms.office.com** → **Formular nou** (*New Form*). Formularul trebuie să fie **personal**, nu de grup, ca să apară direct în trigger.

**Setări** (… → *Settings*): **Doar persoanele din organizația mea pot răspunde** + **Înregistrați numele** (*Record name*). Așa vine emailul solicitantului în `responder`.

| # | Întrebare | Tip | Opțiuni / restricții | Obligatoriu |
|---|---|---|---|---|
| 1 | Titlul cererii | Text | — | da |
| 2 | Centru de cost | Alegere (*Choice*) | `IT – Tehnologie`, `MKT – Marketing`, `OPS – Operațiuni`, `HR – Resurse umane`, `SAL – Vânzări` | da |
| 3 | Categorie cheltuială | Alegere → **…** → **Listă verticală** (*Drop-down*) | `HW – Hardware`, `SW – Software/SaaS`, `SRV – Servicii`, `TRN – Training`, `MKT – Marketing`, `BIR – Birotică` | da |
| 4 | CUI furnizor (fără RO) | Text → **…** → **Restricții** → **Număr** | — | da |
| 5 | Valoare (fără TVA) | Text → Restricții → **Mai mare decât** `0` | — | da |
| 6 | Monedă | Alegere | `RON`, `EUR`, `USD` | da |
| 7 | Tip cheltuială | Alegere | `CAPEX`, `OPEX` | da |
| 8 | Data la care e necesară | Dată | — | da |
| 9 | Cheltuială recurentă? | Alegere | `Da`, `Nu` | nu |
| 10 | Urgență | Evaluare (*Rating*), 5 niveluri | — | nu |
| 11 | Justificare | Text → **Răspuns lung** (*Long answer*) | — | da |

> ⚠️ Opțiunile de la 2 și 3 trebuie să înceapă **exact** cu codul și un spațiu (`IT – …`), fiindcă fluxul extrage codul cu `first(split(..., ' '))`. Liniuța din mijloc poate fi orice caracter.

Cele **2 reguli de validare din Forms**: restricția *Număr* la CUI și *Mai mare decât 0* la valoare. Restul validărilor sunt în flux.

---

## Pasul 2 — Crearea fluxului în soluție

1. **make.powerautomate.com** → mediul `ase.ro (default)` → **Soluții** (*Solutions*) → **BudgetGuard**.
2. **+ Nou** (*New*) → **Automatizare** (*Automation*) → **Flux de cloud** (*Cloud flow*) → **Automatizat** (*Automated*).
3. Nume: `BG_Flux1_Cerere`. Trigger: caută **Microsoft Forms** → **Când este trimis un răspuns nou** (*When a new response is submitted*) → **Creare**.
4. **ID formular** (*Form Id*): alegi „BudgetGuard – Cerere de achiziție”. Notă BPMN: `Start_Cerere`.
5. **+** → **Microsoft Forms** → **Obțineți detaliile răspunsului** (*Get response details*). Numele rămâne `Get_response_details`.
   - **ID formular**: același formular.
   - **ID răspuns** (*Response Id*): din conținutul dinamic, **ID răspuns** al trigger-ului.

### 2.1 `Date_Formular` — răspunsurile brute
**+** → **Operații cu date** (*Data Operation*) → **Compunere** (*Compose*). O redenumești `Date_Formular`.

În **Intrări** (*Inputs*) tastezi scheletul de mai jos. Fiecare `«…»` îl **ștergi** și pui în loc, din conținutul dinamic al `Get_response_details`, întrebarea respectivă. **Ghilimelele rămân.**

```
{
  "titlu": "«Titlul cererii»",
  "centru_cost": "«Centru de cost»",
  "categorie": "«Categorie cheltuială»",
  "cui": "«CUI furnizor»",
  "valoare": "«Valoare (fără TVA)»",
  "moneda": "«Monedă»",
  "tip": "«Tip cheltuială»",
  "data_necesara": "«Data la care e necesară»",
  "recurenta": "«Cheltuială recurentă?»",
  "urgenta": "«Urgență»",
  "justificare": "«Justificare»"
}
```

De ce așa: întrebările din Forms au ID-uri generate (`r3a1b...`). Le mapezi **o singură dată** aici, iar restul fluxului citește doar `outputs('Date_Formular')?['cui']` etc.

### 2.2 `Cerere` — valorile normalizate
**+** → **Compunere**, redenumită `Cerere`. **Lipire directă**:

```
{
  "titlu": "@{trim(outputs('Date_Formular')?['titlu'])}",
  "cc": "@{first(split(outputs('Date_Formular')?['centru_cost'], ' '))}",
  "cat": "@{first(split(outputs('Date_Formular')?['categorie'], ' '))}",
  "cui": "@{trim(outputs('Date_Formular')?['cui'])}",
  "valoare": "@{replace(trim(outputs('Date_Formular')?['valoare']), ',', '.')}",
  "moneda": "@{outputs('Date_Formular')?['moneda']}",
  "tip": "@{outputs('Date_Formular')?['tip']}",
  "data_necesara": "@{formatDateTime(outputs('Date_Formular')?['data_necesara'], 'yyyy-MM-dd')}",
  "luna_buget": "@{formatDateTime(outputs('Date_Formular')?['data_necesara'], 'yyyy-MM')}",
  "cheie_buget": "@{concat(formatDateTime(outputs('Date_Formular')?['data_necesara'], 'yyyy-MM'), '_', first(split(outputs('Date_Formular')?['centru_cost'], ' ')), '_', first(split(outputs('Date_Formular')?['categorie'], ' ')))}",
  "recurenta": "@{if(equals(outputs('Date_Formular')?['recurenta'], 'Da'), 'true', 'false')}",
  "urgenta": "@{if(empty(outputs('Date_Formular')?['urgenta']), '0', outputs('Date_Formular')?['urgenta'])}",
  "justificare": "@{trim(outputs('Date_Formular')?['justificare'])}",
  "email": "@{outputs('Get_response_details')?['body/responder']}"
}
```

Toate valorile sunt șiruri. Conversia (`float`, `int`) se face acolo unde e nevoie. Așa JSON-ul rămâne valid indiferent de răspuns, iar ghilimelele sau rândurile noi din justificare nu-l strică.

### 2.3 Config într-un singur obiect
1. **+** → **SharePoint** → **Obținere elemente** (*Get items*), redenumită `Get_Config`. **Adresă site**: site-ul BudgetGuard. **Nume listă**: `Config`.
2. **+** → **Operații cu date** → **Selectare** (*Select*), redenumită `Select_Config`.
   - **Din** (*From*): **fx** → `outputs('Get_Config')?['body/value']`
   - La **Mapare** (*Map*) apeși iconița **Comutare la modul text** (*Switch to text mode*), apoi **fx** →
     ```
     concat('"', item()?['Title'], '":"', item()?['Valoare'], '"')
     ```
3. **+** → **Compunere**, redenumită `cfg`. **fx** →
   ```
   json(concat('{', join(body('Select_Config'), ','), '}'))
   ```
   De aici citești orice parametru, de exemplu `outputs('cfg')?['valoare_max_ron']`. Toate valorile vin ca text.

### 2.4 Variabilele
**+** → **Variabile** → **Inițializare variabilă** (*Initialize variable*), de 8 ori, **în ordinea asta**. Acțiunile nu trebuie redenumite.

| Nume | Tip | Valoare |
|---|---|---|
| `varErori` | Matrice (*Array*) | `[]` |
| `varAvert` | Matrice | `[]` |
| `varIdCerere` | Șir (*String*) | *(gol)* |
| `varCurs` | Float | `1` |
| `varDataCurs` | Șir | *(gol)* |
| `varRespins` | Boolean | **fx** → `false` |
| `varIdx` | Număr întreg (*Integer*) | `0` |
| `varAprobatori` | Matrice | `[]` |
| `varJurnal` | Șir | *(gol)* — adăugată în Faza 5 |
| `varMotiv` | Șir | *(gol)* — adăugată în Faza 5 |

`varRespins`, `varIdx`, `varAprobatori`, `varJurnal` și `varMotiv` sunt folosite abia în Faza 5. Le inițializezi acum, fiindcă inițializarea se poate face doar la nivelul de sus al fluxului, nu în condiții sau scope-uri.

### ✅ Punct de control A
**Salvare** → **Testare** (*Test*) → **Manual** → trimiți un răspuns de test în formular (orice valori valide). Fluxul rulează în fundal.
Din istoricul rulării, trimite-mi **Outputs** de la `Date_Formular`, `Cerere` și `cfg`. Mă interesează în special:
- formatul în care vine data din Forms (**confirmat 2026-11-21: `2026-11-30`**, ISO; ratingul vine ca `"3"`);
- dacă `cfg` are toate cele 16 chei.

---

## Pasul 3 — Înregistrarea cererii (BPMN `Task_Inregistrare`)

### 3.1 `Create_Cerere`
**+** → **SharePoint** → **Creare element** (*Create item*), redenumită `Create_Cerere`. Lista: `Cereri_Achizitie`. Apeși **Afișare toate** (*Show all*) ca să vezi toate coloanele.

| Câmp | Valoare (toate prin **fx**, cu excepția celor marcate) |
|---|---|
| ID_Cerere (Title) | `TEMP` *(text simplu)* |
| TitluCerere | `outputs('Cerere')?['titlu']` |
| CentruCost | `outputs('Cerere')?['cc']` |
| Categorie | `outputs('Cerere')?['cat']` |
| Luna_Buget | `outputs('Cerere')?['luna_buget']` |
| CUI | `outputs('Cerere')?['cui']` |
| Valoare | `float(outputs('Cerere')?['valoare'])` |
| Moneda Value | **Introduceți o valoare particularizată** (*Enter custom value*) → **fx** `outputs('Cerere')?['moneda']` |
| Tip Value | valoare particularizată → `outputs('Cerere')?['tip']` |
| Data_Necesara | `outputs('Cerere')?['data_necesara']` |
| Recurenta | `equals(outputs('Cerere')?['recurenta'], 'true')` |
| Urgenta | `int(outputs('Cerere')?['urgenta'])` |
| Justificare | `outputs('Cerere')?['justificare']` |
| Status Value | **Nouă** *(din listă)* |
| Solicitant_Email | `outputs('Cerere')?['email']` |
| Data_Cerere | `utcNow()` |

Restul câmpurilor rămân goale. Notă BPMN: `Task_Inregistrare`.

### 3.2 ID-ul `PR-2026-0042`
1. **+** → **Setare variabilă** (*Set variable*), redenumită `Set_varIdCerere`. Nume: `varIdCerere`. Valoare **fx**:
   ```
   concat('PR-', formatDateTime(utcNow(), 'yyyy'), '-', formatNumber(outputs('Create_Cerere')?['body/ID'], '0000'))
   ```
2. **+** → **SharePoint** → **Actualizare element** (*Update item*), redenumită `Set_ID_Cerere`. Lista `Cereri_Achizitie`.
   - **Id**: **fx** `outputs('Create_Cerere')?['body/ID']`
   - **ID_Cerere (Title)**: **fx** `variables('varIdCerere')`
   - ⚠️ **Advanced parameters → Clear all** (*Golire totală*). Designerul nou precompletează câmpurile Alegere și Da/Nu cu valoarea implicită (Moneda = RON, Recurenta = No …), iar *Update item* le-ar suprascrie. În `Set_ID_Cerere` trebuie să rămână **doar Id și ID_Cerere**. (Problemă observată la testul din 2026-11-21: Moneda USD → RON.)

> Cele 22 de cereri istorice au ID-urile PR-2026-0001…0022, iar elementele SharePoint au ID 1…22. Prima cerere nouă primește, așadar, `PR-2026-0023`. Nu există coliziuni.

### 3.3 `Log_Noua`, jurnalul
**+** → **SharePoint** → **Creare element**, redenumită `Log_Noua`. Lista `Istoric_Stari`.

| Câmp | Valoare |
|---|---|
| Referinta (Title) | **fx** `variables('varIdCerere')` |
| Flux Value | **F1** |
| Stare_Veche | `—` |
| Stare_Noua | `Nouă` |
| Actor | **fx** `outputs('Cerere')?['email']` |
| Data_Ora | **fx** `utcNow()` |
| Comentariu | `Cerere înregistrată din formular.` |

Folosești același model de jurnalizare la fiecare tranziție, cu valorile din tabelele de mai jos.

### ✅ Punct de control B
Salvezi, trimiți un răspuns nou. În `Cereri_Achizitie` trebuie să apară elementul `PR-2026-00xx` cu Status **Nouă**, iar în `Istoric_Stari` linia de jurnal.

---

## Pasul 4 — `Scope_Validare` (îmbogățire și validare)

**+** → **Control** → **Domeniu** (*Scope*), redenumit `Scope_Validare`. **Toate** acțiunile din pașii 4.1–4.5 se pun **în interiorul** lui.

Fiecare regulă e o **Condiție** cu o singură acțiune pe ramura **True**: **Adăugare la variabila matrice** (*Append to array variable*), cu `varErori` (pentru V…) sau `varAvert` (pentru W…). Ramura **False** rămâne goală.
Mesajele de mai jos sunt **catalogul complet al Fluxului 1**. Le găsești și în `docs/expresii.md`.

### 4.1 ANAF (BPMN `Task_ANAF`)
1. **HTTP** → **HTTP**, redenumită `HTTP_ANAF`.
   - **Metodă**: `POST`. **URI**: `https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva`
   - **Antete** (*Headers*): `Content-Type` = `application/json`
   - **Corp** (*Body*), lipire directă:
     ```
     [{"cui": @{int(outputs('Cerere')?['cui'])}, "data": "@{formatDateTime(utcNow(), 'yyyy-MM-dd')}"}]
     ```
   - **Setări** (*Settings*): **Politică de reîncercare** (*Retry policy*) = **Exponențial** (*Exponential*), număr `3`, interval `PT10S`. **Expirare acțiune** (*Action timeout*) = `PT1M`.
2. **Operații cu date** → **Analizare JSON** (*Parse JSON*), redenumită `Parse_ANAF`.
   - **Conținut**: **fx** `body('HTTP_ANAF')`
   - **Schemă**: lipești conținutul din `schemas/anaf_v9.json`.
   - ⚠️ **Settings → Run after** → `HTTP_ANAF`: bifezi **Is successful** și **Has failed**. ANAF răspunde cu **HTTP 404** când niciun CUI din cerere nu există, dar body-ul e JSON valid (`{"found":[],"notFound":[99999999]}`). Fără această setare, fluxul se oprește la V1. (Verificat pe 2026-11-22.)
3. **Compunere** `Firma`: **fx** `first(body('Parse_ANAF')?['found'])`. Dacă CUI-ul nu există, rezultatul e `null`.
4. **Compunere** `Denumire`: **fx** `coalesce(outputs('Firma')?['date_generale']?['denumire'], '')`

| Condiție (nume) | Stânga (fx) = `true` | Matrice | Valoare de adăugat (fx) |
|---|---|---|---|
| `Cond_V1` | `empty(outputs('Firma'))` | varErori | `concat('[V1] CUI ', outputs('Cerere')?['cui'], ' nu figurează în baza ANAF.')` |
| `Cond_V2` | `equals(outputs('Firma')?['stare_inactiv']?['statusInactivi'], true)` | varErori | `concat('[V2] Furnizorul ', outputs('Denumire'), ' (CUI ', outputs('Cerere')?['cui'], ') este declarat inactiv fiscal.')` |
| `Cond_V2b` | `and(not(empty(outputs('Firma'))), not(empty(outputs('Firma')?['stare_inactiv']?['dataRadiere'])))` | varErori | `concat('[V2b] Furnizorul ', outputs('Denumire'), ' (CUI ', outputs('Cerere')?['cui'], ') este radiat din data de ', outputs('Firma')?['stare_inactiv']?['dataRadiere'], '.')` |
| `Cond_W3` | `equals(outputs('Firma')?['inregistrare_scop_Tva']?['scpTVA'], false)` | varAvert | `concat('[W3] Furnizorul ', outputs('Denumire'), ' nu este înregistrat în scopuri de TVA.')` |

Dacă CUI-ul nu există, `Firma` e `null`, iar V2, V2b și W3 dau automat `false`. Apare doar mesajul V1.

### 4.2 BNR și Valoare_RON (BPMN `Task_BNR`)
1. **Condiție** `Cond_Moneda`: stânga **fx** `equals(outputs('Cerere')?['moneda'], 'RON')`, **este egal cu**, dreapta **fx** `false`.
2. Pe ramura **True** (moneda nu e RON):
   1. **HTTP**, redenumită `HTTP_BNR`. **Metodă** `GET`, **URI** `https://curs.bnr.ro/nbrfxrates.xml`. Aceleași setări de retry și timeout ca la ANAF.
   2. **Condiție** `Cond_BNR_OK`: **fx** `equals(actions('HTTP_BNR')?['status'], 'Succeeded')` = `true`.
      Apoi, pe `Cond_BNR_OK` → **Setări** → **Rulare după** (*Run after*) → `HTTP_BNR`: bifezi **are succes**, **a eșuat** și **a expirat** (*is successful, has failed, has timed out*).
   3. `Cond_BNR_OK` → **True**:
      - **Setare variabilă** `varCurs` (redenumită `Set_Curs_BNR`), **fx**:
        ```
        float(xpath(xml(body('HTTP_BNR')), concat('string(//*[local-name()=''Rate''][@currency=''', outputs('Cerere')?['moneda'], '''])')))
        ```
      - **Setare variabilă** `varDataCurs` (redenumită `Set_Data_Curs`), **fx**:
        ```
        xpath(xml(body('HTTP_BNR')), 'string(//*[local-name()=''Cube'']/@date)')
        ```
   4. `Cond_BNR_OK` → **False** (BNR nu a răspuns):
      - **Setare variabilă** `varCurs` (redenumită `Set_Curs_Fallback`), **fx**: `float(outputs('cfg')?[concat('curs_fallback_', outputs('Cerere')?['moneda'])])`
      - **Setare variabilă** `varDataCurs` = `rezervă Config`
      - **Adăugare la variabila matrice** `varAvert`, **fx**:
        `concat('[W4] Cursul BNR nu a putut fi obținut; s-a folosit cursul de rezervă din Config (1 ', outputs('Cerere')?['moneda'], ' = ', string(variables('varCurs')), ' RON).')`
3. **După** `Cond_Moneda` (în afara ei, dar tot în scope), **Compunere** `Valoare_RON`, **fx**:
   ```
   float(formatNumber(mul(float(outputs('Cerere')?['valoare']), variables('varCurs')), '0.00', 'en-US'))
   ```
4. **Condiție** `Cond_V3`: **fx** `or(lessOrEquals(outputs('Valoare_RON'), 0), greater(outputs('Valoare_RON'), float(outputs('cfg')?['valoare_max_ron'])))` = `true` → `varErori`:
   ```
   concat('[V3] Valoarea de ', formatNumber(outputs('Valoare_RON'), 'N2', 'ro-RO'), ' RON este în afara intervalului acceptat: peste 0 și cel mult ', formatNumber(float(outputs('cfg')?['valoare_max_ron']), 'N0', 'ro-RO'), ' RON.')
   ```

### 4.3 Data necesară (BPMN `Task_VerificaBuget`)
**Condiție** `Cond_V4`: **fx**
```
less(ticks(outputs('Cerere')?['data_necesara']), ticks(formatDateTime(addDays(utcNow(), int(outputs('cfg')?['zile_min_avans'])), 'yyyy-MM-dd')))
```
= `true` → `varErori`:
```
concat('[V4] Data necesară ', formatDateTime(outputs('Cerere')?['data_necesara'], 'dd.MM.yyyy'), ' este prea apropiată. Data minimă acceptată este ', formatDateTime(addDays(utcNow(), int(outputs('cfg')?['zile_min_avans'])), 'dd.MM.yyyy'), ' (', outputs('cfg')?['zile_min_avans'], ' zile de la depunere).')
```

### 4.4 Bugetul (BPMN `Task_VerificaBuget`)
1. **SharePoint** → **Obținere elemente**, redenumită `Get_Buget`. Lista `Bugete`.
   - **Interogare de filtrare** (*Filter Query*), lipire directă: `Title eq '@{outputs('Cerere')?['cheie_buget']}'`
   - **Număr maxim** (*Top Count*): `1`
2. **Compunere** `Buget`: **fx** `first(outputs('Get_Buget')?['body/value'])`
3. **Compunere** `Peste_Buget`: **fx**
   ```
   greater(outputs('Valoare_RON'), coalesce(outputs('Buget')?['Ramas_RON'], 1000000000))
   ```
   `coalesce` evită eroarea când nu există buget. Cazul acela e tratat separat de V5.

| Condiție | Stânga (fx) = `true` | Matrice | Valoare de adăugat (fx) |
|---|---|---|---|
| `Cond_V5` | `empty(outputs('Buget'))` | varErori | `concat('[V5] Nu există buget pentru ', outputs('Cerere')?['cc'], '/', outputs('Cerere')?['cat'], ' în ', outputs('Cerere')?['luna_buget'], '.')` |
| `Cond_W1` | `outputs('Peste_Buget')` | varAvert | `concat('[W1] Valoarea de ', formatNumber(outputs('Valoare_RON'), 'N2', 'ro-RO'), ' RON depășește bugetul rămas de ', formatNumber(outputs('Buget')?['Ramas_RON'], 'N2', 'ro-RO'), ' RON pentru ', outputs('Cerere')?['cheie_buget'], '. Se solicită și aprobarea CFO.')` |
| `Cond_W2` | `and(equals(outputs('Cerere')?['cat'], 'HW'), equals(outputs('Cerere')?['tip'], 'OPEX'), greaterOrEquals(outputs('Valoare_RON'), float(outputs('cfg')?['prag_capex_ron'])))` | varAvert | `concat('[W2] Hardware de ', formatNumber(outputs('Valoare_RON'), 'N2', 'ro-RO'), ' RON încadrat ca OPEX (prag ', outputs('cfg')?['prag_capex_ron'], ' RON): posibilă imobilizare — verificați încadrarea CAPEX.')` |

> V5 acoperă și combinațiile nebugetate (de exemplu IT/MKT) și lunile fără buget (după 2027-03).

### 4.5 Ordinea în scope
`HTTP_ANAF → Parse_ANAF → Firma → Denumire → Cond_V1 → Cond_V2 → Cond_V2b → Cond_W3 → Cond_Moneda → Valoare_RON → Cond_V3 → Cond_V4 → Get_Buget → Buget → Peste_Buget → Cond_V5 → Cond_W1 → Cond_W2`

Toate validările rulează până la capăt, chiar dacă prima a picat. Solicitantul primește **toate** motivele într-un singur email, nu pe rând.

---

## Pasul 5 — `Cond_Erori` (BPMN `Gateway_DateValide`)

**După** `Scope_Validare` (în afara lui): **Condiție** `Cond_Erori`, **fx** `greater(length(variables('varErori')), 0)` = `true`.

---

## Pasul 6 — Ramura **True**: respinsă la validare

### 6.1 `Upd_Respinsa` (BPMN `Task_RespinsaValidare`)
**Actualizare element** în `Cereri_Achizitie`, **Id** = `outputs('Create_Cerere')?['body/ID']`:

| Câmp | Valoare (fx) |
|---|---|
| ID_Cerere (Title) | `variables('varIdCerere')` |
| Furnizor_ANAF | `outputs('Denumire')` |
| Curs_BNR | `variables('varCurs')` |
| Valoare_RON | `outputs('Valoare_RON')` |
| Avertismente | `join(variables('varAvert'), decodeUriComponent('%0A'))` |
| Status Value | **Respinsă** *(din listă)* |
| Motiv_Respingere | `join(variables('varErori'), decodeUriComponent('%0A'))` |
| Data_Finalizare | `utcNow()` |

### 6.2 `Log_Respinsa`
Creare element în `Istoric_Stari`: Title `variables('varIdCerere')`, Flux **F1**, Stare_Veche `Nouă`, Stare_Noua `Respinsă`, Actor `BudgetGuard (validare automată)`, Data_Ora `utcNow()`, Comentariu **fx** `join(variables('varErori'), '; ')`.

### 6.3 Email (BPMN `Send_NotifRespValidare`)
1. **Compunere** `Html_Respinsa`, cu lipire directă:
```html
<div style="font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#222;max-width:640px">
  <div style="background:#b42318;color:#fff;padding:12px 16px;font-size:16px;font-weight:600">
    BudgetGuard · Cerere respinsă la validare
  </div>
  <div style="padding:16px;border:1px solid #ddd;border-top:none">
    <p>Bună ziua,</p>
    <p>Cererea <b>@{variables('varIdCerere')}</b> – „@{outputs('Cerere')?['titlu']}” nu a trecut validarea automată și a fost <b>respinsă</b>.</p>
    <p style="margin-bottom:4px"><b>Motive:</b></p>
    <ul style="margin-top:0;color:#b42318"><li>@{join(variables('varErori'), '</li><li>')}</li></ul>
    <table style="border-collapse:collapse;font-size:13px">
      <tr><td style="padding:4px 12px 4px 0;color:#666">Centru de cost / categorie</td><td>@{outputs('Cerere')?['cc']} / @{outputs('Cerere')?['cat']}</td></tr>
      <tr><td style="padding:4px 12px 4px 0;color:#666">CUI furnizor</td><td>@{outputs('Cerere')?['cui']} @{outputs('Denumire')}</td></tr>
      <tr><td style="padding:4px 12px 4px 0;color:#666">Valoare</td><td>@{outputs('Cerere')?['valoare']} @{outputs('Cerere')?['moneda']}</td></tr>
      <tr><td style="padding:4px 12px 4px 0;color:#666">Data necesară</td><td>@{formatDateTime(outputs('Cerere')?['data_necesara'], 'dd.MM.yyyy')}</td></tr>
    </table>
    <p>Poți corecta datele și trimite o cerere nouă din formular.</p>
    <p style="font-size:12px;color:#888">Mesaj automat BudgetGuard · Vestra Retail SRL · @{convertTimeZone(utcNow(), 'UTC', 'GTB Standard Time', 'dd.MM.yyyy HH:mm')}</p>
  </div>
</div>
```
2. **Gmail** → **Send email (V2)**, redenumită `Email_Respinsa`. Conexiunea se face cu contul `@stud.ase.ro` (Google Workspace). *Office 365 Outlook* nu are cutie poștală la ASE, iar conectorul *Mail* e restricționat (401). Corpul e trimis ca HTML implicit (Gmail V2 nu are opțiunea Is HTML).
   - **Către**: **fx** `outputs('Cerere')?['email']`
   - **Subiect**, lipire directă: `[BudgetGuard] @{variables('varIdCerere')} – cerere respinsă la validare`
   - **Corp**: din conținutul dinamic, **Ieșiri** (*Outputs*) de la `Html_Respinsa`. Nu lipi HTML-ul direct în editorul de email, fiindcă editorul vizual îl strică.
   - Pe acțiunea Teams care urmează (`Html_Teams_Respinsa`): **Settings → Run after** → emailul: **Is successful** + **Has failed**. O eroare de email nu trebuie să blocheze Teams și finalizarea.

### 6.4 Teams
1. **Compunere** `Html_Teams_Respinsa`, lipire directă:
```html
<p>🔴 <b>@{variables('varIdCerere')}</b> – @{outputs('Cerere')?['titlu']}</p>
<p>Nouă → <b>Respinsă</b> (validare automată) · @{outputs('Cerere')?['cc']}/@{outputs('Cerere')?['cat']} · @{outputs('Cerere')?['valoare']} @{outputs('Cerere')?['moneda']}</p>
<p>@{join(variables('varErori'), '<br>')}</p>
<p><a href="@{outputs('Create_Cerere')?['body/{Link}']}">Deschide cererea în SharePoint</a></p>
```
2. **Microsoft Teams** → **Postați un mesaj într-un chat sau canal** (*Post message in a chat or channel*), redenumită `Teams_Respinsa`.
   - **Postare ca** (*Post as*): **Flow bot**. **Postare în** (*Post in*): **Canal** (*Channel*).
   - **Echipă** (*Team*): **Introduceți o valoare particularizată** → **fx** `outputs('cfg')?['teams_team_id']`
   - **Canal** (*Channel*): valoare particularizată → **fx** `outputs('cfg')?['teams_channel_id']`
   - **Mesaj**: **Ieșiri** de la `Html_Teams_Respinsa`.
   > Dacă valoarea particularizată dă eroare, alege echipa și canalul din listă și spune-mi. Notez abaterea.

### 6.5 Oprire (BPMN `End_RespinsaValidare`)
**Control** → **Terminare** (*Terminate*), redenumită `Terminate_Respinsa`. **Stare**: **Reușit** (*Succeeded*). Cererea a fost procesată corect, chiar dacă rezultatul e o respingere.

---

## Pasul 7 — Ramura **False**: în aprobare

### 7.1 `Upd_In_Aprobare` (BPMN `Task_StatusInAprobare`)
**Actualizare element** în `Cereri_Achizitie`, **Id** = `outputs('Create_Cerere')?['body/ID']`:

| Câmp | Valoare (fx) |
|---|---|
| ID_Cerere (Title) | `variables('varIdCerere')` |
| Furnizor_ANAF | `outputs('Denumire')` |
| Platitor_TVA | `equals(outputs('Firma')?['inregistrare_scop_Tva']?['scpTVA'], true)` |
| Curs_BNR | `variables('varCurs')` |
| Valoare_RON | `outputs('Valoare_RON')` |
| Peste_Buget | `outputs('Peste_Buget')` |
| Avertismente | `join(variables('varAvert'), decodeUriComponent('%0A'))` |
| Status Value | **În aprobare** *(din listă)* |

### 7.2 `Log_In_Aprobare`
Creare element în `Istoric_Stari`: Title `variables('varIdCerere')`, Flux **F1**, Stare_Veche `Nouă`, Stare_Noua `În aprobare`, Actor `BudgetGuard (validare automată)`, Data_Ora `utcNow()`, Comentariu **fx**:
```
concat('Validare OK. Valoare_RON ', string(outputs('Valoare_RON')), if(equals(outputs('Cerere')?['moneda'], 'RON'), '', concat(' (curs BNR ', outputs('Cerere')?['moneda'], ' ', string(variables('varCurs')), ' din ', variables('varDataCurs'), ')')), '. Avertismente: ', string(length(variables('varAvert'))), '.')
```

### 7.3 Email (BPMN `Send_NotifInAprobare`)
1. **Compunere** `Html_In_Aprobare`, lipire directă:
```html
<div style="font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#222;max-width:640px">
  <div style="background:#1d4ed8;color:#fff;padding:12px 16px;font-size:16px;font-weight:600">
    BudgetGuard · Cerere înregistrată – în aprobare
  </div>
  <div style="padding:16px;border:1px solid #ddd;border-top:none">
    <p>Bună ziua,</p>
    <p>Cererea <b>@{variables('varIdCerere')}</b> – „@{outputs('Cerere')?['titlu']}” a trecut validarea automată și a intrat în <b>circuitul de aprobare</b>.</p>
    <table style="border-collapse:collapse;font-size:13px">
      <tr><td style="padding:4px 12px 4px 0;color:#666">Furnizor (ANAF)</td><td>@{outputs('Denumire')} · CUI @{outputs('Cerere')?['cui']}</td></tr>
      <tr><td style="padding:4px 12px 4px 0;color:#666">Valoare</td><td>@{outputs('Cerere')?['valoare']} @{outputs('Cerere')?['moneda']} × curs @{variables('varCurs')} = <b>@{formatNumber(outputs('Valoare_RON'), 'N2', 'ro-RO')} RON</b></td></tr>
      <tr><td style="padding:4px 12px 4px 0;color:#666">Buget @{outputs('Cerere')?['cheie_buget']}</td><td>rămas @{formatNumber(outputs('Buget')?['Ramas_RON'], 'N2', 'ro-RO')} RON din @{formatNumber(outputs('Buget')?['Buget_RON'], 'N2', 'ro-RO')} RON</td></tr>
      <tr><td style="padding:4px 12px 4px 0;color:#666">Tip / data necesară</td><td>@{outputs('Cerere')?['tip']} · @{formatDateTime(outputs('Cerere')?['data_necesara'], 'dd.MM.yyyy')}</td></tr>
    </table>
    <p style="margin-bottom:4px"><b>Avertismente:</b></p>
    @{if(empty(variables('varAvert')), '<p style="margin-top:0;color:#15803d">Niciun avertisment.</p>', concat('<ul style="margin-top:0;color:#b45309"><li>', join(variables('varAvert'), '</li><li>'), '</li></ul>'))}
    <p>Vei primi un email la fiecare decizie a aprobatorilor.</p>
    <p style="font-size:12px;color:#888">Mesaj automat BudgetGuard · Vestra Retail SRL · @{convertTimeZone(utcNow(), 'UTC', 'GTB Standard Time', 'dd.MM.yyyy HH:mm')}</p>
  </div>
</div>
```
2. **Gmail → Send email (V2)**, redenumită `Email_In_Aprobare`: **Către** `outputs('Cerere')?['email']`, **Subiect** `[BudgetGuard] @{variables('varIdCerere')} – în aprobare`, **Corp** = **Ieșiri** de la `Html_In_Aprobare`.

### 7.4 Teams
**Compunere** `Html_Teams_In_Aprobare`:
```html
<p>🟡 <b>@{variables('varIdCerere')}</b> – @{outputs('Cerere')?['titlu']}</p>
<p>Nouă → <b>În aprobare</b> · @{outputs('Cerere')?['cc']}/@{outputs('Cerere')?['cat']} · @{formatNumber(outputs('Valoare_RON'), 'N2', 'ro-RO')} RON@{if(outputs('Peste_Buget'), ' · ⚠️ peste buget', '')}</p>
<p><a href="@{outputs('Create_Cerere')?['body/{Link}']}">Deschide cererea în SharePoint</a></p>
```
Apoi `Teams_In_Aprobare`, cu aceleași setări ca la 6.4 și **Mesaj** = Ieșiri de la `Html_Teams_In_Aprobare`.

**Aici se oprește Faza 4.** Faza 5 continuă cu pasul 9, după `Teams_In_Aprobare`.

---

## Pasul 8 — Testele Fazei 4

Data minimă acceptată = azi + 5 zile. Pentru un test din 20.11.2026, alege o dată **≥ 25.11.2026**.

| Test | Date în formular | Rezultat așteptat |
|---|---|---|
| **T4-1** cale fericită RON | IT / SW, CUI `2816464`, 5000 RON, OPEX, 30.11.2026 | `PR-2026-0023`, **În aprobare**, Furnizor_ANAF = DEDEMAN SRL, Curs 1, Valoare_RON 5000, fără avertismente, email albastru + Teams |
| **T4-2** EUR | MKT / SW, CUI `14399840`, 2000 EUR, OPEX, 10.12.2026 | **În aprobare**, Curs_BNR = cursul zilei (~5,3), Valoare_RON ≈ 10.700, Luna_Buget 2026-12, denumirea DANTE INTERNATIONAL SA |
| **T4-3** CUI inexistent | IT / SW, CUI `99999999`, 1000 RON, 30.11.2026 | **Respinsă**, Motiv `[V1] CUI 99999999 nu figurează în baza ANAF.`, email roșu + Teams, Data_Finalizare completat |
| T4-4 (opțional) erori multiple | IT / **MKT**, CUI `99999999`, 1000 RON, data = **mâine** | **Respinsă** cu 3 motive într-un singur email: V1, V4, V5 |
| T4-5 (opțional) avertismente | OPS / HW, CUI `11111110`, 3000 RON, **OPEX**, 30.11.2026 | **În aprobare** cu W2 (CAPEX) și W3 (neplătitor TVA) |

După fiecare test, verifici `Istoric_Stari`: 2 linii pe cerere (`—`→Nouă, Nouă→În aprobare/Respinsă).

**Faza 4 e gata când T4-1, T4-2 și T4-3 trec.** Pentru fiecare, fă o captură cu elementul din listă și cu emailul.

---

# Partea a doua — Faza 5: aprobări, decizie finală, angajarea în buget

## Pasul 9 — Pregătiri pentru Faza 5

### 9.1 Două variabile noi
Sus, după `varAprobatori`, mai adaugi 2 × **Inițializare variabilă** (tabelul din 2.4): `varJurnal` (Șir, gol) și `varMotiv` (Șir, gol).

### 9.2 Config
- `aprobator_1`, `aprobator_2`, `aprobator_3`, `aprobator_cfo` = adrese **din tenantul ASE** (contul tău și/sau al colegului). Approvals nu poate atribui o aprobare unei adrese din afara organizației: acțiunea eșuează.
- `mod_demo` = `false`. Îl comuți pe `true` doar la testul TC-F1-10.

### 9.3 Unde primești aprobările
Cutiile ASE sunt pe Gmail, așa că emailul de aprobare ajunge, dar **butoanele Aprobare/Respingere nu apar în Gmail**. Răspunzi dintr-unul din locurile:
- **Teams** → aplicația **Aprobări** (*Approvals*) din bara din stânga (o adaugi din **…** dacă nu e acolo). Cel mai comod.
- **make.powerautomate.com** → **Elemente de acțiune** (*Action items*) → **Aprobări** (*Approvals*) → **Primite** (*Received*).
- Linkul din emailul primit de la Power Automate.

> Prima acțiune Approvals dintr-un mediu instalează în fundal soluția de aprobări în Dataverse. Dacă primești o eroare de tipul *„approvals are being provisioned”*, aștepți 5–10 minute și reiei rularea.

---

## Pasul 10 — Lista de aprobatori (în ramura **Nu**, după `Teams_In_Aprobare`)

### 10.1 `Necesita_CFO`
**Compunere**, **fx**:
```
or(outputs('Peste_Buget'), greater(outputs('Valoare_RON'), float(outputs('cfg')?['prag_cfo_ron'])))
```
CFO intră în circuit dacă cererea **depășește bugetul rămas (W1)** sau **valoarea depășește `prag_cfo_ron`** (100.000 RON). Al doilea criteriu completează §5.4.3 și folosește cheia `prag_cfo_ron` deja existentă în Config. Notă BPMN: `Gateway_PesteBuget`.

### 10.2 `Set_varAprobatori`
**Setare variabilă** `varAprobatori`, **fx**:
```
if(equals(outputs('cfg')?['mod_demo'], 'true'), createArray(outputs('cfg')?['email_bcc']), if(outputs('Necesita_CFO'), createArray(outputs('cfg')?['aprobator_1'], outputs('cfg')?['aprobator_2'], outputs('cfg')?['aprobator_3'], outputs('cfg')?['aprobator_cfo']), createArray(outputs('cfg')?['aprobator_1'], outputs('cfg')?['aprobator_2'], outputs('cfg')?['aprobator_3'])))
```

### 10.3 `Roluri`
**Compunere**, **fx**:
```
if(equals(outputs('cfg')?['mod_demo'], 'true'), createArray('Aprobator unic (demo)'), createArray('Manager centru de cost', 'Controlling', 'Director financiar', 'CFO'))
```
`Roluri` are aceeași ordine ca `varAprobatori`, deci `outputs('Roluri')[variables('varIdx')]` dă rolul pasului curent.

---

## Pasul 11 — Bucla `Do_until_Aprobare` (BPMN `User_Aprobare1…4`, `Gateway_Aprobat1…4`, `Timer_Aprobare1…4`)

**+** → **Control** → **Efectuare până când** (*Do until*), redenumită `Do_until_Aprobare`.
- **Condiția de oprire** (*Loop until*): stânga **fx**
  ```
  or(variables('varRespins'), greaterOrEquals(variables('varIdx'), length(variables('varAprobatori'))))
  ```
  **este egal cu**, dreapta **fx** `true`.
- **Modificare limite** (*Change limits*) / în **Setări**: **Număr** (*Count*) `10`, **Expirare** (*Timeout*) `P30D`.
- Notă: *„Bucla înlocuiește cele 4 user tasks secvențiale din BPMN (User_Aprobare1…4); vezi Annotation_Aprobatori.”*

Bucla verifică condiția **după** fiecare iterație. Lista are mereu cel puțin un aprobator, deci prima iterație e corectă.

Toate acțiunile de la 11.1 la 11.7 sunt **în interiorul** buclei, în ordinea asta.

### 11.1 `Aprobare`
**Aprobări** (*Approvals*) → **Pornire și așteptare aprobare** (*Start and wait for an approval*), redenumită `Aprobare`.
- **Tip aprobare** (*Approval type*): **Aprobare/Respingere – primul care răspunde** (*Approve/Reject – First to respond*).
- **Titlu** (*Title*), lipire directă:
  ```
  @{variables('varIdCerere')} · aprobare @{add(variables('varIdx'), 1)}/@{length(variables('varAprobatori'))} · @{outputs('Cerere')?['titlu']}
  ```
- **Atribuit lui** (*Assigned to*): **fx** `variables('varAprobatori')[variables('varIdx')]`
- **Detalii** (*Details*), lipire directă (Markdown):
  ```
  **Pas @{add(variables('varIdx'), 1)} din @{length(variables('varAprobatori'))}: @{outputs('Roluri')[variables('varIdx')]}**

  - **Solicitant:** @{outputs('Cerere')?['email']}
  - **Centru de cost / categorie:** @{outputs('Cerere')?['cc']} / @{outputs('Cerere')?['cat']} · luna @{outputs('Cerere')?['luna_buget']}
  - **Furnizor:** @{outputs('Denumire')} (CUI @{outputs('Cerere')?['cui']})
  - **Valoare:** @{outputs('Cerere')?['valoare']} @{outputs('Cerere')?['moneda']} = **@{formatNumber(outputs('Valoare_RON'), 'N2', 'ro-RO')} RON**
  - **Buget rămas la depunere:** @{formatNumber(outputs('Buget')?['Ramas_RON'], 'N2', 'ro-RO')} RON din @{formatNumber(outputs('Buget')?['Buget_RON'], 'N2', 'ro-RO')} RON
  - **Tip / data necesară:** @{outputs('Cerere')?['tip']} · @{formatDateTime(outputs('Cerere')?['data_necesara'], 'dd.MM.yyyy')}
  - **Avertismente:** @{if(empty(variables('varAvert')), 'niciunul', join(variables('varAvert'), ' · '))}

  **Justificare:** @{outputs('Cerere')?['justificare']}

  **Decizii anterioare:**

  @{if(empty(variables('varJurnal')), '_niciuna (primul pas)_', variables('varJurnal'))}
  ```
- **Link element** (*Item link*): **fx** `outputs('Create_Cerere')?['body/{Link}']`. **Descriere link element**: `Deschide cererea în SharePoint`.
- **Solicitant** (*Requestor*), dacă apare în parametrii avansați: **fx** `outputs('Cerere')?['email']`.
- **Setări** → **Expirare acțiune** (*Action timeout*): `P7D`. Notă BPMN: `User_Aprobare1…4` + `Timer_Aprobare1…4`.

### 11.2 `Decizie` — rezultatul pasului, normalizat
**Compunere**, redenumită `Decizie`. **Lipire directă**:
```
{
  "pas": "@{add(variables('varIdx'), 1)}/@{length(variables('varAprobatori'))}",
  "rol": "@{outputs('Roluri')[variables('varIdx')]}",
  "rezultat": "@{if(equals(actions('Aprobare')?['outputs']?['body']?['outcome'], 'Approve'), 'Aprobat', if(equals(actions('Aprobare')?['status'], 'TimedOut'), 'Expirat', 'Respins'))}",
  "aprobator": "@{coalesce(actions('Aprobare')?['outputs']?['body']?['responses']?[0]?['responder']?['email'], variables('varAprobatori')[variables('varIdx')])}",
  "comentariu": "@{coalesce(actions('Aprobare')?['outputs']?['body']?['responses']?[0]?['comments'], '')}",
  "data": "@{convertTimeZone(utcNow(), 'UTC', 'GTB Standard Time', 'dd.MM.yyyy HH:mm')}"
}
```
⚠️ **Setări → Rulare după** (*Run after*) → `Aprobare`: bifezi **are succes** și **a expirat** (*is successful*, *has timed out*). Așa, o aprobare expirată după 7 zile ajunge aici ca rezultat `Expirat`, în loc să oprească fluxul.

De ce `actions('Aprobare')?['outputs']?['body']` și nu `body('Aprobare')`: la o acțiune expirată, body-ul lipsește. Navigarea cu `?` dă `null`, fără eroare.

### 11.3 `Append_Jurnal`
**Adăugare la variabila șir** (*Append to string variable*), `varJurnal`, **fx**:
```
concat('- Pas ', outputs('Decizie')?['pas'], ' (', outputs('Decizie')?['rol'], '): ', outputs('Decizie')?['rezultat'], ' – ', outputs('Decizie')?['aprobator'], ' – ', outputs('Decizie')?['data'], if(empty(outputs('Decizie')?['comentariu']), '', concat(' – „', outputs('Decizie')?['comentariu'], '”')), decodeUriComponent('%0A'))
```

### 11.4 `Upd_Aprobari`
**Actualizare element** în `Cereri_Achizitie` (cu **Clear all** pe parametrii avansați):

| Câmp | Valoare (fx) |
|---|---|
| Id | `outputs('Create_Cerere')?['body/ID']` |
| ID_Cerere (Title) | `variables('varIdCerere')` |
| Aprobari | `variables('varJurnal')` |

Jurnalul se vede în listă imediat după fiecare decizie, nu doar la final.

### 11.5 `Log_Pas`
**Creare element** în `Istoric_Stari`:

| Câmp | Valoare |
|---|---|
| Referinta (Title) | **fx** `variables('varIdCerere')` |
| Flux Value | **F1** |
| Stare_Veche | `În aprobare` |
| Stare_Noua | `În aprobare` |
| Actor | **fx** `outputs('Decizie')?['aprobator']` |
| Data_Ora | **fx** `utcNow()` |
| Comentariu | **fx** `concat('Pas ', outputs('Decizie')?['pas'], ' (', outputs('Decizie')?['rol'], '): ', outputs('Decizie')?['rezultat'], if(empty(outputs('Decizie')?['comentariu']), '.', concat(' – „', outputs('Decizie')?['comentariu'], '”')))` |

Starea cererii nu se schimbă la un pas intermediar. Tranziția finală se jurnalizează la pasul 12.

### 11.6 `Cond_Aprobat_Pas` (BPMN `Gateway_Aprobat1…4`)
**Condiție**: stânga **fx** `equals(outputs('Decizie')?['rezultat'], 'Aprobat')`, **este egal cu**, dreapta **fx** `false`.

Ramura **True** (pas respins sau expirat):
1. **Setare variabilă** `varRespins`, redenumită `Set_varRespins`: **fx** `true`.
2. **Setare variabilă** `varMotiv`, redenumită `Set_varMotiv`, **fx**:
   ```
   if(equals(outputs('Decizie')?['rezultat'], 'Expirat'), concat('Termenul de aprobare a expirat (7 zile) la pasul ', outputs('Decizie')?['pas'], ' – ', outputs('Decizie')?['rol'], ' (', outputs('Decizie')?['aprobator'], ').'), concat('Respinsă la pasul ', outputs('Decizie')?['pas'], ' – ', outputs('Decizie')?['rol'], ' de ', outputs('Decizie')?['aprobator'], if(empty(outputs('Decizie')?['comentariu']), ' (fără comentariu).', concat(': „', outputs('Decizie')?['comentariu'], '”'))))
   ```

Ramura **False** rămâne goală.

### 11.7 `Increment_varIdx`
**În afara** condiției, ultima acțiune din buclă: **Incrementare variabilă** (*Increment variable*), `varIdx`, valoare `1`.

### ✅ Punct de control C
Salvezi și trimiți o cerere validă mică (de exemplu TC-F1-01 din `docs/plan_testare.md`). Aprobi primul pas din Teams → Aprobări. Verifici:
- apare a doua aprobare, cu titlul `… aprobare 2/3` și „Decizii anterioare” completat;
- `Aprobari` din listă are linia `- Pas 1/3 (Manager centru de cost): Aprobat – …`;
- în `Istoric_Stari` există linia `Pas 1/3 …`.

Dacă ceva nu merge, trimite-mi **Outputs** de la `Aprobare` și `Decizie` din istoricul rulării.

---

## Pasul 12 — `Cond_Respins`, decizia finală

**După** bucla `Do_until_Aprobare` (în afara ei, tot în ramura **Nu** a lui `Cond_Erori`): **Condiție** `Cond_Respins`, stânga **fx** `variables('varRespins')`, **este egal cu**, dreapta **fx** `true`.

> În interiorul acestei condiții, `outputs('Decizie')` dă valoarea din **ultima** iterație a buclei (comportament standard pentru *Do until*).

### 12.1 Ramura **True**: respinsă în circuitul de aprobare

**`Upd_Respinsa_Aprobare`** (BPMN `Task_StatusRespinsa`): **Actualizare element** în `Cereri_Achizitie`, cu **Clear all**:

| Câmp | Valoare (fx) |
|---|---|
| Id | `outputs('Create_Cerere')?['body/ID']` |
| ID_Cerere (Title) | `variables('varIdCerere')` |
| Status Value | **Respinsă** *(din listă)* |
| Motiv_Respingere | `variables('varMotiv')` |
| Aprobari | `variables('varJurnal')` |
| Data_Finalizare | `utcNow()` |

**`Log_Respinsa_Aprobare`**: **Creare element** în `Istoric_Stari`: Title `variables('varIdCerere')`, Flux **F1**, Stare_Veche `În aprobare`, Stare_Noua `Respinsă`, Actor **fx** `outputs('Decizie')?['aprobator']`, Data_Ora `utcNow()`, Comentariu **fx** `variables('varMotiv')`.

**`Html_Respinsa_Aprobare`** (**Compunere**, lipire directă):
```html
<div style="font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#222;max-width:640px">
  <div style="background:#b42318;color:#fff;padding:12px 16px;font-size:16px;font-weight:600">
    BudgetGuard · Cerere respinsă
  </div>
  <div style="padding:16px;border:1px solid #ddd;border-top:none">
    <p>Bună ziua,</p>
    <p>Cererea <b>@{variables('varIdCerere')}</b> – „@{outputs('Cerere')?['titlu']}” a fost <b>respinsă</b> în circuitul de aprobare.</p>
    <p style="margin-bottom:4px"><b>Motiv:</b></p>
    <p style="margin-top:0;color:#b42318">@{variables('varMotiv')}</p>
    <p style="margin-bottom:4px"><b>Istoricul deciziilor:</b></p>
    <ul style="margin-top:0"><li>@{join(split(trim(replace(variables('varJurnal'), '- Pas', 'Pas')), decodeUriComponent('%0A')), '</li><li>')}</li></ul>
    <table style="border-collapse:collapse;font-size:13px">
      <tr><td style="padding:4px 12px 4px 0;color:#666">Centru de cost / categorie</td><td>@{outputs('Cerere')?['cc']} / @{outputs('Cerere')?['cat']}</td></tr>
      <tr><td style="padding:4px 12px 4px 0;color:#666">Valoare</td><td>@{formatNumber(outputs('Valoare_RON'), 'N2', 'ro-RO')} RON</td></tr>
    </table>
    <p>Bugetul nu a fost modificat. Poți depune o cerere nouă din formular.</p>
    <p style="font-size:12px;color:#888">Mesaj automat BudgetGuard · Vestra Retail SRL · @{convertTimeZone(utcNow(), 'UTC', 'GTB Standard Time', 'dd.MM.yyyy HH:mm')}</p>
  </div>
</div>
```

**`Email_Respinsa_Aprobare`** (Gmail → Send email (V2), BPMN `Send_NotifRespingere`): **Către** `outputs('Cerere')?['email']`, **Subiect** `[BudgetGuard] @{variables('varIdCerere')} – cerere respinsă`, **Corp** = Ieșiri de la `Html_Respinsa_Aprobare`.

**`Html_Teams_Respinsa_Aprobare`** (**Compunere**, cu *Run after* pe email: **are succes** + **a eșuat**, ca la 6.3):
```html
<p>🔴 <b>@{variables('varIdCerere')}</b> – @{outputs('Cerere')?['titlu']}</p>
<p>În aprobare → <b>Respinsă</b> · @{outputs('Cerere')?['cc']}/@{outputs('Cerere')?['cat']} · @{formatNumber(outputs('Valoare_RON'), 'N2', 'ro-RO')} RON</p>
<p>@{variables('varMotiv')}</p>
<p><a href="@{outputs('Create_Cerere')?['body/{Link}']}">Deschide cererea în SharePoint</a></p>
```
**`Teams_Respinsa_Aprobare`**: aceleași setări ca la 6.4, **Mesaj** = Ieșiri de la `Html_Teams_Respinsa_Aprobare`.

**`Terminate_Respinsa_Aprobare`**: **Terminare**, **Reușit**. Notă BPMN: `End_Respinsa`.

### 12.2 Ramura **False**: aprobată + angajarea în buget

**`Upd_Aprobata`** (BPMN `Task_StatusAprobata`): **Actualizare element** în `Cereri_Achizitie`, cu **Clear all**:

| Câmp | Valoare (fx) |
|---|---|
| Id | `outputs('Create_Cerere')?['body/ID']` |
| ID_Cerere (Title) | `variables('varIdCerere')` |
| Status Value | **Aprobată** *(din listă)* |
| Aprobari | `variables('varJurnal')` |
| Data_Finalizare | `utcNow()` |

**`Get_Buget_Curent`** (BPMN `Task_AngajeazaBuget`): **SharePoint** → **Obținere element** (*Get item*), lista `Bugete`, **Id** **fx** `outputs('Buget')?['ID']`.
Bugetul se **recitește** acum: între depunere și aprobare pot trece zile, iar alte cereri pe aceeași cheie pot fi aprobate între timp.

**`Angajat_Nou`** (**Compunere**, fx):
```
float(formatNumber(add(float(coalesce(body('Get_Buget_Curent')?['Angajat_RON'], 0)), outputs('Valoare_RON')), '0.00', 'en-US'))
```
**`Ramas_Nou`** (**Compunere**, fx):
```
float(formatNumber(sub(float(body('Get_Buget_Curent')?['Buget_RON']), outputs('Angajat_Nou')), '0.00', 'en-US'))
```
`Ramas_Nou` poate ieși **negativ** când cererea a trecut de W1 și a fost aprobată de CFO. E intenționat: depășirea rămâne vizibilă în buget.

**`Upd_Buget`**: **Actualizare element** în `Bugete`, cu **Clear all**:

| Câmp | Valoare (fx) |
|---|---|
| Id | `outputs('Buget')?['ID']` |
| Cheie (Title) | `body('Get_Buget_Curent')?['Title']` |
| Angajat_RON | `outputs('Angajat_Nou')` |
| Ramas_RON | `outputs('Ramas_Nou')` |

**`Log_Aprobata`**: **Creare element** în `Istoric_Stari`: Title `variables('varIdCerere')`, Flux **F1**, Stare_Veche `În aprobare`, Stare_Noua `Aprobată`, Actor **fx** `outputs('Decizie')?['aprobator']`, Data_Ora `utcNow()`, Comentariu **fx**:
```
concat('Aprobată în ', string(length(variables('varAprobatori'))), ' pași. Angajat în ', outputs('Cerere')?['cheie_buget'], ': ', formatNumber(outputs('Valoare_RON'), 'N2', 'ro-RO'), ' RON; total angajat ', formatNumber(outputs('Angajat_Nou'), 'N2', 'ro-RO'), ' RON; rămas ', formatNumber(outputs('Ramas_Nou'), 'N2', 'ro-RO'), ' RON.')
```

**`Html_Aprobata`** (**Compunere**, lipire directă):
```html
<div style="font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#222;max-width:640px">
  <div style="background:#15803d;color:#fff;padding:12px 16px;font-size:16px;font-weight:600">
    BudgetGuard · Cerere aprobată
  </div>
  <div style="padding:16px;border:1px solid #ddd;border-top:none">
    <p>Bună ziua,</p>
    <p>Cererea <b>@{variables('varIdCerere')}</b> – „@{outputs('Cerere')?['titlu']}” a fost <b>aprobată</b> de toți cei @{length(variables('varAprobatori'))} aprobatori, iar suma a fost angajată în buget.</p>
    <table style="border-collapse:collapse;font-size:13px">
      <tr><td style="padding:4px 12px 4px 0;color:#666">Furnizor</td><td>@{outputs('Denumire')} · CUI @{outputs('Cerere')?['cui']}</td></tr>
      <tr><td style="padding:4px 12px 4px 0;color:#666">Suma angajată</td><td><b>@{formatNumber(outputs('Valoare_RON'), 'N2', 'ro-RO')} RON</b></td></tr>
      <tr><td style="padding:4px 12px 4px 0;color:#666">Buget @{outputs('Cerere')?['cheie_buget']}</td><td>@{formatNumber(float(body('Get_Buget_Curent')?['Buget_RON']), 'N2', 'ro-RO')} RON</td></tr>
      <tr><td style="padding:4px 12px 4px 0;color:#666">Total angajat</td><td>@{formatNumber(outputs('Angajat_Nou'), 'N2', 'ro-RO')} RON</td></tr>
      <tr><td style="padding:4px 12px 4px 0;color:#666">Buget rămas</td><td><b style="color:@{if(less(outputs('Ramas_Nou'), 0), '#b42318', '#15803d')}">@{formatNumber(outputs('Ramas_Nou'), 'N2', 'ro-RO')} RON</b></td></tr>
    </table>
    <p style="margin-bottom:4px"><b>Istoricul aprobărilor:</b></p>
    <ul style="margin-top:0"><li>@{join(split(trim(replace(variables('varJurnal'), '- Pas', 'Pas')), decodeUriComponent('%0A')), '</li><li>')}</li></ul>
    <p style="font-size:12px;color:#888">Mesaj automat BudgetGuard · Vestra Retail SRL · @{convertTimeZone(utcNow(), 'UTC', 'GTB Standard Time', 'dd.MM.yyyy HH:mm')}</p>
  </div>
</div>
```

**`Email_Aprobata`** (Gmail → Send email (V2), BPMN `Send_NotifAprobare`): **Către** `outputs('Cerere')?['email']`, **Subiect** `[BudgetGuard] @{variables('varIdCerere')} – cerere aprobată`, **Corp** = Ieșiri de la `Html_Aprobata`.

**`Html_Teams_Aprobata`** (**Compunere**, *Run after* pe email: **are succes** + **a eșuat**):
```html
<p>🟢 <b>@{variables('varIdCerere')}</b> – @{outputs('Cerere')?['titlu']}</p>
<p>În aprobare → <b>Aprobată</b> · @{outputs('Cerere')?['cc']}/@{outputs('Cerere')?['cat']} · @{formatNumber(outputs('Valoare_RON'), 'N2', 'ro-RO')} RON angajați · rămas @{formatNumber(outputs('Ramas_Nou'), 'N2', 'ro-RO')} RON în @{outputs('Cerere')?['cheie_buget']}</p>
<p><a href="@{outputs('Create_Cerere')?['body/{Link}']}">Deschide cererea în SharePoint</a></p>
```
**`Teams_Aprobata`**: aceleași setări ca la 6.4. Notă BPMN: `End_Aprobata`. Fluxul se termină natural, fără *Terminate*.

### ✅ Punct de control D
Rulezi testele din `docs/plan_testare.md` (TC-F1-01 … TC-F1-11). Pentru fiecare îmi trimiți rezultatul (OK / ce nu merge) și faci capturile cerute acolo.

---

## Probleme frecvente

| Simptom | Cauză probabilă / soluție |
|---|---|
| `Cerere` eșuează la `formatDateTime` | Data din Forms vine în alt format. Trimite-mi output-ul `Date_Formular` |
| `Select_Config` → `cfg` dă *invalid JSON* | O valoare din Config conține ghilimele `"`. Șterge-le din listă |
| În email apar literal `@{variables(...)}` | Expresia nu a fost recunoscută la lipire. Reintrodu fragmentul prin **fx** în `Html_…` |
| `HTTP_ANAF` 400 | CUI-ul are spații sau prefixul RO; `int()` eșuează. Verifică `Cerere.cui` |
| `Parse_ANAF`: *ValidationFailed* | ANAF a schimbat un tip. Trimite-mi Outputs de la `HTTP_ANAF` |
| `Get_Buget` nu găsește nimic, deși bugetul există | Compară `Cerere.cheie_buget` cu Title din Bugete (de ex. un spațiu în plus din opțiunea Forms) |
| `Teams_*`: *Team / Channel not found* | ID-urile din Config sunt încă codificate (`%3a`). Decodifică-le (pasul 0.1) |
| Cererea rămâne pe „Nouă” | Fluxul a eșuat în `Scope_Validare`. Deschide rularea și trimite-mi acțiunea roșie + mesajul |
| `Aprobare`: *user not found* / *invalid assignee* | Adresa din Config nu e din tenantul ASE sau are spații. Corectează în Config |
| Bucla nu se oprește după o respingere | Condiția din `Do_until_Aprobare` compară cu textul „true”. Dreapta trebuie pusă prin **fx** `true` |
| `Decizie` e *Skipped* după 7 zile | Lipsește *Run after → a expirat* pe `Decizie` (11.2) |
| `Upd_Buget` eșuează: *Title required* | Lipsește `Cheie (Title)` în tabelul de la 12.2 |
| În emailul de aprobare istoricul apare pe un singur rând | `varJurnal` nu se termină cu `%0A`. Verifică expresia de la 11.3 |
