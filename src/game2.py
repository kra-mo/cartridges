from dataclasses import dataclass, field
from time import time


@dataclass
class Game():
    """Simple game class that contains the necessary fields.
    Saving, updating and removing is done by game manager classes."""

    # State
    removed    : bool = field(default=False, init=False)
    blacklisted: bool = field(default=False, init=False)
    added      : int  = field(default=-1, init=False)
    last_played: int  = field(default=-1, init=False)
    
    # Metadata
    source     : str  = None
    name       : str  = None
    game_id    : str  = None
    developer  : str  = None
    
    # Launching
    executable : str  = None
    
    # Display
    game_cover : str  = None
    hidden     : bool = False

    def __post_init__(self):
        self.added = int(time())