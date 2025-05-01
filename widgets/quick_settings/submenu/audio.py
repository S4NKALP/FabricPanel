from fabric.widgets.box import Box
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow
from gi.repository import Gtk

from services import audio_service
from shared.submenu import QuickSubMenu, ScanButton
from utils.icons import icons
from widgets.quick_settings.sliders.audio import AudioSlider


class AudioSubMenu(QuickSubMenu):
    """A submenu to display application-specific audio controls."""

    def __init__(self, **kwargs):
        self.client = audio_service

        # Create refresh button first since parent needs it
        self.scan_button = ScanButton()
        self.scan_button.connect("clicked", lambda _: self.update_apps())

        # Create app list container
        self.app_list = Gtk.ListBox(
            selection_mode=Gtk.SelectionMode.NONE,
            name="app-list",
            visible=True,
        )
        self.app_list.get_style_context().add_class("menu")

        # Wrap in scrolled window
        self.child = ScrolledWindow(
            min_content_size=(-1, 100),
            max_content_size=(-1, 100),
            propagate_width=True,
            propagate_height=True,
            h_scrollbar_policy=Gtk.PolicyType.NEVER,
            child=self.app_list,
        )

        # Initialize parent with our components
        super().__init__(
            title="Applications",
            title_icon=icons["audio"]["volume"]["high"],
            scan_button=self.scan_button,
            child=Box(orientation="v", children=[self.child]),
            **kwargs,
        )

        # Connect signals
        self.client.connect("changed", self.update_apps)
        self.update_apps()

    def update_apps(self, *args):
        """Update the list of applications with volume controls."""

        self.scan_button.play_animation()
        # Clear existing rows
        while row := self.app_list.get_row_at_index(0):
            self.app_list.remove(row)

        if len(self.client.applications) == 0:
            self.app_list.add(
                Label(
                    label="No applications playing audio",
                    style_classes="menu-item",
                    halign="center",
                    valign="center",
                    h_expand=True,
                    v_expand=True,
                )
            )
            return

        # Clear existing rows
        while row := self.app_list.get_row_at_index(0):
            self.app_list.remove(row)

        # Add applications
        for app in self.client.applications:
            row = Gtk.ListBoxRow()
            row.get_style_context().add_class("menu-item")

            # Main container
            box = Box(
                name="list-box-row",
                orientation="v",
                spacing=10,
                margin_start=6,
                margin_end=6,
                margin_top=3,
                margin_bottom=3,
            )

            # App name
            name_box = Box(orientation="h", spacing=12, h_expand=True)

            # App icon
            icon = Image(
                icon_name=app.icon_name or icons["audio"]["volume"]["high"],
                icon_size=16,
            )
            name_box.pack_start(icon, False, True, 0)

            # App name label
            name_label = Label(
                label=app.name,
                style_classes="submenu-item-label",
                h_align="start",
                tooltip_text=app.description or app.name,
            )
            name_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
            name_box.pack_start(name_label, True, True, 0)

            box.add(name_box)

            # Audio controls
            audio_box = Box(
                orientation="h",
                spacing=6,
                margin_start=24,  # Indent to align with app name
            )

            audio_box.pack_start(AudioSlider(app, show_chevron=False), True, True, 0)

            box.add(audio_box)

            row.add(box)
            self.app_list.add(row)
        self.app_list.show_all()
