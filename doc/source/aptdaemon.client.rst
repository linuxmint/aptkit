:mod:`aptkit.client` --- The client module
=============================================

Introduction
------------

Aptkit comes with a client module which provides a smoother interface on top
of the D-Bus interface. It provides GObjects of the daemon and each transaction.


.. _life_cycle:

Life cycle of a transaction based action
----------------------------------------

At first you initialize an AptClient instance.

    >>> from aptkit import client
    >>>
    >>> apt_client = client.AptClient()

Secondly you call the whished action, e.g. updating the package cache. It will
give you a new transaction instance.

    >>> transaction = apt_client.update()

The transaction has not been started yet. So you can make some further 
adjustements to it, e.g. setting a different language:

    >>> transaction.set_locale("de_DE")

... or setup the monitoring of the transaction:

    >>> transaction.connect("finished", on_transaction_finished)

You can then put the transaction on the queue by calling its :meth:`run()`
method:

    >>> transaction.run()

If you don't need the underlying transcation instance of an action, you can
alternatively set the wait argument to True. The AptClient method will return
after the transaction is done:

    >>> apt_client.update_cache(wait=True)

This can also be used with asynchronous programming, see below.


Asynchronous programming
------------------------

In the above examples simple synchronous calls have been made to the D-Bus. 
Until these calls return your whole application is blocked/frozen.
In the case of password prompts this can be quite long. So aptkit supports
the following asynchronous styles:

D-Bus style callbacks
^^^^^^^^^^^^^^^^^^^^^

Since the client module is basically a wrapper around D-Bus calls, it provides
a pair of reply_handler and error_handler for each method. You are perhaps
already familiar with those if you have written a Python D-Bus client before:

    >>> def run(trans):
    ...     trans.run(reply_handler=trans_has_started, error_handler=on_error)
    ...
    >>> def trans_has_started():
    ...     pass
    ...
    >>> def on_error(error):
    ...     raise error
    ...
    >>> client = AptClient()
    >>> client.update(reply_handler=run, error_handler=on_error)


Deferred callbacks
^^^^^^^^^^^^^^^^^^

Aptkit uses a simplified version of Twisted deferreds internally, called
python-defer. But you can also make use of them in your application.

The inline_callbacks decorator of python-defer allows to write asynchronous
code in a synchronous way:

    >>> @defer.inline_callbacks
    ... def update_cache():
    ...     apt_client = client.AptClient()
    ...     try:
    ...         transaction = yield apt_client.update()
    ...     except errors.NotAuthorizedError:
    ...         print "You are not allowed to update the cache!"
    ...         return
    ...     yield transaction.set_locale("de_DE")
    ...     yield transaction.run()
    ...     print "Transaction has started"


.. _chaining:

Chaining Transactions
---------------------

It is possible to chain transactions. This allows to add a simple
dependency relation, e.g. you want to add a new repository, update
the cache and finally install a new package.

        >>> client = aptkit.client.AptClient()
        >>> trans1 = client.add_repository("deb", [...])
        >>> trans2 = client.update_cache()
        >>> trans3 = client.install_packages(["new-package"])
        >>> trans2.run_after(trans1)
        >>> trans3.run_after(trans2)
        >>> trans1.run()

If a transaction in a chain fails all other ones which follow will
fail too with the :data:`enums.EXIT_PREVIOUS_FAILED` exit state.

Class Reference
---------------

.. autoclass:: aptkit.client.AptClient
    :members:

.. autoclass:: aptkit.client.AptTransaction
    :members:

Function Reference
------------------

.. autofunction:: aptkit.client.get_transaction

.. autofunction:: aptkit.client.get_aptkit
