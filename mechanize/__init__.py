__all__ = [
    'AbstractBasicAuthHandler',
    'AbstractDigestAuthHandler',
    'BaseHandler',
    'Browser',
    'BrowserStateError',
    'CacheFTPHandler',
    'ContentTooShortError',
    'Cookie',
    'CookieJar',
    'CookiePolicy',
    'DefaultCookiePolicy',
    'FTPHandler',
    'Factory',
    'FileCookieJar',
    'FileHandler',
    'FormNotFoundError',
    'HTTPBasicAuthHandler',
    'HTTPCookieProcessor',
    'HTTPDefaultErrorHandler',
    'HTTPDigestAuthHandler',
    'HTTPEquivProcessor',
    'HTTPError',
    'HTTPErrorProcessor',
    'HTTPHandler',
    'HTTPPasswordMgr',
    'HTTPPasswordMgrWithDefaultRealm',
    'HTTPProxyPasswordMgr',
    'HTTPRedirectDebugProcessor',
    'HTTPRedirectHandler',
    'HTTPRefererProcessor',
    'HTTPRefreshProcessor',
    'HTTPResponseDebugProcessor',
    'HTTPRobotRulesProcessor',
    'HTTPSClientCertMgr',
    'HeadParser',
    'History',
    'LWPCookieJar',
    'Link',
    'LinkNotFoundError',
    'LoadError',
    'MozillaCookieJar',
    'OpenerDirector',
    'OpenerFactory',
    'ProxyBasicAuthHandler',
    'ProxyDigestAuthHandler',
    'ProxyHandler',
    'Request',
    'RobotExclusionError',
    'SeekableResponseOpener',
    'URLError',
    'USE_BARE_EXCEPT',
    'UnknownHandler',
    'UserAgent',
    'UserAgentBase',
    'XHTMLCompatibleHeadParser',
    '__version__',
    'build_opener',
    'install_opener',
    'lwp_cookie_str',
    'make_response',
    'request_host',
    'response_seek_wrapper',  # XXX deprecate in public interface?
    # XXX should probably use this internally in place of
    # response_seek_wrapper()
    'seek_wrapped_response',
    'str2time',
    'urlopen',
    'urlretrieve',
    'urljoin',

    # ClientForm API
    'AmbiguityError',
    'ControlNotFoundError',
    'ItemCountError',
    'ItemNotFoundError',
    'LocateError',
    'Missing',
    # deprecated
    'CheckboxControl',
    'Control',
    'FileControl',
    'HTMLForm',
    'HiddenControl',
    'IgnoreControl',
    'ImageControl',
    'Item',
    'Label',
    'ListControl',
    'PasswordControl',
    'RadioControl',
    'ScalarControl',
    'SelectControl',
    'SubmitButtonControl',
    'SubmitControl',
    'TextControl',
    'TextareaControl',
]

import logging

from _version import __version__

# high-level stateful browser-style interface
from _mechanize import \
    Browser, History, \
    BrowserStateError, LinkNotFoundError, FormNotFoundError

# configurable URL-opener interface
from _useragent import UserAgentBase, UserAgent
from _html import Link, Factory

# urllib2 work-alike interface.  This is a superset of the urllib2 interface.
from _urllib2 import *
import _urllib2
if hasattr(_urllib2, "HTTPSHandler"):
    __all__.append("HTTPSHandler")
del _urllib2

# misc
from _http import HeadParser
from _http import XHTMLCompatibleHeadParser
from _opener import ContentTooShortError, OpenerFactory, urlretrieve
from _response import \
    response_seek_wrapper, seek_wrapped_response, make_response
from _rfc3986 import urljoin
from _util import http2time as str2time

# cookies
from _clientcookie import Cookie, CookiePolicy, DefaultCookiePolicy, \
    CookieJar, FileCookieJar, LoadError, request_host_lc as request_host, \
    LWPCookieJar, lwp_cookie_str, MozillaCookieJar, effective_request_host

# forms
from _form_controls import (
    AmbiguityError,
    ControlNotFoundError,
    ItemCountError,
    ItemNotFoundError,
    LocateError,
    Missing,
    # deprecated
    CheckboxControl,
    Control,
    FileControl,
    HTMLForm,
    HiddenControl,
    IgnoreControl,
    ImageControl,
    Item,
    Label,
    ListControl,
    PasswordControl,
    RadioControl,
    ScalarControl,
    SelectControl,
    SubmitButtonControl,
    SubmitControl,
    TextControl,
    TextareaControl,
)

# If you hate the idea of turning bugs into warnings, do:
# import mechanize; mechanize.USE_BARE_EXCEPT = False
USE_BARE_EXCEPT = True

logger = logging.getLogger("mechanize")
if logger.level is logging.NOTSET:
    logger.setLevel(logging.CRITICAL)
del logger
