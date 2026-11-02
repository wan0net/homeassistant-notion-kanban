"""Tests for registering the card as a Lovelace resource."""
from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

from custom_components.notion_ha import _CARD_URL, _ensure_lovelace_resource


@dataclass
class FakeLovelaceData:
    """Stands in for Home Assistant's LovelaceData, which has no .get()."""

    resources: object


def make_hass(resources) -> MagicMock:
    hass = MagicMock()
    hass.data = {"lovelace": FakeLovelaceData(resources=resources)}
    return hass


def make_resources(items: list[dict]) -> MagicMock:
    resources = MagicMock()
    resources.async_items = MagicMock(return_value=items)
    resources.async_create_item = AsyncMock()
    return resources


async def test_creates_resource_when_missing():
    resources = make_resources([])
    hass = make_hass(resources)

    await _ensure_lovelace_resource(hass, _CARD_URL)

    resources.async_create_item.assert_awaited_once_with(
        {"url": _CARD_URL, "res_type": "module"}
    )


async def test_skips_create_when_resource_exists():
    resources = make_resources([{"url": _CARD_URL, "res_type": "module"}])
    hass = make_hass(resources)

    await _ensure_lovelace_resource(hass, _CARD_URL)

    resources.async_create_item.assert_not_awaited()
