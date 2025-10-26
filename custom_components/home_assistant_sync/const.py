"""Constants for the Home Assistant Sync integration."""

DOMAIN = "home_assistant_sync"

# Configuration
CONF_MODE = "mode"
CONF_SERVER_URL = "server_url"
CONF_ACCESS_TOKEN = "access_token"
CONF_JWT_SECRET = "jwt_secret"
CONF_EXPOSED_ENTITIES = "exposed_entities"
CONF_IMPORTED_ENTITIES = "imported_entities"

# Modes
MODE_SERVER = "server"
MODE_CLIENT = "client"

# API Endpoints
API_BASE_PATH = f"/api/{DOMAIN}"
API_WEBSOCKET_PATH = f"{API_BASE_PATH}/ws"
API_ENTITIES_PATH = f"{API_BASE_PATH}/entities"
API_STATE_PATH = f"{API_BASE_PATH}/state"
API_AUTH_PATH = f"{API_BASE_PATH}/auth"

# WebSocket Events
WS_TYPE_AUTH = "auth"
WS_TYPE_STATE_CHANGED = "state_changed"
WS_TYPE_SUBSCRIBE = "subscribe"
WS_TYPE_UNSUBSCRIBE = "unsubscribe"
WS_TYPE_GET_ENTITIES = "get_entities"

# Default Values
DEFAULT_PORT = 8123
DEFAULT_SCAN_INTERVAL = 30

# Attributes
ATTR_ENTITY_ID = "entity_id"
ATTR_STATE = "state"
ATTR_ATTRIBUTES = "attributes"
ATTR_LAST_CHANGED = "last_changed"
ATTR_LAST_UPDATED = "last_updated"