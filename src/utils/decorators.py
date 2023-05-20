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
from os import PathLike, environ
from functools import wraps


def replaced_by_path(override: PathLike):  # Decorator builder
    """Replace the method's returned path with the override
    if the override exists on disk"""

    def decorator(original_function):  # Built decorator (closure)
        @wraps(original_function)
        def wrapper(*args, **kwargs):  # func's override
            path = Path(override).expanduser()
            if path.exists():
                return path
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
            except Exception:  # pylint: disable=broad-exception-caught
                return original_function(*args, **kwargs)
            return replaced_by_path(override)(original_function)(*args, **kwargs)

        return wrapper

    return decorator


def replaced_by_env_path(env_var_name: str, suffix: PathLike | None = None):
    """Replace the method's returned path with a path whose root is the env variable"""

    def decorator(original_function):  # Built decorator (closure)
        @wraps(original_function)
        def wrapper(*args, **kwargs):  # func's override
            try:
                env_var = environ[env_var_name]
            except KeyError:
                return original_function(*args, **kwargs)
            override = Path(env_var) / suffix
            return replaced_by_path(override)(original_function)(*args, **kwargs)

        return wrapper

    return decorator
