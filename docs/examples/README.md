# Dashboard examples

These are copy-paste Lovelace dashboard examples for Hydro Monitor. They are
plain documentation, not part of the integration: nothing here is installed
automatically, and none of it is required for Hydro Monitor to work.

This corresponds to Phase 6 ("Advanced Home Assistant Integration") of the
[technical roadmap](../niwis_reference.md#715-proposed-implementation-order) —
deliberately kept as example configuration rather than custom Lovelace cards
or bundled dashboards, so it needs no maintenance inside
`custom_components/hydro_monitor` and carries no risk of breaking the
integration itself.

## Files

One single-station view file per **measurement type**, each with its own
`icon` and `path` — creating views from more than one file for the same
station (e.g. a discharge tab and a water level tab) won't collide or
share an icon:

| File | Measurement type | Icon | Path |
|---|---|---|---|
| [`dashboard_station_overview_discharge.yaml`](dashboard_station_overview_discharge.yaml) / [`.de.yaml`](dashboard_station_overview_discharge.de.yaml) | Discharge | `mdi:waves` | `hydro-monitor-discharge` / `hydro-monitor-abfluss` |
| [`dashboard_station_overview_water_level.yaml`](dashboard_station_overview_water_level.yaml) / [`.de.yaml`](dashboard_station_overview_water_level.de.yaml) | Water level | `mdi:water` | `hydro-monitor-water-level` / `hydro-monitor-wasserstand` |
| [`dashboard_station_overview_groundwater.yaml`](dashboard_station_overview_groundwater.yaml) / [`.de.yaml`](dashboard_station_overview_groundwater.de.yaml) | Groundwater level | `mdi:water-well` | `hydro-monitor-groundwater` / `hydro-monitor-grundwasser` |
| [`dashboard_station_overview_spring_discharge.yaml`](dashboard_station_overview_spring_discharge.yaml) / [`.de.yaml`](dashboard_station_overview_spring_discharge.de.yaml) | Spring discharge | `mdi:fountain` | `hydro-monitor-spring-discharge` / `hydro-monitor-quellschuettung` |

The discharge and water level files carry current status, trend, a 30-day
history graph, historical-statistics comparison (MQ/MNQ or MW/MNW and the
`%` comparison sensors), classification boundaries and deciles, and station
metadata. The groundwater level and spring discharge files have the same
current status/history/classification/station-metadata cards, but without
historical statistics, deciles, the `%` comparison sensors or the official
7-day development sensor — those don't exist for these two measurement
types (see `providers/niwis/const.py`:
`HISTORICAL_STATISTIC_MEASUREMENT_TYPES`, `DECILES_MEASUREMENT_TYPES`,
`OFFICIAL_DEVELOPMENT_7D_MEASUREMENT_TYPES` — all three are
`{discharge, water_level}` only). The corresponding entities do still exist
on groundwater/spring discharge devices, but sit permanently "unavailable",
so these two files leave them out rather than showing cards that never
have a value. Station metadata also differs: no waterbody/catchment
area/river-kilometre fields (river-specific), locality/ground
elevation/hydrogeological region instead.

All four history graphs plot the actual value alongside a reference band,
so you can tell at a glance whether today's value is low, typical, or high
— not just whether it's rising or falling. How rich that band is depends on
what NIWIS publishes for the measurement type:

- **Discharge** gets NIWIS's own calendar-day min/median/max (the lowest,
  typical, and highest discharge ever recorded specifically on each
  calendar day, reference period 1991-2020) — a genuinely historical
  comparison. These entities are disabled by default (see below) — enable
  them for the comparison to actually render.
- **Water level** gets NIWIS's calendar-day median the same way, but NIWIS
  publishes no calendar-day min/max for water level, so those two lines
  fall back to Hydro Monitor's own rolling 30-day minimum/maximum instead
  — a narrower, locally-computed comparison, not the historical extremes
  for that date. The median entity is disabled by default; the 30-day
  min/max are enabled by default.
- **Groundwater level and spring discharge** have no NIWIS historical
  statistics at all (see above), so their graphs use Hydro Monitor's
  rolling 30-day minimum/maximum only — enabled by default, no entities to
  turn on first.

- [`dashboard_multi_station_comparison.yaml`](dashboard_multi_station_comparison.yaml) /
  [`dashboard_multi_station_comparison.de.yaml`](dashboard_multi_station_comparison.de.yaml) —
  a comparison across several configured stations (any mix of measurement
  types), for users monitoring more than one. Icon `mdi:compare`, path
  `hydro-monitor-comparison` / `hydro-monitor-vergleich`.

All files are available in English and German (`.de.yaml`) — both are
functionally identical; only the static card titles, `path`, and code
comments differ, since those have no automatic translation mechanism
(unlike entity names, see below). `icon` is identical across languages.

All files are complete Lovelace **views** (`title`/`icon`/`path` plus
`cards`), not just a list of cards — pasting one under an existing
dashboard's `views:` list adds a new tab with a title and icon already set,
no manual naming step needed. They use `entities` cards rather than
`glance` cards throughout (other than the two gauges in the discharge/water
level files): glance cards give each entity a fixed, narrow column that
truncates Hydro Monitor's longer, already-localized names (e.g. "Inkofen
Mittlerer Abfluss (MQ)"); entities cards give each row the card's full
width instead, which reads much better in a typical multi-column dashboard
layout.

All files also deliberately avoid overriding most entity `name:` values.
Hydro Monitor's own entity names are already translated
(`translations/en.json` / `de.json`) and follow whatever language your
Home Assistant instance is configured for automatically — a hardcoded
`name:` in the dashboard YAML would just show a second, unlocalized copy
of that label instead. Every file's header is the one exception handled
differently: it uses a Jinja2 template
(`device_attr(device_id('sensor...'), 'model')`) to show the device's
already-localized model text (e.g. "Hydrologische Messstelle (Abfluss)"),
since the plain entity name alone doesn't indicate which measurement type
a same-named station's device represents.

## Before you paste these in

Every entity ID in every file is a placeholder starting with `sensor.REPLACE_`.
Hydro Monitor's entity IDs depend on your station's name, so they cannot be
predicted in an example file — and if a single station offers more than one
measurement type (e.g. discharge and water level), Home Assistant may append
`_2`, `_3`, etc. to keep the underlying devices' entity IDs unique, since
they share the same station name.

To find your real entity IDs:

1. Go to **Settings → Devices & Services → Hydro Monitor**.
2. Open the device for the station/measurement type you want (its title
   shows which measurement type it is, e.g. "Inkofen – Discharge").
3. Each entity's row shows its entity ID, or click into an entity for the
   full ID.

Then replace every `sensor.REPLACE_...` placeholder below with your actual
entity ID.

## How to use a file

1. Open the dashboard you want to add this to, or create a new one.
2. Enter edit mode → the three-dot menu → **Edit in YAML**.
3. Paste the whole file's contents as one new item under the `views:` list
   — this gives you a new tab with the title and icon already set. To add
   the content to an *existing* view instead, paste only the nested
   `cards:` block (everything under `cards:`, without the `title`/`icon`/
   `path` lines), and set that view's own title/icon yourself via the
   pencil icon next to its tab.
4. Replace the placeholder entity IDs as described above.
5. Save.

Several optional Hydro Monitor sensors used in these examples are disabled
by default (classification boundaries, deciles, historical statistics, the
`%`-of-mean comparison sensors). A disabled entity that has never been
turned on has no state at all yet, so its card row will show
**"Entity not found"**, not "unavailable" — enable the ones you want on the
entity's settings page (Settings → Devices & Services → Entities → search
for the sensor), then give it one update cycle to pick up a value. Once
enabled, a genuinely failed fetch (e.g. NIWIS returned an error for that
quantity) shows as "unavailable" instead.
