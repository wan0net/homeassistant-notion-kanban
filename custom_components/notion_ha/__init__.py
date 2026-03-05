"""Notion integration for Home Assistant."""
from __future__ import annotations

from pathlib import Path

import voluptuous as vol

import uuid

from homeassistant.components.http import StaticPathConfig
from homeassistant.helpers.storage import Store
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACTIVE_STATUSES,
    CONF_COMPLETED_STATUSES,
    CONF_DATABASE_ID,
    CONF_STATUS_PROPERTY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import NotionTodoCoordinator
from .notion_client import NotionClient

PLATFORMS = [Platform.SENSOR, Platform.TODO]

SERVICE_SET_ITEM_STATUS = "set_item_status"
SERVICE_ARCHIVE_DONE = "archive_done"

SERVICE_SET_ITEM_STATUS_SCHEMA = vol.Schema(
    {
        vol.Required("item_id"): cv.string,
        vol.Required("status"): cv.string,
    }
)

SERVICE_ARCHIVE_DONE_SCHEMA = vol.Schema(
    {
        vol.Optional("archive_status", default="Archive"): cv.string,
    }
)


def _get_coordinator_for_item(hass: HomeAssistant, item_id: str) -> NotionTodoCoordinator | None:
    """Find the coordinator that owns a given Notion page ID."""
    for coordinator in hass.data.get(DOMAIN, {}).values():
        if not isinstance(coordinator, NotionTodoCoordinator):
            continue
        if coordinator.data and any(
            i["id"] == item_id for i in coordinator.data.get("items", [])
        ):
            return coordinator
    return None


def _get_any_coordinator(hass: HomeAssistant) -> NotionTodoCoordinator | None:
    """Return any available coordinator (used for archive_done across all entries)."""
    for coordinator in hass.data.get(DOMAIN, {}).values():
        if isinstance(coordinator, NotionTodoCoordinator):
            return coordinator
    return None


_CARD_URL = "/notion_ha/notion-kanban-card.js"
_CARD_REGISTERED = f"{DOMAIN}_card_registered"


async def _ensure_lovelace_resource(hass: HomeAssistant, url: str) -> None:
    """Persist the card as a Lovelace resource so HA loads it before rendering."""
    store = Store(hass, 1, "lovelace_resources")
    data = await store.async_load() or {"items": []}
    if any(url in item.get("url", "") for item in data.get("items", [])):
        return
    data.setdefault("items", []).append(
        {"id": uuid.uuid4().hex, "url": url, "type": "module"}
    )
    await store.async_save(data)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Serve and inject the bundled Lovelace card (once per HA lifetime)
    if not hass.data.get(_CARD_REGISTERED):
        await hass.http.async_register_static_paths([
            StaticPathConfig(
                _CARD_URL,
                str(Path(__file__).parent / "notion-kanban-card.js"),
                cache_headers=False,
            )
        ])
        await _ensure_lovelace_resource(hass, _CARD_URL)
        hass.data[_CARD_REGISTERED] = True

    session = async_get_clientsession(hass)
    client = NotionClient(session, entry.data[CONF_API_KEY])

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    coordinator = NotionTodoCoordinator(
        hass=hass,
        client=client,
        database_id=entry.data[CONF_DATABASE_ID],
        status_property=entry.data[CONF_STATUS_PROPERTY],
        active_statuses=entry.data[CONF_ACTIVE_STATUSES],
        completed_statuses=entry.data[CONF_COMPLETED_STATUSES],
        scan_interval=scan_interval,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Register services once (idempotent — HA deduplicates)
    if not hass.services.has_service(DOMAIN, SERVICE_SET_ITEM_STATUS):

        async def handle_set_item_status(call: ServiceCall) -> None:
            item_id = call.data["item_id"]
            status = call.data["status"]
            coordinator = _get_coordinator_for_item(hass, item_id)
            if coordinator:
                await coordinator.async_set_status(item_id, status)

        async def handle_archive_done(call: ServiceCall) -> None:
            archive_status = call.data.get("archive_status", "Archive")
            for coord in hass.data.get(DOMAIN, {}).values():
                if isinstance(coord, NotionTodoCoordinator):
                    await coord.async_archive_done(archive_status)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_ITEM_STATUS,
            handle_set_item_status,
            schema=SERVICE_SET_ITEM_STATUS_SCHEMA,
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_ARCHIVE_DONE,
            handle_archive_done,
            schema=SERVICE_ARCHIVE_DONE_SCHEMA,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
