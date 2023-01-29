# preferences.py
#
# Copyright 2022 kramo
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

from gi.repository import Adw, Gtk, Gio, GLib

@Gtk.Template(resource_path='/hu/kramo/GameShelf/gtk/preferences.ui')
class PreferencesWindow(Adw.PreferencesWindow):
    __gtype_name__ = 'PreferencesWindow'

    exit_after_launch_switch = Gtk.Template.Child()
    import_epic_games_switch = Gtk.Template.Child()
    import_gog_games_switch = Gtk.Template.Child()
    import_sideload_games_switch = Gtk.Template.Child()

    steam_file_chooser_button = Gtk.Template.Child()
    heroic_file_chooser_button = Gtk.Template.Child()

    def __init__(self, parent_widget, **kwargs):
        super().__init__(**kwargs)

        self.set_transient_for(parent_widget)
        schema = parent_widget.schema
        schema.bind("exit-after-launch", self.exit_after_launch_switch, "active", Gio.SettingsBindFlags.DEFAULT)
        schema.bind("heroic-import-epic", self.import_epic_games_switch, "active", Gio.SettingsBindFlags.DEFAULT)
        schema.bind("heroic-import-gog", self.import_gog_games_switch, "active", Gio.SettingsBindFlags.DEFAULT)
        schema.bind("heroic-import-sideload", self.import_sideload_games_switch, "active", Gio.SettingsBindFlags.DEFAULT)

        filechooser = Gtk.FileDialog()

        def set_steam_dir(source, result, user_data):
            try:
                schema.set_string("steam-location", filechooser.select_folder_finish(result).get_path())
            except GLib.GError:
                pass

        def set_heroic_dir(source, result, user_data):
            try:
                schema.set_string("heroic-location", filechooser.select_folder_finish(result).get_path())
            except GLib.GError:
                pass

        def choose_folder(widget, function):
            filechooser.select_folder(parent_widget, None, None, function, None)

        self.steam_file_chooser_button.connect("clicked", choose_folder, set_steam_dir)
        self.heroic_file_chooser_button.connect("clicked", choose_folder, set_heroic_dir)
