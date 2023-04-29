class GameManager():
    """Interface for systems that save, update and remove games"""

    def add(self, game):
        """Add a game to the manager"""
        raise NotImplementedError()

    def update(self, game):
        """Update an existing game in the manager"""
        raise NotImplementedError()

    def remove(self, game):
        """Remove an existing game from the manager"""
        raise NotImplementedError()