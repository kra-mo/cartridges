desktop_file = configure_file(
    input: 'page.kramo.Cartridges.desktop.in',
    output: '@PLAINNAME@',
    configuration: conf,
)

desktop_file = i18n.merge_file(
    input: desktop_file,
    output: f'@app_id@.desktop',
    type: 'desktop',
    po_dir: '../po',
    install: true,
    install_dir: get_option('datadir') / 'applications',
)

test('Validate desktop file', desktop_utils, args: desktop_file)

configure_file(
    input: 'page.kramo.Cartridges.gschema.xml.in',
    output: f'@app_id@.gschema.xml',
    configuration: conf,
    install_dir: get_option('datadir') / 'glib-2.0' / 'schemas',
)

test(
    'Validate schema file',
    compile_schemas,
    args: ['--strict', '--dry-run', meson.current_source_dir()],
)

appstream_file = configure_file(
    input: 'page.kramo.Cartridges.metainfo.xml.in',
    output: '@PLAINNAME@',
    configuration: conf,
)

appstream_file = i18n.merge_file(
    input: appstream_file,
    output: f'@app_id@.metainfo.xml',
    po_dir: '../po',
    install: true,
    install_dir: get_option('datadir') / 'metainfo',
)

test(
    'Validate appstream file',
    appstreamcli,
    args: ['validate', '--no-net', '--explain', appstream_file],
)

configure_file(
    input: 'page.kramo.Cartridges.service.in',
    output: f'@app_id@.service',
    configuration: conf,
    install_dir: get_option('datadir') / 'dbus-1' / 'services',
)

configure_file(
    input: 'cartridges.in',
    output: '@BASENAME@',
    configuration: conf,
    install_dir: get_option('bindir'),
    install_mode: 'r-xr-xr-x',
)

resource = configure_file(
    input: 'data.gresource.xml.in',
    output: '@BASENAME@',
    configuration: conf,
)

gnome.compile_resources(
    'data',
    resource,
    gresource_bundle: true,
    install: true,
    install_dir: pkgdatadir,
    dependencies: appstream_file,
)

subdir('icons')
