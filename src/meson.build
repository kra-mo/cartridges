pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'cartridges')
gnome = import('gnome')

blueprints = custom_target('blueprints',
  input: files(
    'gtk/help-overlay.blp',
    'window.blp',
    'gtk/game.blp',
    'gtk/preferences.blp'
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@'],
)

gnome.compile_resources('cartridges',
  'cartridges.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
  dependencies: blueprints,
)

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
  'utils/steam_parser.py',
  'utils/heroic_parser.py',
  'utils/run_command.py',
  'utils/get_games.py',
  'utils/get_cover.py',
  'utils/save_games.py',
  'utils/save_cover.py',
  'utils/toggle_hidden.py',
  'utils/create_dialog.py',
  'utils/create_details_window.py'
]

install_data(cartridges_sources, install_dir: moduledir)
