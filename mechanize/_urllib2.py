# urllib2 work-alike interface
# ...from urllib2...
from urllib2 import \
     URLError, \
     HTTPError
# ...and from mechanize
from _auth import \
     HTTPPasswordMgr, \
     HTTPPasswordMgrWithDefaultRealm, \
     AbstractBasicAuthHandler, \
     AbstractDigestAuthHandler, \
     HTTPProxyPasswordMgr, \
     ProxyHandler, \
     ProxyBasicAuthHandler, \
     ProxyDigestAuthHandler, \
     HTTPBasicAuthHandler, \
     HTTPDigestAuthHandler, \
     HTTPSClientCertMgr
from _debug import \
     HTTPResponseDebugProcessor, \
     HTTPRedirectDebugProcessor
from _file import \
     FileHandler
# crap ATM
## from _gzip import \
##      HTTPGzipProcessor
from _urllib2_fork import \
     HTTPHandler, \
     HTTPDefaultErrorHandler, \
     HTTPRedirectHandler, \
     HTTPCookieProcessor, \
     HTTPErrorProcessor, \
     BaseHandler, \
     UnknownHandler, \
     FTPHandler, \
     CacheFTPHandler
from _http import \
     HTTPEquivProcessor, \
     HTTPRefererProcessor, \
     HTTPRefreshProcessor, \
     HTTPRobotRulesProcessor, \
     RobotExclusionError
import httplib
if hasattr(httplib, 'HTTPS'):
    from _urllib2_fork import HTTPSHandler
del httplib
from _opener import OpenerDirector, \
     SeekableResponseOpener, \
     build_opener, install_opener, urlopen
from _request import \
     Request
from _seek import \
     SeekableProcessor
from _upgrade import \
     HTTPRequestUpgradeProcessor, \
     ResponseUpgradeProcessor
