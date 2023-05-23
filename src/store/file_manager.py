from src.store.manager import Manager
from src.game import Game


class FileManager(Manager):
    """Manager in charge of saving a game to a file"""

    def run(self, game: Game) -> None:
        # TODO make game.save (disk) not trigger game.update (UI)
        game.save()
