import json
import os
from typing import Literal

from fabric.utils import exec_shell_command, get_relative_path
from loguru import logger

from .functions import check_executable_exists, flatten_dict
from .thread import run_in_thread


class MatugenUtil:
    """Utility class for matugen operations."""

    def _normalize_contrast(self, contrast: float) -> float:
        return max(-1, min(1, contrast))

    def _is_valid_image(self, path: str) -> bool:
        """Check if the provided path is a valid image file."""
        valid_extensions = (".jpg", ".jpeg", ".png")
        return path.lower().endswith(valid_extensions)

    @run_in_thread
    def set_css_colors(self, colors):
        logger.info("Applying css colors...")
        css_styles = flatten_dict(colors)

        settings = ""
        for setting in css_styles:
            # Convert python boolean to scss boolean
            value = (
                json.dumps(css_styles[setting])
                if isinstance(css_styles[setting], bool)
                else css_styles[setting]
            )
            settings += f"${setting}: {value};\n"

        with open(get_relative_path("../styles/_colors.scss"), "w") as f:
            f.write(settings)

    def __init__(
        self,
        wallpaper_path,
        contrast: float = 0.0,
        mode: Literal["dark", "light"] = "dark",
    ):
        check_executable_exists("matugen")
        self.normalized_contrast = self._normalize_contrast(contrast)
        self.mode = mode
        self.wallpaper_path = os.path.abspath(os.path.expanduser(wallpaper_path))

        if not self._is_valid_image(self.wallpaper_path):
            raise ValueError(
                f"Invalid image file: {self.wallpaper_path}. Supported formats: .jpg, .jpeg, .png"
            )

        self.base_command = (
            f"matugen image {self.wallpaper_path} --contrast {self.normalized_contrast}"
        )

    def generate_colors(self):
        result = exec_shell_command(f"{self.base_command} --dry-run --json hex")

        print(result)
        if not result:
            logger.error("Matugen command returned no output.")
            return

        try:
            self.json = json.loads(result)
        except json.JSONDecodeError:
            logger.exception(f"Failed to parse JSON from matugen output: {result}")

        colors = self.json.get("colors", {})

        if not colors:
            logger.error("No colors found in matugen output.")
            return

        final_colors = colors.get(self.mode, {})

        if not final_colors:
            logger.error(f"No colors found for mode '{self.mode}' in matugen output.")
            return

        logger.info(f"Colors generated for mode '{self.mode}': {final_colors}")

        self.set_css_colors(final_colors)
