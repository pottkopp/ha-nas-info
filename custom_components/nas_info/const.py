"""Constants fuer NAS-Info."""

from homeassistant.util.hass_dict import HassKey

DOMAIN = "nas_info"

KEY_CLIENT: HassKey = HassKey("nas_info_client")

MIN_UPDATE_INTERVAL = 30
DEFAULT_UPDATE_INTERVAL = 300

CONF_UPDATE_INTERVAL = "update_interval"
CONF_IGNORED_MOUNTS = "ignored_mounts"
CONF_UNIT_MODE = "unit_mode"
DEFAULT_UNIT_MODE = "auto"
UNIT_MODES = ("auto", "gb", "bytes")
