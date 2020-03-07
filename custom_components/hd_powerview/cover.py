import json
import logging
from base64 import b64decode
from datetime import timedelta

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.cover import (
    ATTR_POSITION,
    DEVICE_CLASS_SHADE,
    PLATFORM_SCHEMA,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_SET_POSITION,
    SUPPORT_STOP,
    CoverDevice,
)
from homeassistant.const import ATTR_BATTERY_LEVEL, CONF_HOST, CONF_NAME
from homeassistant.core import callback
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=10)

DEFAULT_NAME = "PowerView"
CONF_VERSION = "version"

VERSIONS = {1, 2}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_VERSION, default=2): vol.In(VERSIONS),
    }
)

############


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the PowerView covers."""
    ip_address = config[CONF_HOST]
    hub_vers = config[CONF_VERSION]

    websession = aiohttp_client.async_get_clientsession(hass)
    pv_gateway = PowerView(ip_address, websession)

    async def async_update_data():
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        data = await pv_gateway.async_get_shades()

        if data is False or "shadeData" not in data:
            raise UpdateFailed

        shade_data = data["shadeData"]
        return {shade["id"]: Shade(shade) for shade in shade_data}

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="hd_powerview",
        update_method=async_update_data,
        update_interval=timedelta(seconds=10),
    )

    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise PlatformNotReady

    covers = []
    for cover_id in coordinator.data:
        # Refresh on init
        cover_data = await pv_gateway.async_get_shade(cover_id, True)
        if cover_data is False:
            cover_data = coordinator.data[cover_id]
        covers.append(
            HdPowerView(pv_gateway, cover_id, hub_vers, cover_data, coordinator)
        )

    async_add_entities(covers)


class HdPowerView(CoverDevice):
    """Representation of PowerView cover."""

    def __init__(self, pv_gateway, cover_id, hub_vers, cover_data, coordinator):
        """Initialize the cover."""
        self._coordinator = coordinator
        self._cover_id = cover_id
        self._pv_gateway = pv_gateway
        self._available = True
        self._cover_data = cover_data
        self._hub_vers = hub_vers

    @property
    def name(self):
        """Return the name of the cover."""
        return self._cover_data.name

    @property
    def _cover_data(self):
        return self._coordinator.data[self._cover_id]

    @_cover_data.setter
    def _cover_data(self, cover_data):
        self._coordinator.data[self._cover_id] = cover_data

    @property
    def available(self):
        """Return True if entity is available."""
        return self._coordinator.last_update_success

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self._cover_data.position < 1

    @property
    def unique_id(self):
        """Return the cover unique id."""
        return f"{self._cover_id} cover"

    @property
    def current_cover_position(self):
        """Return the cover position."""
        return self._cover_data.position

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        data = await self._pv_gateway.async_close_shade(self._cover_id)
        if data:
            self._cover_data = data

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        data = await self._pv_gateway.async_open_shade(self._cover_id)
        if data:
            self._cover_data = data

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        data = await self._pv_gateway.async_stop_shade(self._cover_id)
        if data:
            self._cover_data = data

    async def async_set_cover_position(self, **kwargs):
        """Set the cover position."""
        if ATTR_POSITION in kwargs:
            position = int(kwargs[ATTR_POSITION] / 100 * 65535)
        data = await self._pv_gateway.async_set_shade_position(self._cover_id, position)
        if data:
            self._cover_data = data

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return DEVICE_CLASS_SHADE

    @property
    def supported_features(self):
        """Flag supported features."""
        if self._hub_vers == 2:
            return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION | SUPPORT_STOP
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return {ATTR_BATTERY_LEVEL: self._cover_data.battery_level}

    @callback
    def _update_from_data_and_write_state(self, data):
        if data:
            self._cover_data = data
        self._available = data is not False
        self.async_write_ha_state()

    @property
    def should_poll(self):
        """Return False, updates are controlled via the hub."""
        return False

    async def async_update(self):
        await self._coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        """Subscribe to updates."""
        self._coordinator.async_add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Undo subscription."""
        self._coordinator.async_remove_listener(self.async_write_ha_state)


SHADE_BASE_ENDPOINT = "/api/shades"
REQUEST_TIMEOUT = 5


class PowerView:
    """Class for interacting with the Powerview API."""

    def __init__(self, host, websession):
        """Initialize the PowerView Hub."""
        if host is not None:
            self.host = "http://" + host
        self._websession = websession

    async def make_request(self, method, request, data=None):
        url = self.host + request
        _LOGGER.debug(
            "url[%s] method[%s] request[%s] data[%s]", url, method, request, data
        )

        try:
            response = None
            if method == "get":
                response = await self._websession.get(url, timeout=REQUEST_TIMEOUT)
            if method == "put":
                response = await self._websession.put(
                    url, json=data, timeout=REQUEST_TIMEOUT
                )
            return await response.json()
        except Exception as ex:
            _LOGGER.error("HTTP %s request to url[%s] failed: %s", method, url, str(ex))

        return False

    async def async_get_shades(self):
        """Return data for all shades."""
        response = await self.make_request("get", SHADE_BASE_ENDPOINT)
        _LOGGER.debug("New shade ids: %s", json.dumps(response))
        return response

    async def async_get_shade(self, shade, refresh=False):
        """List all shades."""
        response = await self.make_request(
            "get",
            SHADE_BASE_ENDPOINT
            + "/"
            + str(shade)
            + "?refresh="
            + ("true" if refresh else "false"),
        )
        return Shade(response["shade"]) if response else False

    async def async_close_shade(self, shade):
        """Close a shade."""
        return await self.async_set_shade_position(shade, 0)

    async def async_open_shade(self, shade):
        """Open a shade."""
        return await self.async_set_shade_position(shade, 65535)

    async def async_stop_shade(self, shade):
        """Stop a shade."""
        return await self._async_shade_motion(shade, "stop")

    async def async_set_shade_position(self, shade, position: int):
        """Set a shade to a specific position."""
        return await self._async_shade_action(
            shade, {"positions": {"posKind1": 1, "position1": position}}
        )

    async def _async_shade_motion(self, shade, motion):
        return await self._async_shade_action(shade, {"motion": motion})

    async def _async_shade_action(self, shade, action):
        url = SHADE_BASE_ENDPOINT + "/" + str(shade) + "?refresh=true"
        response = await self.make_request("put", url, {"shade": action})
        return Shade(response["shade"]) if response else False


class Shade:
    """Class to represent a PowerView shade"""

    def __init__(self, shade_data):
        _LOGGER.debug("New shade data: %s", json.dumps(shade_data))

        self._cover_id = shade_data["id"]
        self._name = b64decode(shade_data["name"]).decode("UTF-8")
        self._position = round((shade_data["positions"]["position1"] / 65535) * 100)
        self._battery_level = round(shade_data["batteryStrength"] / 2)

    @property
    def cover_id(self):
        return self._cover_id

    @property
    def name(self):
        return self._name

    @property
    def position(self):
        return self._position

    @property
    def battery_level(self):
        return self._battery_level
