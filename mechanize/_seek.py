from urllib2 import BaseHandler
from _response import response_seek_wrapper


class SeekableProcessor(BaseHandler):
    """Make responses seekable."""

    def any_response(self, request, response):
        if not hasattr(response, "seek"):
            return response_seek_wrapper(response)
        return response
