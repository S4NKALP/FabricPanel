from fabric.widgets.box import Box

from services import audio_service
from shared import SettingSlider
from shared.widget_container import HoverButton
from utils.icons import icons
from utils.widget_utils import text_icon


class AudioSlider(SettingSlider):
    """A widget to display a scale for audio settings.

    Can be used for both device audio and application audio control.
    """

    def __init__(self, audio_stream=None, show_chevron=True):
        """Initialize the audio slider.

        Args:
            audio_stream: Optional AudioStream object. If None, controls device audio.
                        If provided, controls application-specific audio.
        """
        self.client = audio_service
        self.audio_stream = audio_stream

        self.pixel_size = 16

        # Initialize with default values first
        super().__init__(
            icon_name=icons["audio"]["volume"]["high"],
            start_value=0,
            pixel_size=self.pixel_size,
        )

        if show_chevron:
            self.chevron_icon = text_icon(icon="", props={"style": "font-size:12px;"})

            self.chevron_btn = HoverButton(
                child=Box(
                    children=(self.chevron_icon,),
                )
            )
            self.chevron_btn.connect("clicked", self.on_button_click)
            self.children = (*self.children, self.chevron_btn)

        if not audio_stream:

            def init_device_audio(*args):
                if not self.client.speaker:
                    return
                self.audio_stream = self.client.speaker
                self.update_state()
                self.client.disconnect_by_func(init_device_audio)
                self.client.connect("speaker-changed", lambda *_: self.update_state())

            self.client.connect("changed", init_device_audio)
            if self.client.speaker:
                init_device_audio()
        else:
            self.update_state()
            self.audio_stream.connect("changed", lambda *_: self.update_state())

        # Connect signals
        self.scale.connect("change-value", self.on_scale_move)

        self.icon_button.connect("clicked", self.on_mute_click)

    def _get_icon_name(self):
        """Get the appropriate icon name based on mute state."""
        if not self.audio_stream:
            return icons["audio"]["volume"]["high"]
        return icons["audio"]["volume"]["muted" if self.audio_stream.muted else "high"]

    def update_state(self):
        """Update the slider state from the audio stream."""
        if not self.audio_stream:
            return

        self.scale.set_sensitive(not self.audio_stream.muted)
        self.scale.set_value(self.audio_stream.volume)
        self.scale.set_tooltip_text(f"{round(self.audio_stream.volume)}%")
        self.icon.set_from_icon_name(self._get_icon_name(), self.pixel_size)

    def on_scale_move(self, _, __, moved_pos):
        """Handle volume slider changes."""
        if self.audio_stream:
            self.audio_stream.volume = moved_pos

    def on_button_click(self, button):
        parent = self.get_parent()
        while parent and not hasattr(parent, "audio_submenu"):
            parent = parent.get_parent()

        if parent and hasattr(parent, "audio_submenu"):
            is_visible = parent.audio_submenu.toggle_reveal()

            self.chevron_icon.set_label("" if is_visible else "")

    def on_mute_click(self, button):
        """Toggle mute state."""
        if self.audio_stream:
            self.audio_stream.muted = not self.audio_stream.muted
