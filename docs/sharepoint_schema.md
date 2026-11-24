# Schema SharePoint — BudgetGuard

> Generat automat din `sharepoint/schema.json` de `sharepoint/build_requests.py`. Nu edita manual.

Site: `<SITE_URL>` (adresa reală e doar în `.env`, cheia `SP_SITE_URL`).
Numele interne ale coloanelor nu au diacritice sau spații. Coloana `Title` e cheia listei și apare sub numele afișat din tabel.

## Liste

### Config

Parametri de configurare (praguri, aprobatori, mod demo).

| Coloană (nume intern) | Tip | Detalii |
|---|---|---|
| `Title` (afișat „Cheie”) | Text | cheia listei — **valori unice, indexată** |
| `Valoare` | Text (o linie) |  |

### Nomenclator

Coduri centre de cost (CC) și categorii (CAT). Codul MKT apare la ambele tipuri.

| Coloană (nume intern) | Tip | Detalii |
|---|---|---|
| `Title` (afișat „Cod”) | Text | cheia listei |
| `Tip` | Alegere | opțiuni: CC, CAT |
| `Denumire` | Text (o linie) |  |

### Bugete

Buget lunar pe {yyyy-MM}_{CC}_{CAT}.

| Coloană (nume intern) | Tip | Detalii |
|---|---|---|
| `Title` (afișat „Cheie”) | Text | cheia listei — **valori unice, indexată** |
| `Luna` | Text (o linie) |  |
| `CentruCost` | Text (o linie) |  |
| `Categorie` | Text (o linie) |  |
| `Buget_RON` | Număr | 2 zecimale |
| `Angajat_RON` | Număr | 2 zecimale |
| `Realizat_RON` | Număr | 2 zecimale |
| `Ramas_RON` | Număr | 2 zecimale |

### Cereri_Achizitie

Cererile de achiziție (Flux 1).

| Coloană (nume intern) | Tip | Detalii |
|---|---|---|
| `Title` (afișat „ID_Cerere”) | Text | cheia listei |
| `TitluCerere` | Text (o linie) |  |
| `CentruCost` | Text (o linie) |  |
| `Categorie` | Text (o linie) |  |
| `Luna_Buget` | Text (o linie) |  |
| `CUI` | Text (o linie) |  |
| `Furnizor_ANAF` | Text (o linie) |  |
| `Platitor_TVA` | Da/Nu |  |
| `Valoare` | Număr | 2 zecimale |
| `Moneda` | Alegere | opțiuni: RON, EUR, USD; implicit: RON |
| `Curs_BNR` | Număr | 4 zecimale |
| `Valoare_RON` | Număr | 2 zecimale |
| `Tip` | Alegere | opțiuni: CAPEX, OPEX |
| `Data_Necesara` | Dată și oră | doar dată |
| `Recurenta` | Da/Nu |  |
| `Urgenta` | Număr | 0 zecimale |
| `Justificare` | Text pe mai multe linii |  |
| `Peste_Buget` | Da/Nu |  |
| `Avertismente` | Text pe mai multe linii |  |
| `Status` | Alegere | opțiuni: Nouă, În aprobare, Aprobată, Respinsă, Exportată; implicit: Nouă |
| `Solicitant_Email` | Text (o linie) |  |
| `Data_Cerere` | Dată și oră | dată + oră (UTC) |
| `Aprobari` | Text pe mai multe linii |  |
| `Motiv_Respingere` | Text pe mai multe linii |  |
| `Data_Finalizare` | Dată și oră | dată + oră (UTC) |

### Istoric_Stari

Jurnalul tranzițiilor de stare (ID_Cerere sau Rulare_ID).

| Coloană (nume intern) | Tip | Detalii |
|---|---|---|
| `Title` (afișat „Referinta”) | Text | cheia listei |
| `Flux` | Alegere | opțiuni: F1, F2, EXPORT |
| `Stare_Veche` | Text (o linie) |  |
| `Stare_Noua` | Text (o linie) |  |
| `Actor` | Text (o linie) |  |
| `Data_Ora` | Dată și oră | dată + oră (UTC) |
| `Comentariu` | Text pe mai multe linii |  |

### Realizat_Lunar

Cheltuieli realizate importate (Flux 2), upsert pe cheie.

| Coloană (nume intern) | Tip | Detalii |
|---|---|---|
| `Title` (afișat „Cheie”) | Text | cheia listei — **valori unice, indexată** |
| `Luna` | Text (o linie) |  |
| `CentruCost` | Text (o linie) |  |
| `Categorie` | Text (o linie) |  |
| `Suma` | Număr | 2 zecimale |
| `Moneda` | Text (o linie) |  |
| `Suma_RON` | Număr | 2 zecimale |
| `Nr_Documente` | Număr | 0 zecimale |
| `Aprobat_RON` | Număr | 2 zecimale |
| `Maverick_RON` | Număr | 2 zecimale |
| `Sursa_Fisier` | Text (o linie) |  |
| `Rulare_ID` | Text (o linie) |  |
| `Data_Import` | Dată și oră | dată + oră (UTC) |

### Analize_AI

Analiza pe centru de cost și lună ({Luna}_{CC}).

| Coloană (nume intern) | Tip | Detalii |
|---|---|---|
| `Title` (afișat „Cheie”) | Text | cheia listei |
| `Luna` | Text (o linie) |  |
| `CentruCost` | Text (o linie) |  |
| `Buget_RON` | Număr | 2 zecimale |
| `Angajat_RON` | Număr | 2 zecimale |
| `Realizat_RON` | Număr | 2 zecimale |
| `Varianta_RON` | Număr | 2 zecimale |
| `Varianta_Pct` | Număr | 2 zecimale |
| `Maverick_RON` | Număr | 2 zecimale |
| `Alerta_Regula` | Alegere | opțiuni: Verde, Galben, Roșu |
| `Alerta_AI` | Alegere | opțiuni: Verde, Galben, Roșu |
| `Necesita_Revizuire` | Da/Nu |  |
| `Comentariu_AI` | Text pe mai multe linii |  |
| `Cauze` | Text pe mai multe linii |  |
| `Actiune` | Text pe mai multe linii |  |
| `Status_Analiza` | Alegere | opțiuni: OK, Eșuată |
| `Mesaj_Eroare` | Text pe mai multe linii |  |
| `Rulare_ID` | Text (o linie) |  |

### Erori_Import

Rândurile respinse la import (Flux 2).

| Coloană (nume intern) | Tip | Detalii |
|---|---|---|
| `Title` (afișat „Rulare_ID”) | Text | cheia listei |
| `Fisier` | Text (o linie) |  |
| `Rand` | Număr | 0 zecimale |
| `Cheie` | Text (o linie) |  |
| `Tip_Eroare` | Alegere | opțiuni: Câmp lipsă, Tip invalid, Valoare în afara domeniului, Format lună, Cod necunoscut, Duplicat |
| `Mesaj` | Text pe mai multe linii |  |
| `Data_Import` | Dată și oră | dată + oră (UTC) |

## Biblioteci de documente

- **Import_Realizat** — Fișierele JSON de import (Flux 2). Subfoldere: `Procesate`
- **Exporturi** — Exporturile CSV/JSON (BG_Export). Subfoldere: —

## Fișiere generate

- `sharepoint/provision_requests.json`: 94 cereri REST (liste, coloane, biblioteci, foldere)
- `sharepoint/seed_requests.json`: 169 cereri REST (datele inițiale din `data/seed/`)
