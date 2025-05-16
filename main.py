import setproctitle
from fabric import Application
from fabric.utils import cooldown, exec_shell_command, get_relative_path, monitor_file
from gi.repository import Gtk
from loguru import logger

import utils.functions as helpers
from modules import StatusBar
from utils import (
    APP_CACHE_DIRECTORY,
    APPLICATION_NAME,
    Colors,
    ExecutableNotFoundError,
    widget_config,
)


@cooldown(2)
@helpers.run_in_thread
def process_and_apply_css(app: Application):
    if not helpers.executable_exists("sass"):
        raise ExecutableNotFoundError(
            "sass"
        )  # Raise an error if sass is not found and exit the application

    logger.info(f"{Colors.INFO}[Main] Compiling CSS")
    output = exec_shell_command("sass styles/main.scss dist/main.css --no-source-map")

    if output == "":
        logger.info(f"{Colors.INFO}[Main] CSS applied")
        app.set_stylesheet_from_file(get_relative_path("dist/main.css"))
    else:
        app.set_stylesheet_from_string("")
        logger.error(f"{Colors.ERROR}[Main]Failed to compile sass!")
        logger.error(f"{Colors.ERROR}[Main] {output}")


general_options = widget_config["general"]
module_options = widget_config["modules"]

if not general_options["debug"]:
    for log in [
        "fabric",
        "widgets",
        "utils",
        "modules",
        "services",
    ]:
        logger.disable(log)


if __name__ == "__main__":
    helpers.ensure_directory(APP_CACHE_DIRECTORY)

    # Create the status bar
    bar = StatusBar(widget_config)

    windows = [bar]

    if module_options["app_launcher"]["enabled"]:
        from modules.app_launcher import Launcher

        launcher = Launcher(widget_config)
        windows.append(launcher)

    if module_options["notification"]["enabled"]:
        from modules import NotificationPopup

        windows.append(NotificationPopup(widget_config))

    if module_options["screen_corners"]["enabled"]:
        from modules.corners import ScreenCorners

        windows.append(ScreenCorners(widget_config))

    if module_options["dock"]["enabled"]:
        from modules.dock import Dock

        windows.append(Dock(widget_config))

    if module_options["desktop_clock"]["enabled"]:
        from widgets.desktop_clock import DesktopClock

        windows.append(
            DesktopClock(
                widget_config,
            )
        )

    if module_options["osd"]["enabled"]:
        from modules import OSDContainer

        windows.append(OSDContainer(widget_config))

    # Initialize the application with the status bar
    app = Application(APPLICATION_NAME, windows=windows)

    helpers.copy_theme(widget_config["theme"]["name"])

    # Set custom `-symbolic.svg` icons' dir
    icon_theme = Gtk.IconTheme.get_default()
    icons_dir = get_relative_path("./assets/icons/svg/gtk")
    icon_theme.append_search_path(icons_dir)

    # Monitor styles folder for changes
    if general_options["debug"]:
        main_css_file = monitor_file(get_relative_path("styles"))
        common_css_file = monitor_file(get_relative_path("styles/common"))
        main_css_file.connect("changed", lambda *_: process_and_apply_css(app))
        common_css_file.connect("changed", lambda *_: process_and_apply_css(app))
    else:
        process_and_apply_css(app)

    setproctitle.setproctitle(APPLICATION_NAME)

    # Run the application
    app.run()
