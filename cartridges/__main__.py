# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed

import sys

from gi.events import GLibEventLoopPolicy  # pyright: ignore[reportMissingImports]

with GLibEventLoopPolicy():
    from .application import Application
    from .config import APP_ID

    app = Application(application_id=APP_ID)
    raise SystemExit(app.run(sys.argv))
