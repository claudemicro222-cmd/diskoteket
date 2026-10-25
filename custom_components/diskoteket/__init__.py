"""Diskoteket i Home Assistant: sensorer för samlingen och ett eget Lovelace-kort.

Kortet (frontend/diskoteket-card.js) följer med integrationen och laddas automatiskt –
du behöver inte lägga till någon resurs själv."""
from __future__ import annotations

import re
from pathlib import Path

import aiohttp
from aiohttp import web

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .const import CARD_URL, DOMAIN, VERSION
from .coordinator import DiskoteketCoordinator

PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
POSTER_RE = re.compile(r"^[A-Za-z0-9_\-]+\.(?:jpg|jpeg|png|webp)$")

type DiskoteketConfigEntry = ConfigEntry[DiskoteketCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Registrera kortet och omslagsvägen en gång, oavsett hur många Diskotek som läggs till."""
    card = Path(__file__).parent / "frontend" / "diskoteket-card.js"
    await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, str(card), False)])
    # Kortet laddas på alla instrumentpaneler. ?v= gör att webbläsaren hämtar nytt efter en uppdatering.
    add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")
    hass.http.register_view(DiskoteketPosterView())
    return True


async def async_setup_entry(hass: HomeAssistant, entry: DiskoteketConfigEntry) -> bool:
    coordinator = DiskoteketCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DiskoteketConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


class DiskoteketPosterView(HomeAssistantView):
    """Omslag via Home Assistant, så att kortet fungerar även när HA nås över HTTPS
    och Diskoteket bara över HTTP på hemmanätet. Kortet ber om en signerad adress."""

    url = "/api/diskoteket/{entry_id}/poster/{name}"
    name = "api:diskoteket:poster"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str, name: str) -> web.StreamResponse:
        hass: HomeAssistant = request.app["hass"]
        entry = hass.config_entries.async_get_entry(entry_id)
        if not entry or entry.domain != DOMAIN or not POSTER_RE.match(name) or not hasattr(entry, "runtime_data"):
            return web.Response(status=404)
        coordinator: DiskoteketCoordinator = entry.runtime_data
        try:
            async with async_get_clientsession(hass).get(
                    f"{coordinator.url}/poster/{name}", timeout=aiohttp.ClientTimeout(total=20)) as r:
                if r.status != 200:
                    return web.Response(status=404)
                return web.Response(body=await r.read(), content_type=r.content_type or "image/jpeg",
                                    headers={"Cache-Control": "private, max-age=604800"})
        except (aiohttp.ClientError, TimeoutError):
            return web.Response(status=502)
