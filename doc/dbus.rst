The D-Bus API of the aptkit
==============================

Aptkit provides two D-Bus interfaces on the system bus.

org.aptkit --- The aptkit interface
------------------------------------------

This is the main interface which allows you to perform package managing tasks. 
It is proivded by the aptkit object at ``/org/aptkit``. 

There are two kind of tasks: ones which are performed immediately and ones 
which are queued up in transaction and performed in a sequence.

Non-transaction based methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automethod:: aptkit.core.AptKit.GetTrustedVendorKeys() -> array(string)

.. automethod:: aptkit.core.AptKit.Quit()


Transaction based methos
^^^^^^^^^^^^^^^^^^^^^^^^

Instead of performing the task immediately, a new transaction will be created
and the method will return the D-Bus path of it. Afterwards you can simulate
the transaction or put it on the queue.

:ref:`life_cycle` and :ref:`chaining` are described in the Python client
documentation with code examples.

.. automethod:: aptkit.core.AptKit.UpdateCache() -> string

.. automethod:: aptkit.core.AptKit.UpdateCachePartially(sources_list : string) -> string

.. automethod:: aptkit.core.AptKit.AddRepository(src_type : string, uri : string, dist : string, comps : array(string), comment : string, sourcesfile : string) -> string

.. automethod:: aptkit.core.AptKit.EnableDistroComponent(component : string) -> string

.. automethod:: aptkit.core.AptKit.InstallFile(path : string, force : boolean) -> string

.. automethod:: aptkit.core.AptKit.InstallPackages(package_names : array(string)) -> string

.. automethod:: aptkit.core.AptKit.RemovePackages(package_names : array(string)) -> string

.. automethod:: aptkit.core.AptKit.UpgradePackages(package_names : array(string)) -> string

.. automethod:: aptkit.core.AptKit.CommitPackages(install : array(string), reinstall : array(string), remove : array(string), purge : array(string), upgrade : array(string), downgrade : array(string)) -> string

.. automethod:: aptkit.core.AptKit.UpgradeSystem(safe_mode : boolean) -> string

.. automethod:: aptkit.core.AptKit.FixIncompleteInstall() -> string

.. automethod:: aptkit.core.AptKit.FixBrokenDepends() -> string

.. automethod:: aptkit.core.AptKit.AddVendorKeyFromKeyserver(keyid : string, keyserver : string) -> string

.. automethod:: aptkit.core.AptKit.AddVendorKeyFromFile(path : string) -> string


Signals
^^^^^^^

The following singal can be emitted on the org.aptkit interface.

.. automethod:: aptkit.core.AptKit.ActiveTransactionsChanged(current : string, queued : array(string))

Properties
^^^^^^^^^^

The daemon interface provides a set of properties which can be accessed and modified through :meth:`Set()`, :meth:`Get()` and :meth:`GetAll()` methods of the ``org.freedesktop.DBus.Properties`` interface.
See the `D-Bus specification <http://dbus.freedesktop.org/doc/dbus-specification.html#standard-interfaces-properties>`_ for more details.

The following properties are available:

.. attribute:: AutoCleanInterval : i

    The interval in days in which the cache of downloaded packages should
    should be cleaned. A value of 0 disables this feature.

    *writable*


.. attribute:: AutoDownload : b

    If available upgrades should be already downloaded in the background.
    The upgrades won't get installed automatically.

    *writable*

.. attribute:: AutoUpdateInterval : i
   
    The interval in days in which the software repositories should be checked
    for updates. A value of 0 disables the automatic check.

    *writable*

.. attribute:: PopConParticipation : b

    If statistics about installed software and how often it is used should be
    sent to the distribution anonymously. This helps to determine which
    software should be shipped on the first install CDROMs and to make software
    recommendations.

    *writable*

.. attribute:: UnattendedUpgrade : i

    The interval in days in which updates should be installed
    automatically. A value of 0 disables this feature.

    *writable*

.. attribute:: RebootRequired : b

   Set if a reboot is required in order to complete the update.

    *readonly*


org.aptkit.transaction --- The transaction interface
--------------------------------------------------------

This is the main interface of a transaction object. It allows to control and
monitor the transaction. Transactions are created by using the org.aptkit
interface of aptkit.

The path of a transaction object consists of ``/org/aptkit/transaction/`` and an unique identifier.

Methods
^^^^^^^

.. automethod:: aptkit.core.Transaction.Run()

.. automethod:: aptkit.core.Transaction.RunAfter(tid : string)

.. automethod:: aptkit.core.Transaction.Cancel()

.. automethod:: aptkit.core.Transaction.Simulate()

.. automethod:: aptkit.core.Transaction.ProvideMedium(medium : string)

.. automethod:: aptkit.core.Transaction.ResolveConfigFileConflict(config : string, answer : string)

Signals
^^^^^^^

.. automethod:: aptkit.core.Transaction.Finished() -> string

.. automethod:: aptkit.core.Transaction.PropertyChanged() -> string, variant

Properties
^^^^^^^^^^

The transaction interface provides a set of properties which can be accessed and modified through :meth:`Set()`, :meth:`Get()` and :meth:`GetAll()` methods of the ``org.freedesktop.DBus.Properties`` interface.
See the `D-Bus specification <http://dbus.freedesktop.org/doc/dbus-specification.html#standard-interfaces-properties>`_ for more details.

For the documentation of the available string enumerations, see :mod:`aptkit.enums`.

The following properties are available:


.. attribute:: AllowUnauthenticated : b

    If it is allowed to install not authenticated packages by the transaction.
    Defaults to False.

    *writable*

.. attribute:: Cancellable : b

    If the transaction can be cancelled at the moment.

    *read-only*

.. attribute:: ConfigFileConflict : (ss)

    If the transaction waits for the resolution of a configuration file
    conflict, this property contains an array of the path to the old and
    the path to the new configuration file. See
    :meth:`ResolveConfigFileConflict()`.

    *read-only*
 
.. attribute:: DebconfSocket : s

    The path to the socket which should be used to proxy debconf communication
    to the user.

    *writable*

.. attribute:: Dependencies : (asasasasasasas)

    Array of package groups which will be modified as dependencies:

    * array of the packages to install
    * array of the packages to re-install
    * array of the packages to remove
    * array of the packages to purge
    * array of the packages to upgrade
    * array of the packages to downgrade
    * array of the packages to not upgrade (keep)

    The packages are specified by their name and a version number
    separated by an "=", e.g. "xterm=261-1".
    The dependencies are calculated after :meth:`Simulate()` or :meth:`Run()`
    was called.

    *read-only*

.. attribute:: Download : x

    The required download size in Bytes.

    The property is available after :meth:`Simulate()` or :meth:`Run()` has
    been called.

    *read-only*

.. attribute:: Error : (ss)

    If the transaction failed this property contains an array of the error
    code, e.g. ``error-no-lock`` and a detailed error message.

    *read-only*

.. attribute:: ExitState : s

    If the transaction is completed it contains the exit status enum of
    the transaction, e.g. ``exit-failed``. If the transaction has not yet
    been completed it is ``exit-unfinished``.

    *read-only*

.. attribute:: HttpProxy : s

    The URL of an http proxy which should be used for downloads by
    the transaction, e.g. ``http://proxy:8080``.

    *writable*

.. attribute:: Locale : s

    The locale which is used to translate messages, e.g. ``de_DE@UTF-8``.

    *writable*

.. attribute:: MetaData : a{sv}

    The meta data dictionary allows client applications to store additional
    data persistently in the transaction object. The key has to be a string
    and be prefixed by an underscore separated identifier of the client 
    application, e.g. Software Center uses ``sc_app`` to store the application
    corresponding to the transaction.

    If a dict is written to the property it will be merged with the existing
    one. It is not allowed to override already existing keys.

    *writable*

.. attribute:: Progress : i
   
    The progress in percent of the transaction.

    *read-only*

.. attribute:: Packages : (asasasasasas)

    Array of package groups which have been specified by the user intially
    to be modified:

    * array of the packages to install
    * array of the packages to re-install
    * array of the packages to remove
    * array of the packages to purge
    * array of the packages to upgrade
    * array of the packages to downgrade

    The packages are specified by their name and an optional version number
    separated by an "=", e.g. "xterm=261-1". Furthermore if specified the
    target release of the package will be separated by a "/", e.g.
    "xterm/experimental".

    *read-only*

.. attribute:: Paused : b

    If the transaction is paused, e.g. it is waiting for a medium or the
    resolution of a configuration file conflict.

    *read-only*

.. attribute:: ProgressDetails : (iixxdx)

    A list with detailed progress information:

    * number of already processed items
    * number of total items
    * number of already downloaded bytes
    * number of total bytes which have to be downloaded
    * number of bytes downloaded per second
    * remaining time in seconds

    *read-only*

.. attribute:: ProgressDownload : (sssxxs)

    The last progress information update of a currently running download.
    A list of ..

    * URL of the download
    * status enum of the download, e.g. ``download-fetching``.
    * short description of the download
    * number of already downloaded bytes
    * number of total bytes which have to be downloaded
    * Status message

    *read-only*

.. attribute:: RemoveObsoletedDepends : b

    If in the case of a removal obsolete dependencies which have been installed
    automatically before should be removed, too.
    *writable*

.. attribute:: RequiredMedium : (ss)

    If the transaction waits for a medium to be inserted this property contains
    an array of the medium name and the path to the drive in which
    it should be inserted.
    *read-only*

.. attribute:: Role : s

    The enum representing the type of action performed by the transaction e.g.
    ``role-install-packages``.
    *read-only*

.. attribute:: Space : x

    The required disk space in Bytes. If disk spaces is freed the value will
    be negative.

    The property is available after :meth:`Simulate()` or :meth:`Run()` has
    been called.

    *read-only*

.. attribute:: Status : s
  
    The status enum of the transaction, e.g. ``status-loading-cache``.

    *read-only*

.. attribute:: StatusDetails : s
 
    A human readable string with additional download information.

    *read-only*

.. attribute:: Terminal : s

    The path to the slave end of the controlling terminal which should be
    used to controll the underlying :command:`dpkg` call.

    *writable*

.. attribute:: TerminalAttached : b

    If the controlling terminal can be used to control the underlying
    :command:`dpkg` call.

    *read-only*

.. attribute:: Unauthenticated : as

    List of packages which are going to be installed but are not from an
    authenticated repository.

    *read-only*


.. _policykit:

PolicyKit privileges
--------------------

Most actions require the user to authenticate. The PolicyKit
framework is used by aptkit for the authentication process.
This allows to run aptkit as root and the client application as normal user.

For non-transaction based actions the authentication will happen immediately. 
For transaction based actions the privilege will be checked after :meth:`Run()`
has been called. If the privilege has not yet been granted the user will
be requested to authenticate interactively. 
This allows the user to simulate a transaction before having to
authenticate.

Aptkit supports so called high level privileges which allow to perform
a specified set of actions in a row without having to authenticate for each
one separately. This only works if the client application authenticates for 
the high level privilge before running the transactions and the authentication
is cached.

There are two high level privileges ``install-packages-from-new-repo`` and
``install-purchased-software``. Both allow to add a repository, install the
key of vendor from a keyserver, update the cache and to install packages.

.. literalinclude:: ../examples/chained.py
