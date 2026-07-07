from utils.functions import normalize_address


class NativeClient:
    """Lightweight Hyprland client adapter matching dock expectations."""

    __slots__ = ("_active", "_data", "_hyprland_connection")

    def __init__(self, data: dict, hyprland_connection, active_address: str | None):
        self._data = data
        self._hyprland_connection = hyprland_connection
        self._active = normalize_address(data.get("address")) == active_address

    def get_app_id(self) -> str:
        return self._data.get("initialClass") or self._data.get("class") or ""

    def get_title(self) -> str:
        return self._data.get("title") or self.get_app_id()

    def get_hyprland_address(self) -> int:
        addr = normalize_address(self._data.get("address"))
        return int(addr, 16) if addr else 0

    def get_address_str(self) -> str | None:
        return normalize_address(self._data.get("address"))

    def get_fullscreen(self) -> bool:
        return bool(self._data.get("fullscreen", False))

    def get_activated(self) -> bool:
        return self._active

    def set_activated(self, active: bool):
        self._active = active

    def activate(self):
        addr = self.get_address_str()
        if addr:
            self._hyprland_connection.send_command_async(
                f"dispatch focuswindow address:{addr}",
                lambda *_: None,
            )

    def close(self):
        addr = self.get_address_str()
        if addr:
            self._hyprland_connection.send_command_async(
                f"dispatch closewindow address:{addr}",
                lambda *_: None,
            )

    def fullscreen(self):
        self.activate()
        self._hyprland_connection.send_command_async(
            "dispatch fullscreen 1",
            lambda *_: None,
        )

    def unfullscreen(self):
        self.activate()
        self._hyprland_connection.send_command_async(
            "dispatch fullscreen 0",
            lambda *_: None,
        )
