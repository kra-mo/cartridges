from src import shared
from src.game import Game
from src.store.managers.file_manager import FileManager
from src.store.managers.manager import Manager


class DisplayManager(Manager):
    """Manager in charge of adding a game to the UI"""

    run_after = set((FileManager,))

    def final_run(self, game: Game) -> None:
        # TODO decouple a game from its widget
        # TODO make the display manager async
        shared.win.games[game.game_id] = game
        game.update()
