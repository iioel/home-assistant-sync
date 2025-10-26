"""Sensor platform for Home Assistant Sync."""
import logging

from homeassistant.components.sensor import SensorEntity
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
    """Set up sensor platform."""
    # Only create entities in client mode
    if entry.data.get(CONF_MODE) != MODE_CLIENT:
        return

    coordinator = hass.data[DOMAIN][entry.entry_id]
    imported_entities = entry.options.get(CONF_IMPORTED_ENTITIES, [])
    
    entities = []
    for entity_id in imported_entities:
        if entity_id.startswith("sensor."):
            entity_data = coordinator.get_synced_entity_state(entity_id)
            if entity_data:
                entities.append(SyncedSensor(coordinator, entity_id, entity_data))
    
    async_add_entities(entities)


class SyncedSensor(EntitySyncEntity, SensorEntity):
    """Representation of a synced sensor."""

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self._entity_data:
            return self._entity_data.get("state")
        return None

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        if self._entity_data:
            return self._entity_data.get("attributes", {}).get("unit_of_measurement")
        return None

    @property
    def device_class(self):
        """Return the device class."""
        if self._entity_data:
            return self._entity_data.get("attributes", {}).get("device_class")
        return None