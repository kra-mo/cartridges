from typing import Iterable, Optional


class FriendlyError(Exception):
    """
    An error that is supposed to be shown to the user in a nice format

    Use `raise ... from ...` to preserve context.
    """

    title_format: str
    title_args: Iterable[str]
    subtitle_format: str
    subtitle_args: Iterable[str]

    @property
    def title(self) -> str:
        """Get the gettext translated error title"""
        return self.title_format.format(self.title_args)

    @property
    def subtitle(self) -> str:
        """Get the gettext translated error subtitle"""
        return self.subtitle_format.format(self.subtitle_args)

    def __init__(
        self,
        title: str,
        subtitle: str,
        title_args: Optional[Iterable[str]] = None,
        subtitle_args: Optional[Iterable[str]] = None,
    ) -> None:
        """Create a friendly error

        :param str title: The error's title, translatable with gettext
        :param str subtitle: The error's subtitle, translatable with gettext
        """
        super().__init__()
        if title is not None:
            self.title_format = title
        if subtitle is not None:
            self.subtitle_format = subtitle
        self.title_args = title_args if title_args else ()
        self.subtitle_args = subtitle_args if subtitle_args else ()

    def __str__(self) -> str:
        return f"{self.title} - {self.subtitle}"
