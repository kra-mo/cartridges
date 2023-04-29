from dataclasses import dataclass
from functools import cached_property
from pathlib import Path


@dataclass
class Location():
    """Abstraction for a location that can be overriden by a schema key"""

    win = None
    
    default: str = None
    key: str = None

    @cached_property
    def path(self):
        override = Path(self.win.schema.get_string(self.path_override_key))
        if override.exists(): 
            return override
        return self.path_default