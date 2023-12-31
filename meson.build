project('cartridges',
          version: '2.7.2',
    meson_version: '>= 0.59.0',
  default_options: [ 'warning_level=2', 'werror=false', ],
)

i18n = import('i18n')
gnome = import('gnome')
python = import('python')

py_installation = python.find_installation('python3')

python_dir = join_paths(get_option('prefix'), py_installation.get_install_dir())
pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
libexecdir = join_paths(get_option('prefix'), get_option('libexecdir'))

profile = get_option('profile')
if profile == 'development'
  app_id = 'hu.kramo.Cartridges.Devel'
  prefix = '/hu/kramo/Cartridges/Devel'
elif profile ==  'release'
  app_id = 'hu.kramo.Cartridges'
  prefix = '/hu/kramo/Cartridges'
endif

conf = configuration_data()
conf.set('PYTHON', py_installation.full_path())
conf.set('PYTHON_VERSION', py_installation.language_version())
conf.set('APP_ID', app_id)
conf.set('PREFIX', prefix)
conf.set('VERSION', meson.project_version())
conf.set('PROFILE', profile)
conf.set('TIFF_COMPRESSION', get_option('tiff_compression'))
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)
conf.set('libexecdir', libexecdir)

subdir('data')
subdir('cartridges')
subdir('po')

if host_machine.system() == 'windows'
  subdir('windows')
else
  subdir('search-provider')
endif

gnome.post_install(
     glib_compile_schemas: true,
    gtk_update_icon_cache: true,
  update_desktop_database: true,
)