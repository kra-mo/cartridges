# Contributing

## Code
Fork the repository, make your changes, then create a pull request.

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
1. Install [GNOME Builder](https://flathub.org/apps/details/org.gnome.Builder).
2. Click "Clone Repository" with `https://github.com/kra-mo/cartridges.git` as the URL.
3. Click on the build button (hammer) at the top.

## For Windows
1. Install [MSYS2](https://www.msys2.org/).
2. From the MSYS2 shell, install the required dependencies listed [here](https://github.com/kra-mo/cartridges/blob/main/.github/workflows/windows.yml).
3. Build it via Meson

## Meson
```bash
git clone https://github.com/kra-mo/cartridges.git
cd cartridges
meson setup build
ninja -C build install
```
