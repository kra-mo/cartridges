project(
    'cartridges',
    version: '49.0',
    meson_version: '>= 1.1.0',
    default_options: ['warning_level=2', 'werror=false'],
)

i18n = import('i18n')
gnome = import('gnome')
python = import('python').find_installation('python3')

blueprint_compiler = find_program('blueprint-compiler')
desktop_utils = find_program(
    'desktop-file-validate',
    required: false,
    disabler: true,
)
compile_schemas = find_program(
    'glib-compile-schemas',
    required: false,
    disabler: true,
)
appstreamcli = find_program('appstreamcli', required: false, disabler: true)

localedir = get_option('prefix') / get_option('localedir')
pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
bindir = get_option('prefix') / get_option('bindir')

profile = get_option('profile')
if profile == 'development'
    app_id = 'page.kramo.Cartridges.Devel'
    prefix = '/page/kramo/Cartridges/Devel'
elif profile == 'release'
    app_id = 'page.kramo.Cartridges'
    prefix = '/page/kramo/Cartridges'
endif

conf = configuration_data(
    {
        'PYTHON': python.full_path(),
        'APP_ID': app_id,
        'PREFIX': prefix,
        'PROFILE': profile,
        'LOCALEDIR': localedir,
        'PKGDATADIR': pkgdatadir,
        'BINDIR': bindir,
    },
)

subdir('data')
subdir('cartridges')
subdir('po')

gnome.post_install(
    glib_compile_schemas: true,
    gtk_update_icon_cache: true,
    update_desktop_database: true,
)
