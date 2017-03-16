Advanced topics
==================

Thread safety
---------------

The global `mechanize.urlopen()` and `mechanize.urlretrieve()` functions are
thread safe. However, mechanize browser instances **are not** thread safe. If
you want to use a mechanize Browser instance in multiple threads, clone it,
using `copy.copy(browser_object)` method. The clone will share the same,
thread safe cookie jar, and have the same settings/handlers as the original,
but all other state is not shared, making the clone safe to use in a different
thread.

Using custom CA certificates
-------------------------------

mechanize supports the same mechanism for using custom CA certificates as
python >= 2.7.9. To change the certificates a mechanize browser instance uses,
call the `set_ca_data()` method on it. This method accepts the same arguments
as the `SSLContext.load_verify_locations() <https://docs.python.org/2/library/ssl.html#ssl.SSLContext.load_verify_locations>`_
method from the python standard library. You can also pass a pre-built context
via the `context` keyword argument. Note that to use this feature, you
must be using python >= 2.7.9.


