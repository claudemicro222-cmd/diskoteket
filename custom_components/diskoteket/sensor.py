"""Sensorer för samlingen. 'Titlar' bär hela sammanfattningen som attribut – den läser kortet."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DiskoteketConfigEntry
from .const import DOMAIN, VERSION
from .coordinator import DiskoteketCoordinator


@dataclass(frozen=True, kw_only=True)
class DiskoteketSensorDescription(SensorEntityDescription):
    value: Callable[[dict], Any]


def _count(key: str, icon: str, unit: str | None = None) -> DiskoteketSensorDescription:
    return DiskoteketSensorDescription(key=key, translation_key=key, icon=icon, native_unit_of_measurement=unit,
                                       state_class=SensorStateClass.MEASUREMENT, value=lambda d: d.get(key))


SENSORS: tuple[DiskoteketSensorDescription, ...] = (
    _count("total", "mdi:bookshelf", "titlar"),
    _count("movies", "mdi:movie-open", "filmer"),
    _count("series", "mdi:television-classic", "serier"),
    _count("seasons", "mdi:television-box", "säsonger"),
    _count("music", "mdi:album", "album"),
    _count("discs", "mdi:disc", "skivor"),
    _count("unwatched", "mdi:eye-off-outline", "titlar"),
    _count("wishlist", "mdi:star-outline", "titlar"),
    _count("loaned", "mdi:hand-extended-outline", "titlar"),
    _count("overdue", "mdi:clock-alert-outline", "titlar"),
    _count("value", "mdi:cash-multiple", "kr"),
    DiskoteketSensorDescription(key="latest", translation_key="latest", icon="mdi:new-box",
                                value=lambda d: d.get("latest_title")),
)

# Kortet behöver listorna, men databasen i HA (recorder) ska inte fyllas med dem varje gång
BIG = frozenset({"latest", "overdue_list", "collections", "formats", "summary"})


async def async_setup_entry(hass: HomeAssistant, entry: DiskoteketConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    async_add_entities(DiskoteketSensor(coordinator, entry, d) for d in SENSORS)


class DiskoteketSensor(CoordinatorEntity[DiskoteketCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _unrecorded_attributes = BIG
    entity_description: DiskoteketSensorDescription

    def __init__(self, coordinator: DiskoteketCoordinator, entry: DiskoteketConfigEntry,
                 description: DiskoteketSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name="Diskoteket", manufacturer="Diskoteket",
            model="Film-, serie- och musiksamling", sw_version=VERSION, configuration_url=coordinator.url,
            entry_type=DeviceEntryType.SERVICE)

    @property
    def native_value(self):
        return self.entity_description.value(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        d = self.coordinator.data or {}
        if self.entity_description.key == "total":
            # Allt kortet visar. 'diskoteket_entry' låter kortet hämta omslag via Home Assistant.
            return {"diskoteket_entry": self._entry.entry_id, "url": self.coordinator.url,
                    **{k: d.get(k) for k in ("movies", "series", "seasons", "music", "discs", "unwatched", "wishlist",
                                             "loaned", "overdue", "value", "video")},
                    "latest": d.get("latest") or [], "overdue_list": d.get("overdue_list") or [],
                    "collections": d.get("collections") or [], "formats": d.get("formats") or []}
        if self.entity_description.key == "latest":
            return {"added": d.get("latest_added")}
        if self.entity_description.key == "overdue":
            return {"overdue_list": d.get("overdue_list") or []}
        return None
