from math import ceil

from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.stack import Stack

from shared.mixins import PopoverMixin
from shared.widget_container import ButtonWidget
from utils.widget_utils import nerd_font_icon

_DEFAULT_GROUPS = [
    {
        "title": "Session",
        "entries": [
            {"keys": "SUPER + Q", "description": "Close active window"},
            {"keys": "SUPER + M", "description": "Exit Hyprland session"},
            {"keys": "SUPER + SHIFT + E", "description": "Power menu"},
            {"keys": "SUPER + SHIFT + R", "description": "Reload config"},
        ],
    },
    {
        "title": "Apps",
        "entries": [
            {"keys": "SUPER + Return", "description": "Terminal"},
            {"keys": "SUPER + D", "description": "App launcher"},
            {"keys": "SUPER + E", "description": "File manager"},
            {"keys": "SUPER + B", "description": "Browser"},
        ],
    },
    {
        "title": "Windows",
        "entries": [
            {"keys": "SUPER + H/J/K/L", "description": "Focus window"},
            {"keys": "SUPER + SHIFT + H/J/K/L", "description": "Move window"},
            {"keys": "SUPER + F", "description": "Toggle fullscreen"},
            {"keys": "SUPER + V", "description": "Toggle floating"},
        ],
    },
    {
        "title": "Layout",
        "entries": [
            {"keys": "SUPER + P", "description": "Pseudo tiling"},
            {"keys": "SUPER + J", "description": "Split toggle"},
            {"keys": "SUPER + S", "description": "Toggle special workspace"},
            {
                "keys": "SUPER + SHIFT + S",
                "description": "Move to special workspace",
            },
        ],
    },
    {
        "title": "Workspaces",
        "entries": [
            {"keys": "SUPER + [1..0]", "description": "Switch workspace"},
            {
                "keys": "SUPER + SHIFT + [1..0]",
                "description": "Move window to workspace",
            },
            {"keys": "SUPER + Mouse Wheel", "description": "Cycle workspace"},
        ],
    },
    {
        "title": "System",
        "entries": [
            {"keys": "SUPER + PRINT", "description": "Area screenshot"},
            {"keys": "PRINT", "description": "Full screenshot"},
            {"keys": "XF86AudioRaiseVolume", "description": "Volume up"},
            {"keys": "XF86AudioLowerVolume", "description": "Volume down"},
        ],
    },
]


class CheatSheetMenu(Box):
    """Popover content that renders grouped Hyprland keybinds."""

    def __init__(self, parent=None, config=None, **kwargs):
        super().__init__(
            name="cheatsheet-menu",
            orientation="v",
            spacing=12,
            h_expand=True,
            **kwargs,
        )

        self._parent = parent
        self.config = config or {}

        self.columns = max(1, int(self.config.get("columns", 3)))
        self.groups_per_page = max(1, int(self.config.get("groups_per_page", 6)))
        self.max_entries_per_group = max(
            1, int(self.config.get("max_entries_per_group", 8))
        )

        self.groups = self._normalize_groups(self.config.get("groups", _DEFAULT_GROUPS))
        self.current_page = 0
        self.total_pages = max(1, ceil(len(self.groups) / self.groups_per_page))

        self.title = Label(
            name="cheatsheet-title",
            style_classes=["cheatsheet-title"],
            label=self.config.get("title", "Hyprland Cheatsheet"),
            h_align="start",
        )

        self.stack = Stack(
            name="cheatsheet-stack",
            orientation="v",
            transition_type="slide-left-right",
            transition_duration=180,
            h_expand=True,
            v_expand=True,
        )

        self.prev_button = Button(
            name="cheatsheet-nav-btn",
            style_classes=["cheatsheet-nav-btn"],
            child=Label(
                name="cheatsheet-nav-icon",
                style_classes=["cheatsheet-nav-icon"],
                label="<",
            ),
            on_clicked=lambda *_: self._change_page(-1),
        )
        self.next_button = Button(
            name="cheatsheet-nav-btn",
            style_classes=["cheatsheet-nav-btn"],
            child=Label(
                name="cheatsheet-nav-icon",
                style_classes=["cheatsheet-nav-icon"],
                label=">",
            ),
            on_clicked=lambda *_: self._change_page(1),
        )
        self.page_label = Label(
            name="cheatsheet-page-label",
            style_classes=["cheatsheet-page-label"],
            label="1/1",
        )

        self.pagination = Box(
            name="cheatsheet-pagination",
            style_classes=["cheatsheet-pagination"],
            orientation="h",
            spacing=12,
            h_align="center",
            children=[self.prev_button, self.page_label, self.next_button],
        )

        self.children = [self.title, self.stack, self.pagination]

        self._build_pages()

    def _normalize_groups(self, raw_groups):
        groups = []
        if not isinstance(raw_groups, list):
            raw_groups = _DEFAULT_GROUPS

        for group in raw_groups:
            if not isinstance(group, dict):
                continue
            title = str(group.get("title", "Group")).strip()
            entries = group.get("entries", [])
            if not isinstance(entries, list):
                continue

            parsed_entries = []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                keys = str(entry.get("keys", "")).strip()
                description = str(entry.get("description", "")).strip()
                if keys and description:
                    parsed_entries.append({"keys": keys, "description": description})

            if parsed_entries:
                groups.append({"title": title or "Group", "entries": parsed_entries})

        return groups or _DEFAULT_GROUPS

    def _build_pages(self):
        self.stack.children = []

        for page_index in range(self.total_pages):
            start = page_index * self.groups_per_page
            end = start + self.groups_per_page
            page_groups = self.groups[start:end]

            page = Box(
                name="cheatsheet-page",
                style_classes=["cheatsheet-page"],
                orientation="v",
                spacing=12,
            )

            for row_start in range(0, len(page_groups), self.columns):
                row_groups = page_groups[row_start : row_start + self.columns]
                row = Box(
                    name="cheatsheet-row",
                    style_classes=["cheatsheet-row"],
                    orientation="h",
                    spacing=12,
                    h_expand=True,
                )

                for group in row_groups:
                    row.add(self._build_group(group))

                for _ in range(self.columns - len(row_groups)):
                    row.add(
                        Box(
                            name="cheatsheet-group-placeholder",
                            style_classes=["cheatsheet-group-placeholder"],
                            h_expand=True,
                        )
                    )

                page.add(row)

            self.stack.add_named(page, f"page-{page_index}")

        self._set_page(0)

    def _build_group(self, group):
        box = Box(
            name="cheatsheet-group",
            style_classes=["cheatsheet-group"],
            orientation="v",
            spacing=8,
            h_expand=True,
        )
        box.add(
            Label(
                name="cheatsheet-group-title",
                style_classes=["cheatsheet-group-title"],
                label=group["title"],
                h_align="start",
            )
        )

        entries = group["entries"]
        shown_entries = entries[: self.max_entries_per_group]
        for entry in shown_entries:
            row = Box(
                name="cheatsheet-entry",
                style_classes=["cheatsheet-entry"],
                orientation="h",
                spacing=10,
            )
            row.add(
                Label(
                    name="cheatsheet-key",
                    style_classes=["cheatsheet-key"],
                    label=entry["keys"],
                    h_align="start",
                )
            )
            row.add(
                Label(
                    name="cheatsheet-description",
                    style_classes=["cheatsheet-description"],
                    label=entry["description"],
                    h_align="start",
                    h_expand=True,
                )
            )
            box.add(row)

        if len(entries) > self.max_entries_per_group:
            box.add(
                Label(
                    name="cheatsheet-more",
                    style_classes=["cheatsheet-more"],
                    label=f"+{len(entries) - self.max_entries_per_group} more",
                    h_align="start",
                )
            )

        return box

    def _set_page(self, page_index):
        if page_index < 0 or page_index >= self.total_pages:
            return

        self.current_page = page_index
        self.stack.set_visible_child_name(f"page-{self.current_page}")
        self.page_label.set_label(f"{self.current_page + 1}/{self.total_pages}")
        self._update_nav_state()

    def _change_page(self, delta):
        self._set_page(self.current_page + delta)

    def _update_nav_state(self):
        is_first = self.current_page == 0
        is_last = self.current_page >= self.total_pages - 1

        self.prev_button.set_sensitive(not is_first)
        self.next_button.set_sensitive(not is_last)

        if is_first:
            self.prev_button.add_style_class("disabled")
        else:
            self.prev_button.remove_style_class("disabled")

        if is_last:
            self.next_button.add_style_class("disabled")
        else:
            self.next_button.remove_style_class("disabled")

    def close(self, *_):
        if self._parent is not None:
            self._parent.hide_popover()


class CheatSheetWidget(ButtonWidget, PopoverMixin):
    """Panel widget that opens Hyprland keybind cheatsheet popover."""

    def __init__(self, **kwargs):
        super().__init__(name="cheatsheet", **kwargs)

        self.container_box.add(
            nerd_font_icon(
                icon=self.config.get("icon", "󰌌"),
                props={"style_classes": ["panel-font-icon"]},
            )
        )

        if self.config.get("label", True):
            self.container_box.add(
                Label(
                    label=self.config.get("label_text", "Keys"),
                    style_classes=["panel-text"],
                )
            )

        if self.config.get("tooltip", True) and self.tooltips_enabled:
            self.set_tooltip_text("Hyprland keybind cheatsheet")

        self.setup_popover(lambda: CheatSheetMenu(parent=self, config=self.config))
