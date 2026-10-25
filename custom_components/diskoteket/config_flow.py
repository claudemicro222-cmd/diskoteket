"""Lägg till Diskoteket: adress och (om inloggning är på) API-nyckel."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_URL

from .const import CONF_API_KEY, DOMAIN
from .coordinator import DiskoteketAuthError, DiskoteketError, fetch_summary


def _normalize(url: str) -> str:
    url = url.strip().rstrip("/")
    return url if url.startswith(("http://", "https://")) else f"http://{url}"


class DiskoteketConfigFlow(ConfigFlow, domain=DOMAIN):
    """Steg för steg i Inställningar → Enheter och tjänster."""

    VERSION = 1

    async def _test(self, url: str, key: str | None) -> str | None:
        try:
            await fetch_summary(self.hass, url, key)
        except DiskoteketAuthError:
            return "invalid_auth"
        except DiskoteketError:
            return "cannot_connect"
        return None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = _normalize(user_input[CONF_URL])
            key = (user_input.get(CONF_API_KEY) or "").strip() or None
            await self.async_set_unique_id(url.lower())
            self._abort_if_unique_id_configured()
            if not (error := await self._test(url, key)):
                return self.async_create_entry(title="Diskoteket", data={CONF_URL: url, CONF_API_KEY: key})
            errors["base"] = error
        schema = vol.Schema({
            vol.Required(CONF_URL, default=(user_input or {}).get(CONF_URL, "http://")): str,
            vol.Optional(CONF_API_KEY): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ny API-nyckel (t.ex. efter 'Skapa ny nyckel' i Diskoteket)."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            key = (user_input.get(CONF_API_KEY) or "").strip() or None
            if not (error := await self._test(entry.data[CONF_URL], key)):
                return self.async_update_reload_and_abort(entry, data_updates={CONF_API_KEY: key})
            errors["base"] = error
        return self.async_show_form(step_id="reauth_confirm", data_schema=vol.Schema({vol.Optional(CONF_API_KEY): str}),
                                    errors=errors)
