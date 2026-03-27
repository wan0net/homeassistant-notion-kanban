# Notion Kanban

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](LICENSE)
[![AI Generated](https://img.shields.io/badge/AI%20Generated-Claude-blueviolet)](https://claude.ai)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=wan0net&repository=homeassistant-notion-kanban&category=integration)

<p align="center"><strong>Turn any Notion database into a kanban board and todo list in Home Assistant</strong><br>Drag-and-drop columns, label chips, due dates, and real-time sync back to Notion.</p>

<p align="center">
<a href="#why-notion-kanban">Why</a> &bull;
<a href="#how-it-works">How It Works</a> &bull;
<a href="#getting-started">Getting Started</a> &bull;
<a href="#lovelace-card">Lovelace Card</a> &bull;
<a href="#entities">Entities</a> &bull;
<a href="#services">Services</a> &bull;
<a href="#development">Development</a>
</p>

---

> **Status:** Active. Tested on Home Assistant 2024.1+. Multiple databases supported as separate config entries.

## Why Notion Kanban

Notion is a capable project tracker, but Home Assistant has no native way to surface or interact with Notion data on dashboards. This integration bridges that gap: it pulls your Notion database into HA as a structured sensor and a standard todo entity, then provides a custom Lovelace card that lets you drag tasks between columns and check them off — all writing back to Notion in real time.

If you already manage tasks in Notion and want them visible (and actionable) on your HA dashboard without leaving either tool, this is the integration for you.

## How It Works

```
Notion API
    |
    v
HA Integration (coordinator)
    |-- polls every 5 min (configurable)
    |-- disk cache for instant restart load
    |
    +-- Sensor entity  (sensor.<db>_kanban)
    |       state: active item count
    |       attributes: sections, items, labels, due dates
    |
    +-- Todo entity    (todo.<db>)
            standard HA todo — create, rename, complete, delete
            all writes sync back to Notion immediately

Lovelace Card  (notion-kanban-card)
    reads sensor.<db>_kanban
    drag-and-drop columns → calls notion_ha.set_item_status
    auto-registered as a resource on integration setup
```

## Features

- **Todo list entity** — create, update, and check off tasks; all changes write back to Notion instantly
- **Kanban sensor** — structured data for the included kanban card
- **`notion-kanban-card`** — built-in Lovelace card with drag-and-drop, click-to-move popup, label chips with Notion colours, due dates, and an Archive All button
- **Disk cache** — instant load on HA restart, graceful fallback on API errors
- Works with any Notion database that has a `select` or `status` property
- Configurable active/completed statuses and custom column order
- Configurable poll interval (default 5 min)
- Supports multiple databases as separate config entries

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.<db>_kanban` | Sensor | State: active item count. Attributes: sections, items, labels, due dates |
| `todo.<db>` | Todo | Standard HA todo entity with full CRUD — create, rename, complete, delete |

The entity name is derived from your database name. If your database is "Personal To-Do", the sensor is `sensor.personal_to_do_kanban`.

## Services

| Service | Fields | Description |
|---------|--------|-------------|
| `notion_ha.set_item_status` | `item_id`, `status` | Set the status of a Notion page |
| `notion_ha.archive_done` | `archive_status` (optional, default `Archive`) | Move all completed items to archive |

## Lovelace Card

The card auto-registers on setup. Add it to a dashboard — best in a **Panel** view for full-width layout:

```yaml
type: custom:notion-kanban-card
entity: sensor.my_notion_kanban
title: My Tasks                     # optional
hide_sections:                      # optional (default: [Archive])
  - Archive
archive_all_section: Done           # optional, shows Archive All button
column_order:                       # optional, custom left-to-right order
  - On Hold
  - Do Next
  - Doing
  - Done
```

**Interaction:**

- **Drag a card** between columns — moves instantly (optimistic), Notion updates in the background
- **Click a card** — popup to move to any column without dragging
- **Archive All** button moves all completed items to the archive status

## Options

| Option | Default | Description |
|--------|---------|-------------|
| Poll interval | 300s | How often to sync from Notion |

## Limitations

- Image attachments on Notion pages are not fetched
- Notion API rate limit: 3 req/s — increase poll interval for large databases

## Getting Started

### Requirements

- Home Assistant 2024.1+
- A [Notion internal integration](https://www.notion.so/my-integrations) token with access to your database

### HACS (Recommended)

1. Open HACS → Integrations → three-dot menu → **Custom repositories**
2. Add `wan0net/homeassistant-notion-kanban` as **Integration**
3. Download and restart Home Assistant

The integration automatically registers `notion-kanban-card` as a Lovelace resource — no manual resource steps needed.

### Manual

Copy `custom_components/notion_ha/` to your HA `custom_components/` directory and restart.

### Setup

1. Create a [Notion internal integration](https://www.notion.so/my-integrations) and copy the API key
2. Share your database with the integration in Notion (database → `...` menu → Connections)
3. In HA: **Settings → Integrations → Add → Notion Kanban**
4. Paste the API key, then the database URL or ID
5. Select the status property and configure which values are active vs completed

## Development

```bash
pip install -r requirements-dev.txt
pytest
```

This integration was generated by [Claude](https://claude.ai) (Anthropic) and validated by the maintainer. All code, tests, and the Lovelace card were authored by AI with human review and testing.

## License

BSD-3-Clause — see [LICENSE](LICENSE).
