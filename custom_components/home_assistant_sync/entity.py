"""Base entity for Home Assistant Sync."""
import logging

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class EntitySyncEntity(Entity):
    """Base class for synced entities."""

    def __init__(self, coordinator, entity_id: str, entity_data: dict):
        """Initialize the synced entity."""
        self.coordinator = coordinator
        self._entity_id = entity_id
        self._entity_data = entity_data
        self._attr_unique_id = f"{DOMAIN}_{entity_id}"
        self._attr_name = entity_data.get("attributes", {}).get("friendly_name", entity_id)

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._entity_id}_updated",
                self._handle_update,
            )
        )

    async def _handle_update(self):
        """Handle entity update."""
        entity_data = self.coordinator.get_synced_entity_state(self._entity_id)
        if entity_data:
            self._entity_data = entity_data
            self.async_write_ha_state()

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def available(self):
        """Return if entity is available."""
        return self._entity_data is not None

    @property
    def extra_state_attributes(self):
        """Return entity attributes."""
        if self._entity_data:
            attrs = self._entity_data.get("attributes", {}).copy()
            attrs["synced_from"] = self.coordinator.entry.data.get("server_url", "server")
            return attrs
        return {}