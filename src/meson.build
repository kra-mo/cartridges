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

# TODO move to absolute imports = keep real structure, do not flatten

cartridges_sources = [
  '__init__.py',
  'main.py',
  'window.py',
  'preferences.py',
  'details_window.py',
  'game.py',
  'game_cover.py',
  'shared.py',
  'utils/steamgriddb.py',
  'utils/save_cover.py',
  'utils/create_dialog.py',

  # Added
  'importer/sources/lutris_source.py',
  'importer/importer.py',
  'importer/source.py',
  'utils/decorators.py',

  # TODO remove before merge
  'importers/bottles_importer.py',
  'importers/heroic_importer.py',
  'importers/itch_importer.py',
  'importers/lutris_importer.py',
  'importers/steam_importer.py',
  'utils/check_install.py'
]

install_data(cartridges_sources, install_dir: moduledir)
