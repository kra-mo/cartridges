from pathlib import Path

import requests
from gi.repository import GdkPixbuf, Gio
from requests.exceptions import HTTPError, SSLError

from src import shared
from src.game import Game
from src.store.managers.local_cover_manager import LocalCoverManager
from src.store.managers.manager import Manager
from src.utils.save_cover import resize_cover, save_cover


# TODO Remove by generalizing OnlineCoverManager


class ItchCoverManager(Manager):
    """Manager in charge of downloading the game's cover from itch.io"""

    run_after = (LocalCoverManager,)
    retryable_on = (HTTPError, SSLError)

    def manager_logic(self, game: Game, additional_data: dict) -> None:
        # Get the first matching cover url
        base_cover_url: str = additional_data.get("itch_cover_url", None)
        still_cover_url: str = additional_data.get("itch_still_cover_url", None)
        cover_url = still_cover_url or base_cover_url
        if not cover_url:
            return

        # Download cover
        tmp_file = Gio.File.new_tmp()[0]
        with requests.get(cover_url, timeout=5) as cover:
            cover.raise_for_status()
            Path(tmp_file.get_path()).write_bytes(cover.content)

        # Create background blur
        game_cover = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
            tmp_file.read(), 2, 2, False
        ).scale_simple(*shared.image_size, GdkPixbuf.InterpType.BILINEAR)

        # Resize square image
        itch_pixbuf = GdkPixbuf.Pixbuf.new_from_stream(tmp_file.read())
        itch_pixbuf = itch_pixbuf.scale_simple(
            shared.image_size[0],
            itch_pixbuf.get_height() * (shared.image_size[0] / itch_pixbuf.get_width()),
            GdkPixbuf.InterpType.BILINEAR,
        )

        # Composite
        itch_pixbuf.composite(
            game_cover,
            0,
            (shared.image_size[1] - itch_pixbuf.get_height()) / 2,
            itch_pixbuf.get_width(),
            itch_pixbuf.get_height(),
            0,
            (shared.image_size[1] - itch_pixbuf.get_height()) / 2,
            1.0,
            1.0,
            GdkPixbuf.InterpType.BILINEAR,
            255,
        )

        # Resize and save the cover
        save_cover(game.game_id, resize_cover(pixbuf=game_cover))
