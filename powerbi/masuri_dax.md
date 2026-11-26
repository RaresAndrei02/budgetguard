# Power BI — model, măsuri DAX și pagini

> Raport pe 2 pagini peste listele SharePoint: **Buget vs. Realizat** și **Pipeline aprobări**.
> Conector: **SharePoint Online List**, implementarea **2.0**, vizualizarea **All** (*Toate*). Adresa site-ului: rădăcina site-ului BudgetGuard (fără `/Lists/...`).
> Fișierul `.pbix` nu se pune în git (conține datele); se salvează capturi ale paginilor în `docs/capturi/powerbi/`.

---

## 1. Tabelele (Power Query)

| Tabel | Listă | Coloane păstrate | Tip de date |
|---|---|---|---|
| `Bugete` | Bugete | `Title`, `Luna`, `CentruCost`, `Categorie`, `Buget_RON`, `Angajat_RON`, `Realizat_RON`, `Ramas_RON` | sumele: *Decimal number* |
| `Realizat_Lunar` | Realizat_Lunar | `Title`, `Luna`, `CentruCost`, `Categorie`, `Suma_RON`, `Aprobat_RON`, `Maverick_RON`, `Nr_Documente` | sumele: *Decimal number* |
| `Cereri` | Cereri_Achizitie | `Title`, `TitluCerere`, `CentruCost`, `Categorie`, `Luna_Buget`, `Valoare_RON`, `Tip`, `Peste_Buget`, `Status`, `Data_Cerere`, `Data_Finalizare`, `Aprobari`, `Furnizor_ANAF` | datele: *Date/Time* |
| `Istoric` | Istoric_Stari | `Title`, `Flux`, `Stare_Veche`, `Stare_Noua`, `Actor`, `Data_Ora` | `Data_Ora`: *Date/Time* |
| `Analize` | Analize_AI | `Title`, `Luna`, `CentruCost`, `Varianta_Pct`, `Alerta_Regula`, `Alerta_AI`, `Necesita_Revizuire`, `Status_Analiza`, `Comentariu_AI` | — |
| `CC` | Nomenclator, filtrat `Tip = CC` | `Title` (redenumit `CC`), `Denumire` | — |
| `CAT` | Nomenclator, filtrat `Tip = CAT` | `Title` (redenumit `CAT`), `Denumire` | — |

Pași comuni în Power Query:
1. *Choose Columns* → doar coloanele din tabel. Conectorul aduce și coloane de sistem (`ContentType`, `Modified`, `Attachments`…).
2. Dacă o coloană Choice (`Status`, `Flux`, `Alerta_*`) apare ca **Record**, o extinzi și păstrezi doar `Value`.
3. Datele din SharePoint vin în **UTC**. Pentru afișare în ora României: coloană nouă `DateTimeZone.ToLocal(DateTimeZone.From([Data_Cerere]))` sau, mai simplu, se lasă UTC (diferența de 2 ore nu schimbă indicatorii lunari).

### Tabelul de date `Calendar` (DAX)

Luna din liste e text `yyyy-MM`, deci calendarul e la nivel de lună, cu o cheie text:

```DAX
Calendar =
VAR _Start = DATE ( 2026, 9, 1 )
VAR _End   = DATE ( 2027, 3, 31 )
RETURN
    ADDCOLUMNS (
        CALENDAR ( _Start, _End ),
        "Luna", FORMAT ( [Date], "yyyy-MM" ),
        "An", YEAR ( [Date] ),
        "Nr luna", MONTH ( [Date] ),
        "Luna afisata", FORMAT ( [Date], "MMM yyyy" )
    )
```

*Mark as date table* pe `Calendar[Date]`. Coloana `Luna afisata` se sortează după `Calendar[Date]` (*Sort by column*).

Pentru relațiile pe lună, un tabel de luni unice:

```DAX
Luni = DISTINCT ( SELECTCOLUMNS ( Calendar, "Luna", Calendar[Luna], "Luna afisata", Calendar[Luna afisata], "Data", DATE ( Calendar[An], Calendar[Nr luna], 1 ) ) )
```

## 2. Relațiile

Toate sunt *one-to-many*, cu filtrare într-o singură direcție (dimensiune → fapt):

| Din (1) | În (*) |
|---|---|
| `Luni[Luna]` | `Bugete[Luna]`, `Realizat_Lunar[Luna]`, `Cereri[Luna_Buget]`, `Analize[Luna]` |
| `CC[CC]` | `Bugete[CentruCost]`, `Realizat_Lunar[CentruCost]`, `Cereri[CentruCost]`, `Analize[CentruCost]` |
| `CAT[CAT]` | `Bugete[Categorie]`, `Realizat_Lunar[Categorie]`, `Cereri[Categorie]` |
| `Calendar[Date]` | `Cereri[Data cerere (zi)]` *(coloană calculată, mai jos)* |

```DAX
-- coloană calculată în Cereri
Data cerere (zi) = DATEVALUE ( Cereri[Data_Cerere] )
```

## 3. Măsurile

Se creează într-un tabel gol `_Masuri` (*Enter data* → un tabel fără rânduri), ca să fie grupate.

### Buget vs. Realizat

```DAX
Buget = SUM ( Bugete[Buget_RON] )

Angajat = SUM ( Bugete[Angajat_RON] )

Realizat = SUM ( Bugete[Realizat_RON] )

Ramas = [Buget] - [Angajat]

Varianta = [Realizat] - [Buget]

Varianta % = DIVIDE ( [Varianta], [Buget] )

Utilizare buget % = DIVIDE ( [Angajat], [Buget] )      -- cât din buget e deja angajat prin cereri aprobate

Executie buget % = DIVIDE ( [Realizat], [Buget] )      -- cât din buget s-a cheltuit efectiv

Maverick = SUM ( Realizat_Lunar[Maverick_RON] )

Maverick % din realizat = DIVIDE ( [Maverick], SUM ( Realizat_Lunar[Suma_RON] ) )
```

Alerta, cu aceeași regulă ca în flux (pragurile 5% și 10%):

```DAX
Alerta =
VAR _v = ABS ( [Varianta %] )
RETURN
    IF (
        ISBLANK ( [Realizat] ) || [Realizat] = 0, BLANK (),
        SWITCH ( TRUE (), _v <= 0.05, "Verde", _v <= 0.10, "Galben", "Roșu" )
    )

Alerta culoare =
SWITCH ( [Alerta], "Verde", "#15803d", "Galben", "#b45309", "Roșu", "#b42318", "#6b7280" )

Analize de revizuit =
CALCULATE ( COUNTROWS ( Analize ), Analize[Necesita_Revizuire] = TRUE () )
```

`Alerta culoare` se folosește la *Conditional formatting → Font color / Background → Format style: Field value*.

### Pipeline aprobări

```DAX
Nr cereri = COUNTROWS ( Cereri )

Cereri in aprobare = CALCULATE ( [Nr cereri], Cereri[Status] = "În aprobare" )

Cereri aprobate = CALCULATE ( [Nr cereri], Cereri[Status] IN { "Aprobată", "Exportată" } )

Cereri respinse = CALCULATE ( [Nr cereri], Cereri[Status] = "Respinsă" )

Rata respingere =
DIVIDE ( [Cereri respinse], [Cereri aprobate] + [Cereri respinse] )

Respinse la validare =
CALCULATE ( [Cereri respinse], ISBLANK ( Cereri[Aprobari] ) )   -- respinse automat (V1–V5), fără niciun aprobator

Valoare aprobata = CALCULATE ( SUM ( Cereri[Valoare_RON] ), Cereri[Status] IN { "Aprobată", "Exportată" } )

Timp mediu aprobare (ore) =
AVERAGEX (
    FILTER (
        Cereri,
        NOT ISBLANK ( Cereri[Data_Finalizare] )
            && NOT ISBLANK ( Cereri[Aprobari] )     -- exclude respingerile automate, care durează secunde
    ),
    DATEDIFF ( Cereri[Data_Cerere], Cereri[Data_Finalizare], MINUTE ) / 60
)

Cereri peste buget % = DIVIDE ( CALCULATE ( [Nr cereri], Cereri[Peste_Buget] = TRUE () ), [Nr cereri] )
```

Format: sumele cu *Whole number* și separator de mii; procentele cu *Percentage*, 1–2 zecimale.

## 4. Paginile

### Pagina 1 — Buget vs. Realizat

| Zonă | Vizual | Câmpuri |
|---|---|---|
| Sus | 4 × *Card* | `Buget`, `Realizat`, `Varianta %`, `Maverick` |
| Stânga | *Slicer* (listă) | `Luni[Luna afisata]` (implicit 2026-10) |
| Centru | *Clustered column chart* | Axa `CC[CC]`; valori `Buget`, `Angajat`, `Realizat` |
| Dreapta | *Table* | `CC[CC]`, `Buget`, `Realizat`, `Varianta %`, `Maverick`, `Alerta` (culoare din `Alerta culoare`) |
| Jos | *Matrix* | Rânduri `CC[CC]`, coloane `CAT[CAT]`, valori `Maverick` (formatare condiționată roșie pentru > 0) → scoate în evidență **HR / TRN** |
| Jos, dreapta | *Table* | `Analize[CentruCost]`, `Alerta_Regula`, `Alerta_AI`, `Necesita_Revizuire`, `Comentariu_AI` |

### Pagina 2 — Pipeline aprobări

| Zonă | Vizual | Câmpuri |
|---|---|---|
| Sus | 4 × *Card* | `Nr cereri`, `Valoare aprobata`, `Timp mediu aprobare (ore)`, `Rata respingere` |
| Stânga | *Donut* sau *Funnel* | Legendă `Cereri[Status]`, valori `Nr cereri` |
| Centru | *Line chart* | Axa `Calendar[Date]` (zi), valori `Nr cereri` |
| Dreapta | *Stacked bar* | Axa `CC[CC]`, valori `Cereri aprobate`, `Cereri respinse` |
| Jos | *Table* | `Cereri[Title]`, `TitluCerere`, `CentruCost`, `Valoare_RON`, `Status`, `Peste_Buget`, `Data_Cerere` (filtrat implicit pe „În aprobare” + „Aprobată”) |

## 5. Verificare rapidă (pe datele de test, luna 2026-10)

| Măsură | Valoare așteptată (aprox.) |
|---|---|
| `Buget` | 500.000 |
| `Realizat` | ~518.200 (depinde de cursul BNR al ultimului import) |
| `Varianta %` | ~+3,6% |
| `Maverick` | 12.348 (tot pe HR / TRN) |
| `Alerta` pe CC | MKT Roșu, OPS Galben, IT / HR / SAL Verde |
| `Analize de revizuit` | 1 (HR) |

Aceleași cifre apar în raportul pe email din Flux 2, deci cele două se pot verifica reciproc.
