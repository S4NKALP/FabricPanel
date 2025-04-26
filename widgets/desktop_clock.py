from fabric.widgets.box import Box
from fabric.widgets.datetime import DateTime
from fabric.widgets.wayland import WaylandWindow as Window

from utils.types import Anchor, Layer


class DesktopClock(Window):
    """
    A simple desktop clock widget.
    """

    def __init__(self, date_format: str, anchor: Anchor, layer: Layer, **kwargs):
        super().__init__(
            name="desktop_clock",
            layer=layer,
            anchor=anchor,
            child=Box(
                name="desktop-clock-box",
                orientation="v",
                children=[
                    DateTime(formatters=["%I:%M"], name="clock"),
                    DateTime(formatters=[date_format], interval=10000, name="date"),
                ],
            ),
            all_visible=True,
            **kwargs,
        )
