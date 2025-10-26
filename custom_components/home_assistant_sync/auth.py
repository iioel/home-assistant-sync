"""Authentication module for Home Assistant Sync."""
import logging
from datetime import datetime, timedelta
import jwt
import aiohttp
from typing import Optional

from homeassistant.core import HomeAssistant

from .const import API_AUTH_PATH

_LOGGER = logging.getLogger(__name__)

TOKEN_EXPIRATION_HOURS = 24


def generate_jwt_token(secret: str, client_id: str) -> str:
    """Generate a JWT token for authentication."""
    payload = {
        "client_id": client_id,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRATION_HOURS),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


def verify_jwt_token(token: str, secret: str) -> Optional[dict]:
    """Verify a JWT token."""
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        _LOGGER.error("Token has expired")
        return None
    except jwt.InvalidTokenError:
        _LOGGER.error("Invalid token")
        return None


async def validate_server_connection(
    hass: HomeAssistant, server_url: str, jwt_secret: str
) -> bool:
    """Validate connection to the server."""
    try:
        # Generate a test token
        token = generate_jwt_token(jwt_secret, "test_client")
        
        # Try to connect to the server
        url = f"{server_url.rstrip('/')}{API_AUTH_PATH}"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    return True
                else:
                    _LOGGER.error(
                        "Server connection validation failed with status: %s",
                        response.status
                    )
                    return False
    except aiohttp.ClientError as ex:
        _LOGGER.error("Connection error during validation: %s", ex)
        return False
    except Exception as ex:
        _LOGGER.error("Unexpected error during validation: %s", ex)
        return False