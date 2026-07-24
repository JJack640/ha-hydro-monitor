# NIWIS API Inventory

Generated: 2026-07-22T07:11:57.757996+00:00

## Representative stations

| Measurement type | Station ID | Station name |
|---|---|---|
| discharge | DESM_DEBY16607001 | Inkofen |
| discharge | DESM_DEBY16612001 | Peißenberg |
| discharge | DESM_DEBY16825002 | Appolding |
| discharge | DESM_DEBY17207508 | Grafenmühle |
| discharge | DESM_DEBY17404000 | Schrottenbaummühle |
| discharge | DESM_DEBY17464001 | Fürsteneck |
| discharge | DESM_DEBY18003004 | Wasserburg |
| discharge | DESM_DEBY18263005 | Bad Aibling |
| discharge | DESM_DEBY18384509 | Engfurt |
| discharge | DESM_DEBY18454003 | Staudach |
| groundwater_level | DEGM_DEBY83614 | NBS-H/W KB 11/1 |
| groundwater_level | DEGM_DEBY9230 | EGG D 4 |
| groundwater_level | DEGM_DEBY9248 | FRAUENRIEDHAUSEN D 48 |
| groundwater_level | DEGM_DEHBHB_GMS 220 | GMS 220 - An der Aue |
| groundwater_level | DEGM_DEHE11324 | OFFENBACH |
| groundwater_level | DEGM_DEHE11765 | TREBUR |
| groundwater_level | DEGM_DEHE11847 | BAUSCHHEIM |
| groundwater_level | DEGM_DEHE12029 | EGELSBACH  |
| groundwater_level | DEGM_DEHE12909 | GERNSHEIM |
| groundwater_level | DEGM_DEHE13415 | VIELBRUNN |
| spring_discharge | DEGM_DEHE5122 | CALDEN |
| spring_discharge | DEGM_DEBW0601/517-7 | QF Gallusquelle WV, Veringenstadt-Hermentingen |
| spring_discharge | DEGM_DEBW1/415-1 | QF Bronnbachquelle, Rottenburg |
| spring_discharge | DEGM_DEBW600/068-1 | QF 1 Seipfertquelle, Amoltern |
| spring_discharge | DEGM_DEBW600/554-9 | QF Nächstquelle Götzingen, Buchen (Odenwald) |
| spring_discharge | DEGM_DEBW600/665-7 | Q Blautopf, Blaubeuren |
| spring_discharge | DEGM_DEBY15500 | Helchenbach 18/2 |
| spring_discharge | DEGM_DEBY20501 | Hohenwarth 14/2 |
| spring_discharge | DEGM_DEBY24504 | Kirchendemenreuth 9/12 |
| spring_discharge | DEGM_DEBY2500 | Dorfquelle Adlholz 9/21 |
| water_level | DESM_DEBY16607001 | Inkofen |
| water_level | DESM_DEBY16612001 | Peißenberg |
| water_level | DESM_DEBY16825002 | Appolding |
| water_level | DESM_DEBY17207508 | Grafenmühle |
| water_level | DESM_DEBY17404000 | Schrottenbaummühle |
| water_level | DESM_DEBY17464001 | Fürsteneck |
| water_level | DESM_DEBY18003004 | Wasserburg |
| water_level | DESM_DEBY18263005 | Bad Aibling |
| water_level | DESM_DEBY18384509 | Engfurt |
| water_level | DESM_DEBY18454003 | Staudach |

## Datasets and fields

### `catalog`

| Field | Types | Present | Non-null | Coverage | Example |
|---|---|---:|---:|---:|---|
| `landcode` | string | 632/632 | 632/632 | 100.0% | `"DEBY"` |
| `lizenz` | string | 632/632 | 632/632 | 100.0% | `"cc-by/4.0"` |
| `messgroesse` | array | 632/632 | 632/632 | 100.0% | `["Abfluss", "Wasserstand"]` |
| `messstelleNr` | string | 632/632 | 632/632 | 100.0% | `"DESM_DEBY16607001"` |
| `name` | string | 632/632 | 632/632 | 100.0% | `"Inkofen"` |

### `derived_quantities`

| Field | Types | Present | Non-null | Coverage | Example |
|---|---|---:|---:|---:|---|
| `abgeleiteteGroesse` | string | 43/43 | 43/43 | 100.0% | `"Abfluss Dezile tageweise"` |
| `benoetigtReferenzzeitraum` | boolean | 43/43 | 43/43 | 100.0% | `true` |
| `benoetigtZeitintervall` | boolean | 43/43 | 43/43 | 100.0% | `false` |
| `einheit` | null, string | 43/43 | 33/43 | 76.7% | `"m³/s"` |
| `endpunkt` | string | 43/43 | 43/43 | 100.0% | `"berechneKlassifikationsgrenzeDynamisch"` |
| `messgroesse` | string | 43/43 | 43/43 | 100.0% | `"ABFLUSS"` |

### `series_discharge`

| Field | Types | Present | Non-null | Coverage | Example |
|---|---|---:|---:|---:|---|
| `datum` | string | 300/300 | 300/300 | 100.0% | `"2026-07-21"` |
| `einheit` | string | 300/300 | 300/300 | 100.0% | `"m³/s"` |
| `flag` | null | 300/300 | 0/300 | 0.0% | `null` |
| `messstelleNr` | string | 300/300 | 300/300 | 100.0% | `"DESM_DEBY16607001"` |
| `messwert` | number | 300/300 | 300/300 | 100.0% | `15.3` |

### `series_groundwater_level`

| Field | Types | Present | Non-null | Coverage | Example |
|---|---|---:|---:|---:|---|
| `datum` | string | 300/300 | 300/300 | 100.0% | `"2026-07-21"` |
| `einheit` | string | 300/300 | 300/300 | 100.0% | `"m. ü. NHN"` |
| `flag` | null, string | 300/300 | 3/300 | 1.0% | `"BfGAdded"` |
| `messstelleNr` | string | 300/300 | 300/300 | 100.0% | `"DEGM_DEBY83614"` |
| `messwert` | number | 300/300 | 300/300 | 100.0% | `-777.0` |

### `series_spring_discharge`

| Field | Types | Present | Non-null | Coverage | Example |
|---|---|---:|---:|---:|---|
| `datum` | string | 300/300 | 300/300 | 100.0% | `"2026-07-21"` |
| `einheit` | string | 300/300 | 300/300 | 100.0% | `"l/s"` |
| `flag` | null, string | 300/300 | 138/300 | 46.0% | `"BfGAdded"` |
| `messstelleNr` | string | 300/300 | 300/300 | 100.0% | `"DEGM_DEHE5122"` |
| `messwert` | number | 300/300 | 300/300 | 100.0% | `-777.0` |

### `series_water_level`

| Field | Types | Present | Non-null | Coverage | Example |
|---|---|---:|---:|---:|---|
| `datum` | string | 300/300 | 300/300 | 100.0% | `"2026-07-21"` |
| `einheit` | string | 300/300 | 300/300 | 100.0% | `"cm"` |
| `flag` | null | 300/300 | 0/300 | 0.0% | `null` |
| `messstelleNr` | string | 300/300 | 300/300 | 100.0% | `"DESM_DEBY16607001"` |
| `messwert` | number | 300/300 | 300/300 | 100.0% | `37.0` |

### `station_discharge`

| Field | Types | Present | Non-null | Coverage | Example |
|---|---|---:|---:|---:|---|
| `bemerkung` | null, string | 10/10 | 3/10 | 30.0% | `"Abflüsse seit 1976 durch den Vilstalsee (AEo = 666 km²;Gesamtstauraum = 10.7 hm³) beeinflusst"` |
| `betreiber` | string | 10/10 | 10/10 | 100.0% | `"WWA München"` |
| `breite` | number | 10/10 | 10/10 | 100.0% | `48.4606574767785` |
| `darstellungGok` | null | 10/10 | 0/10 | 0.0% | `null` |
| `ezgGroesse` | integer | 10/10 | 10/10 | 100.0% | `3097` |
| `gewaesser` | string | 10/10 | 10/10 | 100.0% | `"Amper"` |
| `gkz` | integer | 10/10 | 10/10 | 100.0% | `164` |
| `hoeheGok` | null | 10/10 | 0/10 | 0.0% | `null` |
| `hoehePnp` | number | 10/10 | 10/10 | 100.0% | `415.58` |
| `hoehensystem` | string | 10/10 | 10/10 | 100.0% | `"DHHN12"` |
| `institution` | string | 10/10 | 10/10 | 100.0% | `"LfU BY"` |
| `kennwertWasserstand` | null | 10/10 | 0/10 | 0.0% | `null` |
| `laenge` | number | 10/10 | 10/10 | 100.0% | `11.8655273361443` |
| `lageGewaesser` | string | 10/10 | 10/10 | 100.0% | `"11.9"` |
| `landcode` | string | 10/10 | 10/10 | 100.0% | `"DEBY"` |
| `lizenz` | string | 10/10 | 10/10 | 100.0% | `"cc-by/4.0"` |
| `messgroesse` | array | 10/10 | 10/10 | 100.0% | `["Abfluss", "Wasserstand"]` |
| `messstelleNr` | string | 10/10 | 10/10 | 100.0% | `"DESM_DEBY16607001"` |
| `messstellentyp` | null | 10/10 | 0/10 | 0.0% | `null` |
| `name` | string | 10/10 | 10/10 | 100.0% | `"Inkofen"` |
| `nnq` | number | 10/10 | 10/10 | 100.0% | `10.7` |
| `nnqDatum` | string | 10/10 | 10/10 | 100.0% | `"1947-10-03"` |
| `nnw` | null | 10/10 | 0/10 | 0.0% | `null` |
| `nnwDatum` | null | 10/10 | 0/10 | 0.0% | `null` |
| `ortslage` | null | 10/10 | 0/10 | 0.0% | `null` |
| `teilraumName` | null | 10/10 | 0/10 | 0.0% | `null` |
| `teilraumNr` | null | 10/10 | 0/10 | 0.0% | `null` |
| `typKennwert` | null | 10/10 | 0/10 | 0.0% | `null` |
| `urlBetreiber` | null | 10/10 | 0/10 | 0.0% | `null` |
| `urlInstitution` | string | 10/10 | 10/10 | 100.0% | `"https://www.gkd.bayern.de/de/"` |
| `urlMessstelle` | string | 10/10 | 10/10 | 100.0% | `"https://www.gkd.bayern.de/de/fluesse/abfluss/kelheim/inkofen-16607001"` |

### `station_groundwater_level`

| Field | Types | Present | Non-null | Coverage | Example |
|---|---|---:|---:|---:|---|
| `bemerkung` | null, string | 10/10 | 6/10 | 60.0% | `"Über HE-API verfügbar"` |
| `betreiber` | string | 10/10 | 10/10 | 100.0% | `"WWA AB"` |
| `breite` | number | 10/10 | 10/10 | 100.0% | `50.2036860313345` |
| `darstellungGok` | boolean | 10/10 | 10/10 | 100.0% | `false` |
| `ezgGroesse` | null | 10/10 | 0/10 | 0.0% | `null` |
| `gewaesser` | null | 10/10 | 0/10 | 0.0% | `null` |
| `gkz` | null | 10/10 | 0/10 | 0.0% | `null` |
| `hoeheGok` | number | 10/10 | 10/10 | 100.0% | `233.3` |
| `hoehePnp` | null | 10/10 | 0/10 | 0.0% | `null` |
| `hoehensystem` | string | 10/10 | 10/10 | 100.0% | `"DHHN12"` |
| `institution` | string | 10/10 | 10/10 | 100.0% | `"LFU BY"` |
| `kennwertWasserstand` | null | 10/10 | 0/10 | 0.0% | `null` |
| `laenge` | number | 10/10 | 10/10 | 100.0% | `9.62182150403828` |
| `lageGewaesser` | null | 10/10 | 0/10 | 0.0% | `null` |
| `landcode` | string | 10/10 | 10/10 | 100.0% | `"DEBY"` |
| `lizenz` | string | 10/10 | 10/10 | 100.0% | `"cc-by/4.0"` |
| `messgroesse` | array | 10/10 | 10/10 | 100.0% | `["Grundwasserstand"]` |
| `messstelleNr` | string | 10/10 | 10/10 | 100.0% | `"DEGM_DEBY83614"` |
| `messstellentyp` | string | 10/10 | 10/10 | 100.0% | `"W"` |
| `name` | string | 10/10 | 10/10 | 100.0% | `"NBS-H/W KB 11/1"` |
| `nnq` | null | 10/10 | 0/10 | 0.0% | `null` |
| `nnqDatum` | null | 10/10 | 0/10 | 0.0% | `null` |
| `nnw` | null | 10/10 | 0/10 | 0.0% | `null` |
| `nnwDatum` | null | 10/10 | 0/10 | 0.0% | `null` |
| `ortslage` | string | 10/10 | 10/10 | 100.0% | `"Obersinn"` |
| `teilraumName` | string | 10/10 | 10/10 | 100.0% | `"Spessart, Rhönvorland und Buntsandstein des Odenwaldes"` |
| `teilraumNr` | string | 10/10 | 10/10 | 100.0% | `"6201"` |
| `typKennwert` | null | 10/10 | 0/10 | 0.0% | `null` |
| `urlBetreiber` | null, string | 10/10 | 6/10 | 60.0% | `"https://rp-darmstadt.hessen.de/umwelt-und-energie/gewaesser-und-bodenschutz"` |
| `urlInstitution` | string | 10/10 | 10/10 | 100.0% | `"https://www.gkd.bayern.de/de/grundwasser"` |
| `urlMessstelle` | null, string | 10/10 | 9/10 | 90.0% | `"https://www.gkd.bayern.de/de/grundwasser/oberesstockwerk/bayern/obersinn-83614"` |

### `station_spring_discharge`

| Field | Types | Present | Non-null | Coverage | Example |
|---|---|---:|---:|---:|---|
| `bemerkung` | null, string | 10/10 | 1/10 | 10.0% | `"Nicht über API verfügbar"` |
| `betreiber` | null, string | 10/10 | 5/10 | 50.0% | `"RPU Kassel"` |
| `breite` | number | 10/10 | 10/10 | 100.0% | `51.4114734836788` |
| `darstellungGok` | boolean | 10/10 | 10/10 | 100.0% | `false` |
| `ezgGroesse` | null | 10/10 | 0/10 | 0.0% | `null` |
| `gewaesser` | null | 10/10 | 0/10 | 0.0% | `null` |
| `gkz` | null | 10/10 | 0/10 | 0.0% | `null` |
| `hoeheGok` | number | 10/10 | 10/10 | 100.0% | `0.0` |
| `hoehePnp` | null | 10/10 | 0/10 | 0.0% | `null` |
| `hoehensystem` | null, string | 10/10 | 5/10 | 50.0% | `"DHHN12"` |
| `institution` | string | 10/10 | 10/10 | 100.0% | `"HLNUG"` |
| `kennwertWasserstand` | null | 10/10 | 0/10 | 0.0% | `null` |
| `laenge` | number | 10/10 | 10/10 | 100.0% | `9.4031086416366` |
| `lageGewaesser` | null | 10/10 | 0/10 | 0.0% | `null` |
| `landcode` | string | 10/10 | 10/10 | 100.0% | `"DEHE"` |
| `lizenz` | string | 10/10 | 10/10 | 100.0% | `"dl-zero-de/2.0"` |
| `messgroesse` | array | 10/10 | 10/10 | 100.0% | `["Quellschüttung"]` |
| `messstelleNr` | string | 10/10 | 10/10 | 100.0% | `"DEGM_DEHE5122"` |
| `messstellentyp` | string | 10/10 | 10/10 | 100.0% | `"Q"` |
| `name` | string | 10/10 | 10/10 | 100.0% | `"CALDEN"` |
| `nnq` | null | 10/10 | 0/10 | 0.0% | `null` |
| `nnqDatum` | null | 10/10 | 0/10 | 0.0% | `null` |
| `nnw` | null | 10/10 | 0/10 | 0.0% | `null` |
| `nnwDatum` | null | 10/10 | 0/10 | 0.0% | `null` |
| `ortslage` | string | 10/10 | 10/10 | 100.0% | `"Calden"` |
| `teilraumName` | string | 10/10 | 10/10 | 100.0% | `"Borgentreicher Mulde und Kasseler Graben"` |
| `teilraumNr` | string | 10/10 | 10/10 | 100.0% | `"05112"` |
| `typKennwert` | null | 10/10 | 0/10 | 0.0% | `null` |
| `urlBetreiber` | null, string | 10/10 | 1/10 | 10.0% | `"https://rp-kassel.hessen.de/umwelt/wasser-und-bodenschutz"` |
| `urlInstitution` | string | 10/10 | 10/10 | 100.0% | `"https://umweltdaten.hessen.de/mapapps/resources/apps/lgd/"` |
| `urlMessstelle` | null, string | 10/10 | 5/10 | 50.0% | `"https://www.hlnug.de/messwerte/datenportal/messstelle/4/10/13488"` |

### `station_water_level`

| Field | Types | Present | Non-null | Coverage | Example |
|---|---|---:|---:|---:|---|
| `bemerkung` | null, string | 10/10 | 3/10 | 30.0% | `"Abflüsse seit 1976 durch den Vilstalsee (AEo = 666 km²;Gesamtstauraum = 10.7 hm³) beeinflusst"` |
| `betreiber` | string | 10/10 | 10/10 | 100.0% | `"WWA München"` |
| `breite` | number | 10/10 | 10/10 | 100.0% | `48.4606574767785` |
| `darstellungGok` | null | 10/10 | 0/10 | 0.0% | `null` |
| `ezgGroesse` | integer | 10/10 | 10/10 | 100.0% | `3097` |
| `gewaesser` | string | 10/10 | 10/10 | 100.0% | `"Amper"` |
| `gkz` | integer | 10/10 | 10/10 | 100.0% | `164` |
| `hoeheGok` | null | 10/10 | 0/10 | 0.0% | `null` |
| `hoehePnp` | number | 10/10 | 10/10 | 100.0% | `415.58` |
| `hoehensystem` | string | 10/10 | 10/10 | 100.0% | `"DHHN12"` |
| `institution` | string | 10/10 | 10/10 | 100.0% | `"LfU BY"` |
| `kennwertWasserstand` | null | 10/10 | 0/10 | 0.0% | `null` |
| `laenge` | number | 10/10 | 10/10 | 100.0% | `11.8655273361443` |
| `lageGewaesser` | string | 10/10 | 10/10 | 100.0% | `"11.9"` |
| `landcode` | string | 10/10 | 10/10 | 100.0% | `"DEBY"` |
| `lizenz` | string | 10/10 | 10/10 | 100.0% | `"cc-by/4.0"` |
| `messgroesse` | array | 10/10 | 10/10 | 100.0% | `["Abfluss", "Wasserstand"]` |
| `messstelleNr` | string | 10/10 | 10/10 | 100.0% | `"DESM_DEBY16607001"` |
| `messstellentyp` | null | 10/10 | 0/10 | 0.0% | `null` |
| `name` | string | 10/10 | 10/10 | 100.0% | `"Inkofen"` |
| `nnq` | number | 10/10 | 10/10 | 100.0% | `10.7` |
| `nnqDatum` | string | 10/10 | 10/10 | 100.0% | `"1947-10-03"` |
| `nnw` | null | 10/10 | 0/10 | 0.0% | `null` |
| `nnwDatum` | null | 10/10 | 0/10 | 0.0% | `null` |
| `ortslage` | null | 10/10 | 0/10 | 0.0% | `null` |
| `teilraumName` | null | 10/10 | 0/10 | 0.0% | `null` |
| `teilraumNr` | null | 10/10 | 0/10 | 0.0% | `null` |
| `typKennwert` | null | 10/10 | 0/10 | 0.0% | `null` |
| `urlBetreiber` | null | 10/10 | 0/10 | 0.0% | `null` |
| `urlInstitution` | string | 10/10 | 10/10 | 100.0% | `"https://www.gkd.bayern.de/de/"` |
| `urlMessstelle` | string | 10/10 | 10/10 | 100.0% | `"https://www.gkd.bayern.de/de/fluesse/abfluss/kelheim/inkofen-16607001"` |

## Derived quantity probe results

Successful: 43/43

| Name | Measurement | Endpoint | Station | Success | Response | Error |
|---|---|---|---|---:|---|---|
| Abfluss Dezile tageweise | ABFLUSS | `berechneKlassifikationsgrenzeDynamisch` | DESM_DEBY16607001 | yes | object | `` |
| Abfluss Entwicklung letzte 7 Tage | ABFLUSS | `berechneEinzelwertKategorie` | DESM_DEBY16607001 | yes | object | `` |
| Abfluss Klassifikation mit statischen Grenzwerten | ABFLUSS | `berechneKlassifikationsgrenzeStatisch` | DESM_DEBY16607001 | yes | object | `` |
| Abfluss Klassifikation mit variablen Grenzwerten | ABFLUSS | `berechneKlassifikationsgrenzeDynamisch` | DESM_DEBY16607001 | yes | object | `` |
| Abfluss Niedrigwasserklasse aktueller Tag | ABFLUSS | `berechneEinzelwertKategorie` | DESM_DEBY16607001 | yes | object | `` |
| Klimaindikator Niedrigwassertage | ABFLUSS | `berechneKlimaindikatorNiedrigwassertage` |  | yes | object | `` |
| LFI | ABFLUSS | `berechneLfi` | DESM_DEBY16607001 | yes | object | `` |
| MNQ | ABFLUSS | `berechneEinzelwertNummer` | DESM_DEBY16607001 | yes | object | `` |
| MQ | ABFLUSS | `berechneEinzelwertNummer` | DESM_DEBY16607001 | yes | object | `` |
| Max Q pro Kalendartag | ABFLUSS | `berechneZeitreihenErgebnisNummer` | DESM_DEBY16607001 | yes | object | `` |
| Median Q Statisch | ABFLUSS | `berechneEinzelwertNummer` | DESM_DEBY16607001 | yes | object | `` |
| Median Q pro Kalendertag | ABFLUSS | `berechneZeitreihenErgebnisNummer` | DESM_DEBY16607001 | yes | object | `` |
| Min Q pro Kalendartag | ABFLUSS | `berechneZeitreihenErgebnisNummer` | DESM_DEBY16607001 | yes | object | `` |
| NM30Q | ABFLUSS | `berechneEinzelwertNummer` | DESM_DEBY16607001 | yes | object | `` |
| NM30Q mit Datum | ABFLUSS | `berechneEinzelwertKategorie` | DESM_DEBY16607001 | yes | object | `` |
| NM7Q | ABFLUSS | `berechneEinzelwertNummer` | DESM_DEBY16607001 | yes | object | `` |
| NM7Q mit Datum | ABFLUSS | `berechneEinzelwertKategorie` | DESM_DEBY16607001 | yes | object | `` |
| NQ | ABFLUSS | `berechneEinzelwertNummer` | DESM_DEBY16607001 | yes | object | `` |
| SumD | ABFLUSS | `berechneZeitreihenErgebnisNummer` | DESM_DEBY16607001 | yes | object | `` |
| SumD Zeitfenster | ABFLUSS | `berechneEinzelwertNummer` | DESM_DEBY16607001 | yes | object | `` |
| SumV | ABFLUSS | `berechneZeitreihenErgebnisNummer` | DESM_DEBY16607001 | yes | object | `` |
| SumV Zeitfenster | ABFLUSS | `berechneEinzelwertNummer` | DESM_DEBY16607001 | yes | object | `` |
| Grundwasser Niedrigwasserklasse aktueller Tag | GRUNDWASSER | `berechneEinzelwertKategorie` | DEGM_DEBY83614 | yes | object | `` |
| Grundwasserstand Klassifikation mit statischen Grenzwerten | GRUNDWASSER | `berechneKlassifikationsgrenzeStatisch` | DEGM_DEBY83614 | yes | object | `` |
| Grundwasserstand Klassifikation mit variablen Grenzwerten | GRUNDWASSER | `berechneKlassifikationsgrenzeDynamisch` | DEGM_DEBY83614 | yes | object | `` |
| Klimaindikator monatl. Abw. Mittelwert | GRUNDWASSER | `berechneKlimaindikatorMonatlicheAbweichungenMittelwert` |  | yes | object | `` |
| m unter Geländeoberkante | GRUNDWASSER | `berechneZeitreihenErgebnisNummer` | DEGM_DEBY83614 | yes | object | `` |
| Quellschüttung Klassifikation mit statischen Grenzwerten | QUELLSCHUETTUNG | `berechneKlassifikationsgrenzeStatisch` | DEGM_DEHE5122 | yes | object | `` |
| Quellschüttung Klassifikation mit variablen Grenzwerten | QUELLSCHUETTUNG | `berechneKlassifikationsgrenzeDynamisch` | DEGM_DEHE5122 | yes | object | `` |
| Quellschüttung Niedrigwasserklasse aktueller Tag | QUELLSCHUETTUNG | `berechneEinzelwertKategorie` | DEGM_DEHE5122 | yes | object | `` |
| MNW | WASSERSTAND | `berechneEinzelwertNummer` | DESM_DEBY16607001 | yes | object | `` |
| MW | WASSERSTAND | `berechneEinzelwertNummer` | DESM_DEBY16607001 | yes | object | `` |
| Median W bezogen auf Referenzzeitraum | WASSERSTAND | `berechneEinzelwertNummer` | DESM_DEBY16607001 | yes | object | `` |
| Median W pro Kalendertag | WASSERSTAND | `berechneZeitreihenErgebnisNummer` | DESM_DEBY16607001 | yes | object | `` |
| NW | WASSERSTAND | `berechneEinzelwertNummer` | DESM_DEBY16607001 | yes | object | `` |
| Tage unter GlW/RWN/BWu | WASSERSTAND | `berechneZeitreihenErgebnisNummer` | DESM_DEBY16607001 | yes | object | `` |
| Tage unter GlWRNW/BWu aktueller Tag | WASSERSTAND | `berechneEinzelwertNummer` | DESM_DEBY16607001 | yes | object | `` |
| Wasserstand Dezile tageweise | WASSERSTAND | `berechneKlassifikationsgrenzeDynamisch` | DESM_DEBY16607001 | yes | object | `` |
| Wasserstand Entwicklung letzte 7 Tage | WASSERSTAND | `berechneEinzelwertKategorie` | DESM_DEBY16607001 | yes | object | `` |
| Wasserstand Klassifikation mit statischen Grenzwerten | WASSERSTAND | `berechneKlassifikationsgrenzeStatisch` | DESM_DEBY16607001 | yes | object | `` |
| Wasserstand Klassifikation mit variablen Grenzwerten | WASSERSTAND | `berechneKlassifikationsgrenzeDynamisch` | DESM_DEBY16607001 | yes | object | `` |
| Wasserstand Niedrigwasserklasse aktueller Tag | WASSERSTAND | `berechneEinzelwertKategorie` | DESM_DEBY16607001 | yes | object | `` |
| unter GlW | WASSERSTAND | `berechneEinzelwertKategorie` | DESM_DEBY16607001 | yes | object | `` |

## Derived quantities

| Name | Measurement | Reference period | Time interval | Endpoint |
|---|---|---:|---:|---|
| Abfluss Dezile tageweise | ABFLUSS | yes | no | `berechneKlassifikationsgrenzeDynamisch` |
| Abfluss Entwicklung letzte 7 Tage | ABFLUSS | no | no | `berechneEinzelwertKategorie` |
| Abfluss Klassifikation mit statischen Grenzwerten | ABFLUSS | yes | no | `berechneKlassifikationsgrenzeStatisch` |
| Abfluss Klassifikation mit variablen Grenzwerten | ABFLUSS | yes | no | `berechneKlassifikationsgrenzeDynamisch` |
| Abfluss Niedrigwasserklasse aktueller Tag | ABFLUSS | yes | no | `berechneEinzelwertKategorie` |
| Klimaindikator Niedrigwassertage | ABFLUSS | no | no | `berechneKlimaindikatorNiedrigwassertage` |
| LFI | ABFLUSS | yes | no | `berechneLfi` |
| MNQ | ABFLUSS | yes | no | `berechneEinzelwertNummer` |
| MQ | ABFLUSS | yes | no | `berechneEinzelwertNummer` |
| Max Q pro Kalendartag | ABFLUSS | yes | no | `berechneZeitreihenErgebnisNummer` |
| Median Q Statisch | ABFLUSS | yes | no | `berechneEinzelwertNummer` |
| Median Q pro Kalendertag | ABFLUSS | yes | no | `berechneZeitreihenErgebnisNummer` |
| Min Q pro Kalendartag | ABFLUSS | yes | no | `berechneZeitreihenErgebnisNummer` |
| NM30Q | ABFLUSS | no | yes | `berechneEinzelwertNummer` |
| NM30Q mit Datum | ABFLUSS | no | yes | `berechneEinzelwertKategorie` |
| NM7Q | ABFLUSS | no | yes | `berechneEinzelwertNummer` |
| NM7Q mit Datum | ABFLUSS | no | yes | `berechneEinzelwertKategorie` |
| NQ | ABFLUSS | yes | no | `berechneEinzelwertNummer` |
| SumD | ABFLUSS | yes | yes | `berechneZeitreihenErgebnisNummer` |
| SumD Zeitfenster | ABFLUSS | yes | yes | `berechneEinzelwertNummer` |
| SumV | ABFLUSS | yes | yes | `berechneZeitreihenErgebnisNummer` |
| SumV Zeitfenster | ABFLUSS | yes | yes | `berechneEinzelwertNummer` |
| Grundwasser Niedrigwasserklasse aktueller Tag | GRUNDWASSER | yes | no | `berechneEinzelwertKategorie` |
| Grundwasserstand Klassifikation mit statischen Grenzwerten | GRUNDWASSER | yes | no | `berechneKlassifikationsgrenzeStatisch` |
| Grundwasserstand Klassifikation mit variablen Grenzwerten | GRUNDWASSER | yes | no | `berechneKlassifikationsgrenzeDynamisch` |
| Klimaindikator monatl. Abw. Mittelwert | GRUNDWASSER | no | no | `berechneKlimaindikatorMonatlicheAbweichungenMittelwert` |
| m unter Geländeoberkante | GRUNDWASSER | no | yes | `berechneZeitreihenErgebnisNummer` |
| Quellschüttung Klassifikation mit statischen Grenzwerten | QUELLSCHUETTUNG | yes | no | `berechneKlassifikationsgrenzeStatisch` |
| Quellschüttung Klassifikation mit variablen Grenzwerten | QUELLSCHUETTUNG | yes | no | `berechneKlassifikationsgrenzeDynamisch` |
| Quellschüttung Niedrigwasserklasse aktueller Tag | QUELLSCHUETTUNG | yes | no | `berechneEinzelwertKategorie` |
| MNW | WASSERSTAND | yes | no | `berechneEinzelwertNummer` |
| MW | WASSERSTAND | yes | no | `berechneEinzelwertNummer` |
| Median W bezogen auf Referenzzeitraum | WASSERSTAND | yes | no | `berechneEinzelwertNummer` |
| Median W pro Kalendertag | WASSERSTAND | yes | no | `berechneZeitreihenErgebnisNummer` |
| NW | WASSERSTAND | yes | no | `berechneEinzelwertNummer` |
| Tage unter GlW/RWN/BWu | WASSERSTAND | yes | yes | `berechneZeitreihenErgebnisNummer` |
| Tage unter GlWRNW/BWu aktueller Tag | WASSERSTAND | no | no | `berechneEinzelwertNummer` |
| Wasserstand Dezile tageweise | WASSERSTAND | yes | no | `berechneKlassifikationsgrenzeDynamisch` |
| Wasserstand Entwicklung letzte 7 Tage | WASSERSTAND | no | no | `berechneEinzelwertKategorie` |
| Wasserstand Klassifikation mit statischen Grenzwerten | WASSERSTAND | yes | no | `berechneKlassifikationsgrenzeStatisch` |
| Wasserstand Klassifikation mit variablen Grenzwerten | WASSERSTAND | yes | no | `berechneKlassifikationsgrenzeDynamisch` |
| Wasserstand Niedrigwasserklasse aktueller Tag | WASSERSTAND | yes | no | `berechneEinzelwertKategorie` |
| unter GlW | WASSERSTAND | no | no | `berechneEinzelwertKategorie` |

## Time-series quality

| Measurement type | Total | Valid | Invalid | Coverage | Flags | Units |
|---|---:|---:|---:|---:|---|---|
| discharge | 300 | 300 | 0 | 100.0% | none | m³/s: 300 |
| groundwater_level | 300 | 297 | 3 | 99.0% | BfGAdded: 3 | m. ü. NHN: 300 |
| spring_discharge | 300 | 162 | 138 | 54.0% | BfGAdded: 138 | l/s: 300 |
| water_level | 300 | 300 | 0 | 100.0% | none | cm: 300 |

### `discharge` station quality

| Station ID | Total | Valid | Invalid | Coverage | Flags |
|---|---:|---:|---:|---:|---|
| DESM_DEBY16607001 | 30 | 30 | 0 | 100.0% | none |
| DESM_DEBY16612001 | 30 | 30 | 0 | 100.0% | none |
| DESM_DEBY16825002 | 30 | 30 | 0 | 100.0% | none |
| DESM_DEBY17207508 | 30 | 30 | 0 | 100.0% | none |
| DESM_DEBY17404000 | 30 | 30 | 0 | 100.0% | none |
| DESM_DEBY17464001 | 30 | 30 | 0 | 100.0% | none |
| DESM_DEBY18003004 | 30 | 30 | 0 | 100.0% | none |
| DESM_DEBY18263005 | 30 | 30 | 0 | 100.0% | none |
| DESM_DEBY18384509 | 30 | 30 | 0 | 100.0% | none |
| DESM_DEBY18454003 | 30 | 30 | 0 | 100.0% | none |

### `groundwater_level` station quality

| Station ID | Total | Valid | Invalid | Coverage | Flags |
|---|---:|---:|---:|---:|---|
| DEGM_DEBY83614 | 30 | 29 | 1 | 96.7% | BfGAdded: 1 |
| DEGM_DEBY9230 | 30 | 29 | 1 | 96.7% | BfGAdded: 1 |
| DEGM_DEBY9248 | 30 | 29 | 1 | 96.7% | BfGAdded: 1 |
| DEGM_DEHBHB_GMS 220 | 30 | 30 | 0 | 100.0% | none |
| DEGM_DEHE11324 | 30 | 30 | 0 | 100.0% | none |
| DEGM_DEHE11765 | 30 | 30 | 0 | 100.0% | none |
| DEGM_DEHE11847 | 30 | 30 | 0 | 100.0% | none |
| DEGM_DEHE12029 | 30 | 30 | 0 | 100.0% | none |
| DEGM_DEHE12909 | 30 | 30 | 0 | 100.0% | none |
| DEGM_DEHE13415 | 30 | 30 | 0 | 100.0% | none |

### `spring_discharge` station quality

| Station ID | Total | Valid | Invalid | Coverage | Flags |
|---|---:|---:|---:|---:|---|
| DEGM_DEBW0601/517-7 | 30 | 5 | 25 | 16.7% | BfGAdded: 25 |
| DEGM_DEBW1/415-1 | 30 | 5 | 25 | 16.7% | BfGAdded: 25 |
| DEGM_DEBW600/068-1 | 30 | 2 | 28 | 6.7% | BfGAdded: 28 |
| DEGM_DEBW600/554-9 | 30 | 5 | 25 | 16.7% | BfGAdded: 25 |
| DEGM_DEBW600/665-7 | 30 | 5 | 25 | 16.7% | BfGAdded: 25 |
| DEGM_DEBY15500 | 30 | 29 | 1 | 96.7% | BfGAdded: 1 |
| DEGM_DEBY20501 | 30 | 29 | 1 | 96.7% | BfGAdded: 1 |
| DEGM_DEBY24504 | 30 | 29 | 1 | 96.7% | BfGAdded: 1 |
| DEGM_DEBY2500 | 30 | 29 | 1 | 96.7% | BfGAdded: 1 |
| DEGM_DEHE5122 | 30 | 24 | 6 | 80.0% | BfGAdded: 6 |

### `water_level` station quality

| Station ID | Total | Valid | Invalid | Coverage | Flags |
|---|---:|---:|---:|---:|---|
| DESM_DEBY16607001 | 30 | 30 | 0 | 100.0% | none |
| DESM_DEBY16612001 | 30 | 30 | 0 | 100.0% | none |
| DESM_DEBY16825002 | 30 | 30 | 0 | 100.0% | none |
| DESM_DEBY17207508 | 30 | 30 | 0 | 100.0% | none |
| DESM_DEBY17404000 | 30 | 30 | 0 | 100.0% | none |
| DESM_DEBY17464001 | 30 | 30 | 0 | 100.0% | none |
| DESM_DEBY18003004 | 30 | 30 | 0 | 100.0% | none |
| DESM_DEBY18263005 | 30 | 30 | 0 | 100.0% | none |
| DESM_DEBY18384509 | 30 | 30 | 0 | 100.0% | none |
| DESM_DEBY18454003 | 30 | 30 | 0 | 100.0% | none |

