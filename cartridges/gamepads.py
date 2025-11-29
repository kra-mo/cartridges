# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed

import math
from collections.abc import Generator
from typing import TYPE_CHECKING, Any, cast

from gi.repository import Adw, Gio, GLib, GObject, Gtk, Manette

STICK_DEADZONE = 0.5
REPEAT_DELAY = 280

if TYPE_CHECKING:
    from .ui.window import Window

window: "Window"


class Gamepad(GObject.Object):
    """Data class for gamepad and gamepad UI navigation."""

    window: "Window"
    _device: Manette.Device

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self._device = device
        self._allowed_inputs = {
            Gtk.DirectionType.UP,
            Gtk.DirectionType.DOWN,
            Gtk.DirectionType.LEFT,
            Gtk.DirectionType.RIGHT,
        }

        self._device.connect("button-press-event", self._on_button_press_event)
        self._device.connect("absolute-axis-event", self._on_analog_axis_event)

    def _lock_input(self, direction: Gtk.DirectionType):
        self._allowed_inputs.remove(direction)
        GLib.timeout_add(
            REPEAT_DELAY,
            lambda *_: self._allowed_inputs.add(direction),
        )

    def _on_button_press_event(self, _device: Manette.Device, event: Manette.Event):
        _success, button = event.get_button()
        match button:  # Xbox / Nintendo / PlayStation
            case 304:  # A / B / Circle
                self._on_activate_button_pressed()
            case 305:  # B / A / Cross
                self._on_return_button_pressed()
            case 307:  # Y / X / Triangle
                self._focus_search_entry()
            case 308:  # X / Y / Square
                pass
            case 310:  # Left Shoulder Button
                pass
            case 311:  # Right Shoulder Button
                pass
            case 314:  # Back / - / Options
                pass
            case 315:  # Start / + / Share
                pass
            case 544:
                self._move_vertically(Gtk.DirectionType.UP)
            case 545:
                self._move_vertically(Gtk.DirectionType.DOWN)
            case 546:
                self._move_horizontally(
                    Gtk.DirectionType.RIGHT
                    if Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL
                    else Gtk.DirectionType.LEFT
                )
            case 547:
                self._move_horizontally(
                    Gtk.DirectionType.LEFT
                    if Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL
                    else Gtk.DirectionType.RIGHT
                )
            case 708:  # Screenshot
                pass

    def _on_analog_axis_event(self, _device: Manette.Device, event: Manette.Event):
        _, axis, value = event.get_absolute()
        if abs(value) < STICK_DEADZONE:
            return

        match axis:
            case 0:
                if Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL:
                    direction = (
                        Gtk.DirectionType.RIGHT if value < 0 else Gtk.DirectionType.LEFT
                    )
                else:
                    direction = (
                        Gtk.DirectionType.LEFT if value < 0 else Gtk.DirectionType.RIGHT
                    )

                if direction in self._allowed_inputs:
                    self._lock_input(direction)
                    self._move_horizontally(direction)
            case 1:
                direction = (
                    Gtk.DirectionType.UP if value < 0 else Gtk.DirectionType.DOWN
                )
                if direction in self._allowed_inputs:
                    self._lock_input(direction)
                    self._move_vertically(direction)

    def _on_activate_button_pressed(self):
        if self.window.navigation_view.props.visible_page_tag == "details":
            if focus_widget := self.window.props.focus_widget:
                focus_widget.activate()
            return

        if self._is_focused_on_top_bar() and (
            focus_widget := self.window.props.focus_widget
        ):
            if isinstance(focus_widget, Gtk.ToggleButton):
                focus_widget.props.active = True
                return

            focus_widget.activate()
            self._get_focused_game().grab_focus()
            return

        self.window.grid.activate_action(
            "list.activate-item",
            GLib.Variant.new_uint32(self._get_current_position()),
        )

    def _on_return_button_pressed(self):
        if self.window.navigation_view.props.visible_page_tag == "details":
            if self.window.details.stack.props.visible_child_name == "edit":
                self.window.details.stack.props.visible_child_name = "details"
                return

            if not self._is_focused_on_top_bar():
                self.window.navigation_view.pop_to_tag("games")
            else:
                self.window.sort_button.props.active = False

        open_menu = self._get_active_menu_button()

        if open_menu:
            open_menu.set_active(False)
            open_menu.grab_focus()
        else:
            self._get_focused_game().grab_focus()

        self.window.props.focus_visible = True

    def _focus_search_entry(self):
        self.window.search_entry.grab_focus()
        self.window.props.focus_visible = True

    def _attempt_widget_focus(self, widget: Gtk.Widget | None):
        if not widget:
            self.window.props.display.beep()
            return

        widget.grab_focus()
        self.window.props.focus_visible = True

    def _navigate_to_game_position(self, new_pos: int):
        if new_pos >= 0 and new_pos <= self.window.grid.get_model().get_n_items() - 1:  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
            self.window.grid.scroll_to(new_pos, Gtk.ListScrollFlags.FOCUS, None)
        else:
            self.window.props.display.beep()

        self.window.props.focus_visible = True

    def _move_horizontally(self, direction: Gtk.DirectionType):
        if self._is_focused_on_top_bar():
            self._navigate_top_bar(direction)
            return

        if self._can_navigate_games_page():
            self._navigate_to_game_position(
                self._get_current_position()
                + (-1 if direction == Gtk.DirectionType.LEFT else 1)
            )
            return

        if self.window.navigation_view.props.visible_page_tag == "details":
            if self.window.details.stack.props.visible_child_name == "details":
                self._navigate_action_buttons(direction)
                return

            if not (focus_parent_widget := self.window.props.focus_widget.get_parent()):
                return

            if not focus_parent_widget.child_focus(direction):
                self.window.props.display.beep()
            return

    def _move_vertically(self, direction: Gtk.DirectionType):
        if self._is_focused_on_top_bar() and direction == Gtk.DirectionType.DOWN:
            self._get_focused_game()
            return

        if self._can_navigate_games_page():
            current_grid_columns = math.floor(
                (self.window.get_width() - 24) / self._get_focused_game().get_width()
            )
            new_pos = self._get_current_position() + (
                -current_grid_columns
                if direction == Gtk.DirectionType.UP
                else current_grid_columns
            )
            if new_pos < 0 and direction == Gtk.DirectionType.UP:
                self._focus_search_entry()
                return

            self._navigate_to_game_position(new_pos)
            return

        if self.window.navigation_view.get_visible_page_tag() == "details":
            if self.window.details.stack.props.visible_child_name == "details":
                self._navigate_action_buttons(direction)
                return

            if not (focus_widget := self.window.props.focus_widget):
                return

            if not (
                current_row := (
                    focus_widget.get_ancestor(Adw.EntryRow)
                    if bool(focus_widget.get_ancestor(Adw.EntryRow))
                    else focus_widget.get_ancestor(Adw.WrapBox)
                )
            ):
                self.window.header_bar.grab_focus()
                if not (focus_widget := self.window.get_focus_child()):
                    return

                if focus_widget.child_focus(direction):
                    self.window.props.focus_visible = True
                    return

                self.window.props.display.beep()
                return

            if not (current_box := current_row.get_ancestor(Gtk.Box)):
                return

            if not current_box.child_focus(direction):
                self.window.props.display.beep()

            self.window.props.focus_visible = True

    def _navigate_action_buttons(self, direction: Gtk.DirectionType):
        if not (focus_widget := self.window.props.focus_widget):
            return

        if not (focus_parent_widget := focus_widget.props.parent):
            return

        if focus_parent_widget.child_focus(direction):
            self.window.props.focus_visible = True
            return

        if not (focus_parent_widget := focus_parent_widget.props.parent):
            return

        if focus_parent_widget.child_focus(direction):
            self.window.props.focus_visible = True
            return

        # Focus on header bar if the user goes up/down
        self.window.header_bar.grab_focus()
        if not (focus_widget := self.window.get_focus_child()):
            return

        if focus_widget.child_focus(direction):
            self.window.props.focus_visible = True
            return

        self.window.props.display.beep()

    def _navigate_top_bar(self, direction: Gtk.DirectionType):
        if self.window.title_box.get_focus_child:
            focus = self.window.header_bar.child_focus(direction)

        if not focus:
            self.window.props.display.beep()

        self.window.props.focus_visible = True

    def _get_active_menu_button(self) -> Gtk.MenuButton | None:
        for button in self.window.main_menu, self.window.sort_button:
            if button.props.active:
                return button
        return None

    def _get_focused_game(self) -> Gtk.Widget | None:
        self.window.grid.grab_focus()
        focused_game = self.window.props.focus_widget
        if not focused_game.get_ancestor(Gtk.GridView):
            return None

        return focused_game

    def _get_current_position(self) -> int:
        if not (game_widget := self._get_focused_game()):
            return 0
        return game_widget.get_first_child().position

    def _can_navigate_games_page(self) -> bool:
        return (
            self.window.navigation_view.get_visible_page_tag() == "games"
            and self.window.grid.props.model.get_n_items() != 0  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
            and not bool(self._get_active_menu_button())
        )

    def _is_focused_on_top_bar(self) -> bool:
        return bool(self.window.header_bar.get_focus_child()) and not bool(
            self._get_active_menu_button()
        )


def _iterate_controllers() -> Generator[Gamepad]:
    monitor_iter = monitor.iterate()
    has_next = True
    while has_next:
        has_next, device = monitor_iter.next()
        if device:
            yield Gamepad(device=device, window=window)


def _on_device_disconnected(_monitor: Manette.Monitor, device: Manette.Device):
    pos = next(
        pos
        for pos, gamepad in enumerate(model)
        if cast(Gamepad, gamepad)._device == device
    )
    model.remove(pos)


monitor = Manette.Monitor()
monitor.connect(
    "device-connected",
    lambda _, device: model.append(Gamepad(device=device, window=window)),
)  # pyright: ignore[reportCallIssue]
monitor.connect("device-disconnected", _on_device_disconnected)

model = Gio.ListStore.new(Gamepad)
model.splice(0, 0, tuple(_iterate_controllers()))
