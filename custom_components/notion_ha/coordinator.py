"""DataUpdateCoordinator for Notion todo databases."""
from __future__ import annotations

import json
import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .notion_client import NotionClient

_LOGGER = logging.getLogger(__name__)


def _get_title(page: dict) -> str:
    """Extract plain text title from a Notion page."""
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            parts = prop.get("title", [])
            return "".join(p.get("plain_text", "") for p in parts)
    return "(Untitled)"


def _get_select_value(page: dict, property_name: str) -> str | None:
    """Extract value from a select or status property."""
    prop = page.get("properties", {}).get(property_name, {})
    prop_type = prop.get("type")
    if prop_type == "select":
        sel = prop.get("select")
        return sel.get("name") if sel else None
    if prop_type == "status":
        sel = prop.get("status")
        return sel.get("name") if sel else None
    return None


def _get_multiselect_values(page: dict, property_name: str) -> list[dict]:
    """Extract name+color pairs from a multi_select property."""
    prop = page.get("properties", {}).get(property_name, {})
    if prop.get("type") == "multi_select":
        return [
            {"name": o["name"], "color": o.get("color", "default")}
            for o in prop.get("multi_select", [])
        ]
    return []


def _get_date_value(page: dict, property_name: str) -> str | None:
    """Extract start date string from a date property."""
    prop = page.get("properties", {}).get(property_name, {})
    if prop.get("type") == "date":
        date = prop.get("date")
        return date.get("start") if date else None
    return None


def _get_schema_options(database: dict, property_name: str) -> list[str]:
    """Return the option names for a select/status property in the database schema."""
    prop = database.get("properties", {}).get(property_name, {})
    prop_type = prop.get("type")
    if prop_type == "select":
        return [o["name"] for o in prop.get("select", {}).get("options", [])]
    if prop_type == "status":
        options = []
        for group in prop.get("status", {}).get("groups", []):
            options.extend(group.get("option_ids", []))
        # Fall back to flat options list
        return [o["name"] for o in prop.get("status", {}).get("options", [])]
    return []


def transform_pages(
    pages: list[dict],
    status_property: str,
    active_statuses: list[str],
    completed_statuses: list[str],
) -> dict[str, Any]:
    """Pure function: transform raw Notion pages into coordinator data dict.

    Extracted for testability — no HA dependencies.
    """
    items = []
    for page in pages:
        if page.get("archived"):
            continue

        status = _get_select_value(page, status_property)
        if status not in active_statuses and status not in completed_statuses:
            continue

        due_date = _get_date_value(page, "Due")
        labels = _get_multiselect_values(page, "Label")

        items.append(
            {
                "id": page["id"],
                "content": _get_title(page),
                "status": status,
                "section_id": status.lower().replace(" ", "_"),
                "due_date": due_date,
                "url": page.get("url"),
                "checked": status in completed_statuses,
                "labels": labels,
            }
        )

    all_statuses = list(active_statuses) + list(completed_statuses)
    return {
        "items": items,
        "sections": [
            {"id": s.lower().replace(" ", "_"), "name": s}
            for s in all_statuses
        ],
    }


class NotionTodoCoordinator(DataUpdateCoordinator):
    """Polls a Notion database and exposes todo + kanban data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: NotionClient,
        database_id: str,
        status_property: str,
        active_statuses: list[str],
        completed_statuses: list[str],
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        self.client = client
        self.database_id = database_id
        self.status_property = status_property
        self.active_statuses = active_statuses
        self.completed_statuses = completed_statuses
        self._cache_path = Path(hass.config.path(
            f".notion_ha_cache_{database_id.replace('-', '')}.json"
        ))

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    def _load_cache(self) -> dict[str, Any] | None:
        """Return cached data from disk, or None if unavailable."""
        try:
            return json.loads(self._cache_path.read_text())
        except Exception:
            return None

    def _save_cache(self, data: dict[str, Any]) -> None:
        """Persist data to disk cache."""
        try:
            self._cache_path.write_text(json.dumps(data))
        except Exception as err:
            _LOGGER.warning("Could not write Notion cache: %s", err)

    async def async_config_entry_first_refresh(self) -> None:
        """Load from cache immediately, then kick off a live refresh."""
        cached = self._load_cache()
        if cached:
            self.data = cached
            _LOGGER.debug("Loaded %d items from Notion cache", len(cached.get("items", [])))
        await super().async_config_entry_first_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch pages from Notion and transform into usable structures."""
        try:
            pages = await self.client.query_database(self.database_id)
        except Exception as err:
            if self.data:
                _LOGGER.warning("Notion fetch failed, using cached data: %s", err)
                return self.data
            raise UpdateFailed(f"Error fetching Notion data: {err}") from err

        data = transform_pages(
            pages,
            self.status_property,
            self.active_statuses,
            self.completed_statuses,
        )
        self._save_cache(data)
        return data

    # --- Write-back helpers ---

    async def async_set_status(self, page_id: str, status: str) -> None:
        """Update the status of a page in Notion."""
        prop = await self._detect_property_type()
        await self.client.update_page(
            page_id,
            {self.status_property: {prop: {"name": status}}},
        )
        await self.async_request_refresh()

    async def async_create_item(self, title: str, status: str | None = None) -> None:
        """Create a new page in the database."""
        target_status = status or (self.active_statuses[0] if self.active_statuses else None)
        prop = await self._detect_property_type()
        properties: dict[str, Any] = {
            "Name": {"title": [{"text": {"content": title}}]},
        }
        if target_status:
            properties[self.status_property] = {prop: {"name": target_status}}
        await self.client.create_page(self.database_id, properties)
        await self.async_request_refresh()

    async def async_archive_done(self, archive_status: str = "Archive") -> None:
        """Move all completed (non-archive) items to the archive status."""
        if not self.data:
            return
        prop = await self._detect_property_type()
        done_items = [
            item for item in self.data["items"]
            if item["checked"] and item["status"] != archive_status
        ]
        for item in done_items:
            await self.client.update_page(
                item["id"],
                {self.status_property: {prop: {"name": archive_status}}},
            )
        if done_items:
            await self.async_request_refresh()

    async def async_delete_item(self, page_id: str) -> None:
        """Archive a page (soft-delete)."""
        await self.client.archive_page(page_id)
        await self.async_request_refresh()

    async def _detect_property_type(self) -> str:
        """Return 'select' or 'status' for the status property."""
        try:
            db = await self.client.get_database(self.database_id)
            prop = db.get("properties", {}).get(self.status_property, {})
            return prop.get("type", "select")
        except Exception:
            return "select"
