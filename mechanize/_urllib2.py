# urllib2 work-alike interface
# ...from urllib2...
from urllib2 import \
     URLError, \
     HTTPError, \
     GopherError, \
     HTTPPasswordMgr, \
     HTTPPasswordMgrWithDefaultRealm, \
     AbstractBasicAuthHandler, \
     AbstractDigestAuthHandler
# ...and from mechanize
from _opener import OpenerDirector
from _auth import \
     HTTPProxyPasswordMgr, \
     ProxyHandler, \
     ProxyBasicAuthHandler, \
     ProxyDigestAuthHandler, \
     HTTPBasicAuthHandler, \
     HTTPDigestAuthHandler
from _urllib2_support import \
     Request, \
     build_opener, install_opener, urlopen, \
     OpenerFactory, urlretrieve, \
     RobotExclusionError

# handlers...
# ...from urllib2...
from urllib2 import \
     BaseHandler, \
     HTTPDefaultErrorHandler, \
     UnknownHandler, \
     FTPHandler, \
     CacheFTPHandler, \
     FileHandler, \
     GopherHandler
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
