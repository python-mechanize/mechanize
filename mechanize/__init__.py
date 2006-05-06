from _mechanize import Browser, \
     BrowserStateError, LinkNotFoundError, FormNotFoundError, \
     __version__

from _useragent import UserAgent, HTTPProxyPasswordMgr

from _html import Link, \
     Factory, DefaultFactory, RobustFactory, \
     FormsFactory, LinksFactory, TitleFactory, \
     RobustFormsFactory, RobustLinksFactory, RobustTitleFactory

# If you hate the idea of turning bugs into warnings, do:
# import mechanize; mechanize.USE_BARE_EXCEPT = False
USE_BARE_EXCEPT = True

from _ClientCookie import Cookie, CookiePolicy, DefaultCookiePolicy, \
     CookieJar, FileCookieJar, LoadError, request_host
from _LWPCookieJar import LWPCookieJar, lwp_cookie_str
from _MozillaCookieJar import MozillaCookieJar
from _MSIECookieJar import MSIECookieJar
from _urllib2_support import \
     Request, \
     build_opener, install_opener, urlopen, \
     OpenerFactory, urlretrieve, BaseHandler, HeadParser, \
     RobotExclusionError
from _Opener import OpenerDirector
try:
    from _urllib2_support import XHTMLCompatibleHeadParser
except ImportError:
    pass
from _urllib2_support import \
     HTTPHandler, HTTPRedirectHandler, \
     HTTPRequestUpgradeProcessor, \
     HTTPEquivProcessor, SeekableProcessor, HTTPCookieProcessor, \
     HTTPRefererProcessor, \
     HTTPRefreshProcessor, HTTPErrorProcessor, \
     HTTPResponseDebugProcessor, HTTPRedirectDebugProcessor, \
     HTTPRobotRulesProcessor

import httplib
if hasattr(httplib, 'HTTPS'):
    from _urllib2_support import HTTPSHandler
del httplib

from _Util import http2time as str2time
from _Util import response_seek_wrapper
