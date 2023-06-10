from pathlib import Path

import requests
from gi.repository import Gio
from requests.exceptions import HTTPError, SSLError

from src.game import Game
from src.store.managers.local_cover_manager import LocalCoverManager
from src.store.managers.manager import Manager
from src.utils.save_cover import resize_cover, save_cover


class OnlineCoverManager(Manager):
    """Manager that downloads game covers from URLs"""

    run_after = (LocalCoverManager,)
    retryable_on = (HTTPError, SSLError)

    def manager_logic(self, game: Game, additional_data: dict) -> None:
        # Ensure that we have a cover to download
        cover_url = additional_data.get("online_cover_url", None)
        if not cover_url:
            return
        # Download cover
        tmp_file = Gio.File.new_tmp()[0]
        with requests.get(cover_url, timeout=5) as cover:
            cover.raise_for_status()
            Path(tmp_file.get_path()).write_bytes(cover.content)
        # Resize and save
        save_cover(game.game_id, resize_cover(tmp_file.get_path()))
