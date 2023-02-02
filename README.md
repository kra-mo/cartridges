
<div align="center">
  <img src="data/icons/hicolor/scalable/apps/hu.kramo.Cartridges.svg" width="128" height="128">

  # Cartridges
  A GTK4 + Libadwaita game launcher

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
4. Install `org.gnome.Platform` from the [gnome-nightly repository](https://wiki.gnome.org/Apps/Nightly) if needed.

## Installation

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
Currently, translations can be added manually with the following steps:
1. Clone the repository.
2. If it isn't already there, add your language to `/po/LINGUAS`.
3. Create a new translation from the `/po/cartridges.pot` file with a program such as [Poedit](https://poedit.net/).
4. Save the file as `[YOUR LANGUAGE CODE].po` to `/po/`.
5. Create a pull request with your translations.
