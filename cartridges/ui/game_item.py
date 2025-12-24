# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 kramo

from typing import Any

from gi.repository import Gio, GLib, GObject, Gtk

from cartridges.config import PREFIX
from cartridges.games import Game

from .collections import CollectionsBox
from .cover import Cover  # noqa: F401


@Gtk.Template.from_resource(f"{PREFIX}/game-item.ui")
class GameItem(Gtk.Box):
    """A game in the grid."""

    __gtype_name__ = __qualname__

    motion: Gtk.EventControllerMotion = Gtk.Template.Child()
    options: Gtk.MenuButton = Gtk.Template.Child()
    collections_box: CollectionsBox = Gtk.Template.Child()
    play: Gtk.Button = Gtk.Template.Child()

    position = GObject.Property(type=int)

    @GObject.Property(type=Game)
    def game(self) -> Game | None:
        """The game that `self` represents."""
        return self._game

    @game.setter
    def game(self, game: Game | None):
        self._game = game
        self.insert_action_group("game", game)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self.insert_action_group("item", group := Gio.SimpleActionGroup())
        group.add_action_entries((
            (
                "edit",
                lambda *_: self.activate_action(
                    "win.edit", GLib.Variant.new_uint32(self.position)
                ),
            ),
            (
                "add-collection",
                lambda *_: self.activate_action(
                    "win.add-collection", GLib.Variant.new_string(self.game.game_id)
                ),
            ),
        ))

        self._reveal_buttons()

    @Gtk.Template.Callback()
    def _reveal_buttons(self, *_args):
        for widget, reveal in (
            (self.play, contains_pointer := self.motion.props.contains_pointer),
            (self.options, contains_pointer or self.options.props.active),
        ):
            widget.props.can_focus = widget.props.can_target = reveal
            (widget.remove_css_class if reveal else widget.add_css_class)("hidden")

    @Gtk.Template.Callback()
    def _setup_collections(self, button: Gtk.MenuButton, *_args):
        if button.props.active:
            self.collections_box.build()
        else:
            self.collections_box.finish()
