# preferences.py
#
# Copyright 2022-2023 kramo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import re
from pathlib import Path
from shutil import rmtree
from typing import Any, Callable, Optional

from gi.repository import Adw, Gio, GLib, Gtk

from cartridges import shared
from cartridges.errors.friendly_error import FriendlyError
from cartridges.game import Game
from cartridges.importer.bottles_source import BottlesSource
from cartridges.importer.flatpak_source import FlatpakSource
from cartridges.importer.heroic_source import HeroicSource
from cartridges.importer.itch_source import ItchSource
from cartridges.importer.legendary_source import LegendarySource
from cartridges.importer.location import UnresolvableLocationError
from cartridges.importer.lutris_source import LutrisSource
from cartridges.importer.retroarch_source import RetroarchSource
from cartridges.importer.source import Source
from cartridges.importer.steam_source import SteamSource
from cartridges.store.managers.sgdb_manager import SgdbManager
from cartridges.utils.create_dialog import create_dialog


@Gtk.Template(resource_path=shared.PREFIX + "/gtk/preferences.ui")
class PreferencesWindow(Adw.PreferencesWindow):
    __gtype_name__ = "PreferencesWindow"

    general_page = Gtk.Template.Child()
    import_page = Gtk.Template.Child()
    sgdb_page = Gtk.Template.Child()

    sources_group = Gtk.Template.Child()

    exit_after_launch_switch = Gtk.Template.Child()
    cover_launches_game_switch = Gtk.Template.Child()
    high_quality_images_switch = Gtk.Template.Child()

    remove_missing_switch = Gtk.Template.Child()

    steam_expander_row = Gtk.Template.Child()
    steam_data_action_row = Gtk.Template.Child()
    steam_data_file_chooser_button = Gtk.Template.Child()

    lutris_expander_row = Gtk.Template.Child()
    lutris_config_action_row = Gtk.Template.Child()
    lutris_config_file_chooser_button = Gtk.Template.Child()
    lutris_cache_action_row = Gtk.Template.Child()
    lutris_cache_file_chooser_button = Gtk.Template.Child()
    lutris_import_steam_switch = Gtk.Template.Child()
    lutris_import_flatpak_switch = Gtk.Template.Child()

    heroic_expander_row = Gtk.Template.Child()
    heroic_config_action_row = Gtk.Template.Child()
    heroic_config_file_chooser_button = Gtk.Template.Child()
    heroic_import_epic_switch = Gtk.Template.Child()
    heroic_import_gog_switch = Gtk.Template.Child()
    heroic_import_amazon_switch = Gtk.Template.Child()
    heroic_import_sideload_switch = Gtk.Template.Child()

    bottles_expander_row = Gtk.Template.Child()
    bottles_data_action_row = Gtk.Template.Child()
    bottles_data_file_chooser_button = Gtk.Template.Child()

    itch_expander_row = Gtk.Template.Child()
    itch_config_action_row = Gtk.Template.Child()
    itch_config_file_chooser_button = Gtk.Template.Child()

    legendary_expander_row = Gtk.Template.Child()
    legendary_config_action_row = Gtk.Template.Child()
    legendary_config_file_chooser_button = Gtk.Template.Child()

    retroarch_expander_row = Gtk.Template.Child()
    retroarch_config_action_row = Gtk.Template.Child()
    retroarch_config_file_chooser_button = Gtk.Template.Child()

    flatpak_expander_row = Gtk.Template.Child()
    flatpak_system_data_action_row = Gtk.Template.Child()
    flatpak_system_data_file_chooser_button = Gtk.Template.Child()
    flatpak_user_data_action_row = Gtk.Template.Child()
    flatpak_user_data_file_chooser_button = Gtk.Template.Child()
    flatpak_import_launchers_switch = Gtk.Template.Child()

    desktop_switch = Gtk.Template.Child()

    sgdb_key_group = Gtk.Template.Child()
    sgdb_key_entry_row = Gtk.Template.Child()
    sgdb_switch = Gtk.Template.Child()
    sgdb_prefer_switch = Gtk.Template.Child()
    sgdb_animated_switch = Gtk.Template.Child()
    sgdb_fetch_button = Gtk.Template.Child()
    sgdb_stack = Gtk.Template.Child()
    sgdb_spinner = Gtk.Template.Child()

    danger_zone_group = Gtk.Template.Child()
    remove_all_games_list_box = Gtk.Template.Child()
    reset_list_box = Gtk.Template.Child()
    reset_group = Gtk.Template.Child()

    removed_games: set[Game] = set()
    warning_menu_buttons: dict = {}

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.file_chooser = Gtk.FileDialog()
        self.set_transient_for(shared.win)

        self.toast = Adw.Toast.new(_("All games removed"))
        self.toast.set_button_label(_("Undo"))
        self.toast.connect("button-clicked", self.undo_remove_all, None)
        self.toast.set_priority(Adw.ToastPriority.HIGH)

        (shortcut_controller := Gtk.ShortcutController()).add_shortcut(
            Gtk.Shortcut.new(
                Gtk.ShortcutTrigger.parse_string("<primary>z"),
                Gtk.CallbackAction.new(self.undo_remove_all),
            )
        )
        self.add_controller(shortcut_controller)

        # General
        self.remove_all_games_list_box.connect("row-activated", self.remove_all_games)

        # Debug
        if shared.PROFILE == "development":
            self.reset_group.set_visible(True)
            self.reset_list_box.connect("row-activated", self.reset_app)

        # Sources settings
        for source_class in (
            BottlesSource,
            FlatpakSource,
            HeroicSource,
            ItchSource,
            LegendarySource,
            LutrisSource,
            RetroarchSource,
            SteamSource,
        ):
            source = source_class()
            if not source.is_available:
                expander_row = getattr(self, f"{source.source_id}_expander_row")
                expander_row.set_visible(False)
            else:
                self.init_source_row(source)

        # SteamGridDB
        def sgdb_key_changed(*_args: Any) -> None:
            shared.schema.set_string("sgdb-key", self.sgdb_key_entry_row.get_text())

        self.sgdb_key_entry_row.set_text(shared.schema.get_string("sgdb-key"))
        self.sgdb_key_entry_row.connect("changed", sgdb_key_changed)

        self.sgdb_key_group.set_description(
            _(
                "An API key is required to use SteamGridDB. You can generate one {}here{}."
            ).format(
                '<a href="https://www.steamgriddb.com/profile/preferences/api">', "</a>"
            )
        )

        def update_sgdb(*_args: Any) -> None:
            counter = 0
            games_len = len(shared.store)
            sgdb_manager = shared.store.managers[SgdbManager]
            sgdb_manager.reset_cancellable()

            self.sgdb_spinner.set_spinning(True)
            self.sgdb_stack.set_visible_child(self.sgdb_spinner)

            self.add_toast(download_toast := Adw.Toast.new(_("Downloading covers…")))

            def update_cover_callback(manager: SgdbManager) -> None:
                nonlocal counter
                nonlocal games_len
                nonlocal download_toast

                counter += 1
                if counter != games_len:
                    return

                for error in manager.collect_errors():
                    if isinstance(error, FriendlyError):
                        create_dialog(self, error.title, error.subtitle)
                        break

                for game in shared.store:
                    game.update()

                toast = Adw.Toast.new(_("Covers updated"))
                toast.set_priority(Adw.ToastPriority.HIGH)
                download_toast.dismiss()
                self.add_toast(toast)

                self.sgdb_spinner.set_spinning(False)
                self.sgdb_stack.set_visible_child(self.sgdb_fetch_button)

            for game in shared.store:
                sgdb_manager.process_game(game, {}, update_cover_callback)

        self.sgdb_fetch_button.connect("clicked", update_sgdb)

        # Switches
        self.bind_switches(
            {
                "exit-after-launch",
                "cover-launches-game",
                "high-quality-images",
                "remove-missing",
                "lutris-import-steam",
                "lutris-import-flatpak",
                "heroic-import-epic",
                "heroic-import-gog",
                "heroic-import-amazon",
                "heroic-import-sideload",
                "flatpak-import-launchers",
                "sgdb",
                "sgdb-prefer",
                "sgdb-animated",
                "desktop",
            }
        )

        def set_sgdb_sensitive(widget: Adw.EntryRow) -> None:
            if not widget.get_text():
                shared.schema.set_boolean("sgdb", False)

            self.sgdb_switch.set_sensitive(widget.get_text())

        self.sgdb_key_entry_row.connect("changed", set_sgdb_sensitive)
        set_sgdb_sensitive(self.sgdb_key_entry_row)

    def get_switch(self, setting: str) -> Any:
        return getattr(self, f'{setting.replace("-", "_")}_switch')

    def bind_switches(self, settings: set[str]) -> None:
        for setting in settings:
            shared.schema.bind(
                setting,
                self.get_switch(setting),
                "active",
                Gio.SettingsBindFlags.DEFAULT,
            )

    def choose_folder(
        self, _widget: Any, callback: Callable, callback_data: Optional[str] = None
    ) -> None:
        self.file_chooser.select_folder(shared.win, None, callback, callback_data)

    def undo_remove_all(self, *_args: Any) -> None:
        shared.win.get_application().state = shared.AppState.UNDO_REMOVE_ALL_GAMES
        for game in self.removed_games:
            game.removed = False
            game.save()
            game.update()

        self.removed_games = set()
        self.toast.dismiss()
        shared.win.get_application().state = shared.AppState.DEFAULT
        shared.win.create_source_rows()

    def remove_all_games(self, *_args: Any) -> None:
        shared.win.get_application().state = shared.AppState.REMOVE_ALL_GAMES
        shared.win.row_selected(None, shared.win.all_games_row_box.get_parent())
        for game in shared.store:
            if not game.removed:
                self.removed_games.add(game)
                game.removed = True
                game.save()
                game.update()

        if shared.win.navigation_view.get_visible_page() == shared.win.details_page:
            shared.win.navigation_view.pop()

        self.add_toast(self.toast)
        shared.win.get_application().state = shared.AppState.DEFAULT
        shared.win.create_source_rows()

    def reset_app(self, *_args: Any) -> None:
        rmtree(shared.data_dir / "cartridges", True)
        rmtree(shared.config_dir / "cartridges", True)
        rmtree(shared.cache_dir / "cartridges", True)

        for key in (
            (settings_schema_source := Gio.SettingsSchemaSource.get_default())
            .lookup(shared.APP_ID, True)
            .list_keys()
        ):
            shared.schema.reset(key)
        for key in settings_schema_source.lookup(
            shared.APP_ID + ".State", True
        ).list_keys():
            shared.state_schema.reset(key)

        shared.win.get_application().quit()

    def update_source_action_row_paths(self, source: Source) -> None:
        """Set the dir subtitle for a source's action rows"""
        for location_name, location in source.locations._asdict().items():
            # Get the action row to subtitle
            action_row = getattr(
                self, f"{source.source_id}_{location_name}_action_row", None
            )
            if not action_row:
                continue
            path = Path(shared.schema.get_string(location.schema_key)).expanduser()
            # Remove the path prefix if picked via Flatpak portal
            subtitle = re.sub("/run/user/\\d*/doc/.*/", "", str(path))
            action_row.set_subtitle(subtitle)

    def resolve_locations(self, source: Source) -> None:
        """Resolve locations and add a warning if location cannot be found"""

        for location_name, location in source.locations._asdict().items():
            action_row = getattr(
                self, f"{source.source_id}_{location_name}_action_row", None
            )
            if not action_row:
                continue

            try:
                location.resolve()

            except UnresolvableLocationError:
                title = _("Installation Not Found")
                description = _("Select a valid directory.")
                format_start = '<span rise="12pt"><b><big>'
                format_end = "</big></b></span>\n"

                popover = Gtk.Popover(
                    focusable=True,
                    child=(
                        Gtk.Label(
                            label=format_start + title + format_end + description,
                            use_markup=True,
                            wrap=True,
                            max_width_chars=50,
                            halign=Gtk.Align.CENTER,
                            valign=Gtk.Align.CENTER,
                            justify=Gtk.Justification.CENTER,
                            margin_top=9,
                            margin_bottom=9,
                            margin_start=12,
                            margin_end=12,
                        )
                    ),
                )

                popover.update_property(
                    (Gtk.AccessibleProperty.LABEL,), (title + description,)
                )

                def set_a11y_label(widget: Gtk.Popover) -> None:
                    self.set_focus(widget)

                popover.connect("show", set_a11y_label)

                menu_button = Gtk.MenuButton(
                    icon_name="dialog-warning-symbolic",
                    valign=Gtk.Align.CENTER,
                    popover=popover,
                    tooltip_text=_("Warning"),
                )
                menu_button.add_css_class("warning")

                action_row.add_prefix(menu_button)
                self.warning_menu_buttons[source.source_id] = menu_button

    def init_source_row(self, source: Source) -> None:
        """Initialize a preference row for a source class"""

        def set_dir(_widget: Any, result: Gio.Task, location_name: str) -> None:
            """Callback called when a dir picker button is clicked"""
            try:
                path = Path(self.file_chooser.select_folder_finish(result).get_path())
            except GLib.Error:
                return

            # Good picked location
            location = source.locations._asdict()[location_name]
            if location.check_candidate(path):
                shared.schema.set_string(location.schema_key, str(path))
                self.update_source_action_row_paths(source)
                if self.warning_menu_buttons.get(source.source_id):
                    action_row = getattr(
                        self, f"{source.source_id}_{location_name}_action_row", None
                    )
                    action_row.remove(  # type: ignore
                        self.warning_menu_buttons[source.source_id]
                    )
                    self.warning_menu_buttons.pop(source.source_id)
                logging.debug("User-set value for %s is %s", location.schema_key, path)

            # Bad picked location, inform user
            else:
                title = _("Invalid Directory")
                dialog = create_dialog(
                    self,
                    title,
                    location.invalid_subtitle.format(source.name),
                    "choose_folder",
                    _("Set Location"),
                )

                def on_response(widget: Any, response: str) -> None:
                    if response == "choose_folder":
                        self.choose_folder(widget, set_dir, location_name)

                dialog.connect("response", on_response)

        # Bind expander row activation to source being enabled
        expander_row = getattr(self, f"{source.source_id}_expander_row")
        shared.schema.bind(
            source.source_id,
            expander_row,
            "enable-expansion",
            Gio.SettingsBindFlags.DEFAULT,
        )

        # Connect dir picker buttons
        for location_name in source.locations._asdict():
            button = getattr(
                self, f"{source.source_id}_{location_name}_file_chooser_button", None
            )
            if button is not None:
                button.connect("clicked", self.choose_folder, set_dir, location_name)

        # Set the source row subtitles
        self.resolve_locations(source)
        self.update_source_action_row_paths(source)
