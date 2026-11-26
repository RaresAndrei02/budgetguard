# Raportul HTML în flux — expresii generate

> Fișier **generat** de `python report/render_preview.py --flow` din `report/template.html` și `report/fragments/*.html`. Nu-l edita de mână: modifici șablonul sau fragmentele și regenerezi.
> Pașii de construcție sunt în `docs/flux2_pas_cu_pas.md` (Pasul 9, varianta finală).

## `Json_RezCC` (Compose, fx)

```
json(concat('{"r":{"c":', string(variables('varRezCC')), '}}'))
```

## `Tot_Raport` (Compose, lipire directă, fără fx)

```
{
  "buget": "@{xpath(xml(outputs('Json_RezCC')), 'sum(/r/c/buget)')}",
  "realizat": "@{xpath(xml(outputs('Json_RezCC')), 'sum(/r/c/realizat)')}",
  "maverick": "@{xpath(xml(outputs('Json_RezCC')), 'sum(/r/c/maverick)')}",
  "varianta_pct": "@{div(mul(sub(float(xpath(xml(outputs('Json_RezCC')), 'sum(/r/c/realizat)')), float(xpath(xml(outputs('Json_RezCC')), 'sum(/r/c/buget)'))), 100), max(float(xpath(xml(outputs('Json_RezCC')), 'sum(/r/c/buget)')), 0.01))}"
}
```

## `Select_Rand_CC` (Select, text mode)

**From**: fx `variables('varRezCC')`

**Map** (fx):

```
concat('<tr><td style="padding:8px;border-top:1px solid #e5e7eb"><b>', item()?['cc'], '</b></td><td align="right" style="padding:8px;border-top:1px solid #e5e7eb">', formatNumber(float(item()?['buget']), 'N0', 'ro-RO'), '</td><td align="right" style="padding:8px;border-top:1px solid #e5e7eb">', formatNumber(float(item()?['realizat']), 'N0', 'ro-RO'), '</td><td align="right" style="padding:8px;border-top:1px solid #e5e7eb;color:', if(greater(float(item()?['varianta_ron']), 0), '#b42318', '#15803d'), '">', concat(if(greater(float(item()?['varianta_ron']), 0), '+', ''), formatNumber(float(item()?['varianta_ron']), 'N0', 'ro-RO')), '</td><td align="right" style="padding:8px;border-top:1px solid #e5e7eb;color:', if(greater(float(item()?['varianta_ron']), 0), '#b42318', '#15803d'), ';font-weight:600">', concat(concat(if(greater(float(item()?['varianta_pct']), 0), '+', ''), formatNumber(float(item()?['varianta_pct']), 'N2', 'ro-RO')), '%'), '</td><td align="right" style="padding:8px;border-top:1px solid #e5e7eb;color:', if(greater(float(item()?['maverick']), 0), '#b42318', '#9ca3af'), '">', formatNumber(float(item()?['maverick']), 'N0', 'ro-RO'), '</td><td align="center" style="padding:8px;border-top:1px solid #e5e7eb"><span style="display:inline-block;padding:2px 10px;border-radius:10px;font-size:12px;font-weight:600;background:', if(equals(item()?['alerta_regula'], 'Roșu'), '#fee4e2', if(equals(item()?['alerta_regula'], 'Galben'), '#fef3c7', if(equals(item()?['alerta_regula'], 'Verde'), '#dcfce7', '#f3f4f6'))), ';color:', if(equals(item()?['alerta_regula'], 'Roșu'), '#b42318', if(equals(item()?['alerta_regula'], 'Galben'), '#92400e', if(equals(item()?['alerta_regula'], 'Verde'), '#166534', '#6b7280'))), '">', item()?['alerta_regula'], '</span></td><td align="center" style="padding:8px;border-top:1px solid #e5e7eb"><span style="display:inline-block;padding:2px 10px;border-radius:10px;font-size:12px;font-weight:600;background:', if(equals(item()?['alerta_ai'], 'Roșu'), '#fee4e2', if(equals(item()?['alerta_ai'], 'Galben'), '#fef3c7', if(equals(item()?['alerta_ai'], 'Verde'), '#dcfce7', '#f3f4f6'))), ';color:', if(equals(item()?['alerta_ai'], 'Roșu'), '#b42318', if(equals(item()?['alerta_ai'], 'Galben'), '#92400e', if(equals(item()?['alerta_ai'], 'Verde'), '#166534', '#6b7280'))), '">', item()?['alerta_ai'], '</span>', if(and(equals(item()?['status'], 'OK'), not(equals(item()?['alerta_ai'], item()?['alerta_regula']))), '<div style="font-size:11px;color:#b45309;font-weight:600;margin-top:3px">⚠ necesită revizuire</div>', if(equals(item()?['status'], 'OK'), '', '<div style="font-size:11px;color:#6b7280;margin-top:3px">AI indisponibil</div>')), '</td></tr>')
```

## `Select_Bloc_AI` (Select, text mode)

**From**: fx `variables('varRezCC')`

**Map** (fx):

```
concat('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:10px;border-collapse:collapse"><tr><td style="border-left:4px solid ', if(equals(item()?['alerta_ai'], 'Roșu'), '#b42318', if(equals(item()?['alerta_ai'], 'Galben'), '#92400e', if(equals(item()?['alerta_ai'], 'Verde'), '#166534', '#6b7280'))), ';background:#f9fafb;padding:10px 14px"><div style="font-size:14px"><b>', item()?['cc'], '</b> <span style="display:inline-block;padding:1px 8px;margin-left:4px;border-radius:10px;font-size:11px;font-weight:600;background:', if(equals(item()?['alerta_ai'], 'Roșu'), '#fee4e2', if(equals(item()?['alerta_ai'], 'Galben'), '#fef3c7', if(equals(item()?['alerta_ai'], 'Verde'), '#dcfce7', '#f3f4f6'))), ';color:', if(equals(item()?['alerta_ai'], 'Roșu'), '#b42318', if(equals(item()?['alerta_ai'], 'Galben'), '#92400e', if(equals(item()?['alerta_ai'], 'Verde'), '#166534', '#6b7280'))), '">', item()?['alerta_ai'], '</span>', if(and(equals(item()?['status'], 'OK'), not(equals(item()?['alerta_ai'], item()?['alerta_regula']))), concat(' <span style="font-size:11px;color:#b45309;font-weight:600;margin-left:6px">⚠ necesită revizuire (regula: ', item()?['alerta_regula'], ')</span>'), if(equals(item()?['status'], 'OK'), '', ' <span style="font-size:11px;color:#6b7280;margin-left:6px">analiza AI a eșuat</span>')), '</div><div style="font-size:13px;margin-top:6px;color:#1f2937">', item()?['comentariu'], '</div>', if(empty(item()?['actiune']), '', concat('<div style="font-size:13px;margin-top:6px;color:#374151"><b>Acțiune recomandată:</b> ', item()?['actiune'], '</div>')), '</td></tr></table>')
```

## `Select_Rand_Mav` (Select, text mode)

**From**: fx `body('Filter_Mav')`

**Map** (fx):

```
concat('<tr><td style="padding:6px 8px;border-top:1px solid #e5e7eb">', item()?['Title'], '</td><td align="right" style="padding:6px 8px;border-top:1px solid #e5e7eb">', formatNumber(float(item()?['Suma_RON']), 'N0', 'ro-RO'), '</td><td align="right" style="padding:6px 8px;border-top:1px solid #e5e7eb">', formatNumber(float(item()?['Aprobat_RON']), 'N0', 'ro-RO'), '</td><td align="right" style="padding:6px 8px;border-top:1px solid #e5e7eb;color:#b42318;font-weight:600">', formatNumber(float(item()?['Maverick_RON']), 'N0', 'ro-RO'), '</td></tr>')
```

## `Select_Rand_Err` (Select, text mode)

**From**: fx `variables('varErori')`

**Map** (fx):

```
concat('<tr><td valign="top" style="padding:6px 8px;border-top:1px solid #e5e7eb">', item()?['rand'], '</td><td valign="top" style="padding:6px 8px;border-top:1px solid #e5e7eb;color:#b42318">', item()?['tip'], '</td><td valign="top" style="padding:6px 8px;border-top:1px solid #e5e7eb;color:#374151">', item()?['mesaj'], '</td></tr>')
```

## `Html_Raport` (Compose, fx)

```
replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(outputs('Sablon_Raport'), '{{LUNA}}', outputs('Luna_Import')), '{{FISIER}}', variables('varFisier')), '{{RULARE_ID}}', variables('varRulare')), '{{CURS_INFO}}', concat('BNR ', variables('varDataCurs'), ': EUR ', string(variables('varCursuri')?['EUR']), ', USD ', string(variables('varCursuri')?['USD']))), '{{TOT_BUGET}}', formatNumber(float(outputs('Tot_Raport')?['buget']), 'N0', 'ro-RO')), '{{TOT_REALIZAT}}', formatNumber(float(outputs('Tot_Raport')?['realizat']), 'N0', 'ro-RO')), '{{TOT_VAR_CULOARE}}', if(greater(float(outputs('Tot_Raport')?['varianta_pct']), 0), '#b42318', '#15803d')), '{{TOT_VAR_PCT}}', concat(concat(if(greater(float(outputs('Tot_Raport')?['varianta_pct']), 0), '+', ''), formatNumber(float(outputs('Tot_Raport')?['varianta_pct']), 'N2', 'ro-RO')), '%')), '{{TOT_MAV_CULOARE}}', if(greater(float(outputs('Tot_Raport')?['maverick']), 0), '#b42318', '#1f2937')), '{{TOT_MAVERICK}}', formatNumber(float(outputs('Tot_Raport')?['maverick']), 'N0', 'ro-RO')), '{{N_TOTAL}}', string(outputs('Sumar_Import')?['total'])), '{{N_AI_OK}}', string(outputs('Sumar_Import')?['ai_ok'])), '{{N_VALIDE}}', string(outputs('Sumar_Import')?['valide'])), '{{N_AI_ESEC}}', string(outputs('Sumar_Import')?['ai_esec'])), '{{N_INVALIDE}}', string(outputs('Sumar_Import')?['invalide'])), '{{N_DUPLICATE}}', string(outputs('Sumar_Import')?['duplicate'])), '{{ROWS_CC}}', join(body('Select_Rand_CC'), '')), '{{PRAG_ALERTA}}', string(outputs('cfg')?['prag_alerta_pct'])), '{{BLOCURI_AI}}', join(body('Select_Bloc_AI'), '')), '{{ROWS_MAVERICK}}', if(empty(body('Select_Rand_Mav')), '<tr><td colspan="4" style="padding:6px 8px;border-top:1px solid #e5e7eb;color:#6b7280">Nicio cheltuială fără cerere aprobată.</td></tr>', join(body('Select_Rand_Mav'), ''))), '{{ROWS_ERORI}}', if(empty(body('Select_Rand_Err')), '<tr><td colspan="3" style="padding:6px 8px;border-top:1px solid #e5e7eb;color:#6b7280">Nicio înregistrare respinsă.</td></tr>', join(body('Select_Rand_Err'), ''))), '{{DATA_RAPORT}}', convertTimeZone(utcNow(), 'UTC', 'GTB Standard Time', 'dd.MM.yyyy HH:mm'))
```
