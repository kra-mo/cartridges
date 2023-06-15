from src import shared  # pylint: disable=no-name-in-module
from src.game import Game
from src.game_cover import GameCover
from src.store.managers.manager import Manager
from src.store.managers.sgdb_manager import SGDBManager
from src.store.managers.steam_api_manager import SteamAPIManager


class DisplayManager(Manager):
    """Manager in charge of adding a game to the UI"""

    run_after = (SteamAPIManager, SGDBManager)
    signals = {"update-ready"}

    def manager_logic(self, game: Game, _additional_data: dict) -> None:
        shared.win.games[game.game_id] = game
        if game.get_parent():
            game.get_parent().get_parent().remove(game)
            if game.get_parent():
                game.get_parent().set_child()

        game.menu_button.set_menu_model(
            game.hidden_game_options if game.hidden else game.game_options
        )

        game.title.set_label(game.name)

        game.menu_button.get_popover().connect(
            "notify::visible", game.toggle_play, None
        )
        game.menu_button.get_popover().connect(
            "notify::visible", game.win.set_active_game, game
        )

        if game.game_id in game.win.game_covers:
            game.game_cover = game.win.game_covers[game.game_id]
            game.game_cover.add_picture(game.cover)
        else:
            game.game_cover = GameCover({game.cover}, game.get_cover_path())
            game.win.game_covers[game.game_id] = game.game_cover

        if (
            game.win.stack.get_visible_child() == game.win.details_view
            and game.win.active_game == game
        ):
            game.win.show_details_view(game)

        if not game.removed and not game.blacklisted:
            if game.hidden:
                game.win.hidden_library.append(game)
            else:
                game.win.library.append(game)
            game.get_parent().set_focusable(False)

        game.win.set_library_child()
