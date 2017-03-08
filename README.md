mechanize - Automate interaction with HTTP web servers
----------------------------------------------------------

Major features
================

Stateful programmatic web browsing in Python, after Andy Lester's Perl
module [`WWW::Mechanize`](http://search.cpan.org/dist/WWW-Mechanize/).

  * `mechanize.Browser` and `mechanize.UserAgentBase` implement the
    interface of `urllib2.OpenerDirector`, so:

      * any URL can be opened, not just `http:`

      * `mechanize.UserAgentBase` offers easy dynamic configuration of
        user-agent features like protocol, cookie, redirection and
        `robots.txt` handling, without having to make a new
        `OpenerDirector` each time, e.g. by calling `build_opener()`.

  * Easy HTML form filling.

  * Convenient link parsing and following.

  * Browser history (`.back()` and `.reload()` methods).

  * The `Referer` HTTP header is added properly (optional).

  * Automatic observance of
    [`robots.txt`](http://www.robotstxt.org/wc/norobots.html).

  * Automatic handling of HTTP-Equiv and Refresh.


Installation
==============

To install for normal usage:
```
sudo pip2 install mechanize
```

To install for development:
```
git clone https://github.com/python-mechanize/mechanize.git
cd mechanize
sudo pip2 install -e
```

To install manually, simply add the `mechanize` sub-directory somwhere on your
`PYTHONPATH`.
