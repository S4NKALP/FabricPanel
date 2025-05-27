import json
import os
from typing import Literal

from fabric.utils import exec_shell_command
from loguru import logger

from .functions import check_executable_exists, flatten_dict, write_scss_settings


class MatugenUtil:
    """Utility class for matugen operations."""

    def _normalize_contrast(self, contrast: float) -> float:
        return max(-1, min(1, contrast))

    def _is_valid_image(self, path: str) -> bool:
        """Check if the provided path is a valid image file."""
        valid_extensions = (".jpg", ".jpeg", ".png")
        return path.lower().endswith(valid_extensions)

    def set_scss_colors(self, colors, file_path):
        logger.info("Applying matugen css colors...")
        css_styles = flatten_dict(colors)

        write_scss_settings(css_styles, file_path=file_path)

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
                (
                    f"Invalid image file: {self.wallpaper_path}. "
                    "Supported formats: .jpg, .jpeg, .png"
                )
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

        self.set_scss_colors(final_colors)
