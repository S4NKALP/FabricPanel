import json
from typing import Literal

from fabric.utils import exec_shell_command, get_relative_path
from loguru import logger

from utils.functions import check_executable_exists


class MatugenUtil:
    """Utility class for matugen operations."""

    def _normalize_contrast(self, contrast: float) -> float:
        return max(-1, min(1, contrast))

    def __init__(
        self,
        wallpaper_path,
        contrast: float = 0.0,
        mode: Literal["dark", "light"] = "dark",
    ):
        check_executable_exists("matugen")
        self.normalized_contrast = self._normalize_contrast(contrast)
        self.mode = mode
        self.wallpaper_path = get_relative_path(wallpaper_path)

        self.base_command = (
            f"matugen image {self.wallpaper_path} --contrast {self.normalized_contrast}"
        )

        result = exec_shell_command(self.base_command)

        try:
            self.json = json.loads(result)
        except json.JSONDecodeError:
            logger.exception(f"Failed to parse JSON from matugen output: {result}")


