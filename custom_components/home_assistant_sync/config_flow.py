"""Config flow for Home Assistant Sync integration."""
import logging
from typing import Any

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
    CONF_EXPOSED_ENTITIES,
    CONF_IMPORTED_ENTITIES,
    MODE_SERVER,
    MODE_CLIENT,
)
from .auth import validate_server_connection

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
                       "Clients will need this secret to connect."
            },
        )

    async def async_step_client(self, user_input=None):
        """Handle client configuration."""
        errors = {}

        if user_input is not None:
            server_url = user_input[CONF_SERVER_URL]
            jwt_secret = user_input[CONF_JWT_SECRET]

            # Validate connection to server
            try:
                is_valid = await validate_server_connection(
                    self.hass, server_url, jwt_secret
                )
                if not is_valid:
                    errors["base"] = "cannot_connect"
            except Exception as ex:
                _LOGGER.error("Error validating server connection: %s", ex)
                errors["base"] = "cannot_connect"

            if not errors:
                self._data[CONF_SERVER_URL] = server_url
                self._data[CONF_JWT_SECRET] = jwt_secret
                
                return self.async_create_entry(
                    title=f"Home Assistant Sync Client ({server_url})",
                    data=self._data,
                )

        data_schema = vol.Schema({
            vol.Required(CONF_SERVER_URL): cv.string,
            vol.Required(CONF_JWT_SECRET): cv.string,
        })

        return self.async_show_form(
            step_id="client",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "info": "Enter the server URL (e.g., http://192.168.1.100:8123) "
                       "and the JWT secret provided by the server."
            },
        )

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