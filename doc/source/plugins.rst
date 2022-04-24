Plugins
=======

Aptdaemon provides a plugin mechanism by making use of setuptools' entry points.
The group name is ``aptdaemon.plugins``. 

Cache modifiers
---------------

Currently there are two types of plugins available which allow you to modify 
the marked changes of a transaction. Each plugin can be a function which 
accepts the resolver (apt.cache.ProblemResolver) and the cache (apt.cache.Cache)
as arguments:

 * *modify_cache_before*
   The plugged-in function is called after the intentional changes of the
   transaction have been marked, but before the dependencies have been resolved.

 * *modify_cache_after*
   The plugged-in function is called after the dependency resolution of the
   transaction. The resolver will be called again afterwards.
 
A short overview of the steps required to process a transaction:

 1. Mark intentional changes (e.g. the to be installed packages of a
    InstallPackages transaction)
 2. Call all modify_cache_before plugins
 3. Run the dependency resolver
 4. Call all modify_cache_after_plugins and re-run the resolver
 5. Commit changes


External helpers
----------------

There is also the *get_license_key* plugin which allows to retrieve the license
key content and path to store. License keys are required by propriatary
software. The plugged-in function gets called with uid of the user who started
the transaction, the package name, a JSON OAuth tocken and the name of a
server to query.

Example
-------

Here is an example which would install language packages :file:`./plugins/aptd.py`:

>>> def install_language_packs(resolver, cache):
>>>     """Marks the required language packs for installation."""
>>>     #... do the magic here ...
>>>     language_pack.mark_install(False, True)
>>>     # Only protect your changes if they are mantadory. If they cannot be
>>>     # be installed the transaction will fail.
>>>     resolver.clear(language_pack)
>>>     resolver.protect(language_pack)

Finally you would have to register your function as entry point in :file:`setup.py`:

>>> setup(
>>> ...
>>> entry_points="""[aptdaemon.plugins]
>>> modify_cache_after=plugins.aptd:install_language_packs
>>> """,
>>> ...
>>> )

.. note::
    Keep in mind that you can only register one entry point per name/plugin per
    distribution.
