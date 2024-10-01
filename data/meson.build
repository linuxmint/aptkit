i18n.merge_file(
    input: 'org.aptkit.policy.in',
    output: 'org.aptkit.policy',
    po_dir: podir,
    type: 'xml',
    install: true,
    install_dir: datadir / 'polkit-1/actions',
)

install_data(['20aptkit'], install_dir : '/etc/apt/apt.conf.d/')
install_data(['org.aptkit.conf'], install_dir: datadir / 'dbus-1/system.d/')
install_data(['org.aptkit.service'], install_dir: datadir / 'dbus-1/system-services/')

install_man('aptk.1')
install_man('aptkcon.1')
install_man('org.aptkit.7')
install_man('org.aptkit.transaction.7')

install_subdir('icons/16x16', install_dir : datadir / 'icons/hicolor/')
install_subdir('icons/22x22', install_dir : datadir / 'icons/hicolor/')
install_subdir('icons/24x24', install_dir : datadir / 'icons/hicolor/')
install_subdir('icons/48x48', install_dir : datadir / 'icons/hicolor/')
