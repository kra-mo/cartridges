# Contributing

## Code

Be sure to follow the [code style](#code-style) of the project.

### Adding a feature
[Create an issue](https://github.com/kra-mo/cartridges/issues/new) or join the [Discord](https://discord.gg/4KSFh3AmQR)/[Matrix](https://matrix.to/#/#cartridges:matrix.org) to discuss it with the maintainers. We will provide additional guidance.

### Fixing a bug
Fork the repository, make your changes, then create a pull request. Be sure to mention the GitHub issue you're fixing if one was already open.

## Translations
### Weblate
The project can be translated on [Weblate](https://hosted.weblate.org/engage/cartridges/).

### Manually
1. Clone the repository.
2. If it isn't already there, add your language to `/po/LINGUAS`.
3. Create a new translation from the `/po/cartridges.pot` file with a translation editor such as [Poedit](https://poedit.net/).
4. Save the file as `[YOUR LANGUAGE CODE].po` to `/po/`.
5. Create a pull request with your translations.

# Building

## GNOME Builder
1. Install [GNOME Builder](https://flathub.org/apps/org.gnome.Builder).
2. Click "Clone Repository" with `https://github.com/kra-mo/cartridges.git` as the URL.
3. Click on the build button (hammer) at the top.

## For Windows
1. Install [MSYS2](https://www.msys2.org/).
2. From the MSYS2 shell, install the required dependencies listed [here](https://github.com/kra-mo/cartridges/blob/main/.github/workflows/ci.yml).
3. Build it via Meson.

## For macOS
1. Install [Homebrew](https://brew.sh/).
2. Using `brew` and `pip3`, install the required dependencies listed [here](https://github.com/kra-mo/cartridges/blob/main/.github/workflows/ci.yml).
3. Build it via Meson.

## Meson
```bash
git clone https://github.com/kra-mo/cartridges.git
cd cartridges
meson setup build
ninja -C build install
```

# Code style

All code is auto-formatted with [Black](https://github.com/psf/black) and linted with [Pylint](https://github.com/pylint-dev/pylint). Imports are sorted by [isort](https://github.com/pycqa/isort).

VSCode extensions are available for all of these and you can set them up with the following `settings.json` configuration:

```json
"python.formatting.provider": "none",
"[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
},
"isort.args":["--profile", "black"],
```

For other code editors, you can install them via `pip` and invoke them from the command line.
