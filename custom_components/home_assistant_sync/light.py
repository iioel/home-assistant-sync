"""Light platform for Home Assistant Sync."""
import logging

from homeassistant.components.light import LightEntity, ColorMode
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

    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        await self.coordinator.async_set_entity_state(self._entity_id, state="on", **kwargs)

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        await self.coordinator.async_set_entity_state(self._entity_id, state="off")