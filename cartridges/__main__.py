import sys

from gi.events import GLibEventLoopPolicy

from .application import Application

with GLibEventLoopPolicy():
    raise SystemExit(Application().run(sys.argv))
