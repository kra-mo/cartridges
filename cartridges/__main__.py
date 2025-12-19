# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed

import sys

from gi.events import GLibEventLoopPolicy  # pyright: ignore[reportMissingImports]

from .application import Application

with GLibEventLoopPolicy():
    raise SystemExit(Application().run(sys.argv))
