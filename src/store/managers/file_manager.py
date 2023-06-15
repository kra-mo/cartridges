import json

from src import shared  # pylint: disable=no-name-in-module
from src.game import Game
from src.store.managers.async_manager import AsyncManager
from src.store.managers.steam_api_manager import SteamAPIManager


class FileManager(AsyncManager):
    """Manager in charge of saving a game to a file"""

    run_after = (SteamAPIManager,)
    signals = {"save-ready"}

    def manager_logic(self, game: Game, additional_data: dict) -> None:
        if additional_data.get("skip_save"):  # Skip saving when loading games from disk
            return

        shared.games_dir.mkdir(parents=True, exist_ok=True)

        attrs = (
            "added",
            "executable",
            "game_id",
            "source",
            "hidden",
            "last_played",
            "name",
            "developer",
            "removed",
            "blacklisted",
            "version",
        )

        json.dump(
            {attr: getattr(game, attr) for attr in attrs if attr},
            (shared.games_dir / f"{game.game_id}.json").open("w"),
            indent=4,
            sort_keys=True,
        )
