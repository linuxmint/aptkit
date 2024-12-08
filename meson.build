project('aptkit', version : '1.0.3', meson_version : '>=0.49.0')

pymod = import('python')
python3 = pymod.find_installation('python3')

i18n = import('i18n')

gettext_package = meson.project_name()

prefix = get_option('prefix')
datadir = get_option('datadir')

podir = meson.source_root() / 'po'

subdir('data')
subdir('po')
subdir('aptkit')
