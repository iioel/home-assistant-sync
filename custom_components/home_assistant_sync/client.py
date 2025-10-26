"""Client implementation for Home Assistant Sync."""
import logging
import json
import asyncio
from typing import Dict, Optional
import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_SERVER_URL,
    CONF_JWT_SECRET,
    CONF_IMPORTED_ENTITIES,
    API_WEBSOCKET_PATH,
    API_ENTITIES_PATH,
    WS_TYPE_AUTH,
    WS_TYPE_STATE_CHANGED,
    WS_TYPE_SUBSCRIBE,
    WS_TYPE_GET_ENTITIES,
)
from .auth import generate_jwt_token

_LOGGER = logging.getLogger(__name__)


class EntitySyncClient:
    """Client for entity synchronization."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the client."""
        self.hass = hass
        self.entry = entry
        self.server_url = entry.data.get(CONF_SERVER_URL)
        self.jwt_secret = entry.data.get(CONF_JWT_SECRET)
        self._ws = None
        self._session = None
        self._entity_states: Dict[str, dict] = {}
        self._connected = False
        self._reconnect_task = None
        self._listen_task = None

    async def async_setup(self):
        """Set up the client."""
        self._session = aiohttp.ClientSession()
        await self._connect()
        _LOGGER.info("Home Assistant Sync Client started")

    async def async_shutdown(self):
        """Shutdown the client."""
        self._connected = False
        
        if self._reconnect_task:
            self._reconnect_task.cancel()
        
        if self._listen_task:
            self._listen_task.cancel()
        
        if self._ws:
            await self._ws.close()
        
        if self._session:
            await self._session.close()
        
        _LOGGER.info("Home Assistant Sync Client stopped")

    async def _connect(self):
        """Connect to the server via WebSocket."""
        try:
            url = f"{self.server_url.rstrip('/')}{API_WEBSOCKET_PATH}".replace("http://", "ws://").replace("https://", "wss://")
            
            self._ws = await self._session.ws_connect(url)
            
            # Authenticate
            token = generate_jwt_token(self.jwt_secret, f"client_{self.entry.entry_id}")
            await self._ws.send_json({
                "type": WS_TYPE_AUTH,
                "token": token,
            })
            
            # Wait for auth response
            msg = await self._ws.receive_json()
            if msg.get("type") == "auth_ok":
                self._connected = True
                _LOGGER.info("Successfully connected to server")
                
                # Subscribe to entities
                await self._subscribe_to_entities()
                
                # Start listening for messages
                self._listen_task = asyncio.create_task(self._listen_for_messages())
            else:
                _LOGGER.error("Authentication failed")
                self._connected = False
                
        except Exception as ex:
            _LOGGER.error("Error connecting to server: %s", ex)
            self._connected = False
            # Schedule reconnection
            self._reconnect_task = asyncio.create_task(self._reconnect_later())

    async def _reconnect_later(self):
        """Reconnect after a delay."""
        await asyncio.sleep(30)
        await self._connect()

    async def _subscribe_to_entities(self):
        """Subscribe to imported entities."""
        imported_entities = self.entry.options.get(CONF_IMPORTED_ENTITIES, [])
        
        for entity_id in imported_entities:
            try:
                await self._ws.send_json({
                    "type": WS_TYPE_SUBSCRIBE,
                    "entity_id": entity_id,
                })
            except Exception as ex:
                _LOGGER.error("Error subscribing to entity %s: %s", entity_id, ex)

    async def _listen_for_messages(self):
        """Listen for messages from the server."""
        try:
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_message(data)
                    except json.JSONDecodeError:
                        _LOGGER.error("Invalid JSON received")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    _LOGGER.error("WebSocket error")
                    break
        except Exception as ex:
            _LOGGER.error("Error in message listener: %s", ex)
        finally:
            self._connected = False
            self._reconnect_task = asyncio.create_task(self._reconnect_later())

    async def _handle_message(self, data: dict):
        """Handle incoming message from server."""
        msg_type = data.get("type")
        
        if msg_type == WS_TYPE_STATE_CHANGED:
            entity_id = data.get("entity_id")
            entity_data = data.get("data")
            
            if entity_data:
                self._entity_states[entity_id] = entity_data
                # Trigger update for this entity
                await self.hass.async_add_executor_job(
                    self.hass.helpers.dispatcher.async_dispatcher_send,
                    f"{entity_id}_updated",
                )
                _LOGGER.debug("State updated for %s", entity_id)

    async def async_get_available_entities(self):
        """Get available entities from server."""
        try:
            url = f"{self.server_url.rstrip('/')}{API_ENTITIES_PATH}"
            token = generate_jwt_token(self.jwt_secret, f"client_{self.entry.entry_id}")
            headers = {"Authorization": f"Bearer {token}"}
            
            async with self._session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return list(data.keys())
                else:
                    _LOGGER.error("Failed to get entities: %s", response.status)
                    return []
        except Exception as ex:
            _LOGGER.error("Error getting available entities: %s", ex)
            return []

    def get_entity_state(self, entity_id: str) -> Optional[dict]:
        """Get the cached state of an entity."""
        return self._entity_states.get(entity_id)

    async def async_set_entity_state(self, entity_id: str, **kwargs):
        """Set entity state (would need to implement service call to server)."""
        # This would require additional server endpoint to handle state changes
        # from client to server (for controllable entities)
        _LOGGER.warning("Setting entity state from client not yet implemented")

    async def async_reconnect_if_needed(self):
        """Reconnect if connection is lost."""
        if not self._connected and not self._reconnect_task:
            self._reconnect_task = asyncio.create_task(self._connect())