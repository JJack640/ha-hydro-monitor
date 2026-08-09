# Automation blueprints

These are copy-paste Home Assistant automation blueprints for Hydro
Monitor. Like [`docs/examples`](../docs/examples), they are plain
documentation, not part of the integration: nothing here is installed
automatically, and none of it is required for Hydro Monitor to work.

## Files

| File | What it does |
|---|---|
| [`automation/hydro_monitor/notify_low_water_class.yaml`](automation/hydro_monitor/notify_low_water_class.yaml) / [`.de.yaml`](automation/hydro_monitor/notify_low_water_class.de.yaml) | Notify when a "Low-water class" sensor changes to a severity you choose (default: extremely low / very low) |
| [`automation/hydro_monitor/notify_stale_data.yaml`](automation/hydro_monitor/notify_stale_data.yaml) / [`.de.yaml`](automation/hydro_monitor/notify_stale_data.de.yaml) | Notify when a station's "Measurement age" sensor flags its data as stale (reuses Hydro Monitor's own `stale` attribute — no threshold to configure) |

Both are available in English and German (`.de.yaml`) — pick whichever
matches your Home Assistant instance's language; the blueprint's own name,
description, and input labels are only shown in that one language (unlike
entity names, blueprints have no automatic per-user translation
mechanism).

Neither blueprint hardcodes a notification service: the "Notification
action" input accepts any action sequence you build with Home Assistant's
action selector (a mobile app notify action, a persistent notification,
a Telegram message, a script, ...), so it works with whatever you already
use.

## How to import a blueprint

**Option A — import by URL** (recommended, keeps the blueprint update-able
from this repo later):

1. Go to **Settings → Automations & Scenes → Blueprints**.
2. Click **Import Blueprint**.
3. Paste the blueprint's raw GitHub URL, for example:
   `https://raw.githubusercontent.com/JJack640/ha-hydro-monitor/main/blueprints/automation/hydro_monitor/notify_low_water_class.yaml`
   (swap in the file you want — use the `.de.yaml` URL for the German
   version).
4. Click **Preview** and then **Import Blueprint**.

**Option B — copy the file manually:**

1. Copy the `.yaml` file into `<config>/blueprints/automation/hydro_monitor/`
   in your Home Assistant configuration folder (create the folders if
   they don't exist).
2. Go to **Settings → Automations & Scenes → Blueprints** and reload, or
   restart Home Assistant.

## Using a blueprint

1. Go to **Settings → Automations & Scenes → Automations → Create
   Automation → Use Blueprint**.
2. Pick the imported Hydro Monitor blueprint.
3. Fill in the sensor entity (your real entity ID — see
   [`docs/examples/README.md`](../docs/examples/README.md) for how to find
   it) and build the notification action.
4. Save, then trigger it manually once (or wait for a real state change)
   to confirm it fires as expected.
