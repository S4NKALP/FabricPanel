import gi
from fabric.utils import exec_shell_command_async
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from gi.repository import GdkPixbuf, Gtk

from services import battery_service
from shared import ButtonWidget
from utils import BarConfig
from utils.functions import format_time

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")


class BatteryWidget(ButtonWidget):
    """A widget to display the current battery status."""

    def __init__(
        self,
        widget_config: BarConfig,
        bar,
        **kwargs,
    ):
        # Initialize the Box with specific name and style
        super().__init__(
            widget_config["battery"],
            name="battery",
            **kwargs,
        )
        self.full_battery_level = self.config["full_battery_level"]

        self.client = battery_service

        self.client.connect("changed", lambda *_: self.update_ui())

        self.state = None

        self.update_ui()

    def update_ui(self):
        """Update the battery status by fetching the current battery information
        and updating the widget accordingly.
        """
        is_present = self.client.get_property("IsPresent")

        battery_percent = (
            round(self.client.get_property("Percentage")) if is_present else 0
        )

        self.battery_label = Label(
            label=f"{battery_percent}%", style_classes="panel-text", visible=False
        )

        battery_state = self.client.get_property("State")

        is_charging = battery_state == 1 if is_present else False

        notification_config = self.config["notifications"]

        if self.state is None or self.state != battery_state:
            self.state = battery_state

            if notification_config["enabled"]:
                if is_charging:
                    percent = f"{battery_percent}%"
                    charging_config = notification_config["charging"]
                    exec_shell_command_async(
                        f"notify-send '{charging_config['title']}' '{
                            charging_config['body'].replace('_LEVEL_%', percent)
                        }'",
                        lambda *_: None,
                    )
                else:
                    percent = f"{battery_percent}%"
                    discharging_config = notification_config["discharging"]
                    exec_shell_command_async(
                        f"notify-send '{discharging_config['title']}' '{
                            discharging_config['body'].replace('_LEVEL_%', percent)
                        }'",
                        lambda *_: None,
                    )

        temperature = self.client.get_property("Temperature")
        energy = self.client.get_property("Energy")

        time_remaining = (
            self.client.get_property("TimeToFull")
            if is_charging
            else self.client.get_property("TimeToEmpty")
        )

        self.battery_icon = Image(
            icon_name=self.client.get_property("IconName"),
            icon_size=self.config["icon_size"],
        )

        if self.config["orientation"] == "horizontal":
            # Get the Pixbuf from the Gtk.Image
            pixbuf = Gtk.IconTheme.get_default().load_icon(
                self.client.get_property("IconName"),
                14,
                Gtk.IconLookupFlags.FORCE_SIZE,
            )

            rotated_pixbuf = pixbuf.rotate_simple(GdkPixbuf.PixbufRotation.CLOCKWISE)
            self.battery_icon.set_from_pixbuf(rotated_pixbuf)

        self.box.children = (self.battery_icon, self.battery_label)

        # Update the label with the battery percentage if enabled
        if self.config["label"]:
            self.battery_label.set_visible(True)

            ## Hide the label when the battery is full
            if (
                self.config["hide_label_when_full"]
                and battery_percent == self.full_battery_level
            ):
                self.battery_label.hide()

        # Update the tooltip with the battery status details if enabled
        if self.config["tooltip"]:
            tool_tip_text = (
                f"󱐋 Energy : {round(energy, 2)} Wh\n Temperature: {temperature}°C"
            )
            if battery_percent == self.full_battery_level:
                self.set_tooltip_text(f"Full\n{tool_tip_text}")
            elif is_charging and battery_percent < self.full_battery_level:
                self.set_tooltip_text(
                    f"󰄉 Time to full: {format_time(time_remaining)}\n{tool_tip_text}"
                )
            else:
                self.set_tooltip_text(
                    f"󰄉 Time to empty: {format_time(time_remaining)}\n{tool_tip_text}"
                )

        return True
