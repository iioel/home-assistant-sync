"""Authentication module for Home Assistant Sync."""
import logging
from datetime import datetime, timedelta
import jwt
from typing import Optional, Dict
import secrets

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    STORAGE_KEY,
    STORAGE_VERSION,
    TOKEN_EXPIRATION_DAYS,
    ATTR_CLIENT_ID,
    ATTR_CLIENT_NAME,
    ATTR_TOKEN,
    ATTR_CREATED_AT,
)

_LOGGER = logging.getLogger(__name__)


class ClientTokenManager:
    """Manage client tokens for the server."""

    def __init__(self, hass: HomeAssistant, jwt_secret: str):
        """Initialize the token manager."""
        self.hass = hass
        self.jwt_secret = jwt_secret
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._clients: Dict[str, dict] = {}

    async def async_load(self):
        """Load clients from storage."""
        data = await self._store.async_load()
        if data:
            self._clients = data.get("clients", {})
            _LOGGER.info("Loaded %d client(s) from storage", len(self._clients))
        else:
            self._clients = {}

    async def async_save(self):
        """Save clients to storage."""
        await self._store.async_save({"clients": self._clients})

    def generate_client_id(self) -> str:
        """Generate a unique client ID."""
        return secrets.token_urlsafe(16)

    async def async_register_client(
        self, 
        client_name: str,
        client_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Register a new client and generate a token."""
        if not client_id:
            client_id = self.generate_client_id()
        
        # Generate JWT token for this client
        token = self._generate_token(client_id, client_name)
        
        # Store client information
        self._clients[client_id] = {
            ATTR_CLIENT_ID: client_id,
            ATTR_CLIENT_NAME: client_name,
            ATTR_TOKEN: token,
            ATTR_CREATED_AT: datetime.utcnow().isoformat(),
        }
        
        await self.async_save()
        
        _LOGGER.info("Registered new client: %s (ID: %s)", client_name, client_id)
        
        return {
            ATTR_CLIENT_ID: client_id,
            ATTR_CLIENT_NAME: client_name,
            ATTR_TOKEN: token,
        }

    def _generate_token(self, client_id: str, client_name: str) -> str:
        """Generate a JWT token for a client."""
        payload = {
            ATTR_CLIENT_ID: client_id,
            ATTR_CLIENT_NAME: client_name,
            "exp": datetime.utcnow() + timedelta(days=TOKEN_EXPIRATION_DAYS),
            "iat": datetime.utcnow(),
        }
        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        return token

    def verify_token(self, token: str) -> Optional[dict]:
        """Verify a client token."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            client_id = payload.get(ATTR_CLIENT_ID)
            
            # Check if client is registered
            if client_id in self._clients:
                return payload
            else:
                _LOGGER.warning("Token valid but client not registered: %s", client_id)
                return None
                
        except jwt.ExpiredSignatureError:
            _LOGGER.error("Token has expired")
            return None
        except jwt.InvalidTokenError as ex:
            _LOGGER.error("Invalid token: %s", ex)
            return None

    async def async_revoke_client(self, client_id: str) -> bool:
        """Revoke a client's access."""
        if client_id in self._clients:
            del self._clients[client_id]
            await self.async_save()
            _LOGGER.info("Revoked client: %s", client_id)
            return True
        return False

    def get_clients(self) -> Dict[str, dict]:
        """Get all registered clients."""
        return self._clients.copy()

    def get_client(self, client_id: str) -> Optional[dict]:
        """Get a specific client."""
        return self._clients.get(client_id)


def generate_jwt_token(secret: str, client_id: str) -> str:
    """Generate a JWT token for authentication (deprecated - use ClientTokenManager)."""
    payload = {
        "client_id": client_id,
        "exp": datetime.utcnow() + timedelta(days=TOKEN_EXPIRATION_DAYS),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


def verify_jwt_token(token: str, secret: str) -> Optional[dict]:
    """Verify a JWT token (deprecated - use ClientTokenManager)."""
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        _LOGGER.error("Token has expired")
        return None
    except jwt.InvalidTokenError:
        _LOGGER.error("Invalid token")
        return None