
<div align="center">
  <img src="data/icons/hicolor/scalable/apps/hu.kramo.Cartridges.svg" width="128" height="128">

  # Cartridges
  A GTK4 + Libadwaita game launcher

  <a href="https://github.com/kra-mo/cartridges/actions"><img src="https://img.shields.io/github/actions/workflow/status/kra-mo/cartridges/flatpak-builder.yml?style=for-the-badge"></a>
  <a href="https://hosted.weblate.org/projects/cartridges/"><img src="https://img.shields.io/weblate/progress/cartridges?style=for-the-badge"></a>
  <a href="https://www.gnu.org/licenses/gpl-3.0.html"><img src="https://img.shields.io/github/license/kra-mo/cartridges?style=for-the-badge"></a>
  <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000?style=for-the-badge"></a>

  <img src="data/screenshot.webp">
</div>


## The Project
Cartridges is a simple game launcher written in Python using GTK4 + Libadwaita.
### Features
- Manually adding and editing games
- Importing games from Steam, Heroic and Bottles
- Hiding games
- Searching and sorting by title, date added and last played

## Building

### GNOME Builder

1. Download [GNOME Builder](https://flathub.org/apps/details/org.gnome.Builder).
2. Click "Clone Repository" with `https://github.com/kra-mo/game-shelf.git` as the URL.
3. Click on the build button (hammer) at the top.

## Installation

### Latest Build From GitHub Actions
1. Install `org.gnome.Platform` from the [gnome-nightly repository](https://wiki.gnome.org/Apps/Nightly) if needed.
2. Download the artifact from the latest workflow run.
3. Decompress the archive.
4. Install it via GNOME Software or `flatpak install hu.kramo.Cartridges.flatpak`.

### From Releases
1. Install `org.gnome.Platform` from the [gnome-nightly repository](https://wiki.gnome.org/Apps/Nightly) if needed.
2. Download the latest release from Releases.
3. Install it via GNOME Software or `flatpak install hu.kramo.Cartridges.flatpak`.

### From GNOME Builder
Click the down arrow next to the hammer at the top of your GNOME Builder window, then click "Export". This will create a flatpak that then can be installed on your system.

## Contributing

### Code
Fork the repository, make your changes, then create a pull request. 

### Translations
#### Weblate
The project can be translated on [Weblate](https://hosted.weblate.org/projects/cartridges/).

#### Manually
1. Clone the repository.
2. If it isn't already there, add your language to `/po/LINGUAS`.
3. Create a new translation from the `/po/cartridges.pot` file with a translation editor such as [Poedit](https://poedit.net/).
4. Save the file as `[YOUR LANGUAGE CODE].po` to `/po/`.
5. Create a pull request with your translations.
