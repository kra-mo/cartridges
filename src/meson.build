moduledir = join_paths(pkgdatadir, 'src')

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

install_subdir('importer', install_dir: moduledir)
install_subdir('importers', install_dir: moduledir)
install_subdir('utils', install_dir: moduledir)
install_subdir('store', install_dir: moduledir)
install_data(
  [
    'main.py',
    'window.py',
    'preferences.py',
    'details_window.py',
    'game.py',
    'game_cover.py',
    'shared.py',
  ],
  install_dir: moduledir
)