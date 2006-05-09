from _mechanize import __version__

# high-level stateful browser-style interface
from _mechanize import Browser, \
     BrowserStateError, LinkNotFoundError, FormNotFoundError

# configurable URL-opener interface
from _useragent import UserAgent, HTTPProxyPasswordMgr
from _html import Link, \
     Factory, DefaultFactory, RobustFactory, \
     FormsFactory, LinksFactory, TitleFactory, \
     RobustFormsFactory, RobustLinksFactory, RobustTitleFactory

# urllib2 work-alike interface
# ...from urllib2...
URLError
HTTPError
GopherError
HTTPPasswordMgr
HTTPPasswordMgrWithDefaultRealm
AbstractBasicAuthHandler
# ...and from mechanize
from _Opener import OpenerDirector
from _urllib2_support import \
     Request, \
     build_opener, install_opener, urlopen, \
     OpenerFactory, urlretrieve, HeadParser, \
     RobotExclusionError

# handlers...
# ...from urllib2...
from urllib2 import BaseHandler, \
     ProxyHandler, \
     ProxyBasicAuthHandler, \
     ProxyDigestAuthHandler, \
     HTTPBasicAuthHandler, \
     HTTPDigestAuthHandler, \
     HTTPDefaultErrorHandler, \
     UnknownHandler, \
     FTPHandler, \
     CacheFTPHandler, \
     FileHandler, \
     GopherHandler, \
# ...and from mechanize
from _urllib2_support import \
     HTTPHandler, \
     HTTPRedirectHandler, \
     HTTPRequestUpgradeProcessor, \
     HTTPEquivProcessor, \
     SeekableProcessor, \
     HTTPCookieProcessor, \
     HTTPRefererProcessor, \
     HTTPRefreshProcessor, \
     HTTPErrorProcessor, \
     HTTPResponseDebugProcessor, \
     HTTPRedirectDebugProcessor, \
     HTTPRobotRulesProcessor
import httplib
if hasattr(httplib, 'HTTPS'):
    from _urllib2_support import HTTPSHandler
del httplib
#from _gzip import HTTPGzipProcessor

# misc
from _Util import http2time as str2time
# XXXXX sort out what people should be using!
from _Util import response_seek_wrapper

# cookies
from _ClientCookie import Cookie, CookiePolicy, DefaultCookiePolicy, \
     CookieJar, FileCookieJar, LoadError, request_host
from _LWPCookieJar import LWPCookieJar, lwp_cookie_str
from _MozillaCookieJar import MozillaCookieJar
from _MSIECookieJar import MSIECookieJar

# HTML HEAD element parsing
try:
    from _urllib2_support import XHTMLCompatibleHeadParser
except ImportError:
    pass

# If you hate the idea of turning bugs into warnings, do:
# import mechanize; mechanize.USE_BARE_EXCEPT = False
USE_BARE_EXCEPT = True
