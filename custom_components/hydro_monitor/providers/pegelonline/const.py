"""Constants for the PEGELONLINE provider (WSV, REST API v2).

PEGELONLINE is the water-level service of the federal waterways and shipping
administration (WSV). Verified live on 2026-10-23: 786 stations, no
authentication, licence DL-DE->Zero-2.0 (use in products and apps allowed,
no attribution required). Documentation:
https://pegelonline.wsv.de/webservice/guideRestapi

The newer HyDAS API of the same service is still a beta that announces
incompatible changes, so this provider uses the established REST API v2.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Final

from ...models import HydroMeasurementType

BASE_URL: Final = "https://www.pegelonline.wsv.de/webservices/rest-api/v2"

# Station page for humans, by station number (`number` in the API).
STATION_PAGE_URL: Final = "https://www.pegelonline.wsv.de/gast/stammdaten"

LICENSE_NAME: Final = "DL-DE->Zero-2.0"

# One request lists all stations with their time series.
STATIONS_ENDPOINT: Final = "stations.json"

# Hydro Monitor measurement type -> PEGELONLINE time series short name.
# W = water level (cm), Q = discharge (m³/s). The service has more series
# (water temperature, air temperature, conductivity, ...) that Hydro Monitor
# does not model.
HYDRO_TO_PEGELONLINE_TIMESERIES: Final = {
    HydroMeasurementType.WATER_LEVEL: "W",
    HydroMeasurementType.DISCHARGE: "Q",
}
PEGELONLINE_TIMESERIES_TO_HYDRO: Final = {
    timeseries: measurement_type
    for measurement_type, timeseries in HYDRO_TO_PEGELONLINE_TIMESERIES.items()
}

# The service keeps about 31 days of raw data; one request covers the
# 30-day statistics and the 7-day trend.
HISTORY_PERIOD: Final = "P31D"

# New values arrive every 15 minutes (some stations every minute).
UPDATE_INTERVAL: Final = timedelta(minutes=30)

# The service reports the local time with its UTC offset.
REQUEST_TIMEOUT_SECONDS: Final = 45
