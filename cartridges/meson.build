python.install_sources(
    files('__init__.py', '__main__.py', 'application.py', 'games.py'),
    subdir: 'cartridges',
)

configure_file(
    input: 'config.py.in',
    output: '@BASENAME@',
    configuration: conf,
    install_dir: python.get_install_dir(subdir: 'cartridges'),
)

subdir('ui')
