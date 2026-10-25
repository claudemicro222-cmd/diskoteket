"""Hämtar sammanfattningen från Diskoteket (GET /api/ha) med jämna mellanrum."""
from __future__ import annotations

import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_API_KEY, DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class DiskoteketError(Exception):
    """Diskoteket svarade inte."""


class DiskoteketAuthError(DiskoteketError):
    """Fel eller saknad API-nyckel."""


async def fetch_summary(hass: HomeAssistant, url: str, api_key: str | None) -> dict:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    session = async_get_clientsession(hass)
    try:
        async with session.get(f"{url}/api/ha", headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as r:
            if r.status == 401:
                raise DiskoteketAuthError
            r.raise_for_status()
            return await r.json()
    except DiskoteketAuthError:
        raise
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        raise DiskoteketError(str(err)) from err


class DiskoteketCoordinator(DataUpdateCoordinator[dict]):
    """En gemensam hämtning som alla sensorer läser från."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL, config_entry=entry)
        self.url: str = entry.data[CONF_URL].rstrip("/")
        self.api_key: str | None = entry.data.get(CONF_API_KEY) or None

    async def _async_update_data(self) -> dict:
        try:
            return await fetch_summary(self.hass, self.url, self.api_key)
        except DiskoteketAuthError as err:
            raise ConfigEntryAuthFailed("Fel API-nyckel – se Meny → Inloggning i Diskoteket") from err
        except DiskoteketError as err:
            raise UpdateFailed(f"Kunde inte nå Diskoteket: {err}") from err
