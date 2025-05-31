from fabric.utils import cooldown, exec_shell_command_async
from gi.repository import Gtk

from shared import QSChevronButton, QuickSubMenu, ScanButton
from utils.functions import is_app_running, set_scale_adjustment, toggle_command
from utils.widget_utils import (
    util_fabricator,
)


class HyprSunsetSubMenu(QuickSubMenu):
    """A submenu to display application-specific audio controls."""

    def __init__(self, **kwargs):
        # Create refresh button first since parent needs it
        self.scan_button = ScanButton(visible=False)

        self.min_value = 1000
        self.max_value = 9000

        adjustment = Gtk.Adjustment(
            value=2500,
            lower=self.min_value,
            upper=self.max_value,
            step_increment=100,
            page_increment=1000,
        )

        # Create the scale with the adjustment
        self.scale = Gtk.Scale(
            name="hyprsunset-scale",
            orientation=Gtk.Orientation.HORIZONTAL,
            adjustment=adjustment,
            visible=True,
            draw_value=False,
        )

        super().__init__(
            title="HyprSunset",
            title_icon="redshift-status-on",
            name="hyprsunset-sub-menu",
            scan_button=self.scan_button,
            child=self.scale,
            **kwargs,
        )

        if self.scale:
            self.scale.connect("change-value", self.on_scale_move)
            self.update_ui(2600)

        # reusing the fabricator to call specified intervals
        util_fabricator.connect("changed", self.update_scale)

    @cooldown(0.1)
    def on_scale_move(self, _, __, moved_pos):
        exec_shell_command_async(
            f"hyprctl hyprsunset temperature {int(moved_pos)}",
            lambda *_: self.update_ui(int(moved_pos)),
        )
        return True

    def update_scale(self, *_):
        if is_app_running("hyprsunset"):
            self.scale.set_sensitive(True)
            exec_shell_command_async(
                "hyprctl hyprsunset temperature",
                self.update_ui,
            )
        else:
            self.scale.set_sensitive(False)

    def update_ui(self, moved_pos):
        # Update the scale value based on the current temperature
        sanitized_value = (
            float(moved_pos.strip("\n").strip(""))
            if isinstance(moved_pos, str)
            else moved_pos
        )

        set_scale_adjustment(
            scale=self.scale, min_value=1000, max_value=10000, steps=100
        )

        self.scale.set_value(sanitized_value)
        self.scale.set_tooltip_text(f"{sanitized_value}K")


class HyprSunsetToggle(QSChevronButton):
    """A widget to display a toggle button for Wifi."""

    def __init__(self, submenu: QuickSubMenu, **kwargs):
        super().__init__(
            action_icon="redshift-status-off",
            pixel_size=20,
            action_label="Enabled",
            submenu=submenu,
            **kwargs,
        )
        self.action_button.set_sensitive(True)

        self.connect("action-clicked", self.on_action)

        # reusing the fabricator to call specified intervals
        util_fabricator.connect("changed", self.update_action_button)

    def redlight_temperature(self):
        """Get the redlight temperature from the scale."""
        return int(self.submenu.scale.get_value())

    def on_action(self, *_):
        """Handle the action button click event."""
        toggle_command(
            "hyprsunset",
            full_command=f"hyprsunset -t {self.redlight_temperature()}",
        )
        return True

    def update_action_button(self, *_):
        self.is_running = is_app_running("hyprsunset")
        icon = "redshift-status-on" if self.is_running else "redshift-status-off"

        self.action_icon.set_from_icon_name(icon, self.pixel_size)
        self.set_action_label("Enabled" if self.is_running else "Disabled")
        if self.is_running:
            self.set_active_style(True)
        else:
            self.set_active_style(False)
