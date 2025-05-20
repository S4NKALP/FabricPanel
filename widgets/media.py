# ruff: noqa: N802
import math
import os
import re
import tempfile
import urllib.parse
import urllib.request
from functools import partial
from typing import List

from fabric.utils import (
    bulk_connect,
    cooldown,
    get_relative_path,
    invoke_repeater,
)
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
from fabric.widgets.scale import Scale
from fabric.widgets.stack import Stack
from gi.repository import GLib, GObject
from loguru import logger

from services import MprisPlayer, MprisPlayerManager
from shared import Animator, CircleImage, HoverButton
from utils import APP_CACHE_DIRECTORY, cubic_bezier, symbolic_icons
from utils.functions import convert_to_percent, ensure_directory
from utils.widget_utils import (
    setup_cursor_hover,
)


class PlayerBoxStack(Box):
    """A widget that displays the current player information."""

    def __init__(self, mpris_manager: MprisPlayerManager, config, **kwargs):
        self.config = config

        ensure_directory(f"{APP_CACHE_DIRECTORY}/media")

        # The player stack
        self.player_stack = Stack(
            transition_type="slide-left-right",
            transition_duration=500,
            name="player-stack",
        )
        self.current_stack_pos = 0

        # List to store player buttons
        self.player_buttons: list[Button] = []

        # Box to contain all the buttons
        self.buttons_box = CenterBox()

        super().__init__(
            orientation="v", children=[self.player_stack, self.buttons_box]
        )
        self.hide()

        self.mpris_manager = mpris_manager

        bulk_connect(
            self.mpris_manager,
            {
                "player-appeared": self.on_new_player,
                "player-vanished": self.on_lost_player,
            },
        )

        for player in self.mpris_manager.players:  # type: ignore
            logger.info(
                f"[PLAYER MANAGER] player found: {player.get_property('player-name')}",
            )
            self.on_new_player(self.mpris_manager, player)

    def on_player_clicked(self, type):
        # unset active from prev active button
        self.player_buttons[self.current_stack_pos].remove_style_class("active")
        if type == "next":
            self.current_stack_pos = (
                self.current_stack_pos + 1
                if self.current_stack_pos != len(self.player_stack.get_children()) - 1
                else 0
            )
        elif type == "prev":
            self.current_stack_pos = (
                self.current_stack_pos - 1
                if self.current_stack_pos != 0
                else len(self.player_stack.get_children()) - 1
            )
        # set new active button
        self.player_buttons[self.current_stack_pos].add_style_class("active")
        self.player_stack.set_visible_child(
            self.player_stack.get_children()[self.current_stack_pos],
        )

    def on_new_player(self, mpris_manager, player):
        player_name = player.props.player_name

        if player_name in self.config["ignore"]:
            return

        self.set_visible(True)
        if len(self.player_stack.get_children()) == 0:
            self.buttons_box.hide()
        else:
            self.buttons_box.set_visible(True)

        self.player_stack.children = [
            *self.player_stack.children,
            PlayerBox(player=MprisPlayer(player), config=self.config),
        ]

        self.make_new_player_button(self.player_stack.get_children()[-1])
        logger.info(
            f"[PLAYER MANAGER] adding new player: {player.get_property('player-name')}",
        )
        self.player_buttons[self.current_stack_pos].set_style_classes(["active"])

    def on_lost_player(self, mpris_manager, player_name):
        # the playerBox is automatically removed from mprisbox children on being removed
        logger.info(f"[PLAYER_MANAGER] Player Removed {player_name}")
        players: List[PlayerBox] = self.player_stack.get_children()
        if len(players) == 1 and player_name == players[0].player.player_name:
            self.hide()
            self.current_stack_pos = 0
            return

        if players[self.current_stack_pos].player.player_name == player_name:
            self.current_stack_pos = max(0, self.current_stack_pos - 1)
            self.player_stack.set_visible_child(
                self.player_stack.get_children()[self.current_stack_pos],
            )
        self.player_buttons[self.current_stack_pos].set_style_classes(["active"])
        self.buttons_box.hide() if len(players) == 2 else self.buttons_box.set_visible(
            True
        )

    def make_new_player_button(self, player_box):
        new_button = HoverButton(name="player-stack-button")

        def on_player_button_click(button: Button):
            self.player_buttons[self.current_stack_pos].remove_style_class("active")
            self.current_stack_pos = self.player_buttons.index(button)
            button.add_style_class("active")
            self.player_stack.set_visible_child(player_box)

        new_button.connect(
            "clicked",
            on_player_button_click,
        )
        self.player_buttons.append(new_button)

        # This will automatically destroy our used button
        player_box.connect(
            "destroy",
            lambda *args: [
                new_button.destroy(),  # type: ignore
                self.player_buttons.pop(self.player_buttons.index(new_button)),
            ],
        )
        self.buttons_box.add_center(self.player_buttons[-1])


def easeOutBounce(t: float) -> float:
    if t < 4 / 11:
        return 121 * t * t / 16
    elif t < 8 / 11:
        return (363 / 40.0 * t * t) - (99 / 10.0 * t) + 17 / 5.0
    elif t < 9 / 10:
        return (4356 / 361.0 * t * t) - (35442 / 1805.0 * t) + 16061 / 1805.0
    return (54 / 5.0 * t * t) - (513 / 25.0 * t) + 268 / 25.0


def easeInBounce(t: float) -> float:
    return 1 - easeOutBounce(1 - t)


def easeInOutBounce(t: float) -> float:
    if t < 0.5:
        return (1 - easeInBounce(1 - t * 2)) / 2
    return (1 + easeOutBounce(t * 2 - 1)) / 2


def easeOutElastic(t: float) -> float:
    c4 = (2 * math.pi) / 3
    return math.sin((t * 10 - 0.75) * c4) * math.pow(2, -10 * t) + 1


class PlayerBox(Box):
    """A widget that displays the current player information."""

    def __init__(self, player: MprisPlayer, config, **kwargs):
        super().__init__(
            h_align="center",
            name="player-box",
            **kwargs,
            h_expand=True,
        )
        # Setup
        self.player: MprisPlayer = player
        self.fallback_cover_path = get_relative_path("../assets/images/disk.png")

        self.image_size = 115

        self.config = config

        self.icon_size = 15

        # State
        self.exit = False
        self.angle_direction = 1
        self.skipped = False

        self.image_box = CircleImage(
            size=self.image_size, image_file=self.fallback_cover_path
        )

        self.image_box.set_size_request(self.image_size, self.image_size)

        self.image_stack = Box(
            h_align="start", v_align="start", name="player-image-stack"
        )
        self.image_stack.children = [*self.image_stack.children, self.image_box]

        self.art_animator = Animator(
            timing_function=partial(cubic_bezier, 0, 0, 1, 1),
            duration=10,
            min_value=0,
            max_value=360,
            tick_widget=self,
            repeat=True,
            notify_value=self._set_notify_value,
        )

        # Track Info
        self.track_title = Label(
            label="No Title",
            name="player-title",
            justfication="left",
            max_chars_width=self.config["truncation_size"],
            ellipsization="end",
            h_align="start",
        )

        self.track_artist = Label(
            label="No Artist",
            name="player-artist",
            justfication="left",
            max_chars_width=self.config["truncation_size"],
            ellipsization="end",
            h_align="start",
            visible=self.config["show_artist"],
        )

        self.track_album = Label(
            label="No Album",
            name="player-album",
            justfication="left",
            max_chars_width=self.config["truncation_size"],
            ellipsization="end",
            h_align="start",
            visible=self.config["show_album"],
        )

        self.player.bind_property(
            "title",
            self.track_title,
            "label",
            GObject.BindingFlags.DEFAULT,
            lambda _, x: re.sub(r"\r?\n", " ", x) if x != "" else "No Title",  # type: ignore
        )
        self.player.bind_property(
            "artist",
            self.track_artist,
            "label",
            GObject.BindingFlags.DEFAULT,
            lambda _, x: re.sub(r"\r?\n", " ", x) if x != "" else "No Artist",  # type: ignore
        )

        self.player.bind_property(
            "album",
            self.track_album,
            "label",
            GObject.BindingFlags.DEFAULT,
            lambda _, x: re.sub(r"\r?\n", " ", x) if x != "" else "No Album",  # type: ignore
        )

        self.track_info = Box(
            name="track-info",
            spacing=5,
            orientation="v",
            v_align="start",
            h_align="start",
            children=[
                self.track_title,
                self.track_artist,
                self.track_album,
            ],
        )

        # Buttons
        self.button_box = Box(
            name="button-box",
            h_align="center",
            spacing=2,
        )

        self.position_label = Label(
            "00:00",
            v_align="center",
            style_classes="time-label",
            visible=self.config["show_time"],
        )
        self.length_label = Label(
            "00:00",
            v_align="center",
            style_classes="time-label",
            visible=self.config["show_time"],
        )

        # Seek Bar
        self.seek_bar = Scale(
            min_value=0,
            max_value=100,
            increments=(5, 5),
            name="seek-bar",
        )

        self.seek_bar.connect("change-value", self._on_scale_move)
        self.player.bind("can-seek", "sensitive", self.seek_bar)

        setup_cursor_hover(self.seek_bar)

        self.controls_box = CenterBox(
            style_classes="player-controls",
            start_children=self.position_label,
            center_children=self.button_box,
            end_children=self.length_label,
        )

        self.skip_next_icon = Image(
            icon_name=symbolic_icons["mpris"]["next"],
            name="player-icon",
            icon_size=self.icon_size,
        )
        self.skip_prev_icon = Image(
            icon_name=symbolic_icons["mpris"]["prev"],
            name="player-icon",
            icon_size=self.icon_size,
        )
        self.loop_icon = Image(
            icon_name=symbolic_icons["mpris"]["prev"],
            name="player-icon",
            icon_size=self.icon_size,
        )
        self.shuffle_icon = Image(
            icon_name=symbolic_icons["mpris"]["shuffle"]["enabled"],
            name="player-icon",
            icon_size=self.icon_size,
        )
        self.play_pause_icon = Image(
            icon_name=symbolic_icons["mpris"]["paused"],
            name="player-icon",
            icon_size=self.icon_size,
        )

        self.play_pause_button = HoverButton(
            name="player-button",
            child=self.play_pause_icon,
        )

        self.play_pause_button.connect("clicked", self.player.play_pause)
        self.player.bind_property("can_pause", self.play_pause_button, "sensitive")

        self.next_button = HoverButton(name="player-button", child=self.skip_next_icon)
        self.next_button.connect("clicked", self._on_player_next)
        self.player.bind_property("can_go_next", self.next_button, "sensitive")

        self.prev_button = HoverButton(name="player-button", child=self.skip_prev_icon)
        self.prev_button.connect("clicked", self._on_player_prev)

        self.shuffle_button = HoverButton(name="player-button", child=self.shuffle_icon)
        self.shuffle_button.connect("clicked", self.player.toggle_shuffle)
        self.player.bind_property("can_shuffle", self.shuffle_button, "sensitive")

        self.button_box.children = (
            self.shuffle_button,
            self.prev_button,
            self.play_pause_button,
            self.next_button,
        )
        self.player_info_box = Box(
            name="player-info-box",
            v_align="center",
            h_align="start",
            orientation="v",
            children=[self.track_info, self.seek_bar, self.controls_box],
        )

        self.inner_box = Box(
            name="inner-player-box",
            v_align="center",
            h_align="start",
        )
        # resize the inner box
        self.outer_box = Box(
            name="outer-player-box",
            h_align="start",
        )

        self.overlay_box = Overlay(
            child=self.outer_box,
            overlays=[
                self.inner_box,
                self.player_info_box,
                self.image_stack,
                Box(
                    children=Image(icon_name=self.player.player_name, icon_size=20),
                    h_align="end",
                    v_align="start",
                    style="margin-top: 5px; margin-right: 10px;",
                    tooltip_text=self.player.player_name,  # type: ignore
                ),
            ],
        )

        self.children = [*self.children, self.overlay_box]

        # Player Signals
        bulk_connect(
            self.player,
            {
                "notify::arturl": self._set_image,
                "notify::title": self._on_title,
                "exit": self._on_player_exit,
                "notify::playback-status": self._on_playback_change,
                "notify::shuffle": self._on_shuffle_update,
                "notify::length": self._on_length,
                "notify::position": self._on_position,
            },
        )

        invoke_repeater(1000, self._move_seekbar)

    def _on_position(self, *_):
        self.seek_bar.set_value(
            convert_to_percent(self.player.position, self.player.length)
        )
        self.position_label.set_label(self.length_str(self.player.position))

    def _on_length(self, *_):
        self.length_label.set_label(self.length_str(self.player.length))
        self.art_animator.play()

    def _set_notify_value(self, p, *_):
        self.image_box.set_angle(p.value)

    def _on_title(self, *_):
        self.track_title.set_label(self.player.title)

    def _on_player_exit(self, _, value):
        self.exit = value
        self.destroy()

    def _on_player_next(self, *_):
        self.angle_direction = 1
        self.art_animator.pause()
        self.player.next()

    def _on_player_prev(self, *_):
        self.angle_direction = -1
        self.art_animator.pause()
        self.player.previous()

    def _on_shuffle_update(self, _, __):
        if self.player.shuffle is None:
            return
        if self.player.shuffle is True:
            self.shuffle_icon.style_classes = []
            self.shuffle_icon.add_style_class("shuffle-on")
        else:
            self.shuffle_icon.style_classes = []
            self.shuffle_icon.add_style_class("shuffle-off")

    def length_str(self, micro_seconds: int) -> str:
        micro_to_seconds = 1000000
        seconds = int(micro_seconds / micro_to_seconds)
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes:02}:{remaining_seconds:02}"

    def _on_playback_change(self, player, status):
        status = self.player.playback_status

        if status == "stopped":
            self.art_animator.stop()

        if status == "paused":
            self.play_pause_icon.set_from_icon_name(
                symbolic_icons["mpris"]["paused"],
                icon_size=self.icon_size,
            )
            self.art_animator.pause()
        if status == "playing":
            self.play_pause_icon.set_from_icon_name(
                symbolic_icons["mpris"]["playing"],
                icon_size=self.icon_size,
            )
            self.art_animator.play()

    def _update_image(self, image_path):
        if image_path and os.path.isfile(image_path):
            self.image_box.set_image_from_file(image_path)
        else:
            self.image_box.set_image_from_file(self.fallback_cover_path)

    def _set_image(self, *_):
        art_url = self.player.arturl

        parsed = urllib.parse.urlparse(art_url)
        if parsed.scheme == "file":
            local_arturl = urllib.parse.unquote(parsed.path)
            self._update_image(local_arturl)
        elif parsed.scheme in ("http", "https"):
            GLib.Thread.new("download-artwork", self._download_and_set_artwork, art_url)
        else:
            self._update_image(art_url)

    def _download_and_set_artwork(self, arturl):
        """
        Download the artwork from the given URL asynchronously and update the cover
        using GLib.idle_add to ensure UI updates occur on the main thread.
        """
        try:
            parsed = urllib.parse.urlparse(arturl)
            suffix = os.path.splitext(parsed.path)[1] or ".png"
            with urllib.request.urlopen(arturl) as response:
                data = response.read()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(data)
                local_arturl = temp_file.name
        except Exception:
            local_arturl = self.fallback_cover_path
        GLib.idle_add(self._update_image, local_arturl)
        return None

    def _move_seekbar(self, *_):
        if self.player.position is None:
            return False
        position = convert_to_percent(self.player.position, self.player.length)
        self.position_label.set_label(self.length_str(self.player.position))
        self.seek_bar.set_value(position)

    @cooldown(1)
    def _on_scale_move(self, scale: Scale, event, pos: int):
        actual_pos = pos * self.player.length * 0.01
        self.player.position = actual_pos
        self.position_label.set_label(self.length_str(actual_pos))
