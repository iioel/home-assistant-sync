"""Coordinator for Home Assistant Sync."""
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.const import EVENT_STATE_CHANGED

from .const import (
    DOMAIN,
    CONF_MODE,
    CONF_EXPOSED_ENTITIES,
    CONF_IMPORTED_ENTITIES,
    MODE_SERVER,
    MODE_CLIENT,
    DEFAULT_SCAN_INTERVAL,
)
from .server import EntitySyncServer
from .client import EntitySyncClient

_LOGGER = logging.getLogger(__name__)


class EntitySyncCoordinator(DataUpdateCoordinator):
    """Coordinator to manage entity synchronization."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.entry = entry
        self.mode = entry.data.get(CONF_MODE)
        self._server = None
        self._client = None
        self._unsub_state_listener = None

    async def async_setup(self):
        """Set up the coordinator."""
        if self.mode == MODE_SERVER:
            self._server = EntitySyncServer(self.hass, self.entry)
            await self._server.async_setup()
            self._setup_state_listener()
        else:
            self._client = EntitySyncClient(self.hass, self.entry)
            await self._client.async_setup()

    async def async_shutdown(self):
        """Shutdown the coordinator."""
        if self._unsub_state_listener:
            self._unsub_state_listener()
            self._unsub_state_listener = None

        if self._server:
            await self._server.async_shutdown()
        
        if self._client:
            await self._client.async_shutdown()

    def _setup_state_listener(self):
        """Set up state change listener for server mode."""
        @callback
        def state_changed_listener(event: Event):
            """Handle state changed events."""
            entity_id = event.data.get("entity_id")
            exposed_entities = self.entry.options.get(CONF_EXPOSED_ENTITIES, [])
            
            if entity_id in exposed_entities:
                new_state = event.data.get("new_state")
                if new_state and self._server:
                    self.hass.async_create_task(
                        self._server.broadcast_state_change(entity_id, new_state)
                    )

        self._unsub_state_listener = self.hass.bus.async_listen(
            EVENT_STATE_CHANGED, state_changed_listener
        )

    async def _async_update_data(self):
        """Update data via library."""
        # Periodic health check
        if self._client:
            await self._client.async_reconnect_if_needed()
        return {}

    async def async_get_available_entities(self):
        """Get available entities from server (client mode only)."""
        if self._client:
            return await self._client.async_get_available_entities()
        return []

    def get_synced_entity_state(self, entity_id: str):
        """Get the state of a synced entity."""
        if self._client:
            return self._client.get_entity_state(entity_id)
        return None

    async def async_set_entity_state(self, entity_id: str, **kwargs):
        """Set the state of an entity on the server."""
        if self._client:
            await self._client.async_set_entity_state(entity_id, **kwargs)