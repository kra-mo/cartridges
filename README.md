
<div align="center">
  <img src="data/icons/hicolor/scalable/apps/hu.kramo.Cartridges.svg" width="128" height="128">

 # Cartridges
 A GTK4 + Libadwaita game launcher
  
[![Build status][github-actions-image]][github-actions-url]
[![Translation Status][weblate-image]][weblate-url]
[![Merged PRs][prs-merged-image]][prs-merged-url]
[![License][license-image]][license-url]
[![Code style][code-style-image]][code-style-url]
  
[github-actions-url]: https://github.com/kra-mo/cartridges
[github-actions-image]: https://img.shields.io/github/actions/workflow/status/kra-mo/cartridges/flatpak-builder.yml?branch=main&label=build
[prs-merged-url]: https://github.com/kra-mo/cartridges/pulls?q=is:pr+is:merged
[prs-merged-image]: https://img.shields.io/github/issues-pr-closed-raw/kra-mo/cartridges.svg?label=merged+PRs&color=green
[license-url]: https://github.com/kra-mo/cartridges/blob/main/LICENSE
[license-image]: https://img.shields.io/github/license/kra-mo/cartridges
[code-style-url]: https://github.com/psf/black
[code-style-image]: https://img.shields.io/badge/code%20style-black-000000?style=flat
[weblate-url]: https://hosted.weblate.org/projects/cartridges/cartridges
[weblate-image]: https://hosted.weblate.org/widgets/cartridges/-/cartridges/svg-badge.svg

  <img src="data/screenshot.webp">
</div>

# The Project
Cartridges is a simple game launcher written in Python using GTK4 + Libadwaita.
## Features
- Manually adding and editing games
- Importing games from Steam, Heroic and Bottles
- Hiding games
- Searching and sorting by title, date added and last played

# Installation

## Linux

### From Releases
1. Install `org.gnome.Platform` from the [gnome-nightly repository](https://wiki.gnome.org/Apps/Nightly) if needed.
2. Download the latest release from [Releases](https://github.com/kra-mo/cartridges/releases).
3. Install it via GNOME Software or `flatpak install hu.kramo.Cartridges.flatpak`.

## Windows

### From Releases
1. Download the latest release from [Releases](https://github.com/kra-mo/cartridges/releases).
2. Run the downloaded installer.

Note: Windows might present you with a warning when trying to install the app. This is expected, just ignore the warning.

# Building

## GNOME Builder

1. Download [GNOME Builder](https://flathub.org/apps/details/org.gnome.Builder).
2. Click "Clone Repository" with `https://github.com/kra-mo/cartridges.git` as the URL.
3. Click on the build button (hammer) at the top.

## Meson
```bash
git clone https://github.com/kra-mo/cartridges.git
cd cartridges
meson build
ninja -C build install
```

# Contributing

## Code
Fork the repository, make your changes, then create a pull request. 

## Translations
### Weblate
The project can be translated on [Weblate](https://hosted.weblate.org/projects/cartridges/).

### Manually
1. Clone the repository.
2. If it isn't already there, add your language to `/po/LINGUAS`.
3. Create a new translation from the `/po/cartridges.pot` file with a translation editor such as [Poedit](https://poedit.net/).
4. Save the file as `[YOUR LANGUAGE CODE].po` to `/po/`.
5. Create a pull request with your translations.
