import os

from fabric.core.service import Property, Service, Signal
from fabric.utils import exec_shell_command_async, monitor_file
from gi.repository import GLib
from loguru import logger

import utils.functions as helpers
from utils.colors import Colors


def exec_brightnessctl_async(args: str):
    if not helpers.executable_exists("brightnessctl"):
        logger.error(f"{Colors.ERROR}Command brightnessctl not found")

    exec_shell_command_async(f"brightnessctl {args}", lambda _: None)


# Discover screen backlight device
screen_device = ""

try:
    screen_device = os.listdir("/sys/class/backlight")
    screen_device = screen_device[0]
except FileNotFoundError:
    logger.error(
        f"{Colors.ERROR}No backlight devices found, brightness control disabled"
    )


class Brightness(Service):
    """Service to manage screen brightness levels."""

    instance = None

    @staticmethod
    def get_initial():
        if Brightness.instance is None:
            Brightness.instance = Brightness()

        return Brightness.instance

    @Signal
    def screen(self, value: int) -> None:
        """Signal emitted when screen brightness changes."""
        # Implement as needed for your application

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Path for screen backlight control
        self.screen_backlight_path = f"/sys/class/backlight/{screen_device}"

        # Initialize maximum brightness level
        self.max_screen = -1

        if screen_device == "":
            return

        # Monitor screen brightness file
        self.screen_monitor = monitor_file(f"{self.screen_backlight_path}/brightness")

        self.screen_monitor.connect(
            "changed",
            lambda _, file, *args: self.emit(
                "screen",
                round(int(file.load_bytes()[0].get_data())),
            ),
        )

        # Log the initialization of the service
        logger.info(
            f"{Colors.INFO}Brightness service initialized for device: {screen_device}"
        )

    @Property(int, "read-write")
    def screen_brightness(self) -> int:
        # Property to get or set the screen brightness.
        brightness_path = os.path.join(self.screen_backlight_path, "brightness")
        if os.path.exists(brightness_path):
            with open(brightness_path) as f:
                return int(f.readline())
        logger.warning(
            f"{Colors.WARNING}Brightness file does not exist: {brightness_path}"
        )
        return -1  # Return -1 if file doesn't exist, indicating error.

    @screen_brightness.setter
    def screen_brightness(self, value: int):
        # Setter for screen brightness property.
        if not (0 <= value <= self.max_screen):
            value = max(0, min(value, self.max_screen))

        try:
            exec_brightnessctl_async(f"--device '{screen_device}' set {value}")
            self.emit("screen", int((value / self.max_screen) * 100))
            logger.info(
                f"{Colors.INFO}Set screen brightness to {value} (out of {self.max_screen})"
            )
        except GLib.Error as e:
            logger.error(f"{Colors.ERROR}Error setting screen brightness: {e.message}")
        except Exception as e:
            logger.exception(f"Unexpected error setting screen brightness: {e}")
