import gi
gi.require_version('Gtk', '3.0')
gi.require_version('XApp', '1.0')
from gi.repository import Gtk, XApp

import apt
import aptkit.client
import aptkit.enums
import aptkit.errors
import aptkit.gtk3widgets

class SimpleAPTClient(object):

    def __init__(self, parent_window=None):
        self.parent_window = parent_window
        self.progress_callback = None
        self.finished_callback = None
        self.error_callback = None
        self.cancelled_callback = None

    def set_progress_callback(self, progress_callback):
        self.progress_callback = progress_callback

    def set_finished_callback(self, finished_callback):
        self.finished_callback = finished_callback

    def set_error_callback(self, error_callback):
        self.error_callback = error_callback

    def set_cancelled_callback(self, cancelled_callback):
        self.cancelled_callback = cancelled_callback

    def update_cache(self):
        client = aptkit.client.AptClient()
        update_transaction = client.update_cache()
        self._run_transaction(update_transaction)

    def install_file(self, path):
        client = aptkit.client.AptClient()
        client.install_file(path, force=True, wait=False, reply_handler=self._simulate_trans, error_handler=self._on_error)

    def install_packages(self, packages, use_apt_resolver=True):
        if use_apt_resolver:
            # Use the resolver from python-apt
            # it works better in complex scenarios
            # mark the packages as mark_install
            cache = apt.Cache()
            for name in packages:
                try:
                    pkg = cache[name]
                    pkg.mark_install()
                except:
                    print(f"Package {name} not found in the cache!")
            # then find out all the resulting installations
            # via cache.get_changes()
            changes = cache.get_changes()
            for pkg in changes:
                if pkg.marked_install and pkg.name not in packages:
                    packages.append(pkg.name)

        client = aptkit.client.AptClient()
        client.install_packages(packages, reply_handler=self._simulate_trans, error_handler=self._on_error)

    def remove_packages(self, packages):
        client = aptkit.client.AptClient()
        client.remove_packages(packages, reply_handler=self._simulate_trans, error_handler=self._on_error)

    def downgrade_packages(self, versioned_packages):
        client = aptkit.client.AptClient()
        client.commit_packages(install=None, reinstall=None, remove=None, purge=None, upgrade=None, downgrade=versioned_packages,
                               reply_handler=self._simulate_trans, error_handler=self._on_error)

    def _run_transaction(self, transaction):
        if self.progress_callback is None:
            dia = aptkit.gtk3widgets.AptProgressDialog(transaction, parent=self.parent_window)
            dia.run(close_on_finished=True, show_error=True, reply_handler=lambda: True, error_handler=self._on_error)
            transaction.connect("finished", self._on_finish)
        else:
            SimpleAptKitTransaction(transaction, self.progress_callback, self.finished_callback, self.error_callback, self.parent_window)

    def _simulate_trans(self, trans):
        trans.simulate(reply_handler=lambda: self._confirm_deps(trans), error_handler=self._on_error)

    def _confirm_deps(self, trans):
        try:
            if [pkgs for pkgs in trans.dependencies if pkgs]:
                dia = aptkit.gtk3widgets.AptConfirmDialog(trans, parent=self.parent_window)
                res = dia.run()
                dia.hide()
                if res != Gtk.ResponseType.OK:
                    if self.cancelled_callback is not None:
                        self.cancelled_callback()
                    return
            self._run_transaction(trans)
        except Exception as e:
            print(e)

    def _on_error(self, error):
        if isinstance(error, aptkit.errors.NotAuthorizedError):
            if self.cancelled_callback is not None:
                self.cancelled_callback()
            return
        elif not isinstance(error, aptkit.errors.TransactionFailed):
            # Catch internal errors of the client
            error = aptkit.errors.TransactionFailed(aptkit.enums.ERROR_UNKNOWN, str(error))
        dia = aptkit.gtk3widgets.AptErrorDialog(error)
        dia.run()
        dia.hide()

    def _on_finish(self, transaction, exit_state):
        if self.finished_callback is not None:
            self.finished_callback(transaction, exit_state)

class SimpleAptKitTransaction():

    def __init__(self, transaction, progress_callback, finished_callback, error_callback, parent_window):
        self.progress_callback = progress_callback
        self.finished_callback = finished_callback
        self.error_callback = error_callback
        self.transaction = transaction
        self.parent_window = parent_window
        transaction.set_debconf_frontend("gnome")
        transaction.connect("progress-changed", self.on_transaction_progress)
        # transaction.connect("cancellable-changed", self.on_driver_changes_cancellable_changed)
        transaction.connect("finished", self.on_transaction_finish)
        transaction.connect("error", self.on_transaction_error)
        transaction.run()

    def on_transaction_progress(self, transaction, progress):
        if self.progress_callback is not None:
            self.progress_callback(progress)
        if self.parent_window is not None:
            XApp.set_window_progress(self.parent_window, progress)

    def on_transaction_error(self, transaction, error_code, error_details):
        if self.error_callback is not None:
            self.error_callback(error_code, error_details)
        if self.parent_window is not None:
            XApp.set_window_progress(self.parent_window, 0)

    def on_transaction_finish(self, transaction, exit_state):
        if (exit_state == aptkit.enums.EXIT_SUCCESS):
            if self.finished_callback is not None:
                self.finished_callback(transaction, exit_state)
