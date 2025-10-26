"""Config flow for Home Assistant Sync integration."""
import logging
from typing import Any
import aiohttp

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_MODE,
    CONF_SERVER_URL,
    CONF_ACCESS_TOKEN,
    CONF_JWT_SECRET,
    CONF_CLIENT_TOKEN,
    CONF_CLIENT_NAME,
    CONF_EXPOSED_ENTITIES,
    CONF_IMPORTED_ENTITIES,
    MODE_SERVER,
    MODE_CLIENT,
    API_REGISTER_CLIENT_PATH,
    ATTR_CLIENT_NAME,
    ATTR_TOKEN,
)

_LOGGER = logging.getLogger(__name__)


class HomeAssistantSyncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Home Assistant Sync."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._mode = None
        self._data = {}

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            self._mode = user_input[CONF_MODE]
            self._data[CONF_MODE] = self._mode

            if self._mode == MODE_SERVER:
                return await self.async_step_server()
            else:
                return await self.async_step_client()

        data_schema = vol.Schema({
            vol.Required(CONF_MODE): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"label": "Server", "value": MODE_SERVER},
                        {"label": "Client", "value": MODE_CLIENT},
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_server(self, user_input=None):
        """Handle server configuration."""
        errors = {}

        if user_input is not None:
            self._data[CONF_JWT_SECRET] = user_input[CONF_JWT_SECRET]
            
            return self.async_create_entry(
                title="Home Assistant Sync Server",
                data=self._data,
            )

        data_schema = vol.Schema({
            vol.Required(CONF_JWT_SECRET): cv.string,
        })

        return self.async_show_form(
            step_id="server",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "info": "Configure the JWT secret for secure authentication. "
                       "This will be used to sign tokens for clients."
            },
        )

    async def async_step_client(self, user_input=None):
        """Handle client configuration."""
        errors = {}

        if user_input is not None:
            server_url = user_input[CONF_SERVER_URL]
            jwt_secret = user_input[CONF_JWT_SECRET]
            client_name = user_input.get(CONF_CLIENT_NAME, f"Client_{self.hass.config.location_name}")

            # Register client with server
            try:
                token_data = await self._register_with_server(
                    server_url,
                    jwt_secret,
                    client_name
                )
                
                if token_data:
                    self._data[CONF_SERVER_URL] = server_url
                    self._data[CONF_JWT_SECRET] = jwt_secret
                    self._data[CONF_CLIENT_TOKEN] = token_data[ATTR_TOKEN]
                    self._data[CONF_CLIENT_NAME] = client_name
                    
                    return self.async_create_entry(
                        title=f"Home Assistant Sync Client ({client_name})",
                        data=self._data,
                    )
                else:
                    errors["base"] = "cannot_register"
                    
            except aiohttp.ClientError as ex:
                _LOGGER.error("Connection error during registration: %s", ex)
                errors["base"] = "cannot_connect"
            except Exception as ex:
                _LOGGER.error("Unexpected error during registration: %s", ex)
                errors["base"] = "unknown"

        data_schema = vol.Schema({
            vol.Required(CONF_SERVER_URL): cv.string,
            vol.Required(CONF_JWT_SECRET): cv.string,
            vol.Optional(
                CONF_CLIENT_NAME, 
                default=f"Client_{self.hass.config.location_name}"
            ): cv.string,
        })

        return self.async_show_form(
            step_id="client",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "info": "Enter the server URL (e.g., http://192.168.1.100:8123), "
                       "the JWT secret from the server, and a name for this client."
            },
        )

    async def _register_with_server(
        self,
        server_url: str,
        jwt_secret: str,
        client_name: str
    ) -> dict:
        """Register this client with the server."""
        try:
            url = f"{server_url.rstrip('/')}{API_REGISTER_CLIENT_PATH}"
            
            # Create a temporary token for registration
            from .auth import generate_jwt_token
            temp_token = generate_jwt_token(jwt_secret, "registration")
            
            headers = {
                "Authorization": f"Bearer {temp_token}",
                "Content-Type": "application/json",
            }
            
            payload = {ATTR_CLIENT_NAME: client_name}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        _LOGGER.info(
                            "Successfully registered with server: %s",
                            client_name
                        )
                        return data
                    else:
                        _LOGGER.error(
                            "Registration failed with status: %s",
                            response.status
                        )
                        return None
                        
        except Exception as ex:
            _LOGGER.error("Error during registration: %s", ex)
            raise

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Home Assistant Sync."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        mode = self.config_entry.data.get(CONF_MODE)

        if mode == MODE_SERVER:
            return await self.async_step_server_options()
        else:
            return await self.async_step_client_options()

    async def async_step_server_options(self, user_input=None):
        """Manage server options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get all entities from Home Assistant
        states = self.hass.states.async_all()
        entity_options = [
            {"label": f"{state.entity_id} ({state.name})", "value": state.entity_id}
            for state in states
        ]

        current_exposed = self.config_entry.options.get(CONF_EXPOSED_ENTITIES, [])

        data_schema = vol.Schema({
            vol.Optional(
                CONF_EXPOSED_ENTITIES,
                default=current_exposed,
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    multiple=True,
                )
            ),
        })

        return self.async_show_form(
            step_id="server_options",
            data_schema=data_schema,
            description_placeholders={
                "info": "Select which entities to expose to clients."
            },
        )

    async def async_step_client_options(self, user_input=None):
        """Manage client options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get available entities from server
        coordinator = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
        available_entities = []
        
        if coordinator:
            available_entities = await coordinator.async_get_available_entities()

        entity_options = [
            {"label": entity_id, "value": entity_id}
            for entity_id in available_entities
        ]

        current_imported = self.config_entry.options.get(CONF_IMPORTED_ENTITIES, [])

        data_schema = vol.Schema({
            vol.Optional(
                CONF_IMPORTED_ENTITIES,
                default=current_imported,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=entity_options,
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        })

        return self.async_show_form(
            step_id="client_options",
            data_schema=data_schema,
            description_placeholders={
                "info": "Select which entities to import from the server."
            },
        )