import json
import shlex

from fabric.utils import (
    GLib,
    exec_shell_command,
    invoke_repeater,
    logger,
    remove_handler,
)
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.label import Label

from shared.buttons import HoverButton
from shared.list import ListBox
from shared.mixins import PopoverMixin
from shared.widget_container import ButtonWidget
from utils.widget_utils import nerd_font_icon


class USBManagerMenu(Box):
    """Popover content for managing removable USB drives."""

    def __init__(self, parent=None, config=None, **kwargs):
        super().__init__(
            name="usb-manager-menu",
            orientation="v",
            spacing=8,
            h_expand=True,
            **kwargs,
        )

        self._parent = parent
        self.config = config or {}
        self.devices = []
        self._refresh_timer_id = 0

        self.title = Label(
            label="USB Manager",
            h_align="start",
            name="usb-manager-title",
            style_classes=["panel-text"],
        )

        self.title_icon = nerd_font_icon(
            icon="󰕓",
            props={"style_classes": ["panel-font-icon", "title-icon"]},
        )

        self.refresh_button = HoverButton(
            name="usb-manager-refresh",
            style_classes=["usb-manager-btn"],
            child=nerd_font_icon(
                icon="",
                props={"style_classes": ["panel-font-icon"]},
            ),
            tooltip_text="Refresh",
            on_clicked=self.refresh_devices,
        )

        header = CenterBox(
            name="usb-manager-header",
            orientation="h",
            h_expand=True,
            start_children=[self.title_icon, self.title],
            end_children=[self.refresh_button],
        )

        self.device_list = ListBox(
            name="usb-manager-list",
            orientation="v",
            spacing=6,
            h_expand=True,
            v_expand=True,
        )

        self.unmount_all_button = HoverButton(
            name="usb-manager-unmount-all",
            style_classes=["usb-manager-btn"],
            child=Label(
                label="Unmount All",
                style_classes=["panel-text", "operation-all"],
            ),
            on_clicked=self.unmount_all,
        )
        self.eject_all_button = HoverButton(
            name="usb-manager-eject-all",
            style_classes=["usb-manager-btn"],
            child=Label(
                label="Mount All",
                style_classes=["panel-text", "operation-all"],
            ),
            on_clicked=self.eject_all,
        )

        footer = CenterBox(
            name="usb-manager-footer",
            orientation="h",
            spacing=8,
            start_children=[self.unmount_all_button],
            end_children=[self.eject_all_button],
        )

        self.children = [header, self.device_list, footer]

        if self.config.get("auto_refresh", True):
            interval_ms = max(1000, int(self.config.get("refresh_interval", 5) * 1000))
            self._refresh_timer_id = invoke_repeater(interval_ms, self._on_refresh_tick)

        self.connect("destroy", self._on_destroy)
        self.refresh_devices()

    def _update_footer_buttons(self):
        mounted_count = sum(1 for device in self.devices if device.get("mountpoint"))
        parent_paths = {
            device.get("parent_path")
            for device in self.devices
            if device.get("parent_path")
        }

        self.unmount_all_button.set_sensitive(mounted_count > 0)
        self.eject_all_button.set_sensitive(bool(parent_paths))

    def _on_refresh_tick(self, *_):
        self.refresh_devices()
        return True

    def _on_destroy(self, *_):
        if self._refresh_timer_id:
            remove_handler(self._refresh_timer_id)
            self._refresh_timer_id = 0

    def close(self, *_):
        if self._parent:
            self._parent.hide_popover()

    def _is_usb_disk(self, node: dict) -> bool:
        return node.get("type") == "disk" and (
            str(node.get("tran", "")).lower() == "usb"
            or bool(node.get("rm"))
            or bool(node.get("hotplug"))
        )

    @staticmethod
    def _is_mountable(node: dict) -> bool:
        return bool(node.get("path")) and bool(node.get("fstype"))

    def _collect_usb_partitions(self, blockdevices: list[dict]) -> list[dict]:
        devices: list[dict] = []

        def walk(node: dict, parent_usb_disk: dict | None = None):
            active_parent = parent_usb_disk
            if self._is_usb_disk(node):
                active_parent = node

            if active_parent and self._is_mountable(node):
                devices.append(
                    {
                        "name": node.get("name", "unknown"),
                        "path": node.get("path", ""),
                        "size": node.get("size", "?"),
                        "fstype": str(node.get("fstype", "")).upper(),
                        "label": node.get("label") or "",
                        "mountpoint": node.get("mountpoint") or "",
                        "parent_path": active_parent.get("path", node.get("path", "")),
                        "parent_name": active_parent.get("name", node.get("name", "")),
                    }
                )

            for child in node.get("children", []) or []:
                walk(child, active_parent)

        for entry in blockdevices:
            walk(entry, None)

        return devices

    def refresh_devices(self, *_):
        try:
            output = exec_shell_command(
                (
                    "lsblk -J -o NAME,PATH,TYPE,SIZE,FSTYPE,"
                    "LABEL,MOUNTPOINT,RM,HOTPLUG,TRAN"
                )
            )

        except Exception as err:
            logger.warning(f"[USBManager] lsblk command failed: {err}")
            output = ""

        self._on_lsblk_ready(output)

    def _on_lsblk_ready(self, output: str):
        parsed = self._parse_lsblk_output(output)

        if parsed is None:
            self.devices = []
            self._render_devices(error_message="USB scan unavailable")
            self._update_footer_buttons()
            if self._parent:
                self._parent.update_device_count(0)
            return

        blockdevices = parsed.get("blockdevices", [])
        self.devices = self._collect_usb_partitions(blockdevices)

        self._render_devices()
        self._update_footer_buttons()
        if self._parent:
            self._parent.update_device_count(len(self.devices))

    @staticmethod
    def _parse_lsblk_output(output: str) -> dict | None:
        text = (output or "").strip()
        if not text:
            return None

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as err:
            logger.warning(f"[USBManager] lsblk output not JSON: {err}")
            return None

        if not isinstance(parsed, dict):
            return None
        return parsed

    def _render_devices(self, error_message: str | None = None):
        self.device_list.remove_all()

        if error_message:
            self.device_list.add(
                Label(
                    label=error_message,
                    style_classes=["panel-text", "usb-manager-status"],
                    h_align="start",
                )
            )
            return

        if not self.devices:
            self.device_list.add(
                Label(
                    label="No removable USB drives detected",
                    style_classes=["panel-text", "usb-manager-status"],
                    h_align="start",
                )
            )
            return

        for device in self.devices:
            self.device_list.add(self._build_device_row(device))

    def _build_device_row(self, device: dict) -> Box:
        mounted = bool(device.get("mountpoint"))
        action_label = "Unmount" if mounted else "Mount"

        title = Label(
            label=device.get("name", "unknown"),
            h_align="start",
            name="usb-manager-device-title",
            style_classes=["panel-text"],
        )

        details_parts = [device.get("size", "?"), device.get("fstype", "")]
        if device.get("label"):
            details_parts.append(device.get("label"))

        details = Label(
            label=" • ".join([part for part in details_parts if part]),
            h_align="start",
            style_classes=["panel-text"],
        )

        action_button = Button(
            name="usb-manager-action",
            style_classes=["usb-manager-btn"],
            label=action_label,
            on_clicked=(
                (lambda *_, d=device: self.unmount_device(d))
                if mounted
                else (lambda *_, d=device: self.mount_device(d))
            ),
        )

        icon = nerd_font_icon(
            icon="󰕓",
            props={"style_classes": ["panel-font-icon"]},
        )

        header = Box(
            name="usb-manager-item-header",
            orientation="h",
            h_expand=True,
            children=[icon, title],
        )

        row_children = [header, details, action_button]

        return Box(
            name="usb-manager-item",
            orientation="v",
            spacing=4,
            children=row_children,
        )

    def _run_command(self, command: str):
        try:
            exec_shell_command(command)
        except Exception as err:
            logger.warning(f"[USBManager] command failed: {err}")

        self._on_action_done()

    def _on_action_done(self, *_):
        GLib.timeout_add(250, self._refresh_after_action)

    def _refresh_after_action(self):
        self.refresh_devices()
        return False

    def mount_device(self, device: dict):
        path = device.get("path")
        if path:
            self._run_command(f"udisksctl mount -b {shlex.quote(path)}")

    def unmount_device(self, device: dict):
        path = device.get("path")
        if path:
            self._run_command(f"udisksctl unmount -b {shlex.quote(path)}")

    def eject_device(self, device: dict):
        path = device.get("parent_path") or device.get("path")
        if path:
            self._run_command(f"udisksctl power-off -b {shlex.quote(path)}")

    def unmount_all(self, *_):
        mounted_paths = [
            shlex.quote(device["path"])
            for device in self.devices
            if device.get("mountpoint") and device.get("path")
        ]
        if not mounted_paths:
            return

        command = " && ".join(
            [f"udisksctl unmount -b {path}" for path in mounted_paths]
        )
        self._run_command(command)

    def eject_all(self, *_):
        parent_paths = {
            shlex.quote(device["parent_path"])
            for device in self.devices
            if device.get("parent_path")
        }
        if not parent_paths:
            return

        command = " && ".join(
            [f"udisksctl power-off -b {path}" for path in sorted(parent_paths)]
        )
        self._run_command(command)


class USBManagerWidget(ButtonWidget, PopoverMixin):
    """A panel widget for mounting and ejecting USB drives."""

    def __init__(self, **kwargs):
        super().__init__(name="usb_manager", **kwargs)

        self.container_box.add(
            nerd_font_icon(
                icon=self.config.get("icon", ""),
                props={"style_classes": ["panel-font-icon"]},
            )
        )

        if self.config.get("label", False):
            self.container_box.add(Label(label="USB", style_classes=["panel-text"]))

        if self.config.get("tooltip", True) and self.tooltips_enabled:
            self.set_tooltip_text("USB Manager")

        self.setup_popover(lambda: USBManagerMenu(parent=self, config=self.config))

    def update_device_count(self, count: int):
        if self.config.get("tooltip", True) and self.tooltips_enabled:
            suffix = "s" if count != 1 else ""
            self.set_tooltip_text(f"USB Manager: {count} drive{suffix}")
