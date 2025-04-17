import json
import re

from fabric.hyprland.widgets import HyprlandEvent, get_hyprland_connection
from fabric.widgets.label import Label
from loguru import logger

from shared import ButtonWidget
from utils import KBLAYOUT_MAP, BarConfig
from utils.widget_utils import text_icon


class KeyboardLayoutWidget(ButtonWidget):
    """A widget to display the current keyboard layout."""

    def __init__(self, widget_config: BarConfig, bar, **kwargs):
        super().__init__(widget_config["keyboard"], name="keyboard", **kwargs)

        self.kb_label = Label(label="0", style_classes="panel-text")

        if self.config["show_icon"]:
            # Create a TextIcon with the specified icon and size
            self.icon = text_icon(
                icon=self.config["icon"],
                props={"style_classes": "panel-icon"},
            )
            self.box.add(self.icon)

        self.box.add(self.kb_label)

        self.connection = get_hyprland_connection()

        # all aboard...
        if self.connection.ready:
            self.on_ready(None)
        else:
            self.connection.connect("event::ready", self.on_ready)

    def on_ready(self, _):
        return self.get_keyboard(), logger.info(
            "[Keyboard] Connected to the hyprland socket"
        )

    def on_activelayout(self, _, event: HyprlandEvent):
        if len(event.data) < 2:
            return logger.warning("[Keyboard] got invalid event data from hyprland")
        keyboard, language = event.data
        matched: bool = False

        if re.match(self.keyboard, keyboard) and (matched := True):
            self.kb_label.set_label(self.formatter.format(language=language))

        return logger.debug(
            f"[Keyboard] Keyboard: {keyboard}, Language: {language}, Match: {matched}"
        )

    def get_keyboard(self):
        data = json.loads(str(self.connection.send_command("j/devices").reply.decode()))
        keyboards = data["keyboards"]
        if len(keyboards) == 0:
            return "Unknown"

        main_kb = next((kb for kb in keyboards if kb["main"]), None)

        if not main_kb:
            main_kb = keyboards[len(keyboards) - 1]

        layout = main_kb["active_keymap"]

        if self.config["tooltip"]:
            self.set_tooltip_text(
                f"Caps Lock 󰪛: {main_kb['capsLock']} | Num Lock : {main_kb['numLock']}"
            )

        # Update the label with the used storage if enabled
        if self.config["label"]:
            self.kb_label.set_label(KBLAYOUT_MAP[layout])
            self.kb_label.set_visible(True)
