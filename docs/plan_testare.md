# Plan de testare

> Fiecare caz are datele de intrare exacte, rezultatul așteptat și locul unde se verifică. Coloana **Rezultat** se completează după rulare: `OK`, sau problema + rezolvarea.
> Capturile se salvează în `docs/capturi/` cu numele cazului (ex. `TC-F1-07_lista.png`, `TC-F1-07_email.png`).
> Faza 5 acoperă Flux 1 și exportul. Testele Flux 2 (TC-F2-…) se adaugă în Faza 7.

## Condiții inițiale

- Data de referință a testelor: **24.11.2026**. Data minimă acceptată (V4) = azi + 5 zile = **29.11.2026**. Dacă testezi în altă zi, mută datele în aceeași lună sau mai târziu.
- Config: `mod_demo = false`, `aprobator_1..3` și `aprobator_cfo` = adrese ASE de test, `zile_min_avans = 5`, `valoare_max_ron = 500000`, `prag_capex_ron = 2500`, `prag_cfo_ron = 100000`.
- Bugetele lunilor 2026-12 și 2027-01 au `Angajat_RON = 0` (din seed). Valorile „înainte → după” de mai jos pornesc de aici. Dacă între timp ai aprobat alte cereri pe aceeași cheie, compari diferența, nu valoarea absolută.
- Aprobările se dau din **Teams → Aprobări** (vezi `flux1_pas_cu_pas.md` §9.3).

## Ce se verifică la fiecare caz Flux 1

1. **Cereri_Achizitie**: Status, Motiv_Respingere / Avertismente, Aprobari, Data_Finalizare.
2. **Istoric_Stari**: liniile cererii, în ordine (`—`→Nouă, Nouă→În aprobare/Respinsă, câte o linie pe pas, tranziția finală).
3. **Bugete**: Angajat_RON și Ramas_RON pe cheie (doar la „Aprobată”).
4. **Email** (Gmail ASE) și **mesaj Teams** pentru fiecare tranziție.
5. **Istoricul rulării** în Power Automate: rulare *Reușită* (*Succeeded*).

---

## Flux 1 — `BG_Flux1_Cerere`

| ID | Caz | Date în formular | Acțiuni la aprobare | Rezultat așteptat | Rezultat |
|---|---|---|---|---|---|
| **TC-F1-01** | Calea fericită, RON | IT / SW · CUI `2816464` · `5000` RON · OPEX · **15.12.2026** · Nu · 3 | Aprobi pașii 1, 2, 3 | 3 aprobări (`1/3`, `2/3`, `3/3`). Status **Aprobată**, Aprobari cu 3 linii. `2026-12_IT_SW`: Angajat 0 → **5.000**, Rămas 51.700 → **46.700**. Email verde + Teams 🟢. Istoric: 6 linii | **OK** 2026-11-24 · PR-2026-0039 · Rămas 51.700 → 46.700, 6 linii în Istoric, email + Teams |
| **TC-F1-02** | EUR cu conversie | MKT / SW · CUI `14399840` · `2000` EUR · OPEX · **10.12.2026** | Aprobi 1, 2, 3 | Curs_BNR = cursul zilei (~5,35), Valoare_RON ≈ **10.700**. Aprobată. `2026-12_MKT_SW`: Angajat 0 → ≈10.700, Rămas 17.200 → ≈**6.500** | **OK** 2026-11-24 · PR-2026-0042, curs 5,3427 → 10.685,40 RON, Rămas 6.514,60 |
| **TC-F1-03** | CUI inexistent | IT / SW · CUI `99999999` · `1000` RON · 15.12.2026 | — | Respinsă la validare: `[V1] CUI 99999999 nu figurează în baza ANAF.` **Nicio aprobare** creată. Email roșu + Teams 🔴. *(Trecut deja în Faza 4: PR-2026-0032. Se poate refolosi dovada)* | |
| **TC-F1-04** | Valoare peste plafon | IT / SW · CUI `2816464` · `600000` RON · 15.12.2026 | — | Respinsă: `[V3] Valoarea de 600.000,00 RON este în afara intervalului acceptat: peste 0 și cel mult 500.000 RON.` Valoarea 0 e blocată deja de Forms (restricția „> 0”). Variantă opțională: `0,001` trece de Forms, iar Valoare_RON rotunjit = 0,00 → V3 | **OK** 2026-11-24 · Respinsă automat |
| **TC-F1-05** | Dată prea apropiată | IT / SW · CUI `2816464` · `1000` RON · **mâine** | — | Respinsă: `[V4] Data necesară … este prea apropiată. Data minimă acceptată este 29.11.2026 (5 zile de la depunere).` | **OK** 2026-11-24 · Respinsă automat |
| **TC-F1-06** | Lipsă buget | IT / **MKT** · CUI `2816464` · `1000` RON · 15.12.2026 | — | Respinsă: `[V5] Nu există buget pentru IT/MKT în 2026-12.` (IT nu are categoria MKT bugetată) | **OK** 2026-11-24 · Respinsă automat |
| **TC-F1-07** | Peste buget → pasul CFO | HR / TRN · CUI `9010105` · `15000` RON · OPEX · **15.01.2027** | Aprobi 1, 2, 3, 4 | Avertisment `[W1] … depășește bugetul rămas de 10.800,00 RON pentru 2027-01_HR_TRN. Se solicită și aprobarea CFO.` Peste_Buget = Da. **4 aprobări** (`4/4 · CFO`). Aprobată. `2027-01_HR_TRN`: Angajat → 15.000, Rămas 10.800 → **−4.200** (afișat cu roșu în email) | **OK** 2026-11-24 · PR-2026-0041, rulat cu data în decembrie → cheia `2026-12_HR_TRN` (buget 13.800): W1, 4 aprobări (4/4 CFO), Rămas **−1.200** cu roșu |
| **TC-F1-08** | Respingere la pasul 2 | SAL / BIR · CUI `2816464` · `3000` RON · OPEX · **20.01.2027** | Aprobi pasul 1. La pasul 2: **Respingere**, comentariu „Birotica pentru T1 e deja acoperită.” | Status **Respinsă**. Motiv: `Respinsă la pasul 2/3 – Controlling de …: „Birotica pentru T1 e deja acoperită.”` **Pasul 3 nu apare** în Aprobări. `2027-01_SAL_BIR` **neschimbat** (Rămas 7.200). Email roșu cu istoricul celor 2 decizii | **OK** 2026-11-24 · PR-2026-0040. Corectat după test: `Teams_Respinsa_Aprobare` folosea HTML-ul emailului; `Upd_Respinsa_Aprobare` scria `varMotiv` în Aprobari (trebuie `varJurnal`) |
| **TC-F1-09** | Avertisment CAPEX | OPS / HW · CUI `2816464` · `3000` RON · **OPEX** · **20.01.2027** | Aprobi 1, 2, 3 | Avertisment `[W2] Hardware de 3.000,00 RON încadrat ca OPEX (prag 2500 RON): posibilă imobilizare — verificați încadrarea CAPEX.`, vizibil și în detaliile aprobării. Aprobată. `2027-01_OPS_HW`: Angajat → 3.000 | **OK** 2026-11-24 · PR-2026-0043, Rămas 31.500 → 28.500 |
| **TC-F1-10** | Mod demo (aprobator unic) | OPS / SRV · CUI `9010105` · `8000` RON · OPEX · **10.02.2027** | ⚠️ **Înainte**: în Config, `email_bcc` = **adresa ta ASE** (temporar) și `mod_demo` = `true`. Aprobi pasul unic | **O singură aprobare**: `aprobare 1/1`, rolul „Aprobator unic (demo)”, atribuită adresei din `email_bcc`. Aprobată. ⚠️ **După**: `mod_demo` = `false`, `email_bcc` = valoarea inițială. Altfel adresa reală primește aprobări de test | **OK** 2026-11-24 · o singură aprobare `1/1` |
| TC-F1-11 *(extra)* | Timeout aprobare | IT / TRN · CUI `2816464` · `1000` RON · 15.12.2026 | ⚠️ **Înainte**: pe acțiunea `Aprobare`, *Expirare acțiune* = `PT3M`. **Nu** răspunzi | După ~3 min: `Decizie.rezultat = Expirat`, Status **Respinsă**, Motiv `Termenul de aprobare a expirat (7 zile) la pasul 1/3 – …`. ⚠️ **După**: readuci `P7D`. Aprobarea rămasă deschisă în Teams se poate anula | **OK** 2026-11-24 · Respinsă după timeout (PT3M), motiv „Termenul de aprobare a expirat…” |

> În TC-F1-11, textul motivului spune „7 zile” chiar și cu timeout-ul de test de 3 minute. E acceptat: valoarea de producție e cea documentată.

---

## Export — `BG_Export`

Se rulează **după** cazurile F1, în ordinea de mai jos. Seed-ul are 22 de cereri istorice: 19 Aprobate și 3 Exportate (PR-2026-0002, 0008, 0021).

| ID | Caz | Parametri | Rezultat așteptat | Rezultat |
|---|---|---|---|---|
| **TC-EX-01** | Export CSV, fără filtre | DataDe `01.09.2026` · DataPana `30.09.2026` · CC gol · Categorie gol · Format **CSV** | **15 rânduri** (PR-2026-0001, 0003–0007, 0009–0017). 0002 și 0008 lipsesc (sunt deja Exportate). Fișierul `Exporturi/BG_export_AAAALLZZ_HHmm.csv` se deschide în Excel cu diacritice corecte. Total Valoare_RON în email: **342.500,08 RON**. Cele 15 cereri trec în **Exportată**, cu 15 linii `EXPORT` în Istoric_Stari | **OK** 2026-11-24 · `BG_export_20261124_1950.csv`, 15 cereri, 342.500,08 RON, 15 linii EXPORT |
| **TC-EX-02** | Export JSON cu filtru pe categorie | DataDe `01.10.2026` · DataPana `31.10.2026` · Categorie `srv` *(litere mici, intenționat)* · Format **JSON** | **1 rând**: PR-2026-0019 (OPS/SRV, 21.750 RON). Filtrul acceptă și litere mici (`toUpper`). Fișier `.json` valid (array cu 1 obiect). PR-2026-0019 → Exportată | **OK** 2026-11-24 · `BG_export_20261124_1949.json`, 1 cerere, 21.750,00 RON |
| **TC-EX-03** | Interval fără rezultate | Aceiași parametri ca TC-EX-01 (re-rulare) | Email „Nicio cerere aprobată în intervalul selectat”. **Niciun fișier** nou în Exporturi. Arată că exportul nu dublează cererile exportate | **OK** 2026-11-24 · email „Nicio cerere”, fără fișier nou |

---

## Capturi necesare (minim)

| Caz | Capturi |
|---|---|
| TC-F1-01 | lista Cereri (rândul Aprobată, cu Aprobari) · Bugete `2026-12_IT_SW` · emailul verde · aprobarea din Teams |
| TC-F1-02 | rândul cererii (Curs_BNR, Valoare_RON) |
| TC-F1-04 / 05 / 06 | emailurile roșii (pot fi într-o singură captură, cu inbox-ul) |
| TC-F1-07 | aprobarea `4/4 · CFO` · Bugete cu Rămas negativ |
| TC-F1-08 | emailul de respingere cu istoricul · lista Aprobări fără pasul 3 |
| TC-F1-09 | detaliile aprobării cu W2 |
| TC-F1-10 | aprobarea `1/1 · Aprobator unic (demo)` |
| TC-F1-11 | istoricul rulării cu `Aprobare` expirată și `Decizie` reușită |
| TC-EX-01 | fișierul în Exporturi · CSV deschis în Excel · emailul |
| TC-EX-02 | conținutul JSON |
| TC-EX-03 | emailul „Nicio cerere” |
| general | istoricul rulărilor `BG_Flux1_Cerere` (toate *Reușit*) · Istoric_Stari filtrat pe o cerere |
