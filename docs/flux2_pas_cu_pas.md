# Flux 2 — `BG_Flux2_Import`, pas cu pas

> Faza 7: importul lunar al cheltuielilor realizate, validare, upsert, Buget vs. Realizat, maverick, analiza AI pe centre de cost, raport, arhivarea fișierului.
> Raportul de aici e **provizoriu** (tabel simplu). În Faza 8 îl înlocuiește șablonul `report/template.html`, fără alte modificări în flux.
> Convențiile sunt cele din `flux1_pas_cu_pas.md`: denumiri românești cu originalul englezesc în paranteză, **fx** = editorul de expresii, **lipire directă** = text cu `@{...}`, **Clear all** pe *Update item*, notă BPMN pe acțiunile principale.
> Numele acțiunilor trebuie redenumite **exact** ca în ghid, fiindcă expresiile le folosesc.

## Harta fluxului

```
Trigger (fișier .json nou în Import_Realizat, nu în Procesate)
→ Get_Config → Select_Config → cfg → System_Prompt → 11 × Inițializare variabilă
→ Scope_Try
    Get_file_content → Fisier_Text → Fisier_JSON → Parse_Fisier → Luna_Import
    Get_Nomenclator → Filter_CC → Select_Coduri_CC → Filter_CAT → Select_Coduri_CAT
    HTTP_BNR → Cond_BNR_OK (True: Set_varCursuri)
    Valideaza_Randuri  [Rand → Luna_OK → Lipsa → Cheie → Suma_Num → Cod_Eroare → Cond_Rand_Valid
                        True: Suma_RON → Append_varChei → Inreg_Valida → Append_varValide
                        False: Prima_Aparitie → Ref → Mesaj_Rand → Err_Rand → Append_varErori]
    Upsert_Realizat    [Get_Realizat → Get_Cereri_Aprobate → Select_Valori → Aprobat_RON → Maverick_RON
                        → Mav_Map → Set_varMav → Cond_Exista_Realizat (Create / Update)
                        → Get_Buget_Rand → Cond_Exista_Buget (Upd_Buget_Realizat)]
    Salveaza_Erori     [Create_Eroare]
    Get_Realizat_Luna → Select_Mav_Luna → Mav_Luna
    Analiza_CC         [Get_Bugete_CC → Select_Categorii → Buget_CC … Alerta_Regula → User_AI
                        → Get_Analiza → Cond_Exista_Analiza → Id_Analiza
                        → AI_Try [Corp_Groq → HTTP_Groq → AI_Text → Parse_AI → Upd_Analiza_OK → Inc_AI_OK]
                        → AI_Catch [Motiv_AI → Mesaj_AI_Esec → Upd_Analiza_Esuata → Inc_AI_Esec]
                        → Rez_CC → Append_varRezCC → Delay_Groq]
    Filter_Duplicate → Sumar_Import → Select_Rand_CC → Select_Rand_Err → Select_Rand_Teams → Html_Raport → Email_Raport → Html_Teams_Raport → Teams_Raport
    Create_Arhiva → Delete_Original → Log_Import
→ Scope_Catch (doar dacă Scope_Try a eșuat)
    Filter_Esec → Actiune_Esuata → Detaliu_Esec → Mesaj_Esec → Html_Esec → Email_Esec → Teams_Esec → Log_Esec
```

Corespondența cu BPMN 2 (`bpmn/flux2_import_analiza.bpmn`):

| Element BPMN | Acțiuni |
|---|---|
| `Start_FisierNou` | trigger + condițiile de declanșare |
| `Task_CitesteFisier`, `Gateway_Lizibil` | `Get_file_content`, `Fisier_JSON`, `Parse_Fisier` (eșec → `Scope_Catch`) |
| `Error_Import`, `Send_NotifEsec`, `End_ImportEsuat` | `Scope_Catch` |
| `Task_Referinte` | `Get_Nomenclator` … `Cond_BNR_OK` |
| `Sub_ValideazaInregistrarea` (`SV_*`) | `Valideaza_Randuri` |
| `Task_Upsert` | `Upsert_Realizat` |
| `Task_SalveazaErori` | `Salveaza_Erori` |
| `Sub_AnalizaCC` (`SA_*`), `Error_AI` | `Analiza_CC`, `AI_Try`, `AI_Catch` |
| `Task_Raport`, `Send_Raport` | `Sumar_Import` … `Teams_Raport` |
| `Task_MutaFisier`, `End_ImportFinalizat` | `Create_Arhiva`, `Delete_Original`, `Log_Import` |

---

## Pasul 0 — Pregătiri

1. **Config**: adaugi un element nou, Cheie `groq_model`, Valoare `openai/gpt-oss-120b`. Opțional: dacă lipsește, fluxul folosește oricum acest model. Cheia permite trecerea la `openai/gpt-oss-20b` fără să modifici fluxul.
2. Verifici în Config: `email_echipa` (adrese separate prin `;`), `email_bcc`, `mod_demo` = `false`, `prag_alerta_pct` = `10`, `curs_fallback_EUR`, `curs_fallback_USD`.
3. Biblioteca **Import_Realizat** trebuie să aibă folderul `Procesate` (creat în Faza 3) și **să nu conțină** alte fișiere `.json` în rădăcină.
4. Variabila de mediu `bg_GroqApiKey` există deja în soluție (Faza 1). Valoarea e în *Current Value*.

---

## Pasul 1 — Crearea fluxului și trigger-ul (BPMN `Start_FisierNou`)

1. **Soluții** → **BudgetGuard** → **+ Nou** → **Automatizare** → **Flux de cloud** → **Automatizat**.
2. Nume: `BG_Flux2_Import`. Trigger: **SharePoint** → **Când este creat un fișier (doar proprietăți)** (*When a file is created (properties only)*).
   - **Adresă site**: site-ul BudgetGuard. **Nume bibliotecă** (*Library Name*): `Import_Realizat`. **Folder**: gol.
3. Pe trigger → **Setări** (*Settings*) → **Condiții de declanșare** (*Trigger conditions*) → **+ Adăugare**, de două ori:
   ```
   @endsWith(toLower(triggerOutputs()?['body/{FilenameWithExtension}']), '.json')
   ```
   ```
   @not(contains(toLower(triggerOutputs()?['body/{Path}']), 'procesate'))
   ```
   Prima condiție ignoră fișierele care nu sunt JSON (de exemplu `.xlsx`). A doua împiedică fluxul să pornească din nou când arhivează fișierul în `Procesate` (pasul 13).
4. Notă BPMN: `Start_FisierNou`.

## Pasul 2 — Config, promptul și variabilele

### 2.1 Config
Exact ca în Flux 1 (§2.3 din `flux1_pas_cu_pas.md`): `Get_Config` → `Select_Config` (mod text, `concat('"', item()?['Title'], '":"', item()?['Valoare'], '"')`) → `cfg` = `json(concat('{', join(body('Select_Config'), ','), '}'))`.

### 2.2 `System_Prompt`
**Compunere**, redenumită `System_Prompt`. În **Intrări** lipești **tot textul** din `ai/system_prompt.txt`, exact cum e (cu rândurile goale). E text simplu, nu expresie.

### 2.3 Variabilele
**Inițializare variabilă**, în ordinea asta:

| Nume | Tip | Valoare |
|---|---|---|
| `varRulare` | Șir | **fx** `workflow()?['run']?['name']` |
| `varFisier` | Șir | **fx** `triggerOutputs()?['body/{FilenameWithExtension}']` |
| `varChei` | Matrice | `[]` |
| `varValide` | Matrice | `[]` |
| `varErori` | Matrice | `[]` |
| `varMav` | Obiect (*Object*) | `{}` |
| `varRezCC` | Matrice | `[]` |
| `varAI_OK` | Număr întreg | `0` |
| `varAI_Esec` | Număr întreg | `0` |
| `varCursuri` | Obiect | **fx** (vezi mai jos) |
| `varDataCurs` | Șir | `rezervă Config` |

`varCursuri`, **fx**:
```
json(concat('{"RON":1,"EUR":', outputs('cfg')?['curs_fallback_EUR'], ',"USD":', outputs('cfg')?['curs_fallback_USD'], '}'))
```
Pornește cu cursurile de rezervă din Config. Dacă BNR răspunde (pasul 4), sunt înlocuite cu cursul zilei.

---

## Pasul 3 — `Scope_Try`: citirea fișierului (BPMN `Task_CitesteFisier`, `Gateway_Lizibil`)

**+** → **Control** → **Domeniu** (*Scope*), redenumit `Scope_Try`. Toți pașii 3–13 sunt **în interiorul** lui.

### 3.1 `Get_file_content`
**SharePoint** → **Obținere conținut fișier** (*Get file content*). **Adresă site**: BudgetGuard. **Identificator fișier** (*File Identifier*): **fx** `triggerOutputs()?['body/{Identifier}']`.

### 3.2 `Fisier_Text` — conținutul ca text
**Compunere**, **fx**:
```
replace(if(empty(body('Get_file_content')?['$content']), string(body('Get_file_content')), base64ToString(coalesce(body('Get_file_content')?['$content'], ''))), decodeUriComponent('%EF%BB%BF'), '')
```
SharePoint întoarce un fișier `.json` fie **deja ca obiect**, fie ca `{"$content-type": …, "$content": "<base64>"}`. Expresia acceptă ambele variante (`docs/expresii.md` notează care apare la tine). La final scoate BOM-ul UTF-8, dacă fișierul a fost salvat cu el.

### 3.3 `Fisier_JSON`
**Compunere**, **fx** `json(outputs('Fisier_Text'))`.
Dacă fișierul nu e JSON valid, **această** acțiune eșuează. `Scope_Catch` recunoaște numele ei și trimite mesajul „fișierul nu este un JSON valid”.

### 3.4 `Parse_Fisier`
**Operații cu date** → **Analizare JSON** (*Parse JSON*). **Conținut**: **fx** `outputs('Fisier_JSON')`. **Schemă**: lipești `schemas/realizat_input.json`.
Schema e **permisivă** pe rânduri (fără `required`, tipuri multiple), ca un rând greșit să ajungă la validarea noastră, cu mesaj clar, în loc să oprească fluxul. La nivelul fișierului cere `inregistrari` cu cel puțin un element. Dacă lipsește, `Parse_Fisier` eșuează și `Scope_Catch` trimite mesajul „lista inregistrari lipsește sau este goală”.

### 3.5 `Luna_Import`
**Compunere**, **fx** `coalesce(body('Parse_Fisier')?['luna'], '')`

### ✅ Punct de control A
Salvezi. **Testare** → **Manual**. Încarci `data/input/realizat_2026-10.json` în biblioteca `Import_Realizat` (rădăcină). Fluxul pornește în ~1 minut.
Rularea se oprește după `Luna_Import`, fiindcă nu există încă alți pași. Trimite-mi:
- primele rânduri din **Outputs** de la `Get_file_content` (văd dacă vine ca obiect sau ca `$content`);
- **Outputs** de la `Luna_Import` (trebuie `2026-10`).
Apoi **ștergi** fișierul din bibliotecă, ca să-l poți încărca din nou la următorul test.

---

## Pasul 4 — Nomenclatorul și cursurile (BPMN `Task_Referinte`)

### 4.1 Codurile valide
1. **SharePoint** → **Obținere elemente**, redenumită `Get_Nomenclator`. Lista `Nomenclator`.
2. **Operații cu date** → **Filtrare matrice** (*Filter array*), redenumită `Filter_CC`.
   - **Din**: **fx** `outputs('Get_Nomenclator')?['body/value']`
   - Condiție: stânga **fx** `item()?['Tip']?['Value']`, **este egal cu**, dreapta `CC`.
3. **Selectare**, redenumită `Select_Coduri_CC`. **Din**: **fx** `body('Filter_CC')`. **Mapare** în **modul text**: **fx** `item()?['Title']`.
4. La fel `Filter_CAT` (dreapta `CAT`) și `Select_Coduri_CAT`.

Rezultatul: `body('Select_Coduri_CC')` = `["IT","MKT","OPS","HR","SAL"]`, iar `body('Select_Coduri_CAT')` = `["HW","SW","SRV","TRN","MKT","BIR"]`.

### 4.2 Cursul BNR, un singur apel
1. **HTTP**, redenumită `HTTP_BNR`: `GET` `https://curs.bnr.ro/nbrfxrates.xml`. **Setări**: retry **Exponențial**, `3`, `PT10S`; **Expirare acțiune** `PT1M`.
2. **Condiție** `Cond_BNR_OK`: **fx** `equals(actions('HTTP_BNR')?['status'], 'Succeeded')` = **fx** `true`. **Setări → Rulare după** → `HTTP_BNR`: **are succes**, **a eșuat**, **a expirat**.
3. Ramura **True**:
   - **Setare variabilă** `varCursuri`, redenumită `Set_varCursuri`, **fx**:
     ```
     json(concat('{"RON":1,"EUR":', xpath(xml(body('HTTP_BNR')), 'string(//*[local-name()=''Rate''][@currency=''EUR''])'), ',"USD":', xpath(xml(body('HTTP_BNR')), 'string(//*[local-name()=''Rate''][@currency=''USD''])'), '}'))
     ```
   - **Setare variabilă** `varDataCurs`, redenumită `Set_varDataCurs`, **fx**:
     ```
     xpath(xml(body('HTTP_BNR')), 'string(//*[local-name()=''Cube'']/@date)')
     ```
4. Ramura **False** rămâne goală: se păstrează cursurile de rezervă, iar raportul afișează „rezervă Config”.

---

## Pasul 5 — `Valideaza_Randuri` (BPMN `Sub_ValideazaInregistrarea`)

**Control** → **Pentru fiecare** (*Apply to each* / *For each*), redenumit `Valideaza_Randuri`.
- **Selectați o ieșire** (*Select an output*): **fx** `body('Parse_Fisier')?['inregistrari']`
- **Setări** → **Control simultaneitate** (*Concurrency control*) **Activat**, **Grad de paralelism** `1`. **Obligatoriu**: bucla modifică variabile, iar ordinea decide care apariție a unui duplicat câștigă.
- Notă: `Sub_ValideazaInregistrarea (multi-instance secvențial)`.

Toate acțiunile 5.1–5.7 sunt **în** buclă.

### 5.1 `Rand` — valorile rândului, ca text
**Compunere**, **lipire directă**:
```
{
  "rand": "@{items('Valideaza_Randuri')?['rand']}",
  "luna": "@{trim(string(coalesce(items('Valideaza_Randuri')?['luna'], '')))}",
  "cc": "@{trim(string(coalesce(items('Valideaza_Randuri')?['centru_cost'], '')))}",
  "cat": "@{trim(string(coalesce(items('Valideaza_Randuri')?['categorie'], '')))}",
  "suma": "@{trim(string(coalesce(items('Valideaza_Randuri')?['suma'], '')))}",
  "moneda": "@{trim(string(coalesce(items('Valideaza_Randuri')?['moneda'], '')))}",
  "nr_documente": "@{items('Valideaza_Randuri')?['nr_documente']}"
}
```
Toate valorile devin șiruri, ca în `Cerere` din Flux 1. Un câmp lipsă devine `""`, iar conversiile se fac abia după ce valoarea a trecut verificarea.

### 5.2 Verificările
Fiecare e o **Compunere** separată, cu **fx**. Le pui în ordinea din tabel.

| Nume | Expresie (fx) | Rezultat |
|---|---|---|
| `Luna_OK` | `and(equals(length(outputs('Rand')?['luna']), 7), equals(substring(concat(outputs('Rand')?['luna'], '_______'), 4, 1), '-'), isInt(substring(concat(outputs('Rand')?['luna'], '_______'), 0, 4)), contains(createArray('01','02','03','04','05','06','07','08','09','10','11','12'), substring(concat(outputs('Rand')?['luna'], '_______'), 5, 2)))` | `true` / `false` |
| `Lipsa` | `join(split(trim(concat(if(empty(outputs('Rand')?['luna']), 'luna ', ''), if(empty(outputs('Rand')?['cc']), 'centru_cost ', ''), if(empty(outputs('Rand')?['cat']), 'categorie ', ''), if(empty(outputs('Rand')?['suma']), 'suma ', ''), if(empty(outputs('Rand')?['moneda']), 'moneda', ''))), ' '), ', ')` | ex. `suma, moneda` sau `""` |
| `Cheie` | `if(and(outputs('Luna_OK'), not(empty(outputs('Rand')?['cc'])), not(empty(outputs('Rand')?['cat']))), concat(outputs('Rand')?['luna'], '_', outputs('Rand')?['cc'], '_', outputs('Rand')?['cat']), '')` | ex. `2026-10_IT_SW` |
| `Suma_Num` | `float(if(isFloat(outputs('Rand')?['suma']), outputs('Rand')?['suma'], '0'))` | număr |
| `Cod_Eroare` | vezi mai jos | `""` = rând valid |

`Cod_Eroare`, **fx** (o singură linie):
```
if(not(empty(outputs('Lipsa'))), 'LIPSA', if(not(outputs('Luna_OK')), 'LUNA', if(not(isFloat(outputs('Rand')?['suma'])), 'TIP', if(lessOrEquals(outputs('Suma_Num'), 0), 'SUMA', if(not(contains(createArray('RON','EUR','USD'), outputs('Rand')?['moneda'])), 'MONEDA', if(not(contains(body('Select_Coduri_CC'), outputs('Rand')?['cc'])), 'CC', if(not(contains(body('Select_Coduri_CAT'), outputs('Rand')?['cat'])), 'CAT', if(contains(variables('varChei'), outputs('Cheie')), 'DUP', ''))))))))
```
Ordinea verificărilor e aceeași ca în `scripts/reference_pipeline.py`: câmpuri lipsă → format lună → tip sumă → sumă > 0 → monedă → cod CC → cod CAT → duplicat. Primul test care pică dă codul.

> De ce `concat(…, '_______')` și `if(isFloat…, …, '0')`: Power Automate evaluează **toți** parametrii unei expresii, chiar și ramura neluată a lui `if` sau restul unui `and`. `substring` pe un text prea scurt sau `float('abc')` ar opri fluxul. Cu umplutura și cu `'0'`, nicio ramură nu poate eșua.

### 5.3 `Cond_Rand_Valid` (BPMN `SV_Rezultat`)
**Condiție**: **fx** `empty(outputs('Cod_Eroare'))` = **fx** `true`.

### 5.4 Ramura **True**: rând valid (BPMN `SV_Valid`)
1. **Compunere** `Suma_RON`, **fx**:
   ```
   float(formatNumber(mul(outputs('Suma_Num'), float(variables('varCursuri')?[outputs('Rand')?['moneda']])), '0.00', 'en-US'))
   ```
2. **Adăugare la variabila matrice** `varChei`, redenumită `Append_varChei`: **fx** `outputs('Cheie')`
3. **Compunere** `Inreg_Valida`, **lipire directă**:
   ```
   {
     "rand": "@{outputs('Rand')?['rand']}",
     "cheie": "@{outputs('Cheie')}",
     "luna": "@{outputs('Rand')?['luna']}",
     "cc": "@{outputs('Rand')?['cc']}",
     "cat": "@{outputs('Rand')?['cat']}",
     "suma": "@{outputs('Suma_Num')}",
     "moneda": "@{outputs('Rand')?['moneda']}",
     "suma_ron": "@{outputs('Suma_RON')}",
     "nr_documente": "@{outputs('Rand')?['nr_documente']}"
   }
   ```
4. **Adăugare la variabila matrice** `varValide`, redenumită `Append_varValide`: **fx** `outputs('Inreg_Valida')`

### 5.5 Ramura **False**: rând invalid sau duplicat (BPMN `SV_Invalid`, `SV_Duplicat`)
1. **Filtrare matrice** `Prima_Aparitie`: **Din** **fx** `variables('varValide')`. Condiție: **fx** `item()?['cheie']` **este egal cu** **fx** `outputs('Cheie')`. Găsește rândul la care cheia a apărut prima dată (doar pentru duplicate).
2. **Compunere** `Ref`, **fx**:
   ```
   if(empty(outputs('Cheie')), concat('Rândul ', outputs('Rand')?['rand']), concat('Rândul ', outputs('Rand')?['rand'], ' (', outputs('Cheie'), ')'))
   ```
3. **Compunere** `Mesaj_Rand`, **fx** (catalogul de mesaje, §5.5.4 din specificație):
   ```
   if(equals(outputs('Cod_Eroare'), 'LIPSA'), concat(outputs('Ref'), ': lipsesc câmpurile obligatorii ', outputs('Lipsa'), '.'), if(equals(outputs('Cod_Eroare'), 'LUNA'), concat(outputs('Ref'), ': luna „', outputs('Rand')?['luna'], '” are format greșit; formatul corect este AAAA-LL (ex. 2026-10).'), if(equals(outputs('Cod_Eroare'), 'TIP'), concat(outputs('Ref'), ': suma „', outputs('Rand')?['suma'], '” nu este un număr.'), if(equals(outputs('Cod_Eroare'), 'SUMA'), concat(outputs('Ref'), ': suma ', outputs('Rand')?['suma'], ' nu este validă; se acceptă doar valori mai mari decât 0.'), if(equals(outputs('Cod_Eroare'), 'MONEDA'), concat(outputs('Ref'), ': moneda „', outputs('Rand')?['moneda'], '” nu este acceptată; valori permise: RON, EUR, USD.'), if(equals(outputs('Cod_Eroare'), 'CC'), concat(outputs('Ref'), ': centrul de cost „', outputs('Rand')?['cc'], '” nu există în nomenclator. Coduri valide: ', join(body('Select_Coduri_CC'), ', '), '.'), if(equals(outputs('Cod_Eroare'), 'CAT'), concat(outputs('Ref'), ': categoria „', outputs('Rand')?['cat'], '” nu există în nomenclator. Coduri valide: ', join(body('Select_Coduri_CAT'), ', '), '.'), concat(outputs('Ref'), ': înregistrare duplicat — cheia a apărut deja la rândul ', coalesce(first(body('Prima_Aparitie'))?['rand'], '?'), '; rândul a fost ignorat.'))))))))
   ```
4. **Compunere** `Err_Rand`, **lipire directă**:
   ```
   {
     "rand": "@{outputs('Rand')?['rand']}",
     "cheie": "@{outputs('Cheie')}",
     "tip": "@{if(equals(outputs('Cod_Eroare'), 'LIPSA'), 'Câmp lipsă', if(equals(outputs('Cod_Eroare'), 'LUNA'), 'Format lună', if(equals(outputs('Cod_Eroare'), 'TIP'), 'Tip invalid', if(or(equals(outputs('Cod_Eroare'), 'SUMA'), equals(outputs('Cod_Eroare'), 'MONEDA')), 'Valoare în afara domeniului', if(equals(outputs('Cod_Eroare'), 'DUP'), 'Duplicat', 'Cod necunoscut')))))}",
     "mesaj": "@{outputs('Mesaj_Rand')}"
   }
   ```
5. **Adăugare la variabila matrice** `varErori`, redenumită `Append_varErori`: **fx** `outputs('Err_Rand')`

### ✅ Punct de control B
**După** bucla `Valideaza_Randuri` (în afara ei, tot în `Scope_Try`), adaugi temporar o **Compunere** `Debug_Validare`, **fx**:
```
concat('valide=', length(variables('varValide')), ' erori=', length(variables('varErori')), ' | ', string(variables('varErori')))
```
Încarci din nou fișierul. Trimite-mi **Outputs** de la `Debug_Validare`. Așteptat: `valide=20 erori=4`, cu mesajele pentru rândurile 9, 14, 17 și 22. Le compar cu oracolul. Apoi ștergi `Debug_Validare` și fișierul din bibliotecă.

---

## Pasul 6 — `Upsert_Realizat` (BPMN `Task_Upsert`)

**Pentru fiecare** `Upsert_Realizat`, **fx** `variables('varValide')`. **Concurență 1** (bucla scrie în `varMav`).

### 6.1 Ce există deja și ce s-a aprobat
1. **Obținere elemente** `Get_Realizat`: lista `Realizat_Lunar`. **Interogare de filtrare**, lipire directă: `Title eq '@{items('Upsert_Realizat')?['cheie']}'`. **Număr maxim**: `1`.
2. **Obținere elemente** `Get_Cereri_Aprobate`: lista `Cereri_Achizitie`. **Interogare de filtrare**, lipire directă:
   ```
   Luna_Buget eq '@{items('Upsert_Realizat')?['luna']}' and CentruCost eq '@{items('Upsert_Realizat')?['cc']}' and Categorie eq '@{items('Upsert_Realizat')?['cat']}' and (Status eq 'Aprobată' or Status eq 'Exportată')
   ```
3. **Selectare** `Select_Valori`: **Din** **fx** `outputs('Get_Cereri_Aprobate')?['body/value']`. **Mapare** în modul text: **fx** `coalesce(item()?['Valoare_RON'], 0)`.

### 6.2 Suma aprobată și maverick
| Nume (Compunere) | Expresie (fx) |
|---|---|
| `Aprobat_RON` | `float(formatNumber(float(xpath(xml(json(concat('{"r":{"v":', string(body('Select_Valori')), '}}'))), 'sum(/r/v)')), '0.00', 'en-US'))` |
| `Maverick_RON` | `max(0, float(formatNumber(sub(float(items('Upsert_Realizat')?['suma_ron']), outputs('Aprobat_RON')), '0.00', 'en-US')))` |
| `Mav_Map` | `setProperty(variables('varMav'), items('Upsert_Realizat')?['cheie'], outputs('Maverick_RON'))` |

Apoi **Setare variabilă** `varMav`, redenumită `Set_varMav`: **fx** `outputs('Mav_Map')`. O variabilă nu se poate referi la ea însăși în *Setare variabilă*, de aceea trece prin `Mav_Map`. `varMav` ajunge un dicționar `cheie → maverick`, folosit la pasul 8.

> **Suma prin xpath** (riscul din §8 al specificației): pentru `[]` rezultă `{"r":{"v":[]}}` → `sum` = `0`; pentru `[5000]` rezultă un singur `<v>` → `5000`. Ambele cazuri apar în datele de test: HR/TRN nu are cereri (0), iar majoritatea cheilor au una singură. La punctul de control C verificăm ambele.

### 6.3 Upsert în `Realizat_Lunar`
**Condiție** `Cond_Exista_Realizat`: **fx** `empty(outputs('Get_Realizat')?['body/value'])` = **fx** `true`.
- **True** → **Creare element** `Create_Realizat` în `Realizat_Lunar`.
- **False** → **Actualizare element** `Update_Realizat` în `Realizat_Lunar`, cu **Clear all**, **Id** = **fx** `first(outputs('Get_Realizat')?['body/value'])?['ID']`.

Ambele primesc aceleași câmpuri (toate prin **fx**):

| Câmp | Valoare |
|---|---|
| Cheie (Title) | `items('Upsert_Realizat')?['cheie']` |
| Luna | `items('Upsert_Realizat')?['luna']` |
| CentruCost | `items('Upsert_Realizat')?['cc']` |
| Categorie | `items('Upsert_Realizat')?['cat']` |
| Suma | `float(items('Upsert_Realizat')?['suma'])` |
| Moneda | `items('Upsert_Realizat')?['moneda']` |
| Suma_RON | `float(items('Upsert_Realizat')?['suma_ron'])` |
| Nr_Documente | `int(if(isInt(items('Upsert_Realizat')?['nr_documente']), items('Upsert_Realizat')?['nr_documente'], '0'))` |
| Aprobat_RON | `outputs('Aprobat_RON')` |
| Maverick_RON | `outputs('Maverick_RON')` |
| Sursa_Fisier | `variables('varFisier')` |
| Rulare_ID | `variables('varRulare')` |
| Data_Import | `utcNow()` |

**Upsert pe cheie**: a doua încărcare a aceluiași fișier găsește rândul și îl actualizează, deci nu apar dubluri.

### 6.4 `Realizat_RON` în `Bugete`
1. **Obținere elemente** `Get_Buget_Rand`: lista `Bugete`, filtru `Title eq '@{items('Upsert_Realizat')?['cheie']}'`, **Număr maxim** `1`.
2. **Condiție** `Cond_Exista_Buget`: **fx** `empty(outputs('Get_Buget_Rand')?['body/value'])` = **fx** `false`.
3. **True** → **Actualizare element** `Upd_Buget_Realizat` în `Bugete`, cu **Clear all**:

| Câmp | Valoare (fx) |
|---|---|
| Id | `first(outputs('Get_Buget_Rand')?['body/value'])?['ID']` |
| Cheie (Title) | `items('Upsert_Realizat')?['cheie']` |
| Realizat_RON | `float(items('Upsert_Realizat')?['suma_ron'])` |

O combinație cu coduri valide, dar nebugetată (de ex. IT/MKT), se salvează în `Realizat_Lunar`, dar nu are rând în `Bugete`. În datele de test nu apare.

## Pasul 7 — `Salveaza_Erori` (BPMN `Task_SalveazaErori`)

**Pentru fiecare** `Salveaza_Erori`, **fx** `variables('varErori')`. Înăuntru, **Creare element** `Create_Eroare` în `Erori_Import`:

| Câmp | Valoare (fx) |
|---|---|
| Rulare_ID (Title) | `variables('varRulare')` |
| Fisier | `variables('varFisier')` |
| Rand | `int(if(isInt(items('Salveaza_Erori')?['rand']), items('Salveaza_Erori')?['rand'], '0'))` |
| Cheie | `items('Salveaza_Erori')?['cheie']` |
| Tip_Eroare Value | **Introduceți o valoare particularizată** → **fx** `items('Salveaza_Erori')?['tip']` |
| Mesaj | `items('Salveaza_Erori')?['mesaj']` |
| Data_Import | `utcNow()` |

`Erori_Import` e un jurnal **pe rulare** (Title = Rulare_ID): un reimport adaugă un set nou de erori, cu alt Rulare_ID, iar seturile vechi rămân ca istoric.

### ✅ Punct de control C
Încarci fișierul. După rulare:
1. **Realizat_Lunar**: 20 de rânduri `2026-10_…`. HR/TRN are `Aprobat_RON` = 0 și `Maverick_RON` = 12.348. Celelalte au maverick 0.
2. **Erori_Import**: 4 rânduri cu același Rulare_ID.
3. **Bugete**: `Realizat_RON` completat pe cele 20 de chei din 2026-10.

Exporți cele două liste (**Export** → **Export în CSV**) în `data/run_check/` (numele fișierelor: `Realizat_Lunar.csv`, `Erori_Import.csv`) și îmi spui. Rulez `python scripts/compare_results.py data/run_check/`. Scriptul citește cursul folosit de flux din rândurile EUR/USD și recalculează oracolul cu el.

---

## Pasul 8 — `Analiza_CC` (BPMN `Sub_AnalizaCC`)

### 8.0 Maverick pe toată luna (înainte de buclă)
Maverick-ul pe categorii se citește din `Realizat_Lunar`, nu din `varMav`. `varMav` conține doar rândurile din fișierul curent: la un import parțial (ex. un fișier de corecție doar pentru IT), CC-urile care lipsesc din fișier ar primi maverick 0, iar analiza lor ar fi suprascrisă greșit (găsit la testare, 2026-11-26). Upsert-ul de la pasul 6 a rulat deja, deci `Realizat_Lunar` are valorile la zi pentru toată luna.

1. **Get items** `Get_Realizat_Luna`: lista `Realizat_Lunar`, **Filter Query** `Luna eq '@{outputs('Luna_Import')}'`, **Top Count** `500`.
2. **Select** `Select_Mav_Luna`, **From** fx `outputs('Get_Realizat_Luna')?['body/value']`, **text mode**, fx:
   ```
   concat('"', item()?['Title'], '":', string(coalesce(item()?['Maverick_RON'], 0)))
   ```
3. **Compose** `Mav_Luna`, fx:
   ```
   json(concat('{', join(body('Select_Mav_Luna'), ','), '}'))
   ```
   Rezultat: `{"2026-10_IT_HW":0, …, "2026-10_HR_TRN":12348, …}`.

**Pentru fiecare** `Analiza_CC`, **fx** `body('Select_Coduri_CC')`. **Concurență 1** (variabile + limita Groq). Notă: `Sub_AnalizaCC (multi-instance secvențial)`.

### 8.1 Bugetul centrului de cost
1. **Obținere elemente** `Get_Bugete_CC`: lista `Bugete`, filtru lipire directă: `Luna eq '@{outputs('Luna_Import')}' and CentruCost eq '@{items('Analiza_CC')}'`
2. **Selectare** `Select_Categorii` (**modul cheie/valoare**, nu text). **Din**: **fx** `outputs('Get_Bugete_CC')?['body/value']`. Mapare, toate valorile prin **fx**:

| Cheie | Valoare (fx) |
|---|---|
| `categorie` | `item()?['Categorie']` |
| `buget` | `coalesce(item()?['Buget_RON'], 0)` |
| `angajat` | `coalesce(item()?['Angajat_RON'], 0)` |
| `realizat` | `coalesce(item()?['Realizat_RON'], 0)` |
| `maverick` | `coalesce(outputs('Mav_Luna')?[item()?['Title']], 0)` |

### 8.2 Totaluri, varianță, alertă (BPMN `SA_Varianta`)
Pentru totaluri se folosește același tipar xpath. Notat mai jos cu **X(câmp)**:
```
float(formatNumber(float(xpath(xml(json(concat('{"r":{"c":', string(body('Select_Categorii')), '}}'))), 'sum(/r/c/câmp)')), '0.00', 'en-US'))
```

| Nume (Compunere, fx) | Expresie |
|---|---|
| `Buget_CC` | X(`buget`) |
| `Angajat_CC` | X(`angajat`) |
| `Realizat_CC` | X(`realizat`) |
| `Maverick_CC` | X(`maverick`) |
| `Varianta_RON` | `float(formatNumber(sub(float(outputs('Realizat_CC')), float(outputs('Buget_CC'))), '0.00', 'en-US'))` |
| `Varianta_Pct` | `float(formatNumber(div(mul(float(outputs('Varianta_RON')), 100), max(float(outputs('Buget_CC')), 0.01)), '0.00', 'en-US'))` |
| `Alerta_Regula` | `if(lessOrEquals(max(float(outputs('Varianta_Pct')), mul(float(outputs('Varianta_Pct')), -1)), 5), 'Verde', if(lessOrEquals(max(float(outputs('Varianta_Pct')), mul(float(outputs('Varianta_Pct')), -1)), float(outputs('cfg')?['prag_alerta_pct'])), 'Galben', 'Roșu'))` |

Exemplu pentru `Buget_CC`, complet:
```
float(formatNumber(float(xpath(xml(json(concat('{"r":{"c":', string(body('Select_Categorii')), '}}'))), 'sum(/r/c/buget)')), '0.00', 'en-US'))
```
Power Automate nu are `abs()`, de aceea |x| se scrie `max(x, mul(x, -1))`. `max(Buget_CC, 0.01)` evită împărțirea la 0 dacă un CC nu are buget în luna respectivă.

> **De ce `float(outputs(...))`:** dacă în câmpul *Inputs* al unui *Compose* rămâne și un spațiu lângă expresie, acțiunea salvează `@{...}` (interpolare), iar ieșirea devine **text**. `sub`/`mul` dau atunci eroarea „expects its first parameter to be an integer or a decimal number. The provided value is of type 'String'” (întâlnită la testare, 2026-11-26). Conversia explicită face expresiile robuste.

### 8.3 `User_AI` — mesajul pentru model
**Compunere**, **fx** (forma e identică cu `ai/samples/user_<CC>.json`, folosită la calibrare):
```
json(concat('{"luna":"', outputs('Luna_Import'), '","centru_cost":"', items('Analiza_CC'), '","buget_ron":', string(outputs('Buget_CC')), ',"angajat_ron":', string(outputs('Angajat_CC')), ',"realizat_ron":', string(outputs('Realizat_CC')), ',"varianta_ron":', string(outputs('Varianta_RON')), ',"varianta_pct":', string(outputs('Varianta_Pct')), ',"maverick_ron":', string(outputs('Maverick_CC')), ',"praguri":{"verde_max_pct":5,"galben_max_pct":', outputs('cfg')?['prag_alerta_pct'], '},"categorii":', string(body('Select_Categorii')), '}'))
```

### 8.4 Upsert în `Analize_AI`: calculele se salvează **înainte** de AI
1. **Obținere elemente** `Get_Analiza`: lista `Analize_AI`, filtru `Title eq '@{outputs('Luna_Import')}_@{items('Analiza_CC')}'`, **Număr maxim** `1`.
2. **Condiție** `Cond_Exista_Analiza`: **fx** `empty(outputs('Get_Analiza')?['body/value'])` = **fx** `true`.
   - **True** → **Creare element** `Create_Analiza`.
   - **False** → **Actualizare element** `Update_Analiza`, cu **Clear all**, **Id** = **fx** `first(outputs('Get_Analiza')?['body/value'])?['ID']`.

   Câmpuri pentru ambele:

   | Câmp | Valoare (fx) |
   |---|---|
   | Cheie (Title) | `concat(outputs('Luna_Import'), '_', items('Analiza_CC'))` |
   | Luna | `outputs('Luna_Import')` |
   | CentruCost | `items('Analiza_CC')` |
   | Buget_RON / Angajat_RON / Realizat_RON | `outputs('Buget_CC')` / `outputs('Angajat_CC')` / `outputs('Realizat_CC')` |
   | Varianta_RON / Varianta_Pct / Maverick_RON | `outputs('Varianta_RON')` / `outputs('Varianta_Pct')` / `outputs('Maverick_CC')` |
   | Alerta_Regula Value | valoare particularizată → `outputs('Alerta_Regula')` |
   | Status_Analiza Value | **Eșuată** *(din listă)* |
   | Mesaj_Eroare | `Analiza AI nu a rulat încă.` *(text simplu)* |
   | Rulare_ID | `variables('varRulare')` |

   Starea pornește ca „Eșuată”. `AI_Try` o trece pe „OK”. Dacă fluxul se oprește la mijloc, rândul nu rămâne marcat greșit ca analizat.
3. **Compunere** `Id_Analiza` (**după** condiție), **fx**:
   ```
   coalesce(first(outputs('Get_Analiza')?['body/value'])?['ID'], actions('Create_Analiza')?['outputs']?['body']?['ID'])
   ```

### 8.5 `AI_Try` (BPMN `SA_AnalizaAI`, `SA_Salveaza`)
**Domeniu** `AI_Try`. Înăuntru, în ordine:

1. **Compunere** `Corp_Groq`, **fx**:
   ```
   setProperty(setProperty(json('{"temperature":0.2,"response_format":{"type":"json_object"}}'), 'model', coalesce(outputs('cfg')?['groq_model'], 'openai/gpt-oss-120b')), 'messages', createArray(setProperty(json('{"role":"system"}'), 'content', outputs('System_Prompt')), setProperty(json('{"role":"user"}'), 'content', string(outputs('User_AI')))))
   ```
   Corpul se construiește ca obiect, cu `setProperty`, nu prin lipire de text. Promptul conține ghilimele și rânduri noi, care ar strica un JSON scris de mână.
2. **HTTP** `HTTP_Groq`:
   - **Metodă** `POST`, **URI** `https://api.groq.com/openai/v1/chat/completions`
   - **Antete**: `Content-Type` = `application/json`; `Authorization` = `Bearer ` + variabila de mediu `bg_GroqApiKey`. O inserezi din conținutul dinamic → **Variabile de mediu**, ca în `BG_Test_API`.
   - **Corp**: **fx** `outputs('Corp_Groq')`
   - **Setări**: **Intrări securizate** (*Secure inputs*) **Activat**; ieșirile securizate rămân oprite (decizia din 2026-11-19). **Politică de reîncercare**: **Interval fix** (*Fixed interval*), număr `4`, interval `PT20S`. **Expirare acțiune**: `PT3M`.
   > Abateri documentate: retry fix în loc de exponențial (limita Groq de 8.000 tokeni/minut, decizia din 2026-11-24). Timeout `PT3M` în loc de `PT60S`, ca reîncercările la 429 să încapă în limita acțiunii.
3. **Compunere** `AI_Text`, **fx** (normalizează diacriticele cu sedilă):
   ```
   replace(replace(replace(replace(body('HTTP_Groq')?['choices']?[0]?['message']?['content'], 'ţ', 'ț'), 'ş', 'ș'), 'Ţ', 'Ț'), 'Ş', 'Ș')
   ```
4. **Analizare JSON** `Parse_AI`: **Conținut** **fx** `json(outputs('AI_Text'))`. **Schemă**: lipești `ai/response_schema.json`. Un răspuns fără una din cele 4 chei sau cu `nivel_alerta` în afara listei face ca `Parse_AI` să eșueze, iar analiza ajunge pe ramura de eroare.
5. **Actualizare element** `Upd_Analiza_OK` în `Analize_AI`, cu **Clear all**:

   | Câmp | Valoare (fx) |
   |---|---|
   | Id | `outputs('Id_Analiza')` |
   | Cheie (Title) | `concat(outputs('Luna_Import'), '_', items('Analiza_CC'))` |
   | Alerta_AI Value | valoare particularizată → `body('Parse_AI')?['nivel_alerta']` |
   | Necesita_Revizuire | `not(equals(body('Parse_AI')?['nivel_alerta'], outputs('Alerta_Regula')))` |
   | Comentariu_AI | `body('Parse_AI')?['comentariu']` |
   | Cauze | `join(body('Parse_AI')?['cauze'], decodeUriComponent('%0A'))` |
   | Actiune | `body('Parse_AI')?['actiune']` |
   | Status_Analiza Value | **OK** *(din listă)* |
   | Mesaj_Eroare | `—` *(text simplu)* |

6. **Incrementare variabilă** `varAI_OK`, redenumită `Inc_AI_OK`, cu `1`.

### 8.6 `AI_Catch` (BPMN `Error_AI`, `SA_Esuata`)
**Domeniu** `AI_Catch`, **după** `AI_Try`. **Setări → Rulare după** → `AI_Try`: **a eșuat**, **a expirat** (debifezi „are succes”).

1. **Compunere** `Motiv_AI`, **fx**:
   ```
   if(equals(actions('HTTP_Groq')?['status'], 'Succeeded'), 'răspunsul AI nu respectă formatul JSON așteptat', if(equals(actions('HTTP_Groq')?['status'], 'TimedOut'), 'serviciul AI nu a răspuns în timp util', concat('HTTP ', string(coalesce(actions('HTTP_Groq')?['outputs']?['statusCode'], 'fără răspuns')), if(equals(string(actions('HTTP_Groq')?['outputs']?['statusCode']), '401'), ' – cheie API invalidă', if(equals(string(actions('HTTP_Groq')?['outputs']?['statusCode']), '429'), ' – limită de cereri', '')))))
   ```
2. **Compunere** `Mesaj_AI_Esec`, **fx**:
   ```
   concat('Analiza AI pentru ', items('Analiza_CC'), ' a eșuat (', outputs('Motiv_AI'), '). Calculele sunt salvate; analiza poate fi reluată.')
   ```
3. **Actualizare element** `Upd_Analiza_Esuata` în `Analize_AI`, cu **Clear all**: Id `outputs('Id_Analiza')`, Cheie (Title) ca mai sus, **Status_Analiza** **Eșuată**, **Mesaj_Eroare** `outputs('Mesaj_AI_Esec')`, **Necesita_Revizuire** `true`, **Comentariu_AI** `Analiza AI nu este disponibilă pentru această rulare.`
4. **Incrementare variabilă** `varAI_Esec`, redenumită `Inc_AI_Esec`, cu `1`.

Fluxul **continuă** cu următorul centru de cost.

### 8.7 Rezultatul pe CC, pentru raport
1. **Compunere** `Rez_CC`, **după** `AI_Catch`. **Setări → Rulare după** → `AI_Catch`: **are succes** și **este omis** (*is skipped*). **Lipire directă**:
   ```
   {
     "cc": "@{items('Analiza_CC')}",
     "buget": "@{outputs('Buget_CC')}",
     "angajat": "@{outputs('Angajat_CC')}",
     "realizat": "@{outputs('Realizat_CC')}",
     "varianta_ron": "@{outputs('Varianta_RON')}",
     "varianta_pct": "@{outputs('Varianta_Pct')}",
     "maverick": "@{outputs('Maverick_CC')}",
     "alerta_regula": "@{outputs('Alerta_Regula')}",
     "alerta_ai": "@{coalesce(actions('Parse_AI')?['outputs']?['body']?['nivel_alerta'], '—')}",
     "status": "@{if(equals(actions('AI_Try')?['status'], 'Succeeded'), 'OK', 'Eșuată')}",
     "comentariu": "@{coalesce(actions('Parse_AI')?['outputs']?['body']?['comentariu'], actions('Mesaj_AI_Esec')?['outputs'], '')}",
     "actiune": "@{coalesce(actions('Parse_AI')?['outputs']?['body']?['actiune'], '')}"
   }
   ```
2. **Adăugare la variabila matrice** `varRezCC`, redenumită `Append_varRezCC`: **fx** `outputs('Rez_CC')`
3. **Control** → **Întârziere** (*Delay*), redenumită `Delay_Groq`: **Număr** `15`, **Unitate** **Secundă**. Ține apelurile sub limita Groq de 8.000 tokeni/minut.

### ✅ Punct de control D
Încarci fișierul. Rularea durează ~2 minute (5 × Delay + apelurile AI). Verifici **Analize_AI**: 5 rânduri `2026-10_IT` … `2026-10_SAL`, toate cu **Status_Analiza = OK**. MKT e Roșu, OPS Galben, IT și SAL Verde. HR: Alerta_Regula **Verde**, Alerta_AI **Galben** și **Necesita_Revizuire = Da**, fiindcă AI-ul aplică și regula maverick.
Exporți și `Analize_AI.csv` în `data/run_check/` și rulez din nou scriptul de comparare.

---

## Pasul 9 — Raportul provizoriu (BPMN `Task_Raport`, `Send_Raport`)

> Faza 8 înlocuiește `Html_Raport` cu șablonul `report/template.html`. Restul acțiunilor rămân.

1. **Filtrare matrice** `Filter_Duplicate`, **după** `Analiza_CC`. **Setări → Rulare după** → `Analiza_CC`: **are succes** și **a eșuat**, ca raportul să plece și dacă o iterație a eșuat dintr-un motiv neprevăzut. **Din** **fx** `variables('varErori')`. Condiție: **fx** `item()?['tip']` **este egal cu** `Duplicat`.
2. **Compunere** `Sumar_Import`, **lipire directă**:
   ```
   {
     "total": "@{length(body('Parse_Fisier')?['inregistrari'])}",
     "valide": "@{length(variables('varValide'))}",
     "invalide": "@{sub(length(variables('varErori')), length(body('Filter_Duplicate')))}",
     "duplicate": "@{length(body('Filter_Duplicate'))}",
     "erori": "@{length(variables('varErori'))}",
     "ai_ok": "@{variables('varAI_OK')}",
     "ai_esec": "@{variables('varAI_Esec')}"
   }
   ```
3. **Selectare** `Select_Rand_CC`, **Din** **fx** `variables('varRezCC')`, **modul text**, **fx**:
   ```
   concat('<tr><td style="padding:6px 8px;border-bottom:1px solid #eee"><b>', item()?['cc'], '</b></td><td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right">', formatNumber(float(item()?['buget']), 'N0', 'ro-RO'), '</td><td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right">', formatNumber(float(item()?['realizat']), 'N0', 'ro-RO'), '</td><td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right">', formatNumber(float(item()?['varianta_pct']), 'N2', 'ro-RO'), '%</td><td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right">', formatNumber(float(item()?['maverick']), 'N0', 'ro-RO'), '</td><td style="padding:6px 8px;border-bottom:1px solid #eee;color:#fff;background:', if(equals(item()?['alerta_regula'], 'Roșu'), '#b42318', if(equals(item()?['alerta_regula'], 'Galben'), '#b45309', '#15803d')), '">', item()?['alerta_regula'], '</td><td style="padding:6px 8px;border-bottom:1px solid #eee">', item()?['alerta_ai'], if(and(equals(item()?['status'], 'OK'), not(equals(item()?['alerta_ai'], item()?['alerta_regula']))), ' ⚠️ necesită revizuire', ''), '</td></tr><tr><td></td><td colspan="6" style="padding:2px 8px 10px;font-size:12px;color:#555;border-bottom:1px solid #ddd">', item()?['comentariu'], '</td></tr>')
   ```
4. **Selectare** `Select_Rand_Err`, **Din** **fx** `variables('varErori')`, **modul text**, **fx**:
   ```
   concat('<li><b>', item()?['tip'], '</b> – ', item()?['mesaj'], '</li>')
   ```
4b. **Selectare** `Select_Rand_Teams` (rândul scurt pentru Teams), **Din** `variables('varRezCC')`, modul text, **fx** `concat(if(equals(item()?['alerta_regula'], 'Roșu'), '🔴', if(equals(item()?['alerta_regula'], 'Galben'), '🟡', '🟢')), ' ', item()?['cc'], ' ', item()?['varianta_pct'], '%')`
5. **Compunere** `Html_Raport`, **lipire directă**:
```html
<div style="font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#222;max-width:760px">
  <div style="background:#1e3a8a;color:#fff;padding:12px 16px;font-size:16px;font-weight:600">
    BudgetGuard · Buget vs. Realizat @{outputs('Luna_Import')}
  </div>
  <div style="padding:16px;border:1px solid #ddd;border-top:none">
    <p style="margin-top:0;font-size:12px;color:#666">Fișier <b>@{variables('varFisier')}</b> · rulare @{variables('varRulare')} · curs BNR @{variables('varDataCurs')}: EUR @{variables('varCursuri')?['EUR']}, USD @{variables('varCursuri')?['USD']}</p>
    <p><b>Import:</b> @{outputs('Sumar_Import')?['total']} înregistrări · @{outputs('Sumar_Import')?['valide']} valide · @{outputs('Sumar_Import')?['invalide']} invalide · @{outputs('Sumar_Import')?['duplicate']} duplicate · analize AI: @{outputs('Sumar_Import')?['ai_ok']} OK, @{outputs('Sumar_Import')?['ai_esec']} eșuate</p>
    <table style="border-collapse:collapse;width:100%;font-size:13px">
      <tr style="background:#f3f4f6;text-align:left"><th style="padding:6px 8px">CC</th><th style="padding:6px 8px;text-align:right">Buget</th><th style="padding:6px 8px;text-align:right">Realizat</th><th style="padding:6px 8px;text-align:right">Varianță</th><th style="padding:6px 8px;text-align:right">Maverick</th><th style="padding:6px 8px">Regulă</th><th style="padding:6px 8px">AI</th></tr>
      @{join(body('Select_Rand_CC'), '')}
    </table>
    <p style="margin-bottom:4px"><b>Anomalii de import:</b></p>
    <ul style="margin-top:0">@{if(empty(variables('varErori')), '<li>niciuna</li>', join(body('Select_Rand_Err'), ''))}</ul>
    <p style="font-size:12px;color:#888">Sume în RON. Raport automat BudgetGuard · Vestra Retail SRL · @{convertTimeZone(utcNow(), 'UTC', 'GTB Standard Time', 'dd.MM.yyyy HH:mm')}</p>
  </div>
</div>
```
6. **Gmail** → **Send email (V2)**, redenumită `Email_Raport`:
   - **Către**: **fx** `outputs('cfg')?['email_echipa']`
   - **Subiect**, lipire directă: `[BudgetGuard] Buget vs. Realizat @{outputs('Luna_Import')} – @{outputs('Sumar_Import')?['valide']} valide, @{outputs('Sumar_Import')?['erori']} respinse`
   - **Corp**: **Ieșiri** de la `Html_Raport`
   - **Bcc** (parametri avansați): **fx** `if(equals(outputs('cfg')?['mod_demo'], 'true'), outputs('cfg')?['email_bcc'], '')`
7. **Compunere** `Html_Teams_Raport` (**Rulare după** pe `Email_Raport`: **are succes** + **a eșuat**), lipire directă:
   ```html
   <p>📊 <b>Import @{outputs('Luna_Import')}</b> (@{variables('varFisier')}): @{outputs('Sumar_Import')?['valide']} valide, @{outputs('Sumar_Import')?['erori']} respinse · AI @{outputs('Sumar_Import')?['ai_ok']} OK / @{outputs('Sumar_Import')?['ai_esec']} eșuate</p>
   <p>@{join(body('Select_Rand_Teams'), ' · ')}</p>
   ```
8. **Teams** → **Postați un mesaj într-un chat sau canal**, redenumită `Teams_Raport`: aceleași setări ca în Flux 1 §6.4, **Mesaj** = Ieșiri de la `Html_Teams_Raport`.

---

## Pasul 9b — Raportul final (Faza 8)

Înlocuiește raportul provizoriu cu șablonul `report/template.html`. Expresiile sunt **generate** în `docs/raport_expresii.md` (`python report/render_preview.py --flow`), din aceleași fragmente din care se face `report/preview.html`. Restul pasului 9 (`Filter_Duplicate`, `Sumar_Import`, `Select_Rand_Teams`, email, Teams) rămâne.

Ordinea, între `Sumar_Import` și `Email_Raport`:

| # | Acțiune | Ce faci |
|---|---|---|
| 1 | Compose `Json_RezCC` | nouă |
| 2 | Compose `Tot_Raport` | nouă (lipire directă) |
| 3 | Select `Select_Rand_CC` | **înlocuiești** Map-ul |
| 4 | Select `Select_Bloc_AI` | nouă, From `variables('varRezCC')` |
| 5 | Filter array `Filter_Mav` | nouă: From fx `outputs('Get_Realizat_Luna')?['body/value']`, *Edit in advanced mode*: `@greater(float(coalesce(item()?['Maverick_RON'], 0)), 0)` |
| 6 | Select `Select_Rand_Mav` | nouă, From `body('Filter_Mav')` |
| 7 | Select `Select_Rand_Err` | **înlocuiești** Map-ul |
| 8 | Compose `Sablon_Raport` | nouă: lipești tot conținutul lui `report/template.html` |
| 9 | Compose `Html_Raport` | **înlocuiești** Inputs cu expresia `replace(...)` |

`Email_Raport` folosește în continuare *Outputs* de la `Html_Raport`. `Get_Realizat_Luna` (pasul 8.0) rulează după upsert, deci `Filter_Mav` vede maverick-ul la zi.

> Șablonul nu are voie să conțină caracterul at (`@`): designerul l-ar interpreta ca început de expresie. `render_preview.py --flow` verifică asta.

---

## Pasul 10 — Arhivarea fișierului (BPMN `Task_MutaFisier`)

1. **SharePoint** → **Creare fișier** (*Create file*), redenumită `Create_Arhiva`. **Rulare după** pe `Teams_Raport`: **are succes** + **a eșuat**.
   - **Cale folder** (*Folder Path*): `/Import_Realizat/Procesate` (îl alegi din iconița de folder)
   - **Nume fișier**: **fx** `concat(replace(variables('varFisier'), '.json', ''), '_', variables('varRulare'), '.json')`
   - **Conținut fișier**: **fx** `outputs('Fisier_Text')`
2. **SharePoint** → **Ștergere fișier** (*Delete file*), redenumită `Delete_Original`. **Identificator fișier**: **fx** `triggerOutputs()?['body/{Identifier}']`.

*Mutare fișier* (*Move file*) nu poate redenumi, iar specificația cere sufixul `_{Rulare_ID}`. De aceea se folosește copia + ștergerea. Copia din `Procesate` nu repornește fluxul, datorită celei de-a doua condiții de declanșare.

## Pasul 11 — `Log_Import`
**Creare element** în `Istoric_Stari`:

| Câmp | Valoare |
|---|---|
| Referinta (Title) | **fx** `variables('varRulare')` |
| Flux Value | **F2** |
| Stare_Veche | `Fișier nou` |
| Stare_Noua | `Import finalizat` |
| Actor | `BudgetGuard (import automat)` |
| Data_Ora | **fx** `utcNow()` |
| Comentariu | **fx** `concat(variables('varFisier'), ': ', outputs('Sumar_Import')?['valide'], ' valide, ', outputs('Sumar_Import')?['erori'], ' respinse; AI ', outputs('Sumar_Import')?['ai_ok'], ' OK / ', outputs('Sumar_Import')?['ai_esec'], ' eșuate; curs ', variables('varDataCurs'), '.')` |

Notă BPMN: `End_ImportFinalizat`. Aici se termină `Scope_Try`.

---

## Pasul 12 — `Scope_Catch` (BPMN `Error_Import`, `Send_NotifEsec`, `End_ImportEsuat`)

**Domeniu** `Scope_Catch`, **după** `Scope_Try` (în afara lui). **Setări → Rulare după** → `Scope_Try`: **a eșuat**, **a expirat** (debifezi „are succes”).

1. **Filtrare matrice** `Filter_Esec`: **Din** **fx** `result('Scope_Try')`. Condiție: **fx** `item()?['status']` **este egal cu** `Failed`.
2. **Compunere** `Actiune_Esuata`, **fx** `coalesce(first(body('Filter_Esec'))?['name'], 'necunoscută')`
3. **Compunere** `Detaliu_Esec`, **fx**:
   ```
   coalesce(first(body('Filter_Esec'))?['error']?['message'], first(body('Filter_Esec'))?['outputs']?['body']?['error']?['message'], 'fără detalii')
   ```
4. **Compunere** `Mesaj_Esec`, **fx**:
   ```
   if(or(equals(outputs('Actiune_Esuata'), 'Fisier_JSON'), equals(outputs('Actiune_Esuata'), 'Fisier_Text'), contains(outputs('Detaliu_Esec'), 'not a valid JSON')), concat('Fișierul „', variables('varFisier'), '” nu este un JSON valid (verificați acoladele, ghilimelele și virgulele). Nicio înregistrare nu a fost importată.'), if(equals(outputs('Actiune_Esuata'), 'Parse_Fisier'), concat('Fișierul „', variables('varFisier'), '” nu are structura așteptată: lista „inregistrari” lipsește sau este goală. Nicio înregistrare nu a fost importată.'), concat('Importul fișierului „', variables('varFisier'), '” a eșuat la pasul ', outputs('Actiune_Esuata'), '. Rândurile procesate până la eroare au rămas salvate; după corectare, reîncărcați fișierul (importul nu creează dubluri).')))
   ```
   > Pentru un fișier `.json` invalid, eroarea apare deja la `Get_file_content` (conectorul încearcă să parseze conținutul și răspunde „the content was not a valid JSON”), nu la `Fisier_JSON`. De aceea condiția verifică și textul erorii (testat 2026-11-26).
5. **Compunere** `Html_Esec`, lipire directă:
```html
<div style="font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#222;max-width:640px">
  <div style="background:#b42318;color:#fff;padding:12px 16px;font-size:16px;font-weight:600">BudgetGuard · Import eșuat</div>
  <div style="padding:16px;border:1px solid #ddd;border-top:none">
    <p>@{outputs('Mesaj_Esec')}</p>
    <table style="border-collapse:collapse;font-size:13px">
      <tr><td style="padding:4px 12px 4px 0;color:#666">Fișier</td><td>@{variables('varFisier')}</td></tr>
      <tr><td style="padding:4px 12px 4px 0;color:#666">Acțiunea care a eșuat</td><td>@{outputs('Actiune_Esuata')}</td></tr>
      <tr><td style="padding:4px 12px 4px 0;color:#666">Detalii tehnice</td><td style="font-family:Consolas,monospace;font-size:12px">@{outputs('Detaliu_Esec')}</td></tr>
      <tr><td style="padding:4px 12px 4px 0;color:#666">Rulare</td><td>@{variables('varRulare')}</td></tr>
    </table>
    <p>Fișierul a rămas în biblioteca Import_Realizat. Corectați-l, ștergeți-l și încărcați-l din nou.</p>
    <p style="font-size:12px;color:#888">Mesaj automat BudgetGuard · @{convertTimeZone(utcNow(), 'UTC', 'GTB Standard Time', 'dd.MM.yyyy HH:mm')}</p>
  </div>
</div>
```
6. **Gmail → Send email (V2)** `Email_Esec`: **Către** `outputs('cfg')?['email_echipa']`, **Subiect** `[BudgetGuard] Import eșuat – @{variables('varFisier')}`, **Corp** = Ieșiri de la `Html_Esec`.
7. `Teams_Esec` (**Rulare după** pe email: **are succes** + **a eșuat**), **Mesaj** lipire directă: `<p>🔴 <b>Import eșuat</b> – @{variables('varFisier')}</p><p>@{outputs('Mesaj_Esec')}</p>`
8. **Creare element** `Log_Esec` în `Istoric_Stari`: Title `variables('varRulare')`, Flux **F2**, Stare_Veche `Fișier nou`, Stare_Noua `Import eșuat`, Actor `BudgetGuard (import automat)`, Data_Ora `utcNow()`, Comentariu **fx** `concat(outputs('Actiune_Esuata'), ': ', outputs('Detaliu_Esec'))`.

> `result('Scope_Try')` vede doar acțiunile de pe primul nivel al scope-ului. Dacă eroarea e într-o buclă, numele raportat e al buclei (de exemplu `Upsert_Realizat`), iar detaliile sunt în istoricul rulării.

---

## Pasul 13 — Testele Fazei 7

Înainte de fiecare test: biblioteca `Import_Realizat` nu are fișiere `.json` în rădăcină. Fișierele de test pentru robustețe sunt în `data/input/test/`.

| ID | Caz | Ce faci | Rezultat așteptat |
|---|---|---|---|
| **TC-F2-01** | Import complet | Încarci `realizat_2026-10.json` | Rulare reușită. Realizat_Lunar 20 rânduri, Erori_Import 4, Analize_AI 5 (OK). Raport pe email + Teams. Fișierul ajunge în `Procesate/realizat_2026-10_<rulare>.json`. `compare_results.py` → 0 diferențe |
| **TC-F2-02** | Reimport fără dubluri | Încarci **din nou** același fișier | Realizat_Lunar tot **20** rânduri (Rulare_ID nou, Data_Import nouă), Analize_AI tot **5**. Erori_Import: un set nou de 4, cu alt Rulare_ID |
| **TC-F2-03** | Cheie AI greșită | În soluție, *Current Value* la `bg_GroqApiKey` = `gsk_invalid`. Încarci fișierul | Analize_AI: 5 × **Eșuată**, Mesaj_Eroare `Analiza AI pentru IT a eșuat (HTTP 401 – cheie API invalidă). …`. Calculele (buget, varianță, Alerta_Regula) sunt salvate. **Raportul ajunge totuși**, cu „0 OK, 5 eșuate”. ⚠️ **După**: pui cheia corectă la loc |
| **TC-F2-04** | JSON corupt | Încarci `data/input/test/realizat_corupt.json` | Ramura `Scope_Catch`: email „Import eșuat”, cu mesajul „nu este un JSON valid”, acțiunea `Get_file_content` și detaliile. Linie `Import eșuat` în Istoric_Stari. Nimic nou în Realizat_Lunar |
| TC-F2-05 *(extra)* | Fără `inregistrari` | Încarci `data/input/test/realizat_fara_inregistrari.json` | `Scope_Catch` cu mesajul „lista inregistrari lipsește sau este goală” (acțiunea `Parse_Fisier`) |
| TC-F2-06 *(extra)* | Fișier non-JSON | Încarci `realizat_2026-10.xlsx` | Fluxul **nu pornește** (condiția de declanșare) |

Pentru TC-F2-03 și TC-F2-04 faci capturi cu emailul și cu lista, în `docs/capturi/`.

---

## Probleme frecvente

| Simptom | Cauză / soluție |
|---|---|
| Fluxul nu pornește la încărcare | Trigger-ul verifică la ~1 minut. Verifică și condițiile de declanșare (fără spații în plus, cu `@` la început) |
| Fluxul pornește de 2 ori | A doua rulare e pentru fișierul din `Procesate`: lipsește condiția `not(contains(… 'procesate'))` |
| `Fisier_Text` eșuează: *property '$content' cannot be selected* | Conținutul vine ca text simplu. Trimite-mi Outputs de la `Get_file_content`; expresia devine `string(body('Get_file_content'))` |
| `Parse_Fisier`: *ValidationFailed* la fișierul bun | Schema lipită greșit (lipsește o acoladă). Relipește `schemas/realizat_input.json` |
| Toate rândurile ies „Cod necunoscut” | `Filter_CC` compară `item()?['Tip']` în loc de `item()?['Tip']?['Value']` |
| Rândul 22 nu e marcat duplicat | Bucla `Valideaza_Randuri` nu are concurența 1 |
| `Aprobat_RON` eșuează pe HR/TRN | Problema cu array gol în xpath. Trimite-mi Outputs de la `Select_Valori` |
| `Set_varMav`: *self-reference* | Valoarea trebuie să fie `outputs('Mav_Map')`, nu expresia `setProperty` direct |
| Analize_AI toate „Eșuată” cu HTTP 429 | Limita Groq. Verifică retry-ul fix 4 × PT20S pe `HTTP_Groq` și `Delay_Groq` |
| Analize_AI toate „Eșuată” cu HTTP 400 | Corpul cererii e greșit: trimite-mi Outputs de la `Corp_Groq` (nu conține cheia) |
| `Rez_CC` e *Skipped* | Lipsește *Rulare după → este omis* pe `Rez_CC` |
| Email fără BCC în mod demo | `mod_demo` din Config trebuie să fie exact `true`, cu litere mici |
