"""Constants for the Home Assistant Sync integration."""

DOMAIN = "home_assistant_sync"

# Configuration
CONF_MODE = "mode"
CONF_SERVER_URL = "server_url"
CONF_ACCESS_TOKEN = "access_token"
CONF_JWT_SECRET = "jwt_secret"
CONF_CLIENT_TOKEN = "client_token"
CONF_CLIENT_NAME = "client_name"
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
API_CALL_SERVICE_PATH = f"{API_BASE_PATH}/call_service"
API_REGISTER_CLIENT_PATH = f"{API_BASE_PATH}/register_client"
API_REVOKE_CLIENT_PATH = f"{API_BASE_PATH}/revoke_client"
API_LIST_CLIENTS_PATH = f"{API_BASE_PATH}/clients"

# WebSocket Events
WS_TYPE_AUTH = "auth"
WS_TYPE_STATE_CHANGED = "state_changed"
WS_TYPE_SUBSCRIBE = "subscribe"
WS_TYPE_UNSUBSCRIBE = "unsubscribe"
WS_TYPE_GET_ENTITIES = "get_entities"
WS_TYPE_CALL_SERVICE = "call_service"
WS_TYPE_SERVICE_RESPONSE = "service_response"

# Default Values
DEFAULT_PORT = 8123
DEFAULT_SCAN_INTERVAL = 30
TOKEN_EXPIRATION_DAYS = 365

# Attributes
ATTR_ENTITY_ID = "entity_id"
ATTR_STATE = "state"
ATTR_ATTRIBUTES = "attributes"
ATTR_LAST_CHANGED = "last_changed"
ATTR_LAST_UPDATED = "last_updated"
ATTR_SERVICE = "service"
ATTR_SERVICE_DATA = "service_data"
ATTR_DOMAIN = "domain"
ATTR_CLIENT_ID = "client_id"
ATTR_CLIENT_NAME = "client_name"
ATTR_TOKEN = "token"
ATTR_CREATED_AT = "created_at"

# Storage
STORAGE_KEY = f"{DOMAIN}.clients"
STORAGE_VERSION = 1