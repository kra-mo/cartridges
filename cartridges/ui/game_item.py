# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 kramo

from typing import Any

from gi.repository import GObject, Gtk

from cartridges.config import PREFIX
from cartridges.games import Game

from .collections import CollectionActions, CollectionsBox
from .cover import Cover  # noqa: F401
from .games import GameActions


@Gtk.Template.from_resource(f"{PREFIX}/game-item.ui")
class GameItem(Gtk.Box):
    """A game in the grid."""

    __gtype_name__ = __qualname__

    motion: Gtk.EventControllerMotion = Gtk.Template.Child()
    options: Gtk.MenuButton = Gtk.Template.Child()
    collections_box: CollectionsBox = Gtk.Template.Child()
    play: Gtk.Button = Gtk.Template.Child()

    game_actions: GameActions = Gtk.Template.Child()
    collection_actions: CollectionActions = Gtk.Template.Child()

    game = GObject.Property(type=Game)
    position = GObject.Property(type=int)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self.insert_action_group("game", self.game_actions)
        self.insert_action_group("collection", self.collection_actions)
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
