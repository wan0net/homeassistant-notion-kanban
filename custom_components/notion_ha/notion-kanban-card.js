/**
 * notion-kanban-card — Custom Lovelace card for Notion task databases.
 *
 * Reads from the notion_ha sensor entity and calls notion_ha services for write-back.
 * Supports drag-and-drop and click-to-move between columns.
 *
 * Config:
 *   type: custom:notion-kanban-card
 *   entity: sensor.my_notion_kanban        # required
 *   title: My Tasks                        # optional, default = entity friendly name
 *   hide_sections: [Archive]               # optional, default = ["Archive"]
 *   archive_all_section: Done              # optional, column that shows Archive All button
 *
 * MIT License — AI-generated with Claude
 */

/* ---------- Notion colour palette ---------------------------------------- */
const NOTION_COLOR = {
  default: "var(--secondary-text-color)",
  gray:    "#9B9B9B",
  brown:   "#A07850",
  orange:  "#E07B39",
  yellow:  "#C9A227",
  green:   "#4CAF50",
  blue:    "#2196F3",
  purple:  "#9C27B0",
  pink:    "#E91E8C",
  red:     "#F44336",
};
const NOTION_BG = {
  default: "rgba(150,150,150,0.15)",
  gray:    "rgba(155,155,155,0.18)",
  brown:   "rgba(160,120,80,0.18)",
  orange:  "rgba(224,123,57,0.18)",
  yellow:  "rgba(201,162,39,0.18)",
  green:   "rgba(76,175,80,0.18)",
  blue:    "rgba(33,150,243,0.18)",
  purple:  "rgba(156,39,176,0.18)",
  pink:    "rgba(233,30,140,0.18)",
  red:     "rgba(244,67,54,0.18)",
};

/* ---------- Static CSS (no user content) ---------------------------------- */
const CSS = `
:host {
  display: block;
  width: 100%;
  box-sizing: border-box;
}
.root {
  background: var(--ha-card-background, var(--card-background-color, #fff));
  border-radius: var(--ha-card-border-radius, 12px);
  box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,.12));
  padding: 16px;
  overflow: hidden;
  width: 100%;
  box-sizing: border-box;
}
.header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 14px;
}
.header-title {
  font-size: 1.1rem; font-weight: 600; color: var(--primary-text-color);
  letter-spacing: 0.01em;
}
.header-count {
  font-size: 0.78rem; color: var(--secondary-text-color);
  background: var(--secondary-background-color, rgba(0,0,0,0.06));
  padding: 2px 8px; border-radius: 10px;
}
.board {
  display: flex; gap: 12px; overflow-x: auto; padding-bottom: 6px;
  scrollbar-width: thin;
  scrollbar-color: var(--divider-color, #e0e0e0) transparent;
  align-items: flex-start;
  width: 100%;
  box-sizing: border-box;
}
.board::-webkit-scrollbar { height: 5px; }
.board::-webkit-scrollbar-thumb {
  background: var(--divider-color, #e0e0e0); border-radius: 3px;
}
.col {
  flex: 1 1 180px; min-width: 160px;
  background: var(--secondary-background-color, rgba(0,0,0,0.04));
  border-radius: 10px; padding: 10px 8px;
  transition: background 0.15s;
}
.col.drag-over {
  background: rgba(var(--rgb-primary-color, 3,169,244), 0.12);
  outline: 2px dashed var(--primary-color, #03a9f4);
  outline-offset: -2px;
}
.col-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px; padding: 0 2px;
}
.col-title {
  font-size: 0.8rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.06em; color: var(--secondary-text-color);
}
.col-count {
  font-size: 0.72rem; color: var(--disabled-text-color, #aaa);
  background: rgba(0,0,0,0.06); padding: 1px 6px; border-radius: 8px;
}
.col-actions { display: flex; gap: 4px; align-items: center; }
.btn-archive-all {
  font-size: 0.68rem; padding: 3px 7px; border-radius: 6px;
  border: 1px solid var(--divider-color, #e0e0e0);
  background: var(--card-background-color, #fff);
  color: var(--secondary-text-color); cursor: pointer; white-space: nowrap;
  transition: background 0.15s, color 0.15s;
}
.btn-archive-all:hover {
  background: var(--primary-color, #03a9f4); color: #fff;
  border-color: var(--primary-color, #03a9f4);
}
.item-list { display: flex; flex-direction: column; gap: 6px; min-height: 32px; }
.task-card {
  background: var(--ha-card-background, var(--card-background-color, #fff));
  border-radius: 8px; padding: 10px 10px 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,.07);
  cursor: grab;
  transition: box-shadow 0.15s, opacity 0.15s, transform 0.15s;
  border: 1.5px solid transparent; user-select: none;
}
.task-card:hover {
  box-shadow: 0 3px 10px rgba(0,0,0,.13);
  border-color: var(--primary-color, #03a9f4);
}
.task-card.dragging {
  opacity: 0.45; transform: rotate(1.5deg) scale(0.97); cursor: grabbing;
}
.task-card.checked .task-title {
  text-decoration: line-through; color: var(--disabled-text-color, #aaa);
}
.task-title { font-size: 0.88rem; color: var(--primary-text-color); line-height: 1.4; word-break: break-word; }
.task-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; margin-top: 6px; }
.label-chip {
  font-size: 0.68rem; padding: 2px 7px; border-radius: 10px;
  font-weight: 500; white-space: nowrap;
}
.due-date {
  font-size: 0.7rem; color: var(--secondary-text-color);
  display: flex; align-items: center; gap: 3px; margin-top: 2px;
}
.due-date.overdue { color: #F44336; font-weight: 600; }
.due-date.today   { color: #FF9800; font-weight: 600; }
.empty-col {
  font-size: 0.75rem; color: var(--disabled-text-color, #bbb);
  text-align: center; padding: 12px 0; font-style: italic;
}
.popup-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.35);
  z-index: 9998; display: flex; align-items: center; justify-content: center;
}
.popup {
  background: var(--ha-card-background, var(--card-background-color, #fff));
  border-radius: 14px; padding: 20px; min-width: 240px; max-width: 320px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.22); z-index: 9999;
}
.popup-label {
  font-size: 0.75rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.07em; color: var(--secondary-text-color); margin-bottom: 4px;
}
.popup-task-name {
  font-size: 0.95rem; font-weight: 600; color: var(--primary-text-color);
  margin-bottom: 14px; word-break: break-word;
}
.popup-sections { display: flex; flex-direction: column; gap: 6px; }
.popup-section-btn {
  padding: 9px 14px; border-radius: 8px;
  border: 1.5px solid var(--divider-color, #e0e0e0);
  background: transparent; color: var(--primary-text-color);
  text-align: left; font-size: 0.88rem; cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.popup-section-btn:hover {
  background: rgba(var(--rgb-primary-color, 3,169,244), 0.1);
  border-color: var(--primary-color, #03a9f4);
}
.popup-section-btn.current {
  background: rgba(var(--rgb-primary-color, 3,169,244), 0.15);
  border-color: var(--primary-color, #03a9f4); font-weight: 600;
}
.popup-cancel {
  margin-top: 10px; width: 100%; padding: 8px; border-radius: 8px;
  border: none; background: var(--secondary-background-color, rgba(0,0,0,0.06));
  color: var(--secondary-text-color); font-size: 0.85rem; cursor: pointer;
}
`;

/* ---------- DOM helpers (no innerHTML with user data) --------------------- */
function mk(tag, cls) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  return e;
}

function txt(text) {
  return document.createTextNode(String(text ?? ""));
}

function append(parent, ...children) {
  for (const c of children.flat()) {
    if (c != null) parent.appendChild(c instanceof Node ? c : txt(c));
  }
  return parent;
}

/* ---------- Card component ------------------------------------------------ */
class NotionKanbanCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass    = null;
    this._config  = {};
    this._drag    = null;
    this._popupCtx = null;
  }

  setConfig(config) {
    if (!config.entity) throw new Error("notion-kanban-card: 'entity' is required");
    this._config = {
      hide_sections:      ["Archive"],
      archive_all_section: "Done",
      ...config,
    };
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() { return 4; }

  /* ---- top-level render -------------------------------------------------- */
  _render() {
    if (!this._hass || !this._config.entity) return;

    const stateObj = this._hass.states[this._config.entity];
    const shadow   = this.shadowRoot;

    if (!stateObj) {
      shadow.replaceChildren();
      const style = mk("style");
      style.textContent = CSS;
      const root = mk("div", "root");
      root.style.color = "var(--error-color, red)";
      root.style.padding = "20px";
      root.textContent = "Entity not found: " + this._config.entity;
      shadow.append(style, root);
      return;
    }

    const attrs = stateObj.attributes || {};
    let sections = (attrs.sections || []).filter(
      (s) => !(this._config.hide_sections || []).includes(s.name)
    );

    // Apply custom column order if specified
    const order = this._config.column_order;
    if (order && order.length) {
      const idx = (s) => { const i = order.indexOf(s.name); return i === -1 ? 9999 : i; };
      sections = [...sections].sort((a, b) => idx(a) - idx(b));
    }
    const allItems   = attrs.items || [];
    const activeCount = allItems.filter((i) => !i.checked).length;
    const title = this._config.title
      || stateObj.attributes.friendly_name
      || this._config.entity;

    // Style node
    const style = mk("style");
    style.textContent = CSS;

    // Root card
    const root = mk("div", "root");

    // Header
    const header = mk("div", "header");
    const headerTitle = mk("span", "header-title");
    headerTitle.textContent = title;
    const headerCount = mk("span", "header-count");
    headerCount.textContent = activeCount + " active";
    append(header, headerTitle, headerCount);

    // Board
    const board = mk("div", "board");
    board.id = "board";
    for (const section of sections) {
      board.appendChild(this._buildColumn(section, allItems));
    }

    append(root, header, board);
    shadow.replaceChildren(style, root);
    this._attachEvents();
  }

  /* ---- build a column ---------------------------------------------------- */
  _buildColumn(section, allItems) {
    const items     = allItems.filter((i) => i.section_id === section.id);
    const isArchive = section.name === (this._config.archive_all_section || "Done");

    const col = mk("div", "col");
    col.dataset.sectionId   = section.id;
    col.dataset.sectionName = section.name;

    // Column header
    const colHeader = mk("div", "col-header");
    const colTitle  = mk("span", "col-title");
    colTitle.textContent = section.name;

    const colActions = mk("div", "col-actions");
    const colCount   = mk("span", "col-count");
    colCount.textContent = String(items.length);
    colActions.appendChild(colCount);

    if (isArchive) {
      const btn = mk("button", "btn-archive-all");
      btn.textContent = "Archive all";
      btn.dataset.action = "archive-all";
      colActions.appendChild(btn);
    }

    append(colHeader, colTitle, colActions);

    // Item list
    const list = mk("div", "item-list");
    list.dataset.sectionId = section.id;

    if (items.length === 0) {
      const empty = mk("div", "empty-col");
      empty.textContent = "Empty";
      list.appendChild(empty);
    } else {
      for (const item of items) {
        list.appendChild(this._buildTask(item));
      }
    }

    append(col, colHeader, list);
    return col;
  }

  /* ---- build a task card ------------------------------------------------- */
  _buildTask(item) {
    const card = mk("div", "task-card" + (item.checked ? " checked" : ""));
    card.draggable = true;
    card.dataset.itemId      = item.id;
    card.dataset.itemStatus  = item.status;
    card.dataset.itemContent = item.content;

    const titleEl = mk("div", "task-title");
    titleEl.textContent = item.content;
    card.appendChild(titleEl);

    const labels  = item.labels || [];
    const hasDue  = !!item.due?.date;
    const hasMeta = labels.length > 0 || hasDue;

    if (hasMeta) {
      const meta = mk("div", "task-meta");

      for (const label of labels) {
        const chip = mk("span", "label-chip");
        chip.textContent = label.name;
        chip.style.color      = NOTION_COLOR[label.color] || NOTION_COLOR.default;
        chip.style.background = NOTION_BG[label.color]    || NOTION_BG.default;
        meta.appendChild(chip);
      }

      if (hasDue) {
        meta.appendChild(this._buildDue(item.due.date));
      }

      card.appendChild(meta);
    }

    return card;
  }

  /* ---- due date badge ---------------------------------------------------- */
  _buildDue(dateStr) {
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const due   = new Date(dateStr); due.setHours(0, 0, 0, 0);
    const diff  = (due - today) / 86400000;

    const span = mk("span", "due-date");
    if (diff < 0)      { span.classList.add("overdue"); }
    else if (diff === 0) { span.classList.add("today"); }

    let label = dateStr;
    if (diff < 0)      label = dateStr + " (overdue)";
    else if (diff === 0) label = "Today";
    else if (diff === 1) label = "Tomorrow";

    append(span, "\uD83D\uDCC5 " + label);
    return span;
  }

  /* ---- events ------------------------------------------------------------ */
  _attachEvents() {
    const shadow = this.shadowRoot;

    shadow.querySelectorAll(".task-card").forEach((card) => {
      card.addEventListener("dragstart", (e) => {
        this._drag = {
          id:      card.dataset.itemId,
          status:  card.dataset.itemStatus,
          content: card.dataset.itemContent,
        };
        card.classList.add("dragging");
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/plain", card.dataset.itemId);
      });
      card.addEventListener("dragend", () => card.classList.remove("dragging"));

      card.addEventListener("click", () => {
        const attrs    = this._hass.states[this._config.entity]?.attributes || {};
        const sections = (attrs.sections || []).filter(
          (s) => !(this._config.hide_sections || []).includes(s.name)
        );
        this._openPopup(
          { id: card.dataset.itemId, status: card.dataset.itemStatus, content: card.dataset.itemContent },
          sections
        );
      });
    });

    shadow.querySelectorAll(".col").forEach((col) => {
      col.addEventListener("dragover", (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
        col.classList.add("drag-over");
      });
      col.addEventListener("dragleave", () => col.classList.remove("drag-over"));
      col.addEventListener("drop", (e) => {
        e.preventDefault();
        col.classList.remove("drag-over");
        if (!this._drag) return;
        const target = col.dataset.sectionName;
        if (target && target !== this._drag.status) {
          this._moveItem(this._drag.id, target);
        }
        this._drag = null;
      });
    });

    shadow.querySelectorAll("[data-action='archive-all']").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        this._hass.callService("notion_ha", "archive_done", {});
      });
    });
  }

  /* ---- popup ------------------------------------------------------------- */
  _openPopup(item, sections) {
    const overlay = mk("div", "popup-overlay");
    const popup   = mk("div", "popup");

    const label = mk("div", "popup-label");
    label.textContent = "Move to";

    const taskName = mk("div", "popup-task-name");
    taskName.textContent = item.content;

    const sectionList = mk("div", "popup-sections");
    for (const s of sections) {
      const btn = mk("button", "popup-section-btn" + (s.name === item.status ? " current" : ""));
      btn.textContent = s.name;
      btn.addEventListener("click", () => {
        if (s.name !== item.status) this._moveItem(item.id, s.name);
        overlay.remove();
      });
      sectionList.appendChild(btn);
    }

    const cancel = mk("button", "popup-cancel");
    cancel.textContent = "Cancel";
    cancel.addEventListener("click", () => overlay.remove());

    overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.remove(); });

    append(popup, label, taskName, sectionList, cancel);
    overlay.appendChild(popup);
    this.shadowRoot.appendChild(overlay);
  }

  /* ---- service call ------------------------------------------------------ */
  _moveItem(itemId, targetStatus) {
    this._hass.callService("notion_ha", "set_item_status", {
      item_id: itemId,
      status:  targetStatus,
    });
  }
}

customElements.define("notion-kanban-card", NotionKanbanCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type:        "notion-kanban-card",
  name:        "Notion Kanban Card",
  description: "Kanban board for Notion task databases via notion_ha integration.",
  preview:     false,
});
