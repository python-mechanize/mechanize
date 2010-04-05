#!/usr/bin/env python

import sys

from mechanize import ParseResponse, urlopen, urljoin

if len(sys.argv) == 1:
    uri = "http://wwwsearch.sourceforge.net/"
else:
    uri = sys.argv[1]

response = urlopen(urljoin(uri, "mechanize/example.html"))
forms = ParseResponse(response, backwards_compat=False)
form = forms[0]
print form
form["comments"] = "Thanks, Gisle"

# form.click() returns a mechanize.Request object
# (see HTMLForm.click.__doc__ if you want to use only the forms support, and
# not the rest of mechanize)
print urlopen(form.click()).read()
