import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gst", "1.0")
from gi.repository import Gtk, Gst, Gdk, Gio

# Initialize GStreamer
Gst.init(None)


class RadioPlayer(Gtk.Window):
    def __init__(self):
        super().__init__(title="GTK Online Radio Player")
        self.set_default_size(400, 300)

        # List of radio stations: (Name, URL)
        self.stations = [
            ("NPR", "https://npr-ice.streamguys1.com/live.mp3"),
            (
                "BBC World Service",
                "http://bbcwssc.ic.llnwd.net/stream/bbcwssc_mp1_ws-eieuk",
            ),
            ("Radio Paradise", "http://stream.radioparadise.com/aac-320"),
        ]

        # Main vertical box layout
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        # Listbox to show stations
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-selected", self.on_station_selected)
        vbox.pack_start(self.listbox, True, True, 0)

        # Add stations to listbox
        for name, url in self.stations:
            label = Gtk.Label(label=name, xalign=0)
            row = Gtk.ListBoxRow()
            row.add(label)
            row.station_url = url
            row.station_name = name
            self.listbox.add(row)

        self.listbox.show_all()

        # Label to show now playing
        self.now_playing_label = Gtk.Label(label="Now Playing: None", xalign=0)
        vbox.pack_start(self.now_playing_label, False, False, 5)

        # GStreamer player
        self.player = Gst.ElementFactory.make("playbin", "player")

        # CSS styling for playing row
        self.css_provider = Gtk.CssProvider()
        self.css_provider.load_from_data(b"""
            .playing {
                background-color: #d0e8ff;
            }
        """)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER,
        )

        self.current_row = None

    def on_station_selected(self, listbox, row):
        if row is not None:
            url = row.station_url
            name = row.station_name

            # Stop previous stream
            self.player.set_state(Gst.State.NULL)

            # Play new stream
            self.player.set_property("uri", url)
            self.player.set_state(Gst.State.PLAYING)

            # Update "Now Playing" label
            self.now_playing_label.set_text(f"Now Playing: {name}")

            # Remove style from previous row
            if self.current_row:
                self.current_row.get_style_context().remove_class("playing")

            # Add style to current row
            row.get_style_context().add_class("playing")
            self.current_row = row


# Run the GTK application
def main():
    from gi.repository import Gdk  # Needed here for Gdk.Screen

    win = RadioPlayer()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
