# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 kramo

from typing import Any

from gi.repository import GObject, Gtk

from cartridges.games import Game

from . import template
from .collections import CollectionActions, CollectionsBox
from .cover import Cover  # noqa: F401
from .games import GameActions


@template.set_template
class GameItem(Gtk.Box):
    """A game in the grid."""

    __gtype_name__ = __qualname__

    game = GObject.Property(type=Game)
    position = GObject.Property(type=int)

    motion: template.Child[Gtk.EventControllerMotion]
    options: template.Child[Gtk.MenuButton]
    collections_box: template.Child[CollectionsBox]
    play: template.Child[Gtk.Button]

    game_actions: template.Child[GameActions]
    collection_actions: template.Child[CollectionActions]

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
