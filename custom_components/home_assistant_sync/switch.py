"""Switch platform for Home Assistant Sync."""
import logging

from homeassistant.components.switch import SwitchEntity
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
    """Set up switch platform."""
    # Only create entities in client mode
    if entry.data.get(CONF_MODE) != MODE_CLIENT:
        return

    coordinator = hass.data[DOMAIN][entry.entry_id]
    imported_entities = entry.options.get(CONF_IMPORTED_ENTITIES, [])
    
    entities = []
    for entity_id in imported_entities:
        if entity_id.startswith("switch."):
            entity_data = coordinator.get_synced_entity_state(entity_id)
            if entity_data:
                entities.append(SyncedSwitch(coordinator, entity_id, entity_data))
    
    async_add_entities(entities)


class SyncedSwitch(EntitySyncEntity, SwitchEntity):
    """Representation of a synced switch."""

    @property
    def is_on(self):
        """Return true if switch is on."""
        if self._entity_data:
            return self._entity_data.get("state") == "on"
        return False

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self.coordinator.async_set_entity_state(self._entity_id, state="on")

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self.coordinator.async_set_entity_state(self._entity_id, state="off")