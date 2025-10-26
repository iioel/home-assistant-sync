"""Client implementation for Home Assistant Sync."""
import logging
import json
import asyncio
from typing import Dict, Optional
import aiohttp
import uuid

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_SERVER_URL,
    CONF_JWT_SECRET,
    CONF_CLIENT_TOKEN,
    CONF_IMPORTED_ENTITIES,
    API_WEBSOCKET_PATH,
    API_ENTITIES_PATH,
    API_CALL_SERVICE_PATH,
    WS_TYPE_AUTH,
    WS_TYPE_STATE_CHANGED,
    WS_TYPE_SUBSCRIBE,
    WS_TYPE_GET_ENTITIES,
    WS_TYPE_CALL_SERVICE,
    WS_TYPE_SERVICE_RESPONSE,
    ATTR_ENTITY_ID,
    ATTR_SERVICE,
    ATTR_SERVICE_DATA,
    ATTR_DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class EntitySyncClient:
    """Client for entity synchronization."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the client."""
        self.hass = hass
        self.entry = entry
        self.server_url = entry.data.get(CONF_SERVER_URL)
        self.jwt_secret = entry.data.get(CONF_JWT_SECRET)
        self.client_token = entry.data.get(CONF_CLIENT_TOKEN)
        self._ws = None
        self._session = None
        self._entity_states: Dict[str, dict] = {}
        self._connected = False
        self._reconnect_task = None
        self._listen_task = None
        self._pending_requests: Dict[str, asyncio.Future] = {}

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
        
        # Cancel all pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()
        
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
            
            # Authenticate with client token
            await self._ws.send_json({
                "type": WS_TYPE_AUTH,
                "token": self.client_token,
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
        
        elif msg_type == WS_TYPE_SERVICE_RESPONSE:
            # Handle service call response
            request_id = data.get("request_id")
            result = data.get("result")
            
            if request_id in self._pending_requests:
                future = self._pending_requests.pop(request_id)
                if not future.done():
                    future.set_result(result)

    async def async_get_available_entities(self):
        """Get available entities from server."""
        try:
            url = f"{self.server_url.rstrip('/')}{API_ENTITIES_PATH}"
            headers = {"Authorization": f"Bearer {self.client_token}"}
            
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

    async def async_call_service(
        self,
        domain: str,
        service: str,
        service_data: Dict[str, any],
        use_websocket: bool = True
    ) -> Dict[str, any]:
        """Call a service on the server."""
        if use_websocket and self._connected and self._ws:
            # Use WebSocket for faster response
            request_id = str(uuid.uuid4())
            future = asyncio.Future()
            self._pending_requests[request_id] = future
            
            try:
                await self._ws.send_json({
                    "type": WS_TYPE_CALL_SERVICE,
                    "request_id": request_id,
                    ATTR_DOMAIN: domain,
                    ATTR_SERVICE: service,
                    ATTR_SERVICE_DATA: service_data,
                })
                
                # Wait for response with timeout
                result = await asyncio.wait_for(future, timeout=10.0)
                return result
                
            except asyncio.TimeoutError:
                _LOGGER.error("Service call timed out")
                self._pending_requests.pop(request_id, None)
                return {"success": False, "error": "Timeout"}
            except Exception as ex:
                _LOGGER.error("Error calling service via WebSocket: %s", ex)
                self._pending_requests.pop(request_id, None)
                return {"success": False, "error": str(ex)}
        else:
            # Fallback to HTTP POST
            try:
                url = f"{self.server_url.rstrip('/')}{API_CALL_SERVICE_PATH}"
                headers = {"Authorization": f"Bearer {self.client_token}"}
                
                payload = {
                    ATTR_DOMAIN: domain,
                    ATTR_SERVICE: service,
                    ATTR_SERVICE_DATA: service_data,
                }
                
                async with self._session.post(
                    url, 
                    json=payload, 
                    headers=headers, 
                    timeout=10
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        _LOGGER.error(
                            "Service call failed with status: %s", 
                            response.status
                        )
                        return {
                            "success": False, 
                            "error": f"HTTP {response.status}"
                        }
            except Exception as ex:
                _LOGGER.error("Error calling service via HTTP: %s", ex)
                return {"success": False, "error": str(ex)}

    async def async_set_entity_state(self, entity_id: str, **kwargs):
        """Set entity state by calling appropriate service."""
        # Extract domain from entity_id
        domain = entity_id.split(".")[0]
        
        # Determine the service based on the state and domain
        state = kwargs.get("state")
        
        service_data = {ATTR_ENTITY_ID: entity_id}
        
        if domain == "light":
            if state == "on":
                service = "turn_on"
                # Add brightness and other light attributes
                if "brightness" in kwargs:
                    service_data["brightness"] = kwargs["brightness"]
                if "rgb_color" in kwargs:
                    service_data["rgb_color"] = kwargs["rgb_color"]
                if "color_temp" in kwargs:
                    service_data["color_temp"] = kwargs["color_temp"]
            else:
                service = "turn_off"
        elif domain == "switch":
            service = "turn_on" if state == "on" else "turn_off"
        elif domain == "cover":
            if state == "open":
                service = "open_cover"
            elif state == "closed":
                service = "close_cover"
            else:
                service = "stop_cover"
        elif domain == "climate":
            service = "set_temperature"
            if "temperature" in kwargs:
                service_data["temperature"] = kwargs["temperature"]
            if "hvac_mode" in kwargs:
                service_data["hvac_mode"] = kwargs["hvac_mode"]
        else:
            # Generic turn_on/turn_off for other domains
            service = "turn_on" if state == "on" else "turn_off"
        
        result = await self.async_call_service(domain, service, service_data)
        
        if result.get("success"):
            _LOGGER.info(
                "Successfully called %s.%s for %s", 
                domain, 
                service, 
                entity_id
            )
        else:
            _LOGGER.error(
                "Failed to call %s.%s for %s: %s",
                domain,
                service,
                entity_id,
                result.get("error", "Unknown error")
            )

    async def async_reconnect_if_needed(self):
        """Reconnect if connection is lost."""
        if not self._connected and not self._reconnect_task:
            self._reconnect_task = asyncio.create_task(self._connect())