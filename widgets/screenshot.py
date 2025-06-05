from fabric.widgets.label import Label

from services.screen_record import ScreenRecorderService
from shared import ButtonWidget
from utils.widget_utils import text_icon


class ScreenShotWidget(ButtonWidget):
    """A widget to switch themes."""

    def __init__(self, **kwargs):
        super().__init__(name="screenshot", **kwargs)

        if self.config["tooltip"]:
            self.set_tooltip_text("Screen Shot")

        self.recorder_service = ScreenRecorderService()

        self.box.children = text_icon(
            self.config["icon"],
            props={"style_classes": "panel-font-icon"},
        )

        if self.config["label"]:
            self.box.add(Label(label="screenshot", style_classes="panel-text"))

        self.connect("clicked", self.handle_click)

    def handle_click(self, *_):
        """Start recording the screen."""
        self.recorder_service.screenshot(path=self.config["path"])
