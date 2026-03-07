"""Tests for coordinator data transformation and write-back helpers."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.notion_ha.coordinator import transform_pages
from .conftest import MOCK_DATABASE_ID, make_page


ACTIVE = ["Do Next", "Doing", "To Do Soon", "On Hold", "Long Term"]
COMPLETED = ["Done", "Archive"]


def transform(pages):
    return transform_pages(pages, "Status", ACTIVE, COMPLETED)


# --- transform_pages (pure function, no HA needed) ---

def test_transform_filters_archived():
    pages = [
        make_page("p1", "Active task", "Do Next"),
        make_page("p2", "Archived", "Done", archived=True),
    ]
    data = transform(pages)
    ids = [i["id"] for i in data["items"]]
    assert "p1" in ids
    assert "p2" not in ids


def test_transform_includes_completed():
    pages = [
        make_page("p1", "Active", "Do Next"),
        make_page("p2", "Done task", "Done"),
    ]
    data = transform(pages)
    items = {i["id"]: i for i in data["items"]}
    assert items["p1"]["checked"] is False
    assert items["p2"]["checked"] is True


def test_transform_sections_from_all_statuses():
    data = transform([])
    section_names = [s["name"] for s in data["sections"]]
    assert section_names == ACTIVE + COMPLETED


def test_transform_section_ids_slugified():
    data = transform([])
    section_ids = [s["id"] for s in data["sections"]]
    assert "do_next" in section_ids
    assert "to_do_soon" in section_ids


def test_transform_due_date():
    pages = [make_page("p1", "Task", "Do Next", due="2026-03-06")]
    data = transform(pages)
    assert data["items"][0]["due_date"] == "2026-03-06"


def test_transform_no_due_date():
    pages = [make_page("p1", "Task", "Do Next")]
    data = transform(pages)
    assert data["items"][0]["due_date"] is None


def test_transform_unknown_status_excluded():
    pages = [make_page("p1", "Task", "Some Random Status")]
    data = transform(pages)
    assert data["items"] == []


def test_transform_empty_pages():
    data = transform([])
    assert data["items"] == []
    assert len(data["sections"]) == len(ACTIVE) + len(COMPLETED)


def test_transform_content_extracted():
    pages = [make_page("p1", "Buy groceries", "Do Next")]
    data = transform(pages)
    assert data["items"][0]["content"] == "Buy groceries"


def test_transform_url_included():
    pages = [make_page("p1", "Task", "Do Next")]
    data = transform(pages)
    assert "notion.so" in data["items"][0]["url"]


# --- Write-back helpers (test via mocked client, no real coordinator needed) ---

@pytest.mark.asyncio
async def test_write_back_set_status():
    """Coordinator.async_set_status calls update_page with correct payload."""
    from custom_components.notion_ha.coordinator import NotionTodoCoordinator

    client = MagicMock()
    client.get_database = AsyncMock(
        return_value={"properties": {"Status": {"type": "select"}}}
    )
    client.update_page = AsyncMock(return_value={})

    # Instantiate without calling super().__init__ to avoid HA setup requirement
    coord = object.__new__(NotionTodoCoordinator)
    coord.client = client
    coord.database_id = MOCK_DATABASE_ID
    coord.status_property = "Status"
    coord.active_statuses = ACTIVE
    coord.completed_statuses = COMPLETED
    coord.async_request_refresh = AsyncMock()

    await coord.async_set_status("page-1", "Done")

    client.update_page.assert_called_once_with(
        "page-1", {"Status": {"select": {"name": "Done"}}}
    )
    coord.async_request_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_write_back_create_item():
    """Coordinator.async_create_item creates page with correct title and status."""
    from custom_components.notion_ha.coordinator import NotionTodoCoordinator

    client = MagicMock()
    client.get_database = AsyncMock(
        return_value={"properties": {"Status": {"type": "select"}}}
    )
    client.create_page = AsyncMock(return_value={})

    coord = object.__new__(NotionTodoCoordinator)
    coord.client = client
    coord.database_id = MOCK_DATABASE_ID
    coord.status_property = "Status"
    coord.active_statuses = ACTIVE
    coord.completed_statuses = COMPLETED
    coord.async_request_refresh = AsyncMock()

    await coord.async_create_item("New task")

    call_args = client.create_page.call_args[0]
    props = call_args[1]
    assert props["Name"]["title"][0]["text"]["content"] == "New task"
    assert props["Status"]["select"]["name"] == ACTIVE[0]


@pytest.mark.asyncio
async def test_write_back_delete_item():
    """Coordinator.async_delete_item archives the page."""
    from custom_components.notion_ha.coordinator import NotionTodoCoordinator

    client = MagicMock()
    client.archive_page = AsyncMock(return_value={})

    coord = object.__new__(NotionTodoCoordinator)
    coord.client = client
    coord.database_id = MOCK_DATABASE_ID
    coord.status_property = "Status"
    coord.active_statuses = ACTIVE
    coord.completed_statuses = COMPLETED
    coord.async_request_refresh = AsyncMock()

    await coord.async_delete_item("page-1")

    client.archive_page.assert_called_once_with("page-1")
