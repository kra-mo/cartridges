import logging
import select
from collections import deque

from gi.repository import GLib
from snegg.oeffis import DisconnectedError, Oeffis, SessionClosedError
from snegg.ei import Sender, DeviceCapability, EventType, Seat, Device, Event


class PortalError(Exception):
    """Error raised when a oeffis portal can't be acquired"""


class KeyboardEmulator:
    """
    A class that triggers keypresses with libei

    Libei docs: https://libinput.pages.freedesktop.org/libei/
    Snegg docs: https://libinput.pages.freedesktop.org/snegg/snegg.ei.html
    """

    app = None
    queue: deque = None

    sender: Sender = None
    seat: Seat = None
    keyboard: Device = None

    def __init__(self, app) -> None:
        self.app = app
        self.queue = deque()

        self.app.connect("emulate-key", self.on_emulate_key)
        GLib.Thread.new(None, self.thread_func)

    def on_emulate_key(self, keyval):
        self.queue.append(keyval)

    @staticmethod
    def get_eis_portal() -> Oeffis:
        """Get a portal to the eis server"""
        portal = Oeffis.create()
        if portal is None:
            raise PortalError()
        poll = select.poll()
        poll.register(portal.fd)
        while poll.poll():
            try:
                if portal.dispatch():
                    # We need to keep the portal object alive so we don't get disconnected
                    return portal
            except (SessionClosedError, DisconnectedError) as error:
                raise PortalError() from error

    def thread_func(self):
        """Daemon thread entry point"""

        # Connect to the EIS server
        try:
            portal = self.get_eis_portal()
        except PortalError as error:
            logging.error("Can't get EIS portal", exc_info=error)
            raise
        self.sender = Sender.create_for_fd(fd=portal.eis_fd, name="ei-debug-events")

        # Handle sender events
        poll = select.poll()
        poll.register(self.sender.fd)
        while poll.poll():
            self.sender.dispatch()
            for event in self.sender.events:
                self.handle_sender_event(event)

    def handle_sender_event(self, event: Event):
        """Handle libei sender (input producer) events"""

        match event.event_type:
            # The emulated seat is created, we need to specify its capabilities
            case EventType.SEAT_ADDED:
                if not event.seat:
                    return
                self.seat = event.seat
                self.seat.bind(DeviceCapability.KEYBOARD)

            # A device was added to the seat (here, we're only doing a keyboard)
            case EventType.DEVICE_ADDED:
                if not event.device:
                    return
                self.keyboard = event.device

            # Input can be processed, send keys
            case EventType.DEVICE_RESUMED:
                self.keyboard.start_emulating()
                keyval = self.queue.popleft()
                self.keyboard.keyboard_key(keyval, True)
                self.keyboard.frame()
                self.keyboard.keyboard_key(keyval, False)
                self.keyboard.frame()
                self.keyboard.stop_emulating()
