# Crearea listelor SharePoint — `BG_Setup_SharePoint` (Faza 3, Planul A)

Fluxul trimite pe rând cererile REST generate de `sharepoint/build_requests.py`, prin acțiunea standard
**Send an HTTP request to SharePoint**. Acțiunea nu e premium și nu cere drepturi de admin, doar drepturi de proprietar pe site.

Rulezi fluxul **de două ori**, cu conținut diferit în Compose:

| Rulare | Conținutul din Compose | Ce face | Nr. cereri |
|---|---|---|---|
| 1 | `sharepoint/provision_requests.json` | 8 liste, coloanele lor, redenumirea `Title`, 2 biblioteci, folderul `Procesate` | 94 |
| 2 | `sharepoint/seed_requests.json` | Datele inițiale: Config (16), Nomenclator (11), Bugete (120), Cereri_Achizitie (22) | 169 |

> ⚠️ Fiecare rulare se face **o singură dată**. Dacă repeți rularea 1, listele există deja, iar cererile dau eroare (inofensiv). Dacă repeți rularea 2, apar rânduri duplicate în Nomenclator și Cereri_Achizitie. La Config și Bugete, `Title` e unic, deci duplicatele dau eroare.

## Construirea fluxului

1. În soluția **BudgetGuard**: **+ New → Automation → Cloud flow → Instant**.
   - Nume: `BG_Setup_SharePoint`. Trigger: **Manually trigger a flow** → **Create**.
2. **+** → acțiunea **Compose**. O redenumești `Cereri_REST`.
   - Deschizi `sharepoint/provision_requests.json` în Notepad → **Ctrl + A**, **Ctrl + C**.
   - Lipești conținutul în câmpul **Inputs**, direct, fără **fx**.
3. **+** → **Control → For each** (*Apply to each*). O redenumești `Pentru_fiecare_cerere`.
   - **Select an output from previous steps**: **fx** → `outputs('Cereri_REST')`
   - **Settings → Concurrency control: On, Degree of parallelism: 1**. Ordinea contează: lista trebuie să existe înaintea coloanelor ei.
4. În interiorul buclei: **+** → **SharePoint → Send an HTTP request to SharePoint**. O redenumești `HTTP_SP`.
   - **Site Address**: alegi site-ul **ucBudgetGuard** din listă.
   - **Method**: `POST`. Toate cererile sunt POST.
   - **Uri**: **fx** → `items('Pentru_fiecare_cerere')?['uri']`
   - **Headers**: apeși iconița **Switch to text mode**, din dreapta perechilor cheie/valoare, apoi **fx** → `items('Pentru_fiecare_cerere')?['headers']`
   - **Body**: **fx** →
     ```
     if(equals(items('Pentru_fiecare_cerere')?['body'], null), '', string(items('Pentru_fiecare_cerere')?['body']))
     ```
5. **Save → Test → Manually → Run flow**. Durează câteva minute.

## Verificarea rulării 1
- În istoricul rulării: **For each** → navighezi prin iterații. Toate cele 94 trebuie să fie verzi.
- Pe site, la **Site contents**, apar: Config, Nomenclator, Bugete, Cereri_Achizitie, Istoric_Stari, Realizat_Lunar, Analize_AI, Erori_Import, plus bibliotecile Import_Realizat (cu folderul Procesate) și Exporturi.

## Rularea 2 (datele inițiale)
1. **Edit** → în `Cereri_REST` ștergi tot conținutul și lipești conținutul din `sharepoint/seed_requests.json`.
2. **Save → Test → Run flow**. Trebuie să vezi 169 de iterații verzi.
3. Verifici numărul de elemente: Bugete **120**, Cereri_Achizitie **22**, Config **16**, Nomenclator **11**.

## După setup: Config
În lista **Config**, înlocuiești valorile `COMPLETEAZA_EMAIL_ASE` cu adresa ta de ASE: `aprobator_1`, `aprobator_2`, `aprobator_3`, `aprobator_cfo`, `email_echipa`. Valorile `teams_team_id` și `teams_channel_id` se completează în Faza 4.

## Dacă o iterație eșuează
Deschide iterația roșie → `HTTP_SP` → **Outputs** și trimite mesajul de eroare (`error.message.value`). Cauze probabile:

| Eroare | Ce înseamnă |
|---|---|
| `A list, survey, discussion board, or document library with the specified title already exists` | rularea a fost repetată: lista există deja, poți ignora |
| `A duplicate field name "..." was found` | coloana există deja, poți ignora |
| `The property '__metadata' does not exist` sau `type` necunoscut, la rularea 2 | site-ul nu acceptă `odata=nometadata`. se regenerează `seed_requests.json` cu tipurile de entitate (`python sharepoint/build_requests.py`) |
| `Access denied` | contul nu e proprietar al site-ului |
