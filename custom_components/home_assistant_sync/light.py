"""Light platform for Home Assistant Sync."""
import logging
from typing import Any

from homeassistant.components.light import (
    LightEntity, 
    ColorMode,
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ATTR_COLOR_TEMP,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_IMPORTED_ENTITIES, MODE_CLIENT, CONF_MODE
from .entity import EntitySyncEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up light platform."""
    # Only create entities in client mode
    if entry.data.get(CONF_MODE) != MODE_CLIENT:
        return

    coordinator = hass.data[DOMAIN][entry.entry_id]
    imported_entities = entry.options.get(CONF_IMPORTED_ENTITIES, [])
    
    entities = []
    for entity_id in imported_entities:
        if entity_id.startswith("light."):
            entity_data = coordinator.get_synced_entity_state(entity_id)
            if entity_data:
                entities.append(SyncedLight(coordinator, entity_id, entity_data))
    
    async_add_entities(entities)


class SyncedLight(EntitySyncEntity, LightEntity):
    """Representation of a synced light."""

    @property
    def is_on(self):
        """Return true if light is on."""
        if self._entity_data:
            return self._entity_data.get("state") == "on"
        return False

    @property
    def brightness(self):
        """Return the brightness of the light."""
        if self._entity_data:
            return self._entity_data.get("attributes", {}).get("brightness")
        return None

    @property
    def rgb_color(self):
        """Return the RGB color value."""
        if self._entity_data:
            return self._entity_data.get("attributes", {}).get("rgb_color")
        return None

    @property
    def color_temp(self):
        """Return the color temperature."""
        if self._entity_data:
            return self._entity_data.get("attributes", {}).get("color_temp")
        return None

    @property
    def color_mode(self):
        """Return the color mode of the light."""
        if self._entity_data:
            color_mode = self._entity_data.get("attributes", {}).get("color_mode")
            if color_mode:
                return color_mode
        return ColorMode.ONOFF

    @property
    def supported_color_modes(self):
        """Return the supported color modes."""
        if self._entity_data:
            modes = self._entity_data.get("attributes", {}).get("supported_color_modes", [])
            if modes:
                return set(modes)
        return {ColorMode.ONOFF}

    async def async_turn_on(self, **kwargs: Any):
        """Turn the light on."""
        try:
            service_kwargs = {"state": "on"}
            
            # Pass through light-specific parameters
            if ATTR_BRIGHTNESS in kwargs:
                service_kwargs["brightness"] = kwargs[ATTR_BRIGHTNESS]
            if ATTR_RGB_COLOR in kwargs:
                service_kwargs["rgb_color"] = kwargs[ATTR_RGB_COLOR]
            if ATTR_COLOR_TEMP in kwargs:
                service_kwargs["color_temp"] = kwargs[ATTR_COLOR_TEMP]
            
            await self.coordinator.async_set_entity_state(
                self._entity_id,
                **service_kwargs
            )
            
            # Optimistically update the state
            if self._entity_data:
                self._entity_data["state"] = "on"
                if ATTR_BRIGHTNESS in kwargs:
                    self._entity_data.setdefault("attributes", {})[
                        "brightness"
                    ] = kwargs[ATTR_BRIGHTNESS]
                if ATTR_RGB_COLOR in kwargs:
                    self._entity_data.setdefault("attributes", {})[
                        "rgb_color"
                    ] = kwargs[ATTR_RGB_COLOR]
                if ATTR_COLOR_TEMP in kwargs:
                    self._entity_data.setdefault("attributes", {})[
                        "color_temp"
                    ] = kwargs[ATTR_COLOR_TEMP]
                self.async_write_ha_state()
                
        except Exception as ex:
            _LOGGER.error("Failed to turn on %s: %s", self._entity_id, ex)

    async def async_turn_off(self, **kwargs: Any):
        """Turn the light off."""
        try:
            await self.coordinator.async_set_entity_state(
                self._entity_id,
                state="off"
            )
            
            # Optimistically update the state
            if self._entity_data:
                self._entity_data["state"] = "off"
                self.async_write_ha_state()
                
        except Exception as ex:
            _LOGGER.error("Failed to turn off %s: %s", self._entity_id, ex)