import os

import pyjson5 as json
import pytomlpp
from fabric.utils import get_relative_path
from loguru import logger

from .constants import DEFAULT_CONFIG
from .functions import (
    exclude_keys,
    flatten_dict,
    merge_defaults,
    validate_widgets,
    write_scss_settings,
)
from .widget_settings import BarConfig


class HydeConfig:
    "A class to read the configuration file and return the default configuration"

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HydeConfig, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.json_config_file = get_relative_path("../config.json")
        self.toml_config_file = get_relative_path("../config.toml")
        self.theme_config_file = get_relative_path("../theme.json")

        self.default_config()

        css_styles = flatten_dict(exclude_keys(self.theme_config, ["name"]))

        write_scss_settings(css_styles, get_relative_path("../styles/_settings.scss"))

    def read_json(self, file) -> dict:
        logger.info(f"[Config] Reading json config from {file}")
        with open(file) as file:
            # Load JSON data into a Python dictionary
            data = json.load(file)
        return data

    def read_config_toml(self) -> dict:
        logger.info(f"[Config] Reading toml config from {self.toml_config_file}")
        with open(self.toml_config_file) as file:
            # Load JSON data into a Python dictionary
            data = pytomlpp.load(file)
        return data

    def default_config(self) -> BarConfig:
        # Read the configuration from the JSON file
        check_toml = os.path.exists(self.toml_config_file)
        check_json = os.path.exists(self.json_config_file)

        if not check_json and not check_toml:
            raise FileNotFoundError("Please provide either a json or toml config.")

        parsed_data = (
            self.read_json(file=self.json_config_file)
            if check_json
            else self.read_config_toml()
        )

        self.theme_config = self.read_json(self.theme_config_file)

        validate_widgets(parsed_data, DEFAULT_CONFIG)

        for key in exclude_keys(DEFAULT_CONFIG, ["$schema"]):
            if key == "widget_groups":
                # For lists, use the user's value or default if not present
                parsed_data[key] = parsed_data.get(key, DEFAULT_CONFIG[key])
            else:
                # For dictionaries, merge with defaults
                parsed_data[key] = merge_defaults(
                    parsed_data.get(key, {}), DEFAULT_CONFIG[key]
                )

        self.config = parsed_data


configuration = HydeConfig()
widget_config = configuration.config
