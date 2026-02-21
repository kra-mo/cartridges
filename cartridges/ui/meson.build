python.install_sources(
    files(
        '__init__.py',
        'closures.py',
        'collection_details.py',
        'collections.py',
        'cover.py',
        'game_details.py',
        'game_item.py',
        'games.py',
        'sources.py',
        'template.py',
        'window.py',
    ),
    subdir: 'cartridges' / 'ui',
)

blueprints = custom_target(
    input: files(
        'collection-details.blp',
        'cover.blp',
        'game-details.blp',
        'game-item.blp',
        'window.blp',
    ),
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

shortcuts_dialog_blueprint = custom_target(
    input: host_machine.system() == 'darwin' ? 'shortcuts-dialog-mac.blp' : 'shortcuts-dialog.blp',
    output: 'shortcuts-dialog.ui',
    command: [
        blueprint_compiler,
        'compile',
        '--minify',
        '--output',
        '@OUTPUT@',
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
    dependencies: [blueprints, shortcuts_dialog_blueprint],
)
