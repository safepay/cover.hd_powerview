import logging

import voluptuous as vol
import requests

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

############

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the PowerView covers."""
    ip_address = config[CONF_HOST]

    pv = PowerView(ip_address)
    cover_ids = pv.get_shades()

    covers = []
    for cover_id in cover_ids:
        covers.append(HdPowerView(hass, pv, cover_id))
    async_add_entities(covers, True)


class HdPowerView(CoverDevice):
    """Representation of PowerView cover."""
    def __init__(self, hass, pv, cover_id):
        """Initialize the cover."""
        self.hass = hass
        self._pv = pv
        self._cover_id = cover_id
        self._available = True
        self._state = None

    @property
    def name(self):
        """Return the name of the cover."""
        return self._cover_data.name

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available
        
    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self._cover_data.position < 1

    @property
    def current_cover_position(self):
        """Return the cover position."""
        return self._cover_data.position

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        self._cover_data.position = self._pv.close_shade(self._cover_id)
            
    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        self._cover_data.position = self._pv.open_shade(self._cover_id)
            
    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        self._cover_data.position = self._pv.stop_shade(self._cover_id)

    async def async_set_cover_position(self, **kwargs):
        """Set the cover position."""
        if ATTR_POSITION in kwargs:
            position = int(kwargs[ATTR_POSITION] / 100 * 65535)
        self._cover_data.position = self._pv.set_shade_position(self._cover_id, position)

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
            if self._cover_data.battery_level:
                attr[ATTR_BATTERY_LEVEL] = self._cover_data.battery_level
        except (ValueError, KeyError):
            pass
        return attr

    async def async_update(self):
        """Get the latest data and update the states."""
        self._cover_data = self._pv.get_shade(self._cover_id)
        if self._cover_data:
            self._available = True
        else:
            self._available = False

class PowerView:
    """Class for interacting with the Powerview API."""

    REQUEST_TIMEOUT = 3.0

    def __init__(self, host):
        """Initialize the PowerView Hub."""
        if host is not None:
            self.host = 'http://' + host

    def make_request(self, method, request, data=None):
        url = self.host + request
        _LOGGER.debug("!!! URL, method, request, data: {}, {}, {}, {}".format(url, method, request, data))

        try:
            if method is "get":
                r = requests.get(url).json()
                return r
            elif method is "put":
                r = requests.put(url, json = data)
                return True
            else:
                return False
        except:
            return False

    def get_shades(self):
        """List all shade Ids."""
        request = self.make_request("get","/api/shades")

        if request != False:
            return request['shadeIds']
        else:
            return False

    def get_shade(self, shade):
        """List all shades."""
        request = self.make_request("get","/api/shades/" + str(shade))

        if request != False:
            shade = Shade(request['id'], b64decode(request['name']).decode('UTF-8'), round((request['positions']['position1'] / 65535) * 100), round(request['batteryStrength'] / 2))
            return shade
        else:
            return False

    def get_status(self, shade):
        """Update status of shade."""
        request = round((self.make_request("get","/api/shades/" + str(shade))['positions']['position1'] / 65535) * 100)
        return request

    def close_shade(self, shade):
        """Close a shade."""
        self.make_request("put","/api/shades/" + str(shade), {"shade": {"motion": "down"}})
        return

    def open_shade(self, shade):
        """Open a shade."""
        self.make_request("put","/api/shades/" + str(shade), {"shade": {"motion": "up"}})
        return

    def stop_shade(self, shade):
        """Stop a shade."""
        request = self.make_request("put","/api/shades/" + str(shade), {"shade": {"motion": "stop"}})
        return

    def set_shade_position(self, shade, position: int):
        """Set a shade to a specific position."""
        if 0 <= position <= 100: 
            position = round(position * 65535 / 100)
            self.make_request("put","/api/shades/" + str(shade), { "shade": { "positions": { "posKind1": 1, "position1": position } } })
            return
        else:
            return False

class Shade:
    """Class to represent a PowerView shade"""
    def __init__(self,
                 id: int,
                 name: str,
                 position: int,
                 battery: int):
        self.id = id
        self.name = name
        self.position = position
        self.battery_level = battery
