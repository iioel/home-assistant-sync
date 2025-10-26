"""Server implementation for Home Assistant Sync."""
import logging
import json
from typing import Set, Dict, Any
from aiohttp import web, WSMsgType
import asyncio

from homeassistant.core import HomeAssistant, State, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.http import HomeAssistantView
from homeassistant.const import (
    SERVICE_TURN_ON,
    SERVICE_TURN_OFF,
    SERVICE_TOGGLE,
)

from .const import (
    DOMAIN,
    CONF_JWT_SECRET,
    CONF_EXPOSED_ENTITIES,
    API_BASE_PATH,
    API_WEBSOCKET_PATH,
    API_ENTITIES_PATH,
    API_AUTH_PATH,
    API_CALL_SERVICE_PATH,
    API_REGISTER_CLIENT_PATH,
    API_REVOKE_CLIENT_PATH,
    API_LIST_CLIENTS_PATH,
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
    ATTR_CLIENT_ID,
    ATTR_CLIENT_NAME,
    ATTR_TOKEN,
)
from .auth import ClientTokenManager

_LOGGER = logging.getLogger(__name__)


class EntitySyncServer:
    """Server for entity synchronization."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the server."""
        self.hass = hass
        self.entry = entry
        self.jwt_secret = entry.data.get(CONF_JWT_SECRET)
        self.clients: Set[web.WebSocketResponse] = set()
        self._views_registered = False
        self._token_manager = ClientTokenManager(hass, self.jwt_secret)

    async def async_setup(self):
        """Set up the server."""
        # Load client tokens from storage
        await self._token_manager.async_load()
        
        # Register HTTP views
        if not self._views_registered:
            self.hass.http.register_view(EntitySyncAuthView(self))
            self.hass.http.register_view(EntitySyncEntitiesView(self))
            self.hass.http.register_view(EntitySyncWebSocketView(self))
            self.hass.http.register_view(EntitySyncCallServiceView(self))
            self.hass.http.register_view(EntitySyncRegisterClientView(self))
            self.hass.http.register_view(EntitySyncRevokeClientView(self))
            self.hass.http.register_view(EntitySyncListClientsView(self))
            self._views_registered = True
        
        _LOGGER.info("Home Assistant Sync Server started")

    async def async_shutdown(self):
        """Shutdown the server."""
        # Close all client connections
        for client in list(self.clients):
            await client.close()
        self.clients.clear()
        _LOGGER.info("Home Assistant Sync Server stopped")

    def verify_client_token(self, token: str) -> bool:
        """Verify client JWT token."""
        payload = self._token_manager.verify_token(token)
        return payload is not None

    async def async_register_client(self, client_name: str) -> Dict[str, str]:
        """Register a new client."""
        return await self._token_manager.async_register_client(client_name)

    async def async_revoke_client(self, client_id: str) -> bool:
        """Revoke a client's access."""
        return await self._token_manager.async_revoke_client(client_id)

    def get_clients(self) -> Dict[str, dict]:
        """Get all registered clients."""
        return self._token_manager.get_clients()

    def get_exposed_entities(self):
        """Get list of exposed entities."""
        return self.entry.options.get(CONF_EXPOSED_ENTITIES, [])

    def get_entity_state(self, entity_id: str) -> dict:
        """Get the state of an entity."""
        state = self.hass.states.get(entity_id)
        if state:
            return self._state_to_dict(state)
        return None

    def _state_to_dict(self, state: State) -> dict:
        """Convert a state object to a dictionary."""
        return {
            "entity_id": state.entity_id,
            "state": state.state,
            "attributes": dict(state.attributes),
            "last_changed": state.last_changed.isoformat(),
            "last_updated": state.last_updated.isoformat(),
        }

    async def broadcast_state_change(self, entity_id: str, state: State):
        """Broadcast state change to all connected clients."""
        message = {
            "type": WS_TYPE_STATE_CHANGED,
            "entity_id": entity_id,
            "data": self._state_to_dict(state),
        }
        
        disconnected_clients = []
        for client in self.clients:
            try:
                await client.send_json(message)
            except Exception as ex:
                _LOGGER.error("Error sending to client: %s", ex)
                disconnected_clients.append(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.clients.discard(client)

    async def call_service(
        self, 
        domain: str, 
        service: str, 
        service_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a service on an entity."""
        entity_id = service_data.get(ATTR_ENTITY_ID)
        
        # Verify the entity is exposed
        exposed_entities = self.get_exposed_entities()
        if entity_id not in exposed_entities:
            _LOGGER.error("Entity %s is not exposed", entity_id)
            return {
                "success": False,
                "error": "Entity not exposed"
            }
        
        try:
            # Call the service
            await self.hass.services.async_call(
                domain,
                service,
                service_data,
                blocking=True
            )
            
            _LOGGER.info(
                "Service %s.%s called for %s",
                domain,
                service,
                entity_id
            )
            
            return {
                "success": True,
                "entity_id": entity_id
            }
        except Exception as ex:
            _LOGGER.error("Error calling service: %s", ex)
            return {
                "success": False,
                "error": str(ex)
            }

    async def handle_websocket(self, request):
        """Handle WebSocket connection."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        authenticated = False
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        msg_type = data.get("type")

                        if msg_type == WS_TYPE_AUTH:
                            token = data.get("token")
                            if self.verify_client_token(token):
                                authenticated = True
                                self.clients.add(ws)
                                await ws.send_json({"type": "auth_ok"})
                                _LOGGER.info("Client authenticated")
                            else:
                                await ws.send_json({"type": "auth_failed"})
                                await ws.close()
                                break

                        elif authenticated:
                            if msg_type == WS_TYPE_GET_ENTITIES:
                                entities = self.get_exposed_entities()
                                await ws.send_json({
                                    "type": "entities",
                                    "data": entities,
                                })
                            elif msg_type == WS_TYPE_SUBSCRIBE:
                                entity_id = data.get("entity_id")
                                state = self.get_entity_state(entity_id)
                                if state:
                                    await ws.send_json({
                                        "type": WS_TYPE_STATE_CHANGED,
                                        "entity_id": entity_id,
                                        "data": state,
                                    })
                            elif msg_type == WS_TYPE_CALL_SERVICE:
                                # Handle service call from client
                                domain = data.get(ATTR_DOMAIN)
                                service = data.get(ATTR_SERVICE)
                                service_data = data.get(ATTR_SERVICE_DATA, {})
                                request_id = data.get("request_id")
                                
                                result = await self.call_service(
                                    domain, 
                                    service, 
                                    service_data
                                )
                                
                                await ws.send_json({
                                    "type": WS_TYPE_SERVICE_RESPONSE,
                                    "request_id": request_id,
                                    "result": result,
                                })
                        else:
                            await ws.send_json({
                                "type": "error", 
                                "message": "Not authenticated"
                            })

                    except json.JSONDecodeError:
                        _LOGGER.error("Invalid JSON received")
                    except Exception as ex:
                        _LOGGER.error("Error processing message: %s", ex)

                elif msg.type == WSMsgType.ERROR:
                    _LOGGER.error("WebSocket error: %s", ws.exception())

        finally:
            self.clients.discard(ws)
            _LOGGER.info("Client disconnected")

        return ws


class EntitySyncAuthView(HomeAssistantView):
    """View to handle authentication validation."""

    url = API_AUTH_PATH
    name = f"api:{DOMAIN}:auth"
    requires_auth = False

    def __init__(self, server: EntitySyncServer):
        """Initialize the view."""
        self.server = server

    async def get(self, request):
        """Handle GET request."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return web.Response(status=401, text="Unauthorized")

        token = auth_header[7:]
        if self.server.verify_client_token(token):
            return web.json_response({"status": "ok"})
        else:
            return web.Response(status=401, text="Invalid token")


class EntitySyncEntitiesView(HomeAssistantView):
    """View to get available entities."""

    url = API_ENTITIES_PATH
    name = f"api:{DOMAIN}:entities"
    requires_auth = False

    def __init__(self, server: EntitySyncServer):
        """Initialize the view."""
        self.server = server

    async def get(self, request):
        """Handle GET request."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return web.Response(status=401, text="Unauthorized")

        token = auth_header[7:]
        if not self.server.verify_client_token(token):
            return web.Response(status=401, text="Invalid token")

        entities = self.server.get_exposed_entities()
        entity_states = {}
        
        for entity_id in entities:
            state = self.server.get_entity_state(entity_id)
            if state:
                entity_states[entity_id] = state

        return web.json_response(entity_states)


class EntitySyncCallServiceView(HomeAssistantView):
    """View to handle service calls."""

    url = API_CALL_SERVICE_PATH
    name = f"api:{DOMAIN}:call_service"
    requires_auth = False

    def __init__(self, server: EntitySyncServer):
        """Initialize the view."""
        self.server = server

    async def post(self, request):
        """Handle POST request."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return web.Response(status=401, text="Unauthorized")

        token = auth_header[7:]
        if not self.server.verify_client_token(token):
            return web.Response(status=401, text="Invalid token")

        try:
            data = await request.json()
            domain = data.get(ATTR_DOMAIN)
            service = data.get(ATTR_SERVICE)
            service_data = data.get(ATTR_SERVICE_DATA, {})

            result = await self.server.call_service(domain, service, service_data)
            return web.json_response(result)

        except Exception as ex:
            _LOGGER.error("Error handling service call: %s", ex)
            return web.json_response({
                "success": False,
                "error": str(ex)
            }, status=500)


class EntitySyncRegisterClientView(HomeAssistantView):
    """View to register a new client."""

    url = API_REGISTER_CLIENT_PATH
    name = f"api:{DOMAIN}:register_client"
    requires_auth = False

    def __init__(self, server: EntitySyncServer):
        """Initialize the view."""
        self.server = server

    async def post(self, request):
        """Handle POST request."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return web.Response(status=401, text="Unauthorized")

        # Verify the JWT secret (basic auth for registration)
        token = auth_header[7:]
        from .auth import verify_jwt_token
        payload = verify_jwt_token(token, self.server.jwt_secret)
        
        if not payload:
            return web.Response(status=401, text="Invalid token")

        try:
            data = await request.json()
            client_name = data.get(ATTR_CLIENT_NAME, "Unknown Client")

            client_data = await self.server.async_register_client(client_name)
            
            return web.json_response(client_data)

        except Exception as ex:
            _LOGGER.error("Error registering client: %s", ex)
            return web.json_response({
                "success": False,
                "error": str(ex)
            }, status=500)


class EntitySyncRevokeClientView(HomeAssistantView):
    """View to revoke a client."""

    url = API_REVOKE_CLIENT_PATH
    name = f"api:{DOMAIN}:revoke_client"
    requires_auth = False

    def __init__(self, server: EntitySyncServer):
        """Initialize the view."""
        self.server = server

    async def post(self, request):
        """Handle POST request."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return web.Response(status=401, text="Unauthorized")

        token = auth_header[7:]
        if not self.server.verify_client_token(token):
            return web.Response(status=401, text="Invalid token")

        try:
            data = await request.json()
            client_id = data.get(ATTR_CLIENT_ID)

            success = await self.server.async_revoke_client(client_id)
            
            if success:
                return web.json_response({"success": True})
            else:
                return web.json_response({
                    "success": False,
                    "error": "Client not found"
                }, status=404)

        except Exception as ex:
            _LOGGER.error("Error revoking client: %s", ex)
            return web.json_response({
                "success": False,
                "error": str(ex)
            }, status=500)


class EntitySyncListClientsView(HomeAssistantView):
    """View to list all clients."""

    url = API_LIST_CLIENTS_PATH
    name = f"api:{DOMAIN}:list_clients"
    requires_auth = False

    def __init__(self, server: EntitySyncServer):
        """Initialize the view."""
        self.server = server

    async def get(self, request):
        """Handle GET request."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return web.Response(status=401, text="Unauthorized")

        token = auth_header[7:]
        if not self.server.verify_client_token(token):
            return web.Response(status=401, text="Invalid token")

        clients = self.server.get_clients()
        
        # Remove token from response for security
        safe_clients = {}
        for client_id, client_data in clients.items():
            safe_clients[client_id] = {
                ATTR_CLIENT_ID: client_data[ATTR_CLIENT_ID],
                ATTR_CLIENT_NAME: client_data[ATTR_CLIENT_NAME],
                ATTR_CREATED_AT: client_data[ATTR_CREATED_AT],
            }
        
        return web.json_response({"clients": safe_clients})


class EntitySyncWebSocketView(HomeAssistantView):
    """View to handle WebSocket connections."""

    url = API_WEBSOCKET_PATH
    name = f"api:{DOMAIN}:websocket"
    requires_auth = False

    def __init__(self, server: EntitySyncServer):
        """Initialize the view."""
        self.server = server

    async def get(self, request):
        """Handle WebSocket connection."""
        return await self.server.handle_websocket(request)