import time
from datetime import datetime

from fabric import Fabricator
from fabric.utils import get_relative_path
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.svg import Svg
from gi.repository import Gtk
from loguru import logger

from services import WeatherService
from shared import ButtonWidget, Popover
from shared.submenu import ScanButton
from utils import BarConfig
from utils.functions import convert_to_12hr_format
from utils.icons import weather_icons
from utils.widget_utils import (
    text_icon,
    util_fabricator,
)

weather_service = WeatherService()


class WeatherMenu(Box):
    """A menu to display the weather information."""

    def sunrise_sunset_time(self) -> str:
        return f" {self.sunrise_time}  {self.sunset_time}"

    def temperature(self, celsius=True) -> str:
        if celsius:
            return f" {self.current_weather['temp_C']}°C"
        else:
            return f" {self.current_weather['temp_F']}°F"

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

        self.scan_btn.connect("clicked", lambda *_: self.scan_btn.play_animation())

        # Get the current weather
        self.current_weather = data["current"]

        # Get the hourly forecast
        self.hourly_forecast = data["hourly"]

        # Get the sunrise and sunset times
        [self.sunrise_time, self.sunset_time] = [
            data["astronomy"]["sunrise"],
            data["astronomy"]["sunset"],
        ]

        self.weather_icons_dir = get_relative_path("../assets/icons/svg/weather")

        self.current_weather_image = Svg(
            svg_file=self.get_weather_asset(self.current_weather["weatherCode"]),
            size=100,
            v_align="start",
            h_align="start",
        )

        self.title_box = Gtk.Grid(
            name="weather-header-grid",
            visible=True,
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
                label=self.temperature(),
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
        self.forecast_box = Gtk.Grid(
            row_spacing=10,
            column_spacing=20,
            name="weather-grid",
            visible=True,
        )

        expander = Gtk.Expander(
            name="weather-expander",
            visible=True,
            child=self.forecast_box,
        )

        self.children = (self.scan_btn, self.title_box, expander)

        # reusing the fabricator to call specified intervals
        util_fabricator.connect("changed", lambda *_: self.update_widget())

    def update_widget(self):
        if (datetime.now() - self.update_time).total_seconds() < 60:
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
                label=f"{convert_to_12hr_format(column_data['time'])}",
                h_align="center",
            )
            icon = Svg(
                svg_file=self.get_weather_asset(
                    column_data["weatherCode"],
                    convert_to_12hr_format(column_data["time"]),
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

    def check_if_day(self, current_time: str | None = None) -> str:
        time_format = "%I:%M %p"

        if current_time is None:
            current_time = datetime.now().strftime(time_format)

        current_time_obj = datetime.strptime(current_time, time_format)
        sunrise_time_obj = datetime.strptime(self.sunrise_time, time_format)
        sunset_time_obj = datetime.strptime(self.sunset_time, time_format)

        # Compare current time with sunrise and sunset
        return sunrise_time_obj <= current_time_obj < sunset_time_obj

    def get_weather_asset(self, code: int, time: str | None = None) -> str:
        is_day = self.check_if_day(time)
        image_name = "image" if is_day else "image-night"
        return f"{self.weather_icons_dir}/{weather_icons[str(code)][image_name]}.svg"


class WeatherWidget(ButtonWidget):
    """A widget to display the current weather."""

    def __init__(
        self,
        widget_config: BarConfig,
        bar,
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

        self.weather_fabricator = Fabricator(poll_from=self.weather_poll, stream=True)

        self.weather_label = Label(
            label="Fetching weather...",
            style_classes="panel-text",
        )
        self.box.children = (self.weather_icon, self.weather_label)

        # Set up a fabricator to call the update_label method at specified intervals
        self.weather_fabricator.connect("changed", self.update_ui)

    def weather_poll(self, fabricator):
        while True:
            yield {"weather": weather_service.get_weather(self.config["location"])}
            time.sleep(self.config["interval"])

    def update_ui(self, fabricator, value):
        # Update the label with the weather icon and temperature in the main thread
        res = value.get("weather")

        if res is None:
            self.weather_label.set_label("")
            self.weather_icon.set_label("")
            if self.config["tooltip"]:
                self.set_tooltip_text("Error fetching weather data")
            return

        # todo: handle error
        current_weather = res["current"]
        text_icon = weather_icons[current_weather["weatherCode"]]["icon"]
        self.weather_label.set_label(f"{current_weather['FeelsLikeC']}°C")
        self.weather_icon.set_label(text_icon)

        # Update the tooltip with the city and weather condition if enabled
        if self.config["tooltip"]:
            self.set_tooltip_text(
                f"{res['location']}, {current_weather['weatherDesc'][0]['value']}"
            )

        popup = Popover(
            content_factory=lambda: WeatherMenu(data=res),
            point_to=self,
        )

        self.connect(
            "clicked",
            lambda *_: popup.open(),
        )
