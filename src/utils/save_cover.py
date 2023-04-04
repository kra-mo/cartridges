# save_cover.py
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


from gi.repository import GdkPixbuf, Gio


def save_cover(parent_widget, game_id, cover_path=None, pixbuf=None):
    covers_dir = parent_widget.data_dir / "cartridges" / "covers"

    covers_dir.mkdir(parents=True, exist_ok=True)

    if not pixbuf:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            str(cover_path), 400, 600, False
        )

    def cover_callback(*_unused):
        pass

    open_file = Gio.File.new_for_path(str(covers_dir / f"{game_id}.tiff"))
    parent_widget.pixbufs[game_id] = pixbuf
    pixbuf.save_to_streamv_async(
        open_file.replace(None, False, Gio.FileCreateFlags.NONE),
        "tiff",
        ["compression"],
        ["8"] if parent_widget.schema.get_boolean("high-quality-images") else ["7"],
        callback=cover_callback,
    )
