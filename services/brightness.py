import os

from fabric.core.service import Property, Service, Signal
from fabric.utils import exec_shell_command_async, monitor_file
from gi.repository import GLib
from loguru import logger

import utils.functions as helpers
from utils.colors import Colors


def exec_brightnessctl_async(args: str):
    exec_shell_command_async(f"brightnessctl {args}", lambda _: None)


class BrightnessService(Service):
    """Service to manage screen brightness levels."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @Signal
    def brightness_changed(self, value: int) -> None:
        """Signal emitted when screen brightness changes."""
        # Implement as needed for your application

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        helpers.check_executable_exists("brightnessctl")

        # Discover screen backlight device
        try:
            screen_device_list = os.listdir("/sys/class/backlight")
            self.screen_device = screen_device_list[0] if screen_device_list else ""
        except FileNotFoundError:
            logger.exception(f"{Colors.ERROR}No backlight devices found")
            self.screen_device = ""

        if self.screen_device == "":
            return

        # Discover keyboard backlight device
        try:
            kbd_list = os.listdir("/sys/class/leds")
            kbd_filtered = [x for x in kbd_list if "kbd_backlight" in x]
            self.kbd = kbd_filtered[0] if kbd_filtered else ""
        except FileNotFoundError:
            logger.exception(f"{Colors.ERROR}No keyboard backlight devices found")
            self.kbd = ""

        # Path for screen backlight control
        self.screen_backlight_path = f"/sys/class/backlight/{self.screen_device}"

        # Initialize maximum brightness level
        self.max_screen = self.do_read_max_brightness(self.screen_backlight_path)

        # Monitor screen brightness file
        self.screen_monitor = monitor_file(
            f"{self.screen_backlight_path}/brightness", initial_call=True
        )

        self.screen_monitor.connect(
            "changed",
            lambda _, file, *args: self.emit(
                "brightness_changed",
                round(int(file.load_bytes()[0].get_data())),
            ),
        )

        # Log the initialization of the service
        logger.info(
            f"{Colors.INFO}Brightness service initialized for device: "
            f"{self.screen_device}"
        )

    def do_read_max_brightness(self, path: str) -> int:
        # Reads the maximum brightness value from the specified path.
        max_brightness_path = os.path.join(path, "max_brightness")
        if os.path.exists(max_brightness_path):
            with open(max_brightness_path, "r") as f:
                return int(f.readline())
        return -1  # Return -1 if file doesn't exist, indicating an error.

    @Property(int, "read-write")
    def screen_brightness(self) -> int:
        # Property to get or set the screen brightness.
        brightness_path = os.path.join(self.screen_backlight_path, "brightness")
        if os.path.exists(brightness_path):
            with open(brightness_path, "r") as f:
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
            exec_brightnessctl_async(f"--device '{self.screen_device}' set {value}")
            self.emit("brightness_changed", int((value / self.max_screen) * 100))
            logger.info(
                f"{Colors.INFO}Set screen brightness to {value} "
                f"(out of {self.max_screen})"
            )
        except GLib.Error as e:
            logger.exception(
                f"{Colors.ERROR}Error setting screen brightness: {e.message}"
            )
        except Exception as e:
            logger.exception(f"Unexpected error setting screen brightness: {e}")

    @Property(int, "read-write")
    def keyboard_brightness(self) -> int:  # type: ignore
        with open(self.kbd_backlight_path + "/brightness", "r") as f:
            brightness = int(f.readline())
        return brightness

    @keyboard_brightness.setter
    def keyboard_brightness(self, value):
        if value < 0 or value > self.max_kbd:
            return
        try:
            exec_brightnessctl_async(f"--device '{self.kbd}' set {value}")
        except GLib.Error as e:
            logger.exception(e.message)

    @Property(int, "readable")
    def screen_brightness_percentage(self):
        max_brightness = self.max_screen
        current_brightness = self.screen_brightness

        if max_brightness <= 0:
            return 0
        return int((current_brightness / max_brightness) * 100)
