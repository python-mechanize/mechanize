from _mechanize import __version__

# high-level stateful browser-style interface
from _mechanize import \
     Browser, \
     BrowserStateError, LinkNotFoundError, FormNotFoundError

# configurable URL-opener interface
from _useragent import UserAgent
from _html import \
     Link, \
     Factory, DefaultFactory, RobustFactory, \
     FormsFactory, LinksFactory, TitleFactory, \
     RobustFormsFactory, RobustLinksFactory, RobustTitleFactory

# urllib2 work-alike interface (part from mechanize, part from urllib2)
from _urllib2 import *

# misc
from _util import http2time as str2time
from _util import response_seek_wrapper, make_response
from _urllib2_support import HeadParser
try:
    from _urllib2_support import XHTMLCompatibleHeadParser
except ImportError:
    pass
#from _gzip import HTTPGzipProcessor  # crap ATM


# cookies
from _clientcookie import Cookie, CookiePolicy, DefaultCookiePolicy, \
     CookieJar, FileCookieJar, LoadError, request_host
from _lwpcookiejar import LWPCookieJar, lwp_cookie_str
from _mozillacookiejar import MozillaCookieJar
from _msiecookiejar import MSIECookieJar

# If you hate the idea of turning bugs into warnings, do:
# import mechanize; mechanize.USE_BARE_EXCEPT = False
USE_BARE_EXCEPT = True
