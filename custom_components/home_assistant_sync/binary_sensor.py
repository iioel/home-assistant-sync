"""Binary sensor platform for Home Assistant Sync."""
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
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
    """Set up binary sensor platform."""
    # Only create entities in client mode
    if entry.data.get(CONF_MODE) != MODE_CLIENT:
        return

    coordinator = hass.data[DOMAIN][entry.entry_id]
    imported_entities = entry.options.get(CONF_IMPORTED_ENTITIES, [])
    
    entities = []
    for entity_id in imported_entities:
        if entity_id.startswith("binary_sensor."):
            entity_data = coordinator.get_synced_entity_state(entity_id)
            if entity_data:
                entities.append(SyncedBinarySensor(coordinator, entity_id, entity_data))
    
    async_add_entities(entities)


class SyncedBinarySensor(EntitySyncEntity, BinarySensorEntity):
    """Representation of a synced binary sensor."""

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        if self._entity_data:
            return self._entity_data.get("state") == "on"
        return False

    @property
    def device_class(self):
        """Return the device class."""
        if self._entity_data:
            return self._entity_data.get("attributes", {}).get("device_class")
        return None