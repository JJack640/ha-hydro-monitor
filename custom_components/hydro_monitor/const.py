"""Constants for the Hydro Monitor integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "hydro_monitor"

CONF_PROVIDER: Final = "provider"
CONF_STATION_ID: Final = "station_id"
CONF_MEASUREMENT_TYPE: Final = "measurement_type"
CONF_SEARCH_QUERY: Final = "query"

PROVIDER_NIWIS: Final = "niwis"
PROVIDER_PEGELONLINE: Final = "pegelonline"

DEFAULT_UPDATE_INTERVAL: Final = timedelta(hours=6)
MEASUREMENT_STALE_AFTER: Final = timedelta(hours=12)

CATALOG_CACHE_HOURS: Final = 24
NEARBY_STATION_LIMIT: Final = 25
SEARCH_RESULT_LIMIT: Final = 50
