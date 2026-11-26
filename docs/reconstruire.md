# Reconstruirea BudgetGuard într-un tenant nou

> Pentru cazul în care tenantul inițial nu mai e disponibil (ex. contul de organizație expiră). Tot ce ține de tenant (liste, formular, fluxuri, conexiuni) se reface din repo, în ordinea de mai jos.
> Timp estimat: 1,5–2 ore.

## Ce trebuie să ai

| Element | Unde e în repo |
|---|---|
| Soluția Power Automate (4 fluxuri + variabila de mediu) | `solution/BudgetGuard_*.zip` (ignorat de git, păstrat local / în arhivă) și versiunea despachetată în `solution/src/` |
| Definiția listelor | `sharepoint/schema.json` → `sharepoint/provision_requests.json` |
| Datele inițiale | `data/seed/*.csv` |
| Datele finale din tenantul vechi | `data/export_final/` |
| Formularul | specificația în `docs/flux1_pas_cu_pas.md` §1 |
| Promptul AI | `ai/system_prompt.txt` |

**Licențe necesare:** acțiunea HTTP e *premium* (Power Automate Premium sau Power Apps Developer Plan). SharePoint, Forms, Teams, Approvals: incluse în Microsoft 365.

## Pașii

### 1. Site-ul și canalul Teams
1. În Teams: echipă nouă „BudgetGuard” (creează automat site-ul SharePoint `/sites/BudgetGuard`).
2. Notezi adresa site-ului și ID-urile echipei și canalului (`docs/flux1_pas_cu_pas.md` §0.1).

### 2. Importul soluției
1. Power Automate → **Solutions** → **Import solution** → `solution/BudgetGuard_*.zip`.
2. La import:
   - **Conexiuni**: creezi câte una pentru SharePoint, Microsoft Forms, Approvals, Microsoft Teams și Gmail (sau Office 365 Outlook, dacă tenantul îl permite).
   - **Variabila de mediu** `bg_GroqApiKey`: pui cheia Groq (de pe console.groq.com, contul personal).
3. Fluxurile se importă **oprite**. Nu le porni încă.

### 3. Adresa site-ului în fluxuri
Acțiunile SharePoint au adresa site-ului vechi scrisă direct. În fiecare flux, la fiecare acțiune SharePoint (*Get items*, *Create item*, *Update item*, *Create file*, *Send an HTTP request to SharePoint* etc.) alegi site-ul nou din lista **Site Address**, apoi lista cu același nume.

> Îmbunătățire posibilă: o a doua variabilă de mediu, `bg_SiteUrl`, folosită în toate acțiunile. La o reconstrucție s-ar schimba o singură valoare.

### 4. Listele SharePoint
1. Rulezi `BG_Setup_SharePoint` (rularea 1: liste și coloane), după `docs/setup_sharepoint_pas_cu_pas.md`.
2. Rularea 2: datele inițiale (Config, Nomenclator, Bugete, cererile istorice).
3. Verifici în `docs/sharepoint_schema.md` tipurile coloanelor.
4. Opțional: datele de la final din `data/export_final/*.csv`, lipite în *Edit in grid view*, dacă vrei starea finală, nu cea inițială.

### 5. Config
Completezi în lista **Config**:

| Cheie | Valoare |
|---|---|
| `aprobator_1…3`, `aprobator_cfo`, `email_echipa` | adresele din tenantul nou |
| `email_bcc` | adresa pentru BCC în mod demo |
| `teams_team_id`, `teams_channel_id` | de la pasul 1 |
| `mod_demo` | `false` (sau `true` pentru demo) |
| `curs_fallback_EUR`, `curs_fallback_USD` | ultimul curs BNR |
| `groq_model` (opțional) | `openai/gpt-oss-120b` |

### 6. Formularul
1. Recreezi formularul după `docs/flux1_pas_cu_pas.md` §1 (11 întrebări, aceleași texte și opțiuni, fiindcă fluxul extrage codul din „IT – Tehnologie”).
2. În `BG_Flux1_Cerere`: trigger-ul și *Get response details* → **Form Id** = formularul nou.
3. Atenție: ID-urile întrebărilor se schimbă. În acțiunea `Date_Formular`, reasociezi fiecare câmp cu răspunsul corespunzător din conținutul dinamic.

### 7. Pornirea și verificarea
| # | Test | Rezultat așteptat |
|---|---|---|
| 1 | O cerere cu CUI `99999999` | Respinsă automat, email + Teams |
| 2 | O cerere validă în EUR, aprobată | Aprobată, bugetul actualizat |
| 3 | `BG_Export` pe intervalul de azi | Fișier CSV în `Exporturi` |
| 4 | `realizat_2026-10.json` în `Import_Realizat` | 20 valide, 4 erori, 5 analize AI, raport pe email |
| 5 | `python scripts/compare_results.py data/run_check/` pe exporturile listelor | 0 diferențe |
