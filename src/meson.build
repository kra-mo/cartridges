moduledir = join_paths(pkgdatadir, 'cartridges')

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'cartridges.in',
  output: 'cartridges',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

cartridges_sources = [
  '__init__.py',
  'main.py',
  'window.py',
  'preferences.py',
  'game.py',
  'utils/importer.py',
  'utils/steamgriddb.py',
  'utils/steam_parser.py',
  'utils/lutris_parser.py',
  'utils/heroic_parser.py',
  'utils/bottles_parser.py',
  'utils/itch_parser.py',
  'utils/get_games.py',
  'utils/save_game.py',
  'utils/save_cover.py',
  'utils/create_dialog.py',
  'utils/create_details_window.py'
]

install_data(cartridges_sources, install_dir: moduledir)
