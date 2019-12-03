import logging

import voluptuous as vol

from homeassistant.components.cover import (
    CoverDevice, PLATFORM_SCHEMA, ATTR_POSITION, SUPPORT_OPEN, SUPPORT_CLOSE, SUPPORT_SET_POSITION, SUPPORT_STOP)
from homeassistant.const import (
    CONF_NAME, CONF_HOST, STATE_CLOSED, STATE_OPEN, STATE_OPENING, STATE_UNKNOWN, ATTR_BATTERY_LEVEL)
import homeassistant.helpers.config_validation as cv

from pyhdpowerview import PowerView

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

        self._pv.open_shade(self._cover_id)
            
    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""

        self._pv.stop_shade(self._cover_id)

    async def async_set_cover_position(self, **kwargs):
        """Set the cover position."""

        if ATTR_POSITION in kwargs:
            position = int(kwargs[ATTR_POSITION] / 100 * 65535)

        self._pv.set_shade_position(self._cover_id, position)

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

