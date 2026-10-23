"""Plain-language explanations for Hydro Monitor's official NIWIS sensors.

Many of Hydro Monitor's sensors mirror NIWIS's own hydrological abbreviations
(MQ, MNQ, NQ, GlW, ...), which are standard terminology for hydrologists but
not self-explanatory to a general Home Assistant user. Home Assistant has no
built-in mechanism for a per-entity "description" tooltip on the device
page, so this text is instead surfaced as a "description" extra_state_attribute,
visible in each entity's "more info" dialog. Like device model text (see
.localization), this has no translation_key mechanism and must be resolved
manually against the configured instance language.
"""

from __future__ import annotations

from typing import Final

SENSOR_GLOSSARY: Final = {
    "level_state": {
        "en": (
            "PEGELONLINE's own classification of the current water level "
            "against the gauge's mean low water (MNW) and mean high water "
            "(MHW): low (at or below MNW), normal, or high (at or above "
            "MHW). Unavailable when the gauge has no such reference values "
            "or reports a fault."
        ),
        "de": (
            "PEGELONLINEs eigene Einordnung des aktuellen Wasserstands "
            "gegenüber dem mittleren Niedrigwasser (MNW) und dem mittleren "
            "Hochwasser (MHW) des Pegels: niedrig (auf oder unter MNW), "
            "normal oder hoch (auf oder über MHW). Nicht verfügbar, wenn "
            "der Pegel keine solchen Bezugswerte hat oder eine Störung "
            "meldet."
        ),
    },
    "low_water_class": {
        "en": (
            "NIWIS's official current low-water classification (extremely "
            "low / very low / low / no low water), based on today's value "
            "compared to the classification boundaries."
        ),
        "de": (
            "NIWIS' offizielle aktuelle Niedrigwasserklassifikation (extrem "
            "niedrig / sehr niedrig / niedrig / kein Niedrigwasser), "
            "basierend auf dem heutigen Wert im Vergleich zu den "
            "Klassifikationsgrenzen."
        ),
    },
    "official_development_7d": {
        "en": "NIWIS's own assessment of how the value has developed over the last 7 days.",
        "de": "NIWIS' eigene Einschätzung, wie sich der Wert in den letzten 7 Tagen entwickelt hat.",
    },
    "boundary_static_extremely_low": {
        "en": (
            "Fixed threshold below which NIWIS classifies the value as "
            "\"extremely low\", unchanged throughout the year."
        ),
        "de": (
            "Fester Schwellenwert, unterhalb dessen NIWIS den Wert als "
            "„extrem niedrig“ einstuft, das ganze Jahr über unverändert."
        ),
    },
    "boundary_static_very_low": {
        "en": (
            "Fixed threshold below which NIWIS classifies the value as "
            "\"very low\", unchanged throughout the year."
        ),
        "de": (
            "Fester Schwellenwert, unterhalb dessen NIWIS den Wert als "
            "„sehr niedrig“ einstuft, das ganze Jahr über unverändert."
        ),
    },
    "boundary_static_low": {
        "en": (
            "Fixed threshold below which NIWIS classifies the value as "
            "\"low\", unchanged throughout the year."
        ),
        "de": (
            "Fester Schwellenwert, unterhalb dessen NIWIS den Wert als "
            "„niedrig“ einstuft, das ganze Jahr über unverändert."
        ),
    },
    "boundary_dynamic_extremely_low": {
        "en": (
            "Threshold below which NIWIS classifies the value as "
            "\"extremely low\" specifically for today's calendar day, "
            "adjusted for the time of year."
        ),
        "de": (
            "Schwellenwert, unterhalb dessen NIWIS den Wert speziell für "
            "den heutigen Kalendertag als „extrem niedrig“ einstuft, "
            "angepasst an die Jahreszeit."
        ),
    },
    "boundary_dynamic_very_low": {
        "en": (
            "Threshold below which NIWIS classifies the value as "
            "\"very low\" specifically for today's calendar day, adjusted "
            "for the time of year."
        ),
        "de": (
            "Schwellenwert, unterhalb dessen NIWIS den Wert speziell für "
            "den heutigen Kalendertag als „sehr niedrig“ einstuft, "
            "angepasst an die Jahreszeit."
        ),
    },
    "boundary_dynamic_low": {
        "en": (
            "Threshold below which NIWIS classifies the value as \"low\" "
            "specifically for today's calendar day, adjusted for the time "
            "of year."
        ),
        "de": (
            "Schwellenwert, unterhalb dessen NIWIS den Wert speziell für "
            "den heutigen Kalendertag als „niedrig“ einstuft, angepasst an "
            "die Jahreszeit."
        ),
    },
    "mq": {
        "en": "Mean discharge across the reference period (1991-2020).",
        "de": "Mittlerer Abfluss über den Referenzzeitraum (1991-2020).",
    },
    "mnq": {
        "en": "Mean of the annual lowest discharge values across the reference period.",
        "de": "Mittelwert der jährlichen niedrigsten Abflusswerte über den Referenzzeitraum.",
    },
    "nm7q": {
        "en": "Lowest 7-day mean discharge within the last 30 days.",
        "de": "Niedrigster 7-Tage-Mittelabfluss innerhalb der letzten 30 Tage.",
    },
    "nm30q": {
        "en": "Lowest 30-day mean discharge within the last 30 days.",
        "de": "Niedrigster 30-Tage-Mittelabfluss innerhalb der letzten 30 Tage.",
    },
    "mw": {
        "en": "Mean water level across the reference period (1991-2020).",
        "de": "Mittlerer Wasserstand über den Referenzzeitraum (1991-2020).",
    },
    "mnw": {
        "en": "Mean of the annual lowest water level values across the reference period.",
        "de": "Mittelwert der jährlichen niedrigsten Wasserstandswerte über den Referenzzeitraum.",
    },
    "percent_of_mq": {
        "en": "Current value as a percentage of MQ (mean discharge) -- 100% means exactly average.",
        "de": "Aktueller Wert als Prozentsatz von MQ (mittlerer Abfluss) -- 100 % bedeutet genau durchschnittlich.",
    },
    "percent_of_mnq": {
        "en": "Current value as a percentage of MNQ (mean low discharge).",
        "de": "Aktueller Wert als Prozentsatz von MNQ (mittlerer Niedrigwasserabfluss).",
    },
    "percent_of_mw": {
        "en": "Current value as a percentage of MW (mean water level) -- 100% means exactly average.",
        "de": "Aktueller Wert als Prozentsatz von MW (mittlerer Wasserstand) -- 100 % bedeutet genau durchschnittlich.",
    },
    "percent_of_mnw": {
        "en": "Current value as a percentage of MNW (mean low water level).",
        "de": "Aktueller Wert als Prozentsatz von MNW (mittlerer Niedrigwasserstand).",
    },
    "nq": {
        "en": "Lowest discharge recorded within the reference period (1991-2020).",
        "de": "Niedrigster im Referenzzeitraum (1991-2020) aufgezeichneter Abfluss.",
    },
    "median_q": {
        "en": "Median discharge across the reference period -- half of all values were higher, half lower.",
        "de": "Medianabfluss über den Referenzzeitraum -- die Hälfte aller Werte lag darüber, die Hälfte darunter.",
    },
    "nw": {
        "en": "Lowest water level recorded within the reference period (1991-2020).",
        "de": "Niedrigster im Referenzzeitraum (1991-2020) aufgezeichneter Wasserstand.",
    },
    "median_w": {
        "en": "Median water level across the reference period.",
        "de": "Medianwasserstand über den Referenzzeitraum.",
    },
    "min_q_calendar_day": {
        "en": "Lowest discharge ever recorded specifically on this calendar day, across the reference period.",
        "de": "Niedrigster jemals an genau diesem Kalendertag im Referenzzeitraum aufgezeichneter Abfluss.",
    },
    "median_q_calendar_day": {
        "en": "Median discharge for this specific calendar day across the reference period -- a typical value for today's date.",
        "de": "Medianabfluss für genau diesen Kalendertag im Referenzzeitraum -- ein typischer Wert für das heutige Datum.",
    },
    "max_q_calendar_day": {
        "en": "Highest discharge ever recorded specifically on this calendar day, across the reference period.",
        "de": "Höchster jemals an genau diesem Kalendertag im Referenzzeitraum aufgezeichneter Abfluss.",
    },
    "median_w_calendar_day": {
        "en": "Median water level for this specific calendar day across the reference period.",
        "de": "Medianwasserstand für genau diesen Kalendertag im Referenzzeitraum.",
    },
    "sum_d": {
        "en": "Number of days within the last 30 days classified as low-water days for this station.",
        "de": "Anzahl der Tage in den letzten 30 Tagen, die für diese Station als Niedrigwassertage eingestuft wurden.",
    },
    "sum_v": {
        "en": "Accumulated discharge deficit volume over the last 30 days -- how much water was \"missing\" compared to normal.",
        "de": "Kumuliertes Abflussdefizit-Volumen der letzten 30 Tage -- wie viel Wasser im Vergleich zum Normalzustand „fehlte“.",
    },
    "below_glw": {
        "en": (
            "Whether the water level is currently above or below GlW "
            "(Gleichwertiger Wasserstand), a reference level used for "
            "waterway navigation. Only meaningful at federal waterway gauges."
        ),
        "de": (
            "Ob der Wasserstand aktuell über oder unter dem GlW "
            "(Gleichwertiger Wasserstand) liegt, einem Referenzpegel für "
            "die Binnenschifffahrt. Nur an Bundeswasserstraßen-Pegeln "
            "aussagekräftig."
        ),
    },
    "days_below_glw": {
        "en": (
            "Number of consecutive days the water level has been below the "
            "GlW/RWN/BWu navigation reference levels. Only meaningful at "
            "federal waterway gauges."
        ),
        "de": (
            "Anzahl der aufeinanderfolgenden Tage, an denen der "
            "Wasserstand unter den Schifffahrts-Referenzpegeln "
            "GlW/RWN/BWu lag. Nur an Bundeswasserstraßen-Pegeln "
            "aussagekräftig."
        ),
    },
    "depth_below_ground": {
        "en": (
            "Groundwater depth below the ground surface (Flurabstand) -- "
            "the distance from ground level down to the water table."
        ),
        "de": (
            "Grundwasser-Flurabstand -- der Abstand von der "
            "Geländeoberkante bis zum Grundwasserspiegel."
        ),
    },
}

_DECILE_TEMPLATE: Final = {
    "en": "{pct}th percentile of the historical discharge/water-level distribution for today's calendar day (reference period 1991-2020).",
    "de": "{pct}. Perzentil der historischen Abfluss-/Wasserstandsverteilung für den heutigen Kalendertag (Referenzzeitraum 1991-2020).",
}


def sensor_description(key: str, language: str) -> str | None:
    """Return the glossary explanation for one sensor key, if any.

    Deciles (decile_pNN) are handled via a shared template rather than 11
    near-identical dict entries; every other key is looked up directly.
    Returns None for keys with no glossary entry (e.g. the primary value
    sensor, whose name/device model already carry enough context).
    """
    if key.startswith("decile_p"):
        percentile = key.removeprefix("decile_p")
        return _DECILE_TEMPLATE[language].format(pct=percentile)

    entry = SENSOR_GLOSSARY.get(key)
    return entry[language] if entry is not None else None
