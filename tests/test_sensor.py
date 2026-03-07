"""Tests for the Notion kanban sensor."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.notion_ha.sensor import NotionKanbanSensor


SECTIONS = [
    {"id": "do_next", "name": "Do Next"},
    {"id": "doing", "name": "Doing"},
]

ITEMS = [
    {
        "id": "p1",
        "content": "Buy groceries",
        "status": "Do Next",
        "section_id": "do_next",
        "due_date": "2026-03-06",
        "checked": False,
        "labels": [],
    },
    {
        "id": "p2",
        "content": "Old task",
        "status": "Done",
        "section_id": "done",
        "due_date": None,
        "checked": True,
        "labels": [],
    },
]


_SENTINEL = object()


def make_sensor(data=_SENTINEL):
    coordinator = MagicMock()
    coordinator.data = {"sections": SECTIONS, "items": ITEMS} if data is _SENTINEL else data

    entry = MagicMock()
    entry.entry_id = "test-entry-id"
    entry.title = "Personal To-Do"

    sensor = NotionKanbanSensor(coordinator, entry)
    return sensor


def test_native_value_counts_active_only():
    sensor = make_sensor()
    assert sensor.native_value == 1  # only p1 is active


def test_native_value_no_data():
    sensor = make_sensor(data=None)
    assert sensor.native_value == 0


def test_attributes_includes_all_items():
    sensor = make_sensor()
    attrs = sensor.extra_state_attributes
    item_ids = [i["id"] for i in attrs["items"]]
    assert "p1" in item_ids
    assert "p2" in item_ids


def test_attributes_section_id_format():
    sensor = make_sensor()
    attrs = sensor.extra_state_attributes
    item = attrs["items"][0]
    assert item["section_id"] == "do_next"


def test_attributes_due_date_structure():
    sensor = make_sensor()
    attrs = sensor.extra_state_attributes
    item = attrs["items"][0]
    assert item["due"] == {"date": "2026-03-06"}


def test_attributes_no_due_date():
    items = [
        {
            "id": "p1",
            "content": "No due",
            "status": "Do Next",
            "section_id": "do_next",
            "due_date": None,
            "checked": False,
            "labels": [],
        }
    ]
    sensor = make_sensor(data={"sections": SECTIONS, "items": items})
    attrs = sensor.extra_state_attributes
    assert attrs["items"][0]["due"] is None


def test_attributes_sections_passthrough():
    sensor = make_sensor()
    attrs = sensor.extra_state_attributes
    assert attrs["sections"] == SECTIONS


def test_attributes_project_stub():
    sensor = make_sensor()
    attrs = sensor.extra_state_attributes
    assert attrs["project"]["name"] == "Personal To-Do"
