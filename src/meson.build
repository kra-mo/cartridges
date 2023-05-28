moduledir = join_paths(pkgdatadir, 'cartridges')

configure_file(
  input: 'cartridges.in',
  output: 'cartridges',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

cartridges_sources = [
  configure_file(
    input: 'shared.py.in',
    output: 'shared.py',
    configuration: conf
  ),
  '__init__.py',
  'main.py',
  'window.py',
  'preferences.py',
  'details_window.py',
  'game.py',
  'game_cover.py',
  'importers/steam_importer.py',
  'importers/lutris_importer.py',
  'importers/heroic_importer.py',
  'importers/bottles_importer.py',
  'importers/itch_importer.py',
  'importers/legendary_importer.py',
  'utils/importer.py',
  'utils/steamgriddb.py',
  'utils/save_cover.py',
  'utils/create_dialog.py',
  'utils/check_install.py'
]

install_data(cartridges_sources, install_dir: moduledir)
