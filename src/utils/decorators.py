"""
A decorator takes a callable A and returns a callable B that will override the name of A.
A decorator with arguments returns a closure decorator having access to the arguments.

Example usage for the location decorators:

class MyClass():
    @cached_property
    @replaced_by_schema_key(key="source-location")
    @replaced_by_path(override="/somewhere/that/doesnt/exist")
    @replaced_by_path(override="/somewhere/that/exists")
    def location(self):
        return None
"""

from pathlib import Path
from os import PathLike
from functools import wraps


def replaced_by_path(path: PathLike):  # Decorator builder
    """Replace the method's returned path with the override
    if the override exists on disk"""

    def decorator(original_function):  # Built decorator (closure)
        @wraps(original_function)
        def wrapper(*args, **kwargs):  # func's override
            p = Path(path).expanduser()
            if p.exists():
                return p
            else:
                return original_function(*args, **kwargs)

        return wrapper

    return decorator


def replaced_by_schema_key(key: str):  # Decorator builder
    """Replace the method's returned path with the path pointed by the key
    if it exists on disk"""

    def decorator(original_function):  # Built decorator (closure)
        @wraps(original_function)
        def wrapper(*args, **kwargs):  # func's override
            schema = args[0].win.schema
            try:
                override = schema.get_string(key)
            except Exception:
                return original_function(*args, **kwargs)
            else:
                return replaced_by_path(override)(original_function)(*args, **kwargs)

        return wrapper

    return decorator
