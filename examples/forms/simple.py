#!/usr/bin/env python

from urllib2 import urlopen
from mechanize import ParseResponse

response = urlopen("http://wwwsearch.sourceforge.net/ClientForm/example.html")
forms = ParseResponse(response, backwards_compat=False)
form = forms[0]
print form
form["comments"] = "Thanks, Gisle"

# form.click() returns a urllib2.Request object
# (see HTMLForm.click.__doc__ if you don't have urllib2)
print urlopen(form.click()).read()
