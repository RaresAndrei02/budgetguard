# Concordanța BPMN ↔ fluxuri Power Automate

> Fiecare element din cele două diagrame BPMN, pus lângă acțiunea (sau grupul de acțiuni) care îl implementează și lângă dovada de funcționare.
> Diagramele: `bpmn/flux1_cerere_achizitie.bpmn`, `bpmn/flux2_import_analiza.bpmn` (randări în `bpmn/png/`). Ghidurile de construcție: `docs/flux1_pas_cu_pas.md`, `docs/flux2_pas_cu_pas.md`.
> Pe acțiunile principale din flux, nota (*Add a note*) conține ID-ul elementului BPMN, deci legătura se poate verifica și direct în designer.
> Dovezile trimit la cazurile din `docs/plan_testare.md`.

Diagramele au fost făcute **înainte** de implementare (Faza 2, 2026-11-20). Diferențele apărute la construcție sunt la final, în secțiunea [Diferențe și corecturi](#diferențe-și-corecturi).

---

## Flux 1 — Cererea de achiziție (`BG_Flux1_Cerere`)

### Participanți, culoare, fluxuri de mesaje

| Element BPMN | Tip | Implementare | Dovadă |
|---|---|---|---|
| `Participant_Vestra` | pool | Fluxul `BG_Flux1_Cerere` din soluția `BudgetGuard` | — |
| `Lane_Solicitant` | lane | Formularul Microsoft Forms + emailurile primite de solicitant | TC-F1-01 |
| `Lane_Sistem` | lane | Acțiunile automate ale fluxului | — |
| `Lane_Manager`, `Lane_Controlling`, `Lane_Financiar`, `Lane_CFO` | lane | Adresele `aprobator_1`, `aprobator_2`, `aprobator_3`, `aprobator_cfo` din lista **Config** | TC-F1-01, TC-F1-07 |
| `Participant_ANAF` | pool închis | Serviciul web ANAF TVA v9 | TC-F1-03 |
| `Participant_BNR` | pool închis | `https://curs.bnr.ro/nbrfxrates.xml` | TC-F1-02 |
| `MsgFlow_Task_ANAF_*` (CUI + data → found / notFound) | message flow | `HTTP_ANAF` (POST) → `Parse_ANAF` | TC-F1-03 |
| `MsgFlow_Task_BNR_*` (GET curs → EUR / USD) | message flow | `HTTP_BNR` (GET) → `xpath` pe `Rate[@currency]` | TC-F1-02 |

### Activități, gateway-uri, evenimente

| Element BPMN | Tip | Acțiuni în flux | Dovadă |
|---|---|---|---|
| `Start_Cerere` | start (mesaj) | Trigger *When a new response is submitted* → `Get_response_details` → `Date_Formular` → `Cerere` | `capturi/faza4/01_formular.png` |
| *(pregătire, fără element BPMN)* | — | `Get_Config` → `Select_Config` → `cfg`; inițializarea variabilelor | — |
| `Task_Inregistrare` | service task | `Create_Cerere` → `Set_ID_Cerere` (ID `PR-2026-0042`) → `Log_Noua` | `capturi/faza4/10_lista_cereri_statusuri.png` |
| `Task_ANAF` | service task | În `Scope_Validare`: `HTTP_ANAF` → `Parse_ANAF` → `Firma` → `Cond_V1`, `Cond_V2`, `Cond_V2b`, `Cond_W3` | TC-F1-03; `capturi/faza4/02_rulare_anaf_cui_inexistent.png` |
| `Task_BNR` | service task | `Cond_Moneda` → `HTTP_BNR` → `Cond_BNR_OK` (curs zilnic sau de rezervă, W4) → `Valoare_RON` → `Cond_V3` | TC-F1-02, TC-F1-04; `capturi/faza4/03_rulare_bnr_v3_v4.png`, `05_curs_bnr_eur.png` |
| `Task_VerificaBuget` | service task | `Cond_V4` (data) → `Get_Buget` → `Cond_V5`, `Cond_W1`, `Cond_W2` | TC-F1-05, 06, 07, 09; `capturi/faza4/04_rulare_buget_v5_w1_w2.png` |
| `Store_Bugete1` | data store (citire) | `Get_Buget` din lista **Bugete** | idem |
| `Store_Cereri1` | data store (scriere) | `Create_Cerere` în **Cereri_Achizitie** | idem |
| `Gateway_DateValide` | gateway exclusiv | `Cond_Erori`: `length(variables('varErori')) > 0` | TC-F1-03…06 |
| `Task_RespinsaValidare` | service task | `Upd_Respinsa` (Status = Respinsă, `Motiv_Respingere`) → `Log_Respinsa` | TC-F1-04 |
| `Send_NotifRespValidare` | send task | `Email_Respinsa` + `Teams_Respinsa` | `capturi/faza4/06_email_respinsa_T4-3.png` |
| `End_RespinsaValidare` | end | `Terminate_Respinsa` (Succeeded) | TC-F1-03…06 |
| `Task_StatusInAprobare` | service task | `Upd_In_Aprobare` (Furnizor_ANAF, curs, Valoare_RON, avertismente, Status = În aprobare) → `Log_In_Aprobare` | `capturi/faza4/07_…`, `08_…` |
| `Send_NotifInAprobare` | send task | `Email_In_Aprobare` + `Teams_In_Aprobare` | `capturi/faza4/09_teams_canal_tranzitii.png` |
| `Gateway_PesteBuget` | gateway exclusiv | `Necesita_CFO` → `Set_varAprobatori` (lista cu sau fără CFO; în mod demo, un singur aprobator) | TC-F1-07, TC-F1-10 |
| `User_Aprobare1…4` | user tasks în secvență | **O singură buclă** `Do_until_Aprobare` peste `varAprobatori`, cu `Aprobare` (*Start and wait for an approval*) → `Decizie` → `Append_Jurnal` → `Upd_Aprobari` → `Log_Pas`. Vezi `Annotation_Aprobatori` | TC-F1-01 (3 pași), TC-F1-07 (4 pași), TC-F1-10 (1 pas) |
| `Gateway_Aprobat1…4` | gateway exclusiv | `Cond_Aprobat_Pas` în buclă + condiția de ieșire `or(varRespins, varIdx ≥ length(varAprobatori))` | TC-F1-08 (pasul 3 nu mai e cerut) |
| `Timer_Aprobare1…4` | boundary timer (7 zile) | *Action timeout* `P7D` pe `Aprobare`; `Decizie` rulează și după *timed out* și dă rezultatul „Expirat” → respingere | TC-F1-11 |
| `Gateway_MergeRespins` | gateway (unire) | `Cond_Respins` → ramura **Da** | TC-F1-08, 11 |
| `Task_StatusRespinsa` | service task | `Upd_Respinsa_Aprobare` (Status, motiv, `Data_Finalizare`) → `Log_Respinsa_Aprobare` | TC-F1-08 |
| `Send_NotifRespingere` | send task | `Email_Respinsa_Aprobare` + `Teams_Respinsa_Aprobare` | TC-F1-08 |
| `End_Respinsa` | end | `Terminate_Respinsa_Aprobare` (Succeeded) | TC-F1-08 |
| `Gateway_MergeAprobat` | gateway (unire) | `Cond_Respins` → ramura **Nu** | TC-F1-01 |
| `Task_StatusAprobata` | service task | `Upd_Aprobata` → `Log_Aprobata` | TC-F1-01 |
| `Task_AngajeazaBuget` | service task | `Get_Buget_Curent` (recitește bugetul) → `Angajat_Nou` → `Ramas_Nou` → `Upd_Buget` | TC-F1-01, 07 (Rămas negativ) |
| `Store_Cereri2`, `Store_Bugete2` | data store (scriere) | `Upd_Aprobata`, `Upd_Buget` | TC-F1-01 |
| `Send_NotifAprobare` | send task | `Email_Aprobata` + `Teams_Aprobata` | TC-F1-01 |
| `End_Aprobata` | end | Sfârșitul natural al fluxului | TC-F1-01 |
| *(jurnalizare, fără element BPMN)* | — | `Log_*` în lista **Istoric_Stari** la fiecare tranziție | TC-F1-01 (6 linii) |

### Exportul (`BG_Export`)

Exportul e un flux separat, pornit manual, și **nu are diagramă BPMN** (diagramele acoperă cele două procese principale). Pașii lui sunt în `docs/export_pas_cu_pas.md`: `Parametri` → `Filtru` → `Get_Aprobate` → `Cond_Gol` → `Select_Export` → `Create_CSV` / JSON → `Create_Fisier` → `Apply_to_each_Export` (Status = Exportată + log `EXPORT`) → email. Dovezi: TC-EX-01…03.

---

## Flux 2 — Importul realizatului și analiza AI (`BG_Flux2_Import`)

### Participanți și fluxuri de mesaje

| Element BPMN | Tip | Implementare | Dovadă |
|---|---|---|---|
| `Participant_BudgetGuard2` | pool | Fluxul `BG_Flux2_Import` | — |
| `Participant_BNR2` | pool închis | `https://curs.bnr.ro/nbrfxrates.xml` | antetul raportului („curs BNR 2026-11-26”) |
| `Participant_Groq` | pool închis | `https://api.groq.com/openai/v1/chat/completions`, model `openai/gpt-oss-120b` | TC-F2-01 (5/5 OK) |
| `MsgFlow_Task_Referinte_*` | message flow | `HTTP_BNR` → `Set_varCursuri`, `Set_varDataCurs` | TC-F2-01 |
| `MsgFlow_SA_AnalizaAI_*` (prompt + date CC → JSON) | message flow | `Corp_Groq` → `HTTP_Groq` → `AI_Text` → `Parse_AI` | TC-F2-01, 03 |

### Activități, gateway-uri, evenimente

| Element BPMN | Tip | Acțiuni în flux | Dovadă |
|---|---|---|---|
| `Start_FisierNou` | start (condițional) | Trigger *When a file is created (properties only)* în `Import_Realizat`, cu 2 condiții: extensia `.json` și fișierul nu e în `Procesate` | TC-F2-01; arhiva din `Procesate` nu repornește fluxul |
| *(pregătire, fără element BPMN)* | — | `Get_Config` → `cfg` → `System_Prompt` → 11 variabile | — |
| `Task_CitesteFisier` | service task | În `Scope_Try`: `Get_file_content` → `Fisier_Text` → `Fisier_JSON` → `Parse_Fisier` → `Luna_Import` | TC-F2-01 |
| `Gateway_Lizibil` | gateway exclusiv | Implicit: dacă o acțiune din `Scope_Try` eșuează, rulează `Scope_Catch` (*Run after: has failed / has timed out*) | TC-F2-04, 05 |
| `Send_NotifEsec` | send task | În `Scope_Catch`: `Filter_Esec` → `Actiune_Esuata` → `Detaliu_Esec` → `Mesaj_Esec` → `Html_Esec` → `Email_Esec` + `Teams_Esec` | TC-F2-04 („nu este un JSON valid”), TC-F2-05 („lista „inregistrari” lipsește”) |
| `End_ImportEsuat` + `Error_Import` | end (eroare) | `Log_Esec` în Istoric_Stari („Import eșuat”); rularea rămâne marcată *Failed* | TC-F2-04 |
| `Task_Referinte` | service task | `Get_Nomenclator` → `Filter_CC` → `Select_Coduri_CC` → `Filter_CAT` → `Select_Coduri_CAT`; `HTTP_BNR` → `Cond_BNR_OK` | TC-F2-01 |
| `Store_Nomenclator` | data store (citire) | `Get_Nomenclator` | idem |
| `Sub_ValideazaInregistrarea` | subproces multi-instance secvențial | `Valideaza_Randuri` (*Apply to each*, concurrency 1) | TC-F2-01 (20 valide, 4 respinse) |
| `SV_Verifica` | service task | `Rand` → `Luna_OK` → `Lipsa` → `Cheie` → `Suma_Num` → `Cod_Eroare` | idem |
| `SV_Rezultat` | gateway exclusiv | `Cond_Rand_Valid` (`Cod_Eroare` gol) | idem |
| `SV_Valid` | task | Ramura True: `Suma_RON` → `Append_varChei` → `Inreg_Valida` → `Append_varValide` | idem |
| `SV_Invalid`, `SV_Duplicat` | task | Ramura False: `Prima_Aparitie` → `Ref` → `Mesaj_Rand` → `Err_Rand` → `Append_varErori` (codul `DUP` dă tipul „Duplicat”) | rândurile 9, 14, 17 (invalide), 22 (duplicat) |
| `Task_Upsert` | service task | `Upsert_Realizat`: `Get_Realizat` → `Get_Cereri_Aprobate` → `Select_Valori` → `Aprobat_RON` → `Maverick_RON` → `Cond_Exista_Realizat` (Create / Update) → `Upd_Buget_Realizat` | TC-F2-01, TC-F2-02 (tot 20 de rânduri după 6 importuri) |
| `Store_Realizat`, `Store_Bugete` | data store (scriere) | `Realizat_Lunar`, `Bugete.Realizat_RON` | idem |
| `Task_SalveazaErori` | service task | `Salveaza_Erori` → `Create_Eroare` | TC-F2-01 (4 rânduri în Erori_Import) |
| `Store_Erori` | data store (scriere) | lista **Erori_Import** | idem |
| `Sub_AnalizaCC` | subproces multi-instance secvențial | `Get_Realizat_Luna` → `Mav_Luna`, apoi `Analiza_CC` (*Apply to each* pe cele 5 CC, concurrency 1) | TC-F2-01 |
| `SA_Varianta` | service task | `Get_Bugete_CC` → `Select_Categorii` → `Buget_CC` … `Alerta_Regula` → `User_AI` → `Get_Analiza` → `Cond_Exista_Analiza` (Create / Update, Status pornește „Eșuată”) → `Id_Analiza` | TC-F2-01 (alertele = cele așteptate) |
| `SA_AnalizaAI` | service task | `AI_Try`: `Corp_Groq` → `HTTP_Groq` → `AI_Text` → `Parse_AI` | TC-F2-01 |
| `SA_Salveaza` | service task | `Upd_Analiza_OK` (Status OK, `Necesita_Revizuire` = alerta AI ≠ regula) → `Inc_AI_OK` | HR: Galben vs. Verde → revizuire |
| `SA_EroareAI` + `Error_AI` | boundary error | `AI_Catch`, *Run after* `AI_Try`: has failed / has timed out | TC-F2-03 |
| `SA_Esuata` | service task | `Motiv_AI` → `Mesaj_AI_Esec` → `Upd_Analiza_Esuata` → `Inc_AI_Esec` | TC-F2-03 (5 × Eșuată, HTTP 401) |
| `SA_Merge`, `SA_End` | gateway (unire), end | `Rez_CC` (*Run after* `AI_Catch`: succeeded / skipped) → `Append_varRezCC` → `Delay_Groq` | TC-F2-01, 03 |
| `Store_Analize1`, `Store_Analize2` | data store (scriere) | lista **Analize_AI** | idem |
| `Task_Raport` | service task | `Filter_Duplicate` → `Sumar_Import` → `Json_RezCC` → `Tot_Raport` → `Select_Rand_CC`, `Select_Bloc_AI`, `Filter_Mav` → `Select_Rand_Mav`, `Select_Rand_Err`, `Select_Rand_Teams` → `Sablon_Raport` → `Html_Raport` | raportul real ≈ `report/preview.html` (Faza 8) |
| `Send_Raport` | send task | `Email_Raport` (către `email_echipa`, BCC `email_bcc` în mod demo) → `Html_Teams_Raport` → `Teams_Raport` | BCC verificat 2026-11-26 |
| `Task_MutaFisier` | service task | `Create_Arhiva` (în `Procesate`, cu sufixul `_{Rulare_ID}`) → `Delete_Original` → `Log_Import` | TC-F2-01 |
| `End_ImportFinalizat` | end | Sfârșitul lui `Scope_Try`; `Scope_Catch` e omis | TC-F2-01 |

---

## Diferențe și corecturi

| # | Unde | Diferența | Decizie |
|---|---|---|---|
| D1 | F1 `User_Aprobare1…4` | BPMN are 4 user tasks în secvență; fluxul are o singură buclă *Do until* peste lista de aprobatori | **Păstrat**, documentat în `Annotation_Aprobatori`. Același comportament: aprobări în ordine, ieșire la prima respingere, număr variabil de pași (1 în mod demo, 3 sau 4) |
| D2 | F1 `Gateway_PesteBuget` | Fluxul cere CFO și când `Valoare_RON > prag_cfo_ron`, nu doar la depășirea bugetului (decizia din 2026-11-24) | **BPMN corectat**: eticheta e acum „Peste buget sau > prag CFO?” |
| D3 | F1 `Task_ANAF` | Regula V2b (furnizor radiat) a fost adăugată la implementare (2026-11-20) | **BPMN corectat**: „(V1, V2, V2b, W3)” |
| D4 | F1 `Task_BNR` | Cursul de rezervă din Config când BNR nu răspunde (W4) | **BPMN corectat**: „Curs BNR (rezervă: W4), calculează Valoare_RON (V3)” |
| D5 | F1 / F2 jurnalizarea | Liniile din **Istoric_Stari** nu au elemente BPMN proprii | **Păstrat**: jurnalizarea e un detaliu tehnic al fiecărei tranziții de stare, nu un pas de proces |
| D6 | F2 `Gateway_Lizibil` | În flux nu e un gateway explicit: orice eșec din `Scope_Try` ajunge în `Scope_Catch`, deci ramura acoperă mai mult decât „fișier ilizibil” | **BPMN corectat**: eroarea `Error_Import` se numește „Fișier ilizibil, fără înregistrări sau eroare la import”. Mesajul din email diferențiază cazurile (JSON invalid / structură / alt pas) |
| D7 | F2 `Send_NotifEsec` | Notificarea de eșec merge pe email **și** în Teams | **BPMN corectat**: „(email + Teams)” |
| D8 | F2 `SA_Varianta` | Calculele CC se salvează în `Analize_AI` **înainte** de apelul AI (Status „Eșuată”, trecut pe „OK” de `SA_Salveaza`) | **BPMN corectat**: „Calculează și salvează totaluri, varianță, alertă (regulă)”; adnotarea AI menționează salvarea prealabilă |
| D9 | F2 `Task_MutaFisier` | *Move file* nu poate redenumi, deci fluxul face copie în `Procesate` + ștergere | **Păstrat**: rezultatul e cel din diagramă (fișierul mutat, cu sufixul rulării) |
| D10 | F2 `Sub_AnalizaCC` | Maverick-ul pe categorii se citește din `Realizat_Lunar` pentru toată luna (`Get_Realizat_Luna`), nu doar din rândurile fișierului curent (bug găsit la test, 2026-11-26) | **Flux corectat**; în BPMN rămâne în `Sub_AnalizaCC`, fără element nou |

Diagramele se regenerează cu `python bpmn/build_bpmn.py`, iar randările cu `cd bpmn/tools && node render.mjs` (D2, D3, D4, D6, D7 și D8 aplicate pe 2026-11-26, 0 avertismente bpmn-js).
