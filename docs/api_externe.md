# API-uri externe: rezultatele testelor (Faza 1)

Răspunsurile reale sunt salvate în `samples/` și se regenerează cu `scripts/check_anaf.py` și `scripts/check_bnr.py`.

## ANAF — TVA v9

- `POST https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva`, `Content-Type: application/json`
- Body: `[{"cui": 2816464, "data": "2026-11-18"}]`
- **Test local 2026-11-18:** HTTP 200, fără autentificare.

| CUI | Rezultat | denumire | scpTVA | statusInactivi |
|---|---|---|---|---|
| 2816464 | found | DEDEMAN SRL | true | false |
| 14399840 | found | DANTE INTERNATIONAL SA (eMAG) | true | false |
| 9010105 | found | ORANGE ROMANIA SA | true | false |
| 99999999 | notFound | — | — | — |

Observații:
- Răspunsul are la nivel de rădăcină doar `found[]` și `notFound[]`. `notFound` conține CUI-urile ca **numere**.
- ⚠️ **Cerere cu un singur CUI inexistent → HTTP 404**, cu body JSON valid `{"found":[],"notFound":[99999999]}`. Dacă în cerere există cel puțin un CUI găsit, răspunsul e 200. În flux, `Parse_ANAF` are *Run after* = succes + eșec (verificat 2026-11-22).
- `11111110`, propus inițial drept CUI inexistent, **există** (o asociație de locatari, neplătitoare de TVA). Poate servi drept caz de test pentru W3.
- Câmpurile folosite în flux sunt confirmate pe răspunsul real:
  - `found[0].date_generale.denumire` (string)
  - `found[0].inregistrare_scop_Tva.scpTVA` (boolean)
  - `found[0].stare_inactiv.statusInactivi` (boolean)
- Schema pentru *Parse JSON*: `schemas/anaf_v9.json`. Conține doar câmpurile folosite, iar restul sunt ignorate de *Parse JSON*.

Expresii Power Automate (acțiunea *Parse JSON* se numește `Parse_ANAF`):
```
V1  greater(length(body('Parse_ANAF')?['found']), 0)
    denumire: first(body('Parse_ANAF')?['found'])?['date_generale']?['denumire']
V2  equals(first(body('Parse_ANAF')?['found'])?['stare_inactiv']?['statusInactivi'], true)   -> eroare
W3  equals(first(body('Parse_ANAF')?['found'])?['inregistrare_scop_Tva']?['scpTVA'], false)  -> avertisment
```
Body-ul cererii HTTP în flux (CUI-ul din Forms vine ca text):
```
[{"cui": @{int(<raspuns CUI>)}, "data": "@{formatDateTime(utcNow(),'yyyy-MM-dd')}"}]
```

## BNR — curs zilnic

- ⚠️ **Adresa s-a schimbat.** `https://www.bnr.ro/nbrfxrates.xml` redirecționează acum (HTTP 301/302) spre pagina principală HTML. Adresa care funcționează este **`https://curs.bnr.ro/nbrfxrates.xml`** (HTTP 200, `text/xml`). Spre același domeniu trimite și `xsi:schemaLocation` din XML.
- **Test local 2026-11-18:** `Cube date="2026-11-18"`, EUR = 5.3459, USD = 4.8725. Atributul `multiplier` lipsește pentru EUR/USD.
- Namespace implicit: `https://www.bnr.ro/xsd`, de aceea XPath-ul folosește `local-name()`.

```
curs EUR:  float(xpath(xml(body('HTTP_BNR')), 'string(//*[local-name()=''Rate''][@currency=''EUR''])'))
data curs: xpath(xml(body('HTTP_BNR')), 'string(//*[local-name()=''Cube'']/@date)')
```

## Groq

- Lista modelelor: `GET https://api.groq.com/openai/v1/models` (salvată în `samples/groq_models.json`), verificată pe 2026-11-19.
- ⚠️ **Abatere de la specificație:** specificația inițială cerea „un model Llama de uz general”. Pe 2026-11-19, Groq **nu mai oferă niciun model Llama de chat**. Singurele modele Meta din listă sunt `llama-prompt-guard-2-22m` și `llama-prompt-guard-2-86m`, clasificatoare de siguranță cu context de 512 tokeni.
- Am testat 3 modele de chat cu `response_format: json_object`, toate cu HTTP 200 și JSON valid:

| Model | JSON valid | Observații |
|---|---|---|
| `openai/gpt-oss-120b` | da | model de raționament (~125–190 tokeni de raționament), română corectă cu diacritice, ctx 131K |
| `openai/gpt-oss-20b` | da | mai rapid, formulări mai sărace |
| `qwen/qwen3.8-27b` | da | `content` vine cu spații și linii noi, dar e parsabil |

- **Ales: `openai/gpt-oss-120b`** (în `.env` ca `GROQ_MODEL`). Fallback: `openai/gpt-oss-20b`.
- Structura răspunsului (`samples/groq_chat_response.json`): `choices[0].message` are cheile `role`, `content`, `reasoning`. Raționamentul vine **separat**, în `reasoning`, iar `content` conține doar JSON-ul. Expresia din flux rămâne:
  `json(body('HTTP_Groq')?['choices']?[0]?['message']?['content'])`
- `finish_reason = stop`. Consumul: ~340 tokeni pe apel de test.

## Teste din Power Automate (cloud)

Fluxul `BG_Test_API`, din soluția `BudgetGuard`, rulat în mediul Developer („Mediul lui Rares-Andrei TABUSCA”). Acțiunea HTTP (premium) e disponibilă în acest mediu.


| API | Rezultat din flux | Data |
|---|---|---|
| ANAF | HTTP 200, `found[0].date_generale.denumire` = DEDEMAN SRL. **Nu e blocat din Azure**, deci fallback-ul nu e necesar | 2026-11-19 |
| BNR | HTTP 200; Compose `float(xpath(...))` = 5.344 (EUR) | 2026-11-19 |
| Groq | `HTTP_Groq` + `AI_Content` = `json(...content)` → Succeeded (JSON valid). Cheia vine din variabila de mediu `bg_GroqApiKey` (Current Value). Secure inputs ON; Secure outputs OFF, pentru că se propagă în aval și ascunde rezultatul | 2026-11-19 |

## Calibrarea promptului AI (Faza 6, 2026-11-24)

- Fișiere: `ai/system_prompt.txt` (promptul final), `ai/response_schema.json` (schema pentru *Parse JSON*), `ai/test_prompt.py` (testul local).
- Mesajul `user` trimis de Flux 2 are exact forma din `ai/samples/user_<CC>.json`: `luna`, `centru_cost`, `buget_ron`, `angajat_ron`, `realizat_ron`, `varianta_ron`, `varianta_pct`, `maverick_ron`, `praguri` (`verde_max_pct` = 5, `galben_max_pct` = `prag_alerta_pct` din Config) și `categorii[]` (`categorie`, `buget`, `angajat`, `realizat`, `maverick`).
- Varianța se calculează **în flux** și se trimite gata calculată. Modelul nu face aritmetică pe totaluri, doar alege categoriile care explică abaterea.
- **Rezultat:** 5 runde × 5 centre de cost cu `openai/gpt-oss-120b`, `temperature 0.2`, `json_object` → **25/25 JSON valid conform schemei, 25/25 `nivel_alerta` = alerta așteptată** (inclusiv HR: Verde după regulă → Galben din cauza maverick-ului, deci „necesită revizuire”). Detalii în `ai/samples/summary.json`, iar răspunsurile din runda 1 sunt în `ai/samples/r1_<CC>.json`.
- Iterații ale promptului: (1) versiunea inițială din specificație dădea alerte corecte, dar cauze care nu explicau direcția varianței (la IT, sub buget, enumera categoriile depășite), „abatere pozitivă” pentru depășire și diacritice cu sedilă; (2) versiunea finală cere cauzele în direcția varianței, cu diferența în RON, terminologia favorabil/nefavorabil și diacritice cu virgulă. Sedila (`ţ`) mai apare rar (3/25), așa că în flux se normalizează cu `replace`.
- **Limita Groq (cont gratuit): 8.000 tokeni/minut** (`x-ratelimit-limit-tokens`). Un apel consumă ~1.600–2.900 tokeni (în medie ~1.950, din care raționamentul modelului e cea mai mare parte), deci încap ~3–4 apeluri pe minut. Testul local a primit HTTP 429 frecvent. Consecință pentru Flux 2: `HTTP_Groq` primește retry policy **fixed, 4 încercări, `PT20S`** (acoperă 429), iar bucla pe centre de cost are un **Delay de 15 secunde** după fiecare analiză. Cele 5 analize durează astfel ~1,5–2 minute.
