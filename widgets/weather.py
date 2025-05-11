import threading
import time
from datetime import datetime

from fabric.utils import get_relative_path
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.svg import Svg
from gi.repository import GLib, Gtk
from loguru import logger

from services import WeatherService
from shared import ButtonWidget, Grid, Popover, ScanButton
from utils import BarConfig
from utils.icons import weather_icons
from utils.widget_utils import (
    text_icon,
    util_fabricator,
)

weather_service = WeatherService()


class BaseWeatherWidget:
    """Base class for weather widgets."""

    def sunrise_sunset_time(self) -> str:
        return f" {self.sunrise_time}  {self.sunset_time}"

    def update_sunrise_sunset(self, data):
        # Get the sunrise and sunset times
        self.sunrise_time = data["astronomy"]["sunrise"]
        self.sunset_time = data["astronomy"]["sunset"]
        return True

    def temperature(self, celsius=True) -> str:
        if celsius:
            return f"{self.current_weather['temp_C']}°C"
        else:
            return f"{self.current_weather['temp_F']}°F"

    def check_if_day(self, current_time: str | None = None) -> str:
        time_format = "%I:%M %p"

        if current_time is None:
            current_time = datetime.now().strftime(time_format)

        current_time_obj = datetime.strptime(current_time, time_format)
        sunrise_time_obj = datetime.strptime(self.sunrise_time, time_format)
        sunset_time_obj = datetime.strptime(self.sunset_time, time_format)

        # Compare current time with sunrise and sunset
        return sunrise_time_obj <= current_time_obj < sunset_time_obj

        # wttr.in time are in 300,400...2100 format ,
        #  we need to convert it to 4:00...21:00

    def convert_to_12hr_format(self, time: str) -> str:
        time = int(time)
        hour = time // 100  # Get the hour (e.g., 1200 -> 12)
        minute = time % 100  # Get the minutes (e.g., 1200 -> 00)

        # Convert to 12-hour format
        period = "AM" if hour < 12 else "PM"

        # Adjust hour for 12-hour format
        if hour == 0:
            hour = 12
        elif hour > 12:
            hour -= 12

        # Format the time as a string
        return f"{hour}:{minute:02d} {period}"


class WeatherMenu(Box, BaseWeatherWidget):
    """A menu to display the weather information."""

    def __init__(
        self,
        data,
        **kwargs,
    ):
        super().__init__(
            style_classes="weather-box",
            orientation="v",
            h_expand=True,
            spacing=5,
            **kwargs,
        )
        self.scan_btn = ScanButton(h_align="start", visible=False)

        self.update_time = datetime.now()
        self.update_sunrise_sunset(data)

        # Get the current weather
        self.current_weather = data["current"]

        # Get the hourly forecast
        self.hourly_forecast = data["hourly"]

        self.weather_icons_dir = get_relative_path("../assets/icons/svg/weather")

        self.current_weather_image = Svg(
            svg_file=self.get_weather_asset(self.current_weather["weatherCode"]),
            size=100,
            v_align="start",
            h_align="start",
        )

        self.title_box = Grid(
            name="weather-header-grid",
        )

        self.title_box.attach(
            self.current_weather_image,
            0,
            0,
            2,
            3,
        )

        self.title_box.attach(
            Label(
                style_classes="header-label",
                h_align="start",
                label=f"{data['location']}",
            ),
            2,
            0,
            1,
            1,
        )

        self.title_box.attach(
            Label(
                name="condition",
                h_align="start",
                label=f"{self.current_weather['weatherDesc'][0]['value']}",
            ),
            2,
            1,
            1,
            1,
        )

        self.title_box.attach(
            Label(
                style_classes="header-label",
                name="sunrise-sunset",
                h_align="start",
                label=self.sunrise_sunset_time(),
            ),
            2,
            2,
            1,
            1,
        )

        self.title_box.attach(
            Label(
                style_classes="stats",
                h_align="center",
                label=f" {self.temperature()}",
            ),
            3,
            0,
            1,
            1,
        )

        self.title_box.attach(
            Label(
                style_classes="stats",
                h_align="center",
                label=f"󰖎 {self.current_weather['humidity']}%",
            ),
            3,
            1,
            1,
            1,
        )

        self.title_box.attach(
            Label(
                style_classes="stats",
                h_align="center",
                label=f" {self.current_weather['windspeedKmph']} mph",
            ),
            3,
            2,
            1,
            1,
        )

        # Create a grid to display the hourly forecast
        self.forecast_box = Grid(
            row_spacing=10,
            column_spacing=20,
            name="weather-grid",
        )

        expander = Gtk.Expander(
            name="weather-expander",
            visible=True,
            child=self.forecast_box,
        )

        self.children = (self.scan_btn, self.title_box, expander)

        self.update_widget(initial=True)

        # reusing the fabricator to call specified intervals
        util_fabricator.connect("changed", lambda *_: self.update_widget())

    def update_widget(self, initial=False):
        if (datetime.now() - self.update_time).total_seconds() < 60 and not initial:
            # Check if the update time is more than 10 minutes ago
            return

        logger.debug("[Weather] Updating weather widget")

        self.update_time = datetime.now()

        current_time = int(time.strftime("%H00"))

        next_values = self.hourly_forecast[:4]

        if current_time > 1200:
            next_values = self.hourly_forecast[4:8]

        # show next 4 hours forecast
        for col in range(4):
            column_data = next_values[col]

            hour = Label(
                style_classes="weather-forecast-time",
                label=f"{self.convert_to_12hr_format(column_data['time'])}",
                h_align="center",
            )
            icon = Svg(
                svg_file=self.get_weather_asset(
                    column_data["weatherCode"],
                    self.convert_to_12hr_format(column_data["time"]),
                ),
                size=65,
                h_align="center",
                h_expand=True,
                style_classes="weather-forecast-icon",
            )

            temp = Label(
                style_classes="weather-forecast-temp",
                label=f"{column_data['tempC']}°C",
                h_align="center",
            )
            self.forecast_box.attach(hour, col, 0, 1, 1)
            self.forecast_box.attach(icon, col, 1, 1, 1)
            self.forecast_box.attach(temp, col, 2, 1, 1)

    def get_weather_asset(self, code: int, time_str: str | None = None) -> str:
        is_day = self.check_if_day(
            current_time=time_str,
        )
        image_name = "image" if is_day else "image-night"
        return f"{self.weather_icons_dir}/{weather_icons[str(code)][image_name]}.svg"


class WeatherWidget(ButtonWidget, BaseWeatherWidget):
    """A widget to display the current weather."""

    def __init__(
        self,
        widget_config: BarConfig,
        **kwargs,
    ):
        # Initialize the Box with specific name and style
        super().__init__(
            widget_config["weather"],
            name="weather",
            **kwargs,
        )

        self.weather_icon = text_icon(
            icon="",
            props={
                "style_classes": "panel-icon",
            },
        )

        self.popover = None

        self.update_time = datetime.now()

        self.weather_label = Label(
            label="Fetching weather...",
            style_classes="panel-text",
        )
        self.box.children = (self.weather_icon, self.weather_label)

        self.update_ui(initial=True)

        # Set up a fabricator to call the update_label method at specified intervals
        util_fabricator.connect("changed", lambda *_: self.update_ui())

    def fetch_data_from_url(self):
        data = weather_service.get_weather(
            location=self.config["location"], ttl=self.config["interval"]
        )

        # Update label in main GTK thread
        GLib.idle_add(self.update_data, data)

    def update_data(self, data):
        self.update_time = datetime.now()

        if data is None:
            self.weather_label.set_label("")
            self.weather_icon.set_label("")
            if self.config["tooltip"]:
                self.set_tooltip_text("Error fetching weather data")
            return

        # Get the current weather
        self.current_weather = data["current"]

        self.update_sunrise_sunset(data)

        text_icon = (
            weather_icons[self.current_weather["weatherCode"]]["icon"]
            if self.check_if_day()
            else weather_icons[self.current_weather["weatherCode"]]["icon-night"]
        )

        self.weather_label.set_label(self.temperature())
        self.weather_icon.set_label(text_icon)

        # Update the tooltip with the city and weather condition if enabled
        if self.config["tooltip"]:
            self.set_tooltip_text(
                f"{data['location']}, {self.current_weather['weatherDesc'][0]['value']}"
            )

        # Create popover only once

        if self.popover is None:
            self.popover = Popover(
                content_factory=lambda: WeatherMenu(data=data),
                point_to=self,
            )

            self._clicked_signal_id = self.connect(
                "clicked",
                lambda *_: self.popover.open(),
            )
        else:
            # Just update content_factory with latest data
            self.popover.set_content_factory(lambda: WeatherMenu(data=data))

        return False

    def update_ui(self, initial=False):
        if (datetime.now() - self.update_time).total_seconds() < self.config[
            "interval"
        ] and not initial:
            # Check if the update time is more than interval seconds ago
            return

            # Start background service
        threading.Thread(target=self.fetch_data_from_url, daemon=True).start()
