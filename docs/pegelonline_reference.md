# PEGELONLINE provider reference

Technical notes on the PEGELONLINE provider (`providers/pegelonline/`).
Everything marked *verified* was checked against the live service on
2026-10-23; the captures are in `pegelonline_inventory/` (see "Fixtures").

## 1. What PEGELONLINE is

The water-level service of the German federal waterways and shipping
administration (WSV), run for the GDWS by the ITZBund. It publishes raw
(unchecked) measurements of the federal waterways. Hydro Monitor uses its
**REST API v2**, documented in the "Leitfaden: REST-API"
(<https://pegelonline.wsv.de/webservice/guideRestapi>):

    https://www.pegelonline.wsv.de/webservices/rest-api/v2

- No authentication, no key. *Verified.*
- Licence **DL-DE->Zero-2.0**; the terms
  (<https://pegelonline.wsv.de/gast/nutzungsbedingungen>, 21.05.2024) allow
  commercial and non-commercial use, copying, changing and embedding in
  products and apps; no attribution is required. No rate limit is documented.
  Hydro Monitor polls gently: one station list per 24 hours, two small
  requests per entry every 30 minutes.
- The data are unchecked raw data; the terms exclude any liability.
- Only the last **~31 days** are available through the REST API.

### Relation to HyDAS

The same service also offers a newer **HyDAS API**
(`https://pegelonline.wsv.de/api/v1`), its implementation of the nationwide
"HydroDaten API Standard". It is the only live HyDAS implementation (listed
at <https://hydrodaten-api.mhwz.de/reals>) and is marked **beta**:
`meta.version` 0.1.0, with a warning that endpoints, parameters and
formats may still change incompatibly. Hydro Monitor therefore uses the
established REST API v2. The HyDAS API serves the same stations (786) and the
same data (W, Q), so switching later needs a new client, not a new model.

## 2. Endpoints used

| Purpose | Request | Notes |
|---|---|---|
| Station list | `GET stations.json?includeTimeseries=true` | All 786 stations, ~60 KB compressed. Cached 24 h in Home Assistant's storage. |
| One station | `GET stations/{uuid}.json?includeTimeseries=true` | Used at setup. |
| Unit and state | `GET stations/{uuid}/{W\|Q}.json?includeCurrentMeasurement=true` | The series with its unit and `currentMeasurement` (incl. `stateMnwMhw` for W). |
| History | `GET stations/{uuid}/{W\|Q}/measurements.json?start=P31D` | Raw values, oldest first. ~30 KB for 15-minute gauges, ~110 KB compressed (3.3 MB raw) for 1-minute gauges. |

Unknown stations or series answer HTTP 404 with
`{"message": "Timeseries does not exist.", "status": 404}`
(`pegelonline_inventory/errors.json`).

### Station

| Field | Meaning | Maps to |
|---|---|---|
| `uuid` | Stable id | `station_id` |
| `number` | WSV station number (also the numeric part of NIWIS's `DESM_DEXX<number>`) | station page URL |
| `shortname`, `longname` | Name; `shortname` is often properly cased, `longname` in capitals | `name` (see "Names") |
| `km` | River kilometre | `waterbody_position` |
| `agency` | Operating office | `operator` |
| `latitude`, `longitude` | Position, absent for 57 stations | `latitude`, `longitude` |
| `water.shortname/longname` | Waterbody | `waterbody` |
| `timeseries[]` | Series offered | `measurement_types` |

### Time series

| Field | Meaning |
|---|---|
| `shortname` | `W` water level, `Q` discharge (also `WT`, `LT`, `LF`, ... which are not used) |
| `unit` | `cm` (668 stations), `m+NN` (67), `m+PNP` (2) for W; `m³/s` for Q |
| `equidistance` | Minutes between values: 15 (502 W stations), 1 (224), 10 (10), 5 (1) |
| `gaugeZero` | `{value, unit, validFrom}`, only for W; becomes `gauge_zero_elevation` / `elevation_system` |
| `currentMeasurement` | `{timestamp, value}` plus `stateMnwMhw` and `stateNswHsw` for W |

**The unit of a water level is not always centimetres.** 69 stations report
metres above a datum. Hydro Monitor therefore always takes the unit from the
series and the trend code reads `m+NN` / `m+PNP` as metres (`trend.py`).

### Status words

`stateMnwMhw` compares the water level with the gauge's mean low water (MNW)
and mean high water (MHW): `low` (at or below MNW), `normal`, `high` (at or
above MHW), `unknown` (no MNW/MHW known for the series), `commented` (fault,
see the series' comment) and `out-dated` (older than 25 hours). Currently
seen across all stations: normal 237, low 138, unknown 357, commented 5. Only
`low`, `normal` and `high` become the state of the `level_state` sensor; the
service's own word is kept as its `raw_value` attribute. `stateNswHsw` (against
the highest navigable level) is not used.

Timestamps carry the local offset (`+01:00` / `+02:00`) and are converted
to UTC.

## 3. Mapping to Hydro Monitor

- A station appears for **water level** if it has a `W` series, for
  **discharge** if it has a `Q` series; stations with both appear for both. A
  station without coordinates cannot be sorted by distance and is not
  offered. Stations with neither W nor Q (42) have no type.
- **Names:** use the properly cased `shortname` if there is one; otherwise
  convert the capitals of the `longname`, keeping abbreviations such as `OP`,
  `UP`, `OW`, `UW` ("Hamm UW", "Berlin-Plötzensee OP", "Hamburg St. Pauli").
  When both are in capitals the long one wins, because a short waterbody
  name can be an abbreviation ("DHK" for "Datteln-Hamm-Kanal").
- **Observation:** `value` is the newest raw reading; `observed_on` its time
  (UTC, a point in time rather than a day).
- **Trends** (`change_1d`, `change_7d`) are the difference between the mean of
  the last 24 hours and the mean of the 24 hours one day / one week earlier.
  Two single readings are meaningless at tidal gauges: at Hamburg St. Pauli
  the level swings between about 340 and 700 cm twice a day, and two
  readings 24 hours apart differ by up to 200 cm from the tide's phase alone.
  Measured there, the spread of the 1-day change halves with 24-hour means
  (standard deviation 75 -> 40 cm), and for a synthetic tide the worst error
  drops from 63 cm to 2 cm. At Kaub the trend becomes smoother, too (5.0 ->
  3.9 cm). It also matches NIWIS, whose series are daily values.
- **30-day low and high** are the raw extremes of the last 30 days. At tidal
  gauges that is the full tidal range, which is what they are.
- **Sensors:** only those a raw series can fill (see
  `OBSERVATION_SENSOR_KEYS` in `providers/pegelonline/provider.py`), plus
  `level_state` (water level only). No low-water class, deciles or reference
  statistics.
- **Update interval:** 30 minutes. The history request is the primary data
  (a failure fails the update); the time-series request supplies the unit and
  the state (a failure after the first success keeps the value and records
  `level_state_error`).

### Known limits

- Only ~31 days of history exist, so there is no reference-period statistic
  (MQ, MNQ, percentiles) as with NIWIS.
- The state (`level_state`) is `unknown` for about half of the water-level
  stations (no MNW/MHW known) and the sensor is then unavailable.
- Tidal gauges have a large raw swing; the value itself is the instantaneous
  level.
- Stations whose station list entry has no coordinates (57, e.g. some abroad)
  cannot be selected.

## 4. Fixtures and checks

- `python -m tools.pegelonline_discovery` captures real responses into
  `pegelonline_inventory/` (`stations_sample.json`, `summary.json`,
  `measurements/`, `timeseries/`, `errors.json`): Kaub (W and Q), a 1-minute
  gauge, a metres-above-NN gauge, tidal Hamburg gauges, stations without
  coordinates or without W/Q, and each status word. Only Kaub keeps its full
  31 days; the others keep their newest 400 points to keep the repository
  small.
- `python -m tools.pegelonline_contract_check` checks the live service
  against what the provider relies on (station list shape and size, units,
  interval field, measurement and time-series shape, status vocabulary, the
  reference gauge Kaub) and exits 1 on drift.
