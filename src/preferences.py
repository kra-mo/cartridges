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

from src import shared
from src.game import Game
from src.importer.sources.bottles_source import BottlesSource
from src.importer.sources.desktop_source import DesktopSource
from src.importer.sources.flatpak_source import FlatpakSource
from src.importer.sources.heroic_source import HeroicSource
from src.importer.sources.itch_source import ItchSource
from src.importer.sources.legendary_source import LegendarySource
from src.importer.sources.location import UnresolvableLocationError
from src.importer.sources.lutris_source import LutrisSource
from src.importer.sources.retroarch_source import RetroarchSource
from src.importer.sources.source import Source
from src.importer.sources.steam_source import SteamSource
from src.utils.create_dialog import create_dialog


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
    lutris_data_action_row = Gtk.Template.Child()
    lutris_data_file_chooser_button = Gtk.Template.Child()
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
    flatpak_data_action_row = Gtk.Template.Child()
    flatpak_data_file_chooser_button = Gtk.Template.Child()
    flatpak_import_launchers_switch = Gtk.Template.Child()

    desktop_expander_row = Gtk.Template.Child()
    desktop_terminal_exec_row = Gtk.Template.Child()
    desktop_tereminal_custom_exec_revealer = Gtk.Template.Child()
    desktop_tereminal_custom_exec = Gtk.Template.Child()

    sgdb_key_group = Gtk.Template.Child()
    sgdb_key_entry_row = Gtk.Template.Child()
    sgdb_switch = Gtk.Template.Child()
    sgdb_switch_row = Gtk.Template.Child()
    sgdb_prefer_switch = Gtk.Template.Child()
    sgdb_animated_switch = Gtk.Template.Child()

    danger_zone_group = Gtk.Template.Child()
    reset_action_row = Gtk.Template.Child()
    reset_button = Gtk.Template.Child()
    remove_all_games_button = Gtk.Template.Child()

    removed_games: set[Game] = set()
    warning_menu_buttons: dict = {}

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.win = shared.win
        self.file_chooser = Gtk.FileDialog()
        self.set_transient_for(self.win)

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
        self.remove_all_games_button.connect("clicked", self.remove_all_games)

        # Debug
        if shared.PROFILE == "development":
            self.reset_action_row.set_visible(True)
            self.reset_button.connect("clicked", self.reset_app)
            self.set_default_size(-1, 560)

        # Sources settings
        for source_class in (
            BottlesSource,
            FlatpakSource,
            DesktopSource,
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

        # Desktop Terminal Exec
        def set_terminal_exec(widget: Adw.ComboRow, _param: Any) -> None:
            shared.schema.set_enum("desktop-terminal", widget.get_selected())
            self.desktop_tereminal_custom_exec_revealer.set_reveal_child(
                widget.get_selected() == 0
            )

        self.desktop_terminal_exec_row.connect("notify::selected", set_terminal_exec)
        self.desktop_terminal_exec_row.set_selected(
            terminal_value := shared.schema.get_enum("desktop-terminal")
        )
        if not terminal_value:
            set_terminal_exec(
                self.desktop_terminal_exec_row, None
            )  # The default value is supposed to be 4294967295, but it's 0 and I can't change it

        self.desktop_tereminal_custom_exec.set_text(
            shared.schema.get_string("desktop-terminal-custom-exec")
        )

        def desktop_custom_exec_changed(*_args: Any) -> None:
            shared.schema.set_string(
                "desktop-terminal-custom-exec",
                self.desktop_tereminal_custom_exec.get_text(),
            )

        self.desktop_tereminal_custom_exec.connect(
            "changed", desktop_custom_exec_changed
        )

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

        def set_sgdb_sensitive(widget: Adw.EntryRow) -> None:
            if not widget.get_text():
                shared.schema.set_boolean("sgdb", False)

            self.sgdb_switch_row.set_sensitive(widget.get_text())

        self.sgdb_key_entry_row.connect("changed", set_sgdb_sensitive)
        set_sgdb_sensitive(self.sgdb_key_entry_row)

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
            }
        )

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
        self.file_chooser.select_folder(self.win, None, callback, callback_data)

    def undo_remove_all(self, *_args: Any) -> None:
        for game in self.removed_games:
            game.removed = False
            game.save()
            game.update()

        self.removed_games = set()
        self.toast.dismiss()

    def remove_all_games(self, *_args: Any) -> None:
        for game in shared.store:
            if not game.removed:
                self.removed_games.add(game)
                game.removed = True
                game.save()
                game.update()

        if self.win.stack.get_visible_child() == self.win.details_view:
            self.win.on_go_back_action()

        self.add_toast(self.toast)

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

        def clear_warning_selection(_widget: Any, label: Gtk.Label) -> None:
            label.select_region(-1, -1)

        for location_name, location in source.locations._asdict().items():
            action_row = getattr(
                self, f"{source.source_id}_{location_name}_action_row", None
            )
            if not action_row:
                continue

            try:
                location.resolve()

            except UnresolvableLocationError:
                popover = Gtk.Popover(
                    child=(
                        label := Gtk.Label(
                            label=(
                                '<span rise="12pt"><b><big>'
                                + _("Installation Not Found")
                                + "</big></b></span>\n"
                                + _("Select a valid directory.")
                            ),
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
                            selectable=True,
                        )
                    )
                )

                popover.connect("show", clear_warning_selection, label)

                menu_button = Gtk.MenuButton(
                    icon_name="dialog-warning-symbolic",
                    valign=Gtk.Align.CENTER,
                    popover=popover,
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
            except GLib.GError:
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
