# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed

import math
from collections.abc import Generator
from typing import cast, TYPE_CHECKING, Any, Optional

from gi.repository import Adw, Gtk, Gio, GLib, GObject, Manette
from cartridges.games import Game


STICK_DEADZONE = 0.5
REPEAT_DELAY = 280

window: Adw.ApplicationWindow


class Direction(GObject.GEnum):
    NONE = 0
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4


class Gamepad(GObject.Object):
    """Data class for a gamepad."""

    device = GObject.Property(type=Manette.Device)
    input_allowed_up = GObject.Property(type=bool, default=True)
    input_allowed_down = GObject.Property(type=bool, default=True)
    input_allowed_left = GObject.Property(type=bool, default=True)
    input_allowed_right = GObject.Property(type=bool, default=True)

    def __init__(self, device: Manette.Device):
        super().__init__()
        self.device = device

        self.device.connect("button-press-event", self._on_button_press_event)
        self.device.connect("absolute-axis-event", self._on_analog_axis_event)

    def _get_focused_game(self) -> Gtk.Widget:
        window.grid.grab_focus()
        focused_game = window.get_focus()
        assert focused_game.get_ancestor(Gtk.GridView), "Focused item is not a game!"
        return cast(Gtk.Widget, focused_game)

    def _get_first_visible_child(self, widget: Gtk.Widget) -> Optional[Gtk.Widget]:
        next_widget = widget.get_first_child()
        while True:
            if next_widget:
                if not (next_widget.get_can_focus() and next_widget.get_visible()):
                    if next_widget.get_next_sibling():
                        next_widget = next_widget.get_next_sibling()
                    else:
                        break
                else:
                    return next_widget
            else:
                break

        return next_widget

    def _get_current_position(self) -> int:
        return self._get_focused_game().get_first_child().position

    def _can_navigate_games_page(self) -> bool:
        return (
            window.navigation_view.get_visible_page_tag() == "games"
            and window.grid.get_model().get_n_items() != 0
        )

    def _can_navigate_details_page(self) -> bool:
        return window.navigation_view.get_visible_page_tag() == "details"

    def _is_focused_on_top_bar(self) -> bool:
        return (
            window.header_bar.get_focus_child()
            and window.navigation_view.get_visible_page_tag() == "games"
        )

    def _is_focused_on_actions(self) -> bool:
        return bool(window.details.actions.get_focus_child())

    def _lock_input(self, direction: Direction):
        setattr(self, f"input_allowed_{direction.value_nick.lower()}", False)
        GLib.timeout_add(
            REPEAT_DELAY,
            lambda *_: setattr(
                self, f"input_allowed_{direction.value_nick.lower()}", True
            ),
        )

    def _device_reverse_controls(self):
        return (
            self.device.get_name().find("Nintendo") != -1
            or self.device.get_name().find("Sony") != -1
            or self.device.get_name().find("PlayStation") != -1
        )

    def _on_button_press_event(self, device: Manette.Device, event: Manette.Event):
        success, button = event.get_button()
        match button:
            case 304:  # Xbox / Nintendo / PlayStation
                if self._device_reverse_controls():
                    self._on_return_button_pressed()
                else:
                    self._on_activate_button_pressed()
            case 305:
                if self._device_reverse_controls():
                    self._on_activate_button_pressed()
                else:
                    self._on_return_button_pressed()
            case 307:
                print("Y / X / Triangle Pressed - Focus Search")
                if not self._device_reverse_controls():
                    self._on_search_button_pressed()
            case 308:
                print("X / Y / Square Pressed - Focus Search")
                if self._device_reverse_controls():
                    self._on_search_button_pressed()
            case 310:
                print("Left Shoulder Pressed")
            case 311:
                print("Right Shoulder Pressed.")
            case 311:
                print("Right Shoulder Pressed.")
            case 314:
                print("Back / - Pressed")
            case 315:
                print("Start / + Pressed")
            case 544:
                self._move_vertically(Direction.UP)
            case 545:
                self._move_vertically(Direction.DOWN)
            case 546:
                self._move_horizontally(Direction.LEFT)
            case 547:
                self._move_horizontally(Direction.RIGHT)
            case 708:
                print("Share/Screenshot Pressed")
            case _:
                print(f"Unknown button of keycode {button}")

    def _on_analog_axis_event(self, _device: Manette.Device, event: Manette.Event):
        _, axis, value = event.get_absolute()
        if abs(value) > STICK_DEADZONE:
            match axis:
                case 0:
                    direction = Direction.LEFT if value < 0 else Direction.RIGHT
                    if not getattr(
                        self, f"input_allowed_{direction.value_nick.lower()}"
                    ):
                        return

                    self._move_horizontally(direction)
                case 1:
                    direction = Direction.UP if value < 0 else Direction.DOWN
                    if not getattr(
                        self, f"input_allowed_{direction.value_nick.lower()}"
                    ):
                        return

                    self._move_vertically(direction)
                case _:
                    print("Other stick in use.")

    def _on_search_button_pressed(self):
        window.search_entry.grab_focus()
        window.set_focus_visible(True)

    def _move_horizontally(self, direction: Direction):
        if self._is_focused_on_top_bar():
            if window.sort_button.get_active():
                return

            header_center_box = window.header_bar.get_first_child()
            focused_widget = header_center_box.get_child().get_focus_child()

            if isinstance(focused_widget, Adw.Bin):
                print("Focused on center box")
                next_widget = window.get_focus().get_parent()
                next_widget = (
                    next_widget.get_prev_sibling()
                    if direction == Direction.LEFT
                    else next_widget.get_next_sibling()
                )
                print(next_widget)
                if next_widget:
                    next_widget.grab_focus()
                    return

            next_widget = (
                focused_widget.get_prev_sibling()
                if direction == Direction.LEFT
                else focused_widget.get_next_sibling()
            )
            if next_widget:
                next_widget = next_widget.get_first_child()

            if next_widget:
                next_widget = self._get_first_visible_child(
                    cast(Gtk.Widget, next_widget)
                )

            if next_widget == window.title_box:
                next_widget = (
                    window.sort_button
                    if direction == Direction.LEFT
                    else window.search_entry
                )

            if next_widget:
                next_widget.grab_focus()
            else:
                window.get_display().beep()

                self._lock_input(direction)

        elif self._can_navigate_games_page():
            current_pos = self._get_current_position()

            if direction == Direction.LEFT:
                if current_pos != 0:
                    window.grid.scroll_to(
                        current_pos - 1, Gtk.ListScrollFlags.FOCUS, None
                    )
                else:
                    window.get_display().beep()
            elif direction == Direction.RIGHT:
                if current_pos != window.grid.get_model().get_n_items() - 1:
                    window.grid.scroll_to(
                        current_pos + 1, Gtk.ListScrollFlags.FOCUS, None
                    )
                else:
                    window.get_display().beep()

            self._lock_input(direction)

        elif self._can_navigate_details_page():
            if window.details.stack.props.visible_child_name == "edit":
                focus_widget = window.get_focus()
                if isinstance(focus_widget.get_parent(), Adw.WrapBox):
                    next_widget = (
                        focus_widget.get_prev_sibling()
                        if direction == Direction.LEFT
                        else focus_widget.get_next_sibling()
                    )
                    if next_widget:
                        next_widget.grab_focus()
                        window.set_focus_visible(True)
                        return
                    else:
                        window.get_display().beep()
                        return
                else:
                    return

            if not self._is_focused_on_actions():
                play_widget = window.details.actions.get_first_child()
                play_widget.grab_focus()
                window.set_focus_visible(True)
                return

            next_widget_found = False
            focus_widget = window.get_focus()
            if isinstance(focus_widget, Gtk.ToggleButton):
                focus_widget = focus_widget.get_parent()

            next_widget = (
                focus_widget.get_prev_sibling()
                if direction == Direction.LEFT
                else focus_widget.get_next_sibling()
            )
            while not next_widget_found:
                if not next_widget:
                    # Refocus on play button.
                    if Direction.LEFT:
                        next_widget = focus_widget.get_parent().get_prev_sibling()
                        next_widget_found = True
                    break

                match direction:
                    case Direction.LEFT:
                        if not next_widget.get_visible():
                            next_widget = next_widget.get_prev_sibling()
                        else:
                            next_widget_found = True

                    case Direction.RIGHT:
                        # Leave play button.
                        if isinstance(next_widget, Gtk.Box):
                            next_widget.get_first_child().grab_focus()
                            next_widget_found = True
                        else:
                            if not next_widget.get_visible():
                                next_widget = next_widget.get_next_sibling()
                            else:
                                next_widget_found = True

            if next_widget:
                next_widget.grab_focus()
                self._lock_input(direction)

        window.set_focus_visible(True)

    def _move_vertically(self, direction: Direction):
        if self._is_focused_on_top_bar():
            if window.sort_button.get_active() or window.main_menu.get_active():
                popover_child = (
                    window.sort_button.get_popover()
                    .get_first_child()
                    .get_first_child()
                    .get_child()
                    .get_child()
                    .get_visible_child()
                    .get_first_child()
                    .get_first_child()
                    .get_last_child()
                )
                focus_widget = popover_child.get_focus_child()
                if not focus_widget:
                    if direction == Direction.UP:
                        popover_child.get_last_child().grab_focus()
                    return

                next_widget = (
                    focus_widget.get_prev_sibling()
                    if direction == Direction.UP
                    else focus_widget.get_next_sibling()
                )
                if next_widget:
                    next_widget.grab_focus()
                else:
                    popover_child = (
                        window.sort_button.get_popover()
                        .get_first_child()
                        .get_first_child()
                        .get_child()
                        .get_child()
                        .get_visible_child()
                        .get_first_child()
                        .get_last_child()
                        .get_last_child()
                    )
                    focus_widget = popover_child.get_first_child()
                    focus_widget.grab_focus()

                self._lock_input(direction)
            else:
                if direction == Direction.DOWN:
                    focused_widget = self._get_focused_game()
                    self._lock_input(direction)
                else:
                    return

        elif self._can_navigate_games_page():
            current_grid_columns = math.floor(
                (window.get_width() - 24) / self._get_focused_game().get_width()
            )
            current_pos = self._get_current_position()

            if direction == Direction.DOWN:
                new_pos = current_pos + current_grid_columns
                if new_pos <= window.grid.get_model().get_n_items() - 1:
                    window.grid.scroll_to(
                        new_pos,
                        Gtk.ListScrollFlags.FOCUS,
                        None,
                    )
                else:
                    window.get_display().beep()

            elif direction == Direction.UP:
                new_pos = current_pos - current_grid_columns
                if new_pos >= 0:
                    window.grid.scroll_to(
                        new_pos,
                        Gtk.ListScrollFlags.FOCUS,
                        None,
                    )
                else:
                    window.search_entry.grab_focus()

            self._lock_input(direction)

        elif self._can_navigate_details_page():
            if window.details.stack.props.visible_child_name != "edit":
                return

            focused_widget = window.get_focus()
            next_row = focused_widget.get_ancestor(Adw.EntryRow)

            if not next_row:
                next_row = focused_widget.get_ancestor(Adw.WrapBox)

            if direction == Direction.DOWN:
                next_row = next_row.get_next_sibling()

                if not next_row:
                    next_row = focused_widget.get_ancestor(
                        Adw.PreferencesGroup
                    ).get_next_sibling()

                    if isinstance(next_row, Adw.PreferencesGroup):
                        next_row = next_row.get_row(0)
                    elif isinstance(next_row, Adw.WrapBox):
                        next_row = next_row.get_first_child()

            elif direction == Direction.UP:
                next_row = next_row.get_prev_sibling()

                if not next_row:
                    next_row = focused_widget.get_ancestor(
                        Adw.PreferencesGroup
                    ).get_prev_sibling()

                    if isinstance(next_row, Adw.PreferencesGroup):
                        next_row = next_row.get_row(1)
                else:
                    if isinstance(next_row, Adw.PreferencesGroup):
                        next_row = next_row.get_row(0)

            if next_row:
                next_row.grab_focus()
            else:
                window.get_display().beep()

            self._lock_input(direction)

        window.set_focus_visible(True)

    def _on_activate_button_pressed(self):
        if self._can_navigate_details_page():
            focus_widget = window.get_focus()
            focus_widget.activate()
        else:
            if self._is_focused_on_top_bar():
                focused_widget = window.get_focus()
                if isinstance(focused_widget, Gtk.ToggleButton):
                    focused_widget.set_active(True)
                else:
                    focused_widget.activate()
                    self._get_focused_game().grab_focus()
            else:
                window.grid.activate_action(
                    "list.activate-item",
                    GLib.Variant.new_uint32(self._get_current_position()),
                )

    def _on_return_button_pressed(self):
        if self._can_navigate_details_page():
            if window.details.stack.props.visible_child_name == "edit":
                window.details.stack.props.visible_child_name = "details"
                return

            if not self._is_focused_on_top_bar():
                window.navigation_view.pop_to_tag("games")
            else:
                window.sort_button.set_active(False)
        elif self._is_focused_on_top_bar():
            if window.main_menu.get_active():
                window.main_menu.set_active(False)
                window.main_menu.grab_focus()
                window.set_focus_visible(True)
                return

            if window.sort_button.get_active():
                window.sort_button.set_active(False)
                window.sort_button.grab_focus()
                window.set_focus_visible(True)
                return

        self._get_focused_game().grab_focus()
        window.set_focus_visible(True)


def _iterate_monitor() -> Generator[Manette.Device]:
    monitor_iter = monitor.iterate()
    while True:
        has_next, device = monitor_iter.next()
        if device:
            yield Gamepad(device)

        if not has_next:
            break


def _on_device_disconnected(_monitor: Manette.Monitor, device: Manette.Device):
    pos = next(pos for pos, gamepad in enumerate(model) if gamepad.device == device)
    model.remove(pos)


monitor = Manette.Monitor()
monitor.connect("device-connected", lambda _, device: model.append(Gamepad(device)))
monitor.connect("device-disconnected", _on_device_disconnected)

model = Gio.ListStore.new(Gamepad)
model.splice(0, 0, tuple(_iterate_monitor()))
