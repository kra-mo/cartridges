# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed

from collections.abc import Generator
from typing import TYPE_CHECKING, Any, cast

from gi.repository import Gio, GLib, GObject, Gtk, Manette

if TYPE_CHECKING:
    from .ui.window import Window

STICK_DEADZONE = 0.5
REPEAT_DELAY = 280


def get_gamepad_navigable_ancestor(target_widget: Gtk.Widget) -> Gtk.Widget | None:
    """Return first ancestor widget with the GamepadNavigable mixin.

    Relative to target_widget. Return value can be None.
    """
    if not (widget := target_widget):
        return None

    while not isinstance(widget, GamepadNavigable):
        if not (widget := widget.props.parent):
            return None

    return widget


class GamepadNavigable:
    """Abstract class for focused widgets to handle forwarded controller input."""

    def move_focus(self, direction: Gtk.DirectionType):
        """Change the focused widget for the given direction."""

    def activate_button_pressed(self):
        """Trigger action when lowest button is pressed (A on XBox Controllers)."""

    def return_button_pressed(self):
        """Trigger action when right-most button is pressed (B on XBox Controllers)."""

    def search_button_pressed(self):
        """Trigger action when top button is pressed (Y on XBox Controllers)."""


class Gamepad(GObject.Object):
    """Data class for gamepad, including UI navigation."""

    __gtype_name__ = __qualname__

    window: "Window"
    device = GObject.Property(type=Manette.Device)

    def __init__(self, device: Manette.Device | None = None, **kwargs: Any):
        super().__init__(**kwargs)

        self._allowed_inputs = {
            Gtk.DirectionType.UP,
            Gtk.DirectionType.DOWN,
            Gtk.DirectionType.LEFT,
            Gtk.DirectionType.RIGHT,
        }

        self._device_signals = GObject.SignalGroup(target_type=Manette.Device)
        self._device_signals.connect_closure(
            "button-press-event", self._on_button_press_event, after=False
        )
        self._device_signals.connect_closure(
            "absolute-axis-event", self._on_analog_axis_event, after=False
        )

        self.bind_property("device", self._device_signals, "target")

        self.device = device

    @staticmethod
    def _get_rtl_direction(
        a: Gtk.DirectionType, b: Gtk.DirectionType
    ) -> Gtk.DirectionType:
        return a if Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL else b

    def _lock_input(self, direction: Gtk.DirectionType):
        self._allowed_inputs.remove(direction)
        GLib.timeout_add(REPEAT_DELAY, lambda *_: self._allowed_inputs.add(direction))

    def _on_button_press_event(self, _device: Manette.Device, event: Manette.Event):
        _success, button = event.get_button()
        match button:  # Xbox / Nintendo / PlayStation
            case 304:  # A / B / Circle
                self._activate()
            case 305:  # B / A / Cross
                self._return()
            case 307:  # Y / X / Triangle
                self._search()
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
                self._move(Gtk.DirectionType.UP)
            case 545:
                self._move(Gtk.DirectionType.DOWN)
            case 546:
                self._move(Gtk.DirectionType.LEFT)
            case 547:
                self._move(Gtk.DirectionType.RIGHT)

    def _move(self, direction: Gtk.DirectionType):
        if not (focus_widget := self.window.props.focus_widget) or not (
            widget := get_gamepad_navigable_ancestor(focus_widget)
        ):
            return

        cast(GamepadNavigable, widget).move_focus(direction)

    def _activate(self):
        if not (focus_widget := self.window.props.focus_widget) or not (
            widget := get_gamepad_navigable_ancestor(focus_widget)
        ):
            return

        cast(GamepadNavigable, widget).activate_button_pressed()

    def _return(self):
        if not (focus_widget := self.window.props.focus_widget) or not (
            widget := get_gamepad_navigable_ancestor(focus_widget)
        ):
            return

        cast(GamepadNavigable, widget).return_button_pressed()

    def _search(self):
        if not (focus_widget := self.window.props.focus_widget) or not (
            widget := get_gamepad_navigable_ancestor(focus_widget)
        ):
            return

        cast(GamepadNavigable, widget).search_button_pressed()

    def _on_analog_axis_event(self, _device: Manette.Device, event: Manette.Event):
        _, axis, value = event.get_absolute()
        if abs(value) < STICK_DEADZONE:
            return

        match axis:
            case 0:
                direction = (
                    Gtk.DirectionType.LEFT if value < 0 else Gtk.DirectionType.RIGHT
                )

                if direction in self._allowed_inputs:
                    self._lock_input(direction)
                    self._move(direction)
            case 1:
                direction = (
                    Gtk.DirectionType.UP if value < 0 else Gtk.DirectionType.DOWN
                )
                if direction in self._allowed_inputs:
                    self._lock_input(direction)
                    self._move(direction)


def _iterate_devices() -> Generator[Gamepad]:
    monitor_iter = monitor.iterate()
    has_next = True
    while has_next:
        has_next, device = monitor_iter.next()
        if device:
            yield Gamepad(device)


def _remove_device(device: Manette.Device):
    model.remove(
        next(
            pos
            for pos, gamepad in enumerate(model)
            if cast(Gamepad, gamepad).device == device
        )
    )


def _update_window_style(model: Gio.ListStore):
    if model.props.n_items > 0:
        Gamepad.window.add_css_class("controller-connected")
    else:
        Gamepad.window.remove_css_class("controller-connected")


def setup_monitor():
    """Connect monitor to device connect/disconnect signals."""
    monitor.connect(
        "device-connected",
        lambda _, device: model.append(Gamepad(device)),
    )
    monitor.connect("device-disconnected", lambda _, device: _remove_device(device))
    model.splice(0, 0, tuple(_iterate_devices()))


monitor = Manette.Monitor()
model = Gio.ListStore(item_type=Gamepad)
model.connect("items-changed", lambda model, *_: _update_window_style(model))
