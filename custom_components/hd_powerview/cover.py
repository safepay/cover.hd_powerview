import logging
import requests

import voluptuous as vol

from homeassistant.components.cover import (
    CoverDevice, PLATFORM_SCHEMA, ATTR_POSITION, SUPPORT_OPEN, SUPPORT_CLOSE, SUPPORT_SET_POSITION, SUPPORT_STOP)
from homeassistant.const import (
    CONF_NAME, CONF_HOST, STATE_CLOSED, STATE_OPEN, STATE_OPENING, STATE_UNKNOWN, ATTR_BATTERY_LEVEL)
import homeassistant.helpers.config_validation as cv

from base64 import b64decode

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'PowerView'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

_shadesURL = 'http://{}/api/shades'
_shadeURL    = 'http://{}/api/shade/{}'

############

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the PowerView covers."""
    ip_address = config[CONF_HOST]

    cover_ids = coverData(ip_address, _shadesURL)

    covers = []
    try:
        await cover_ids.async_update()
    except ValueError as err:
        _LOGGER.error("Received data error from PowerView Hub: %s", err)
        return

    for cover_id in cover_ids.latest_data['shadeIds']:
        covers.append(PowerView(hass, ip_address, cover_id))

    async_add_entities(covers, True)


class PowerView(CoverDevice):
    """Representation of PowerView cover."""

    def __init__(self, hass, ip_address, cover_id):
        """Initialize the cover."""
        self.hass = hass
        self._ip_address = ip_address
        self._cover_id = cover_id
        self._available = True
        self._state = None

    @property
    def name(self):
        """Return the name of the cover."""
        return b64decode(self._cover_data.latest_data['name']).decode('utf-8')

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available
        
    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self._cover_data.latest_data['positions']['position1'] < 1

    @property
    def current_cover_position(self):
        """Return the cover position."""
        return round(self._cover_data.latest_data['positions']['position1'] / 65535 * 100, 0)

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        body = {
            'shade': {
                'positions': {
                    'position1': 0,
                    'posKind1': 1
                }
            }
        }

        url = _shadeURL.format(self._ip_address, self._cover_id)

        try:
            result = requests.put(url, data=body, timeout=10).json()
        except (requests.exceptions.RequestException) as error:
            _LOGGER.error("Unable to connect to PowerView: %s", error)
            
    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        body = {
            'shade': {
                'positions': {
                    'position1': 65535,
                    'posKind1': 1
                }
            }
        }

        url = _shadeURL.format(self._ip_address, self._cover_id)

        try:
            result = requests.put(url, data=body, timeout=10).json()
        except (requests.exceptions.RequestException) as error:
            _LOGGER.error("Unable to connect to PowerView: %s", error)
            
    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        body = {"shade": {"motion": "stop"}}

        url = _shadeURL.format(self._ip_address, self._cover_id)

        try:
            result = requests.put(url, data=body, timeout=10).json()
        except (requests.exceptions.RequestException) as error:
            _LOGGER.error("Unable to connect to PowerView: %s", error)

    async def async_set_cover_position(self, **kwargs):
        """Set the cover position."""
        if ATTR_POSITION in kwargs:
            position = int(kwargs[ATTR_POSITION] / 100 * 65535)

        body = {
            'shade': {
                'positions': {
                    'position1': position,
                    'posKind1': 1
                }
            }
        }

        url = _shadeURL.format(self._ip_address, self._cover_id)

        try:
            result = requests.put(url, data=body, timeout=10).json()
        except (requests.exceptions.RequestException) as error:
            _LOGGER.error("Unable to connect to PowerView: %s", error)

        _LOGGER.debug("Shade postion: %s", position)

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return 'shade'

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION | SUPPORT_STOP

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        attr = {}

        try:
            if "batteryStatus" in self._cover_data.latest_data:
                attr[ATTR_BATTERY_LEVEL] = int(
                    self._cover_data.latest_data['batteryStrength'] / 2
                )
        except (ValueError, KeyError):
            pass

        attr["groupId"] = self._cover_data.latest_data['groupId']
        attr["roomId"] = self._cover_data.latest_data['roomId']
        attr["type"] = self._cover_data.latest_data['type']
        return attr

    async def async_update(self):
        """Get the latest data and update the states."""
        self._cover_data = coverData(self._ip_address, _shadeURL, self._cover_id)
        try:
            await self._cover_data.async_update()
        except ValueError as err:
            self._available = False
            _LOGGER.error("Received data error from PowerView Hub: %s", err)
            return

        self._available = True

class coverData:
    """Handle hub API object."""

    def __init__(self, ip_address, url, cover_id=False):
        """Initialize the data object."""
        self._ip_address = ip_address
        self._url = url
        self._cover_id = cover_id

    def _build_url(self):
        """Build the URL for the requests."""
        url = self._url.format(self._ip_address, self._cover_id)
        _LOGGER.debug("PowerView URL: %s", url)
        return url

    @property
    def latest_data(self):
        """Return the latest data object."""
        if self._data:
            return self._data
        return None

    async def async_update(self):
        """Get the latest data from hub."""
        try:
            result = requests.get(self._build_url(), timeout=10).json()
            self._data = result
        except (requests.exceptions.RequestException) as error:
            _LOGGER.error("Unable to connect to PowerView: %s", error)
            self._data = None