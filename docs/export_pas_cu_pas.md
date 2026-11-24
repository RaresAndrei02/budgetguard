# Export — `BG_Export`, pas cu pas

> Exportul cererilor **aprobate**, filtrat după perioadă și, opțional, după centru de cost / categorie, în CSV sau JSON.
> Convențiile (**fx**, **lipire directă**, **Clear all** pe *Update item*) sunt cele din `docs/flux1_pas_cu_pas.md`.

## Harta fluxului

```
Trigger manual (DataDe, DataPana, CentruCost?, Categorie?, Format)
→ Parametri → Filtru → Get_Aprobate → Cond_Gol
     ├─ Da: Html_Gol → Email_Gol → Terminate (Succeeded)
     └─ Nu: Select_Export → Create_CSV → Nume_Fisier → Continut → Create_Fisier → Get_Link
            → Apply_to_each_Export [Upd_Exportata → Log_Export]
            → Html_Export → Email_Export
```

---

## Pasul 1 — Fluxul și trigger-ul

1. **Soluții** → **BudgetGuard** → **+ Nou** → **Automatizare** → **Flux de cloud** → **Instantaneu** (*Instant*).
2. Nume: `BG_Export`. Trigger: **Declanșarea manuală a unui flux** (*Manually trigger a flow*) → **Creare**.
3. În trigger, **+ Adăugare intrare** (*Add an input*), de 5 ori:

| # | Tip | Nume afișat | Obligatoriu | Observații |
|---|---|---|---|---|
| 1 | **Dată** (*Date*) | `DataDe` | da | |
| 2 | **Dată** | `DataPana` | da | |
| 3 | **Text** | `CentruCost` | **nu** | descriere: „Gol = toate. Ex.: IT” |
| 4 | **Text** | `Categorie` | **nu** | descriere: „Gol = toate. Ex.: SW” |
| 5 | **Text** | `Format` | da | **…** → **Adăugare listă verticală de opțiuni** (*Add a drop-down list of options*): `CSV`, `JSON` |

La intrările 3 și 4: **…** → **Faceți câmpul opțional** (*Make the field optional*).

Notă BPMN: exportul e un proces separat, nedesenat în BPMN 1 (diagrama acoperă doar cererea de achiziție). Îl documentăm în `docs/concordanta_bpmn.md`.

---

## Pasul 2 — Parametrii și filtrul OData

### 2.1 `Parametri`
**Compunere**, redenumită `Parametri`. Tastezi scheletul și înlocuiești fiecare `«…»` cu jetonul intrării din trigger (ca la `Date_Formular`):
```
{
  "de": "«DataDe»",
  "pana": "«DataPana»",
  "cc": "«CentruCost»",
  "cat": "«Categorie»",
  "format": "«Format»",
  "utilizator": "«User email»"
}
```
`User email` (*E-mail utilizator*) e în conținutul dinamic al trigger-ului manual. E adresa celui care a pornit fluxul.

### 2.2 `Filtru`
**Compunere**, **fx**:
```
concat('Status eq ''Aprobată'' and Data_Cerere ge ''', outputs('Parametri')?['de'], 'T00:00:00Z'' and Data_Cerere le ''', outputs('Parametri')?['pana'], 'T23:59:59Z''', if(empty(trim(coalesce(outputs('Parametri')?['cc'], ''))), '', concat(' and CentruCost eq ''', toUpper(trim(outputs('Parametri')?['cc'])), '''')), if(empty(trim(coalesce(outputs('Parametri')?['cat'], ''))), '', concat(' and Categorie eq ''', toUpper(trim(outputs('Parametri')?['cat'])), '''')))
```
Exemplu de rezultat: `Status eq 'Aprobată' and Data_Cerere ge '2026-10-01T00:00:00Z' and Data_Cerere le '2026-10-31T23:59:59Z' and Categorie eq 'SRV'`.

Cererile deja **Exportate** nu mai intră în filtru. Un al doilea export pe același interval nu le dublează.

### 2.3 `Get_Aprobate`
**SharePoint** → **Obținere elemente**, redenumită `Get_Aprobate`. Lista `Cereri_Achizitie`.
- **Interogare de filtrare**: **fx** `outputs('Filtru')`
- **Ordonare după** (*Order By*): `Data_Cerere asc`
- **Număr maxim**: `500`

---

## Pasul 3 — `Cond_Gol`: niciun rezultat

**Condiție** `Cond_Gol`: **fx** `empty(outputs('Get_Aprobate')?['body/value'])` = **fx** `true`.

### Ramura True
1. **Compunere** `Html_Gol`, lipire directă:
```html
<div style="font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#222;max-width:640px">
  <div style="background:#475467;color:#fff;padding:12px 16px;font-size:16px;font-weight:600">BudgetGuard · Export fără rezultate</div>
  <div style="padding:16px;border:1px solid #ddd;border-top:none">
    <p>Nicio cerere aprobată în intervalul selectat.</p>
    <p style="font-size:13px;color:#666">Interval: @{formatDateTime(outputs('Parametri')?['de'], 'dd.MM.yyyy')} – @{formatDateTime(outputs('Parametri')?['pana'], 'dd.MM.yyyy')} · centru de cost: @{if(empty(outputs('Parametri')?['cc']), 'toate', outputs('Parametri')?['cc'])} · categorie: @{if(empty(outputs('Parametri')?['cat']), 'toate', outputs('Parametri')?['cat'])}</p>
    <p style="font-size:13px;color:#666">Cererile exportate anterior au statusul „Exportată” și nu mai sunt incluse.</p>
    <p style="font-size:12px;color:#888">Mesaj automat BudgetGuard · @{convertTimeZone(utcNow(), 'UTC', 'GTB Standard Time', 'dd.MM.yyyy HH:mm')}</p>
  </div>
</div>
```
2. **Gmail → Send email (V2)** `Email_Gol`: **Către** **fx** `outputs('Parametri')?['utilizator']`, **Subiect** `[BudgetGuard] Export – nicio cerere aprobată în interval`, **Corp** = Ieșiri de la `Html_Gol`.
3. **Terminare** `Terminate_Gol`, **Reușit**.

---

## Pasul 4 — Ramura **False**: fișierul

### 4.1 `Select_Export`
**Selectare**, redenumită `Select_Export`. **Din**: **fx** `outputs('Get_Aprobate')?['body/value']`.
**Mapare**, în modul tabel (cheie în stânga, **fx** în dreapta):

| Cheie | Valoare (fx) |
|---|---|
| `ID_Cerere` | `item()?['Title']` |
| `Titlu` | `item()?['TitluCerere']` |
| `CentruCost` | `item()?['CentruCost']` |
| `Categorie` | `item()?['Categorie']` |
| `Luna_Buget` | `item()?['Luna_Buget']` |
| `Tip` | `item()?['Tip']?['Value']` |
| `CUI` | `item()?['CUI']` |
| `Furnizor` | `item()?['Furnizor_ANAF']` |
| `Valoare` | `item()?['Valoare']` |
| `Moneda` | `item()?['Moneda']?['Value']` |
| `Curs_BNR` | `item()?['Curs_BNR']` |
| `Valoare_RON` | `item()?['Valoare_RON']` |
| `Peste_Buget` | `item()?['Peste_Buget']` |
| `Data_Necesara` | `formatDateTime(item()?['Data_Necesara'], 'yyyy-MM-dd')` |
| `Data_Cerere` | `formatDateTime(item()?['Data_Cerere'], 'yyyy-MM-dd HH:mm')` |
| `Data_Aprobare` | `if(empty(item()?['Data_Finalizare']), '', formatDateTime(item()?['Data_Finalizare'], 'yyyy-MM-dd HH:mm'))` |
| `Solicitant` | `item()?['Solicitant_Email']` |

Coloanele Alegere (`Tip`, `Moneda`) vin din SharePoint ca obiect, de aceea `?['Value']`.

### 4.2 `Create_CSV`
**Operații cu date** → **Creare tabel CSV** (*Create CSV table*), redenumită `Create_CSV`. **Din**: **fx** `body('Select_Export')`. **Coloane**: *Automat* (*Automatic*).

### 4.3 `Nume_Fisier`
**Compunere**, **fx**:
```
concat('BG_export_', convertTimeZone(utcNow(), 'UTC', 'GTB Standard Time', 'yyyyMMdd_HHmm'), '.', toLower(outputs('Parametri')?['format']))
```

### 4.4 `Continut`
**Compunere**, **fx**:
```
if(equals(outputs('Parametri')?['format'], 'JSON'), string(body('Select_Export')), concat(decodeUriComponent('%EF%BB%BF'), body('Create_CSV')))
```
Prefixul `%EF%BB%BF` e **BOM-ul UTF-8**. Fără el, Excel afișează diacriticele greșit („AprobatÄ”).

### 4.5 `Create_Fisier`
**SharePoint** → **Creare fișier** (*Create file*), redenumită `Create_Fisier`.
- **Adresă site**: site-ul BudgetGuard. **Cale folder**: `/Exporturi`
- **Nume fișier**: **fx** `outputs('Nume_Fisier')`
- **Conținut fișier**: **fx** `outputs('Continut')`

### 4.6 `Get_Link`
**SharePoint** → **Obținere proprietăți fișier** (*Get file properties*), redenumită `Get_Link`. Biblioteca `Exporturi`, **Id**: **fx** `body('Create_Fisier')?['ItemId']`.
Linkul fișierului este `outputs('Get_Link')?['body/{Link}']`.

---

## Pasul 5 — Statusul „Exportată” și jurnalul

**Control** → **Aplicare la fiecare** (*Apply to each*), redenumită `Apply_to_each_Export`. **Selectați o ieșire**: **fx** `outputs('Get_Aprobate')?['body/value']`.
Concurența poate rămâne implicită: nu se modifică variabile.

În interior:
1. **Actualizare element** `Upd_Exportata` în `Cereri_Achizitie`, cu **Clear all**:

| Câmp | Valoare (fx) |
|---|---|
| Id | `items('Apply_to_each_Export')?['ID']` |
| ID_Cerere (Title) | `items('Apply_to_each_Export')?['Title']` |
| Status Value | **Exportată** *(din listă)* |

2. **Creare element** `Log_Export` în `Istoric_Stari`:

| Câmp | Valoare |
|---|---|
| Referinta (Title) | **fx** `items('Apply_to_each_Export')?['Title']` |
| Flux Value | **EXPORT** |
| Stare_Veche | `Aprobată` |
| Stare_Noua | `Exportată` |
| Actor | **fx** `outputs('Parametri')?['utilizator']` |
| Data_Ora | **fx** `utcNow()` |
| Comentariu | **fx** `concat('Inclusă în ', outputs('Nume_Fisier'), '.')` |

> Dacă `Upd_Exportata` eșuează cu *Title required*, verifică dacă `ID_Cerere (Title)` e completat.

---

## Pasul 6 — Emailul către inițiator

**După** bucla `Apply_to_each_Export`:

1. **Compunere** `Html_Export`, lipire directă:
```html
<div style="font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#222;max-width:640px">
  <div style="background:#1d4ed8;color:#fff;padding:12px 16px;font-size:16px;font-weight:600">BudgetGuard · Export cereri aprobate</div>
  <div style="padding:16px;border:1px solid #ddd;border-top:none">
    <p>Exportul este gata: <b>@{length(outputs('Get_Aprobate')?['body/value'])}</b> cereri, format <b>@{outputs('Parametri')?['format']}</b>.</p>
    <table style="border-collapse:collapse;font-size:13px">
      <tr><td style="padding:4px 12px 4px 0;color:#666">Interval</td><td>@{formatDateTime(outputs('Parametri')?['de'], 'dd.MM.yyyy')} – @{formatDateTime(outputs('Parametri')?['pana'], 'dd.MM.yyyy')}</td></tr>
      <tr><td style="padding:4px 12px 4px 0;color:#666">Centru de cost</td><td>@{if(empty(outputs('Parametri')?['cc']), 'toate', outputs('Parametri')?['cc'])}</td></tr>
      <tr><td style="padding:4px 12px 4px 0;color:#666">Categorie</td><td>@{if(empty(outputs('Parametri')?['cat']), 'toate', outputs('Parametri')?['cat'])}</td></tr>
      <tr><td style="padding:4px 12px 4px 0;color:#666">Total Valoare_RON</td><td><b>@{formatNumber(float(xpath(xml(json(concat('{"r":{"w":', string(body('Select_Export')), '}}'))), 'sum(/r/w/Valoare_RON)')), 'N2', 'ro-RO')} RON</b></td></tr>
      <tr><td style="padding:4px 12px 4px 0;color:#666">Fișier</td><td><a href="@{outputs('Get_Link')?['body/{Link}']}">@{outputs('Nume_Fisier')}</a></td></tr>
    </table>
    <p style="font-size:13px;color:#666">Cererile incluse au acum statusul „Exportată”. CSV-ul se deschide în Excel cu <i>Date → Din text/CSV</i> (delimitator: virgulă).</p>
    <p style="font-size:12px;color:#888">Mesaj automat BudgetGuard · @{convertTimeZone(utcNow(), 'UTC', 'GTB Standard Time', 'dd.MM.yyyy HH:mm')}</p>
  </div>
</div>
```
Totalul se calculează cu xpath peste JSON-ul convertit în XML: array-ul devine elemente `<w>` repetate sub rădăcina unică `<r>`, iar `sum()` le adună. Cu un singur element, `<w>` apare o dată și suma rămâne corectă. Array-ul gol nu ajunge aici (îl oprește `Cond_Gol`). Aceeași tehnică va fi folosită în Flux 2 (§5.5.2, pasul 6), unde cazul gol se tratează separat.

2. **Gmail → Send email (V2)** `Email_Export`: **Către** **fx** `outputs('Parametri')?['utilizator']`, **Subiect** `[BudgetGuard] Export @{outputs('Parametri')?['format']} – @{length(outputs('Get_Aprobate')?['body/value'])} cereri aprobate`, **Corp** = Ieșiri de la `Html_Export`.
   - **Atașamente** (parametri avansați): **Nume** **fx** `outputs('Nume_Fisier')`, **Conținut** **fx** `outputs('Continut')`. Fișierul vine și ca atașament, nu doar ca link (adăugat la testare, 2026-11-24).

---

## Rulare

**Salvare** → **Testare** → **Manual** → completezi parametrii → **Rulare flux** (*Run flow*). Testele sunt TC-EX-01 … 03 din `docs/plan_testare.md`.

## Probleme frecvente

| Simptom | Cauză / soluție |
|---|---|
| `Get_Aprobate`: *The expression is not valid* | O ghilimea lipsă în `Filtru`. Trimite-mi Outputs de la `Filtru` |
| Filtrul nu găsește nimic, deși există cereri | `DataDe` / `DataPana` nu vin ca `yyyy-MM-dd`. Trimite-mi Outputs de la `Parametri` |
| În Excel, toate coloanele sunt într-una singură | Deschide prin *Date → Din text/CSV*, nu dublu-clic: Excel în română așteaptă `;` |
| `Total Valoare_RON` dă eroare xpath | O cheie din `Select_Export` conține spațiu sau diacritice. Cheile trebuie să fie exact cele din tabelul 4.1 |
