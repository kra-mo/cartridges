python.install_sources(
    files('__init__.py', 'cover.py', 'game_item.py', 'window.py'),
    subdir: 'cartridges' / 'ui',
)

blueprints = custom_target(
    input: files('cover.blp', 'game-item.blp', 'window.blp'),
    output: '.',
    command: [
        blueprint_compiler,
        'batch-compile',
        '--minify',
        '@OUTPUT@',
        '@CURRENT_SOURCE_DIR@',
        '@INPUT@',
    ],
)

resource = configure_file(
    input: 'ui.gresource.xml.in',
    output: '@BASENAME@',
    configuration: conf,
)

gnome.compile_resources(
    'ui',
    resource,
    gresource_bundle: true,
    install: true,
    install_dir: pkgdatadir,
    dependencies: blueprints,
)
