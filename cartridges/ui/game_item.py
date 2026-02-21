# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 kramo

from typing import Any

from gi.repository import GObject, Gtk

from cartridges.games import Game

from .collections import CollectionActions, CollectionsBox
from .cover import Cover  # noqa: F401
from .games import GameActions
from .template import Child, template


@template
class GameItem(Gtk.Box):
    """A game in the grid."""

    __gtype_name__ = __qualname__

    game = GObject.Property(type=Game)
    position = GObject.Property(type=int)

    motion: Child[Gtk.EventControllerMotion]
    options: Child[Gtk.MenuButton]
    collections_box: Child[CollectionsBox]
    play: Child[Gtk.Button]

    game_actions: Child[GameActions]
    collection_actions: Child[CollectionActions]

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self.insert_action_group("game", self.game_actions)
        self.insert_action_group("collection", self.collection_actions)
        self._reveal_buttons()

    def _reveal_buttons(self, *_args):
        for widget, reveal in (
            (self.play, contains_pointer := self.motion.props.contains_pointer),
            (self.options, contains_pointer or self.options.props.active),
        ):
            widget.props.can_focus = widget.props.can_target = reveal
            (widget.remove_css_class if reveal else widget.add_css_class)("hidden")

    def _setup_collections(self, button: Gtk.MenuButton, *_args):
        if button.props.active:
            self.collections_box.build()
        else:
            self.collections_box.finish()
