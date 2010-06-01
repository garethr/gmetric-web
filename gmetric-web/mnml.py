#!/usr/bin/env python

"""
MNML WSGI Web Framework

A small python glue framework for building web applications and services that 
run atop WSGI compliant servers. The emphasis is on HTTP best practices, 
readble code and allowing applications to be built with using whatever
other python modules you like.

MNML has borrowed fairly heavily from newf, since that's 
basically the bare minimum code required for a routed WSGI framework.

"""

import re
import sys
import cgi
import urlparse
from wsgiref.simple_server import make_server

# limit exports
__all__ = [
    'HttpRequest', 'HttpResponse', 'HttpResponseRedirect', 'RequestHandler', 
    'development_server', 'TokenBasedApplication', 'RegexBasedApplication',
]
    
class RequestHandler(object):
    """
    Our base HTTP request handler. Clients should subclass this class.
    Subclasses should override get(), post(), head(), options(), etc to handle
    different HTTP methods.
    """

    def __init__(self, request):
        "Stash the request locally to make the API nicer"
        self.request = request

    def GET(self, *args):
        "Handler method for GET requests."
        return self.error(405)

    def POST(self, *args):
        "Handler method for POST requests."
        return self.error(405)

    def HEAD(self, *args):
        "Handler method for HEAD requests."
        return self.error(405)

    def OPTIONS(self, *args):
        "Handler method for OPTIONS requests."
        return self.error(405)

    def PUT(self, *args):
        "Handler method for PUT requests."
        return self.error(405)

    def DELETE(self, *args):
        "Handler method for DELETE requests."
        return self.error(405)

    def TRACE(self, *args):
        "Handler method for TRACE requests."
        return self.error(405)
        
    def error(self, code, message=''):
        "Sets the given HTTP error code."      
        return HttpResponse(message, status_code=code)
        
class HttpError(Exception):
    "Generic exception for HTTP issues"
    pass

class HttpRequest(object):
    "Our request object which stores information about the HTTP request"
    
    def __init__(self, environ):
        "Initialise our request with an environment"
        self.POST = self.GET = {}
        self.environ = environ
        # we often want access to the method so we'll make that 
        # easier to get at
        self.method = environ['REQUEST_METHOD']
        # and the path
        self.path = environ['PATH_INFO']
        
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html
        if self.method not in ('POST', 'GET', 'DELETE', 'PUT', 'HEAD', 
                                'OPTIONS', 'TRACE'):
            raise HttpError, "Invalid request"
        
        # if we have any query string arguments then we'll make then
        # more easily accessible
        if len(environ['QUERY_STRING']):
            self.GET = urlparse.parse_qs(environ['QUERY_STRING'], True)
        
        # if we have post data we'll make that more accessible too
        if self.method == 'POST':
            self.POST = cgi.FieldStorage(fp=environ['wsgi.input'], 
                                         environ=environ, 
                                         keep_blank_values=True)
        
        # like PHP's $_REQUEST - but you should usually be more explicit
        self.REQUEST = self.GET.copy()
        self.REQUEST.update(self.POST)

class HttpResponse(object):
    "Our Response object"
    
    # http://www.faqs.org/rfcs/rfc2616.html
    codes = {
        100: "Continue", 
        101: "Switching Protocols", 
        200: "OK", 
        201: "Created", 
        202: "Accepted", 
        203: "Non-Authoritative Information", 
        204: "No Content", 
        205: "Reset Content", 
        206: "Partial Content", 
        300: "Multiple Choices", 
        301: "Moved Permanently", 
        302: "Found", 
        303: "See Other", 
        304: "Not Modified", 
        305: "Use Proxy", 
        307: "Temporary Redirect", 
        400: "Bad Request", 
        401: "Unauthorized", 
        402: "Payment Required", 
        403: "Forbidden", 
        404: "Not Found", 
        405: "Method Not Allowed", 
        406: "Not Acceptable",
        407: "Proxy Authentication Required", 
        408: "Request Time-out", 
        409: "Conflict", 
        410: "Gone", 
        411: "Length Required", 
        412: "Precondition Failed", 
        413: "Request Entity Too Large", 
        414: "Request-URI Too Large", 
        415: "Unsupported Media Type", 
        416: "Requested range not satisfiable", 
        417: "Expectation Failed", 
        500: "Internal Server Error", 
        501: "Not Implemented", 
        502: "Bad Gateway", 
        503: "Service Unavailable", 
        504: "Gateway Time-out", 
        505: "HTTP Version not supported",
    }
    
    def __init__(self, content='', headers={}, status_code=200):
        "Initialise our response, assuming everything is fine"
        self.status_code = status_code
        self.set_content(content)
        self._headers = headers
        self._headers['content-length'] = str(len(content))
        
        # lets assume text/html unless told otherwise
        if not 'content-type' in self.headers:
            self._headers['content-type'] = 'text/html'
        
    def get_status(self):
        "Get the status code and message, but make sure it's valid first"
        if self.status_code not in self.codes:
            # invalid code, so something has gone wrong
            self.status_code = 500
        return "%s %s" % (self.status_code, self.codes[self.status_code])
        
    def set_status(self, code):
        "API setter method"
        self.status_code = code
        
    def get_headers(self):
        "Return the headers as a list"
        return list(self._headers.iteritems())
        
    def set_headers(self, *args):
        "Set the response headers, takes either a key/value or a dictionary"
        if type(args[0]).__name__ == 'dict':
            self._headers.update(args[0])
        else:
            key, value = args
            self._headers[key] = value
        
    def get_content(self):
        "Return the body of the response in a useful format"
        return [self._content, '\n']
        
    def set_content(self, value):
        "Set the body of the response, ensuring we're using utf-8"
        # http://www.python.org/dev/peps/pep-0333/#unicode-issues
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        self._content = value
        
    # make the important parts of the response properties of the object
    content = property(get_content, set_content)
    status = property(get_status, set_status)
    headers = property(get_headers, set_headers)
    
class HttpResponseRedirect(HttpResponse):
    "Sub class of HttpResponse making redirects easier to handle"
    def __init__(self, redirect_location, permanent=True):        
        super(HttpResponseRedirect, self).__init__()
        self._headers['Location'] = redirect_location
        # allow us to set whether we want a 301 or 302 redirect
        if permanent:
            self.status_code = 301
        else:
            self.status_code = 302
    
class WebApplication(object):
    """
    Accepts a set of routes and provides a WSGI application.
    This specific class is intended to be subclassed depending on
    what sort of routing engine you want to use. If used it will 
    always return a 404.
    """

    def __init__(self, routes):
        self.routes = routes

    def __call__(self, environ, start_response):

        response = self.create_response(environ)

        # we don't have a valid response
        if not isinstance(response, HttpResponse):
            try:
                # must times not having a response means we didn't match
                # a handler so this will fail, but just in case
                return handler.error(404)
            except:
                # in a real application this will probably never happen
                # you should always define your own catch all handler which
                # matches everything that falls all the way through your
                # routes and deal with it yourself.
                response = HttpResponse(
                    '<h1>Page Not Found</h1>', status_code=404)

        start_response(response.status, response.get_headers())
        return response.content

    def create_response(self, environ):
        "Takes the environment and returns a response object or None"
        return None
    
class RegexBasedApplication(WebApplication):
    """
    Example Application using a regex based scheme for routing.
    This is slightly faster and allows more detailed routes
    at the expense of making reversing impossible. Routes look like:
    
    routes = (
        (r'^/foo/([0-9]+)/([0-9]+)', Foo),
        (r'^/bar$', Bar),
        ('/.*', NotFoundPageHandler),
    )
    """
    def create_response(self, environ):
        "Takes the environment and returns a response object or None"
        handler = None
        groups = []
        response = None
        # get the request from the environment
        request = HttpRequest(environ)
        
        # compile all the individual regexs
        routes = tuple((re.compile(a), b) for a, b in self.routes)
        # for each regex, class pair
        for regexp, handler_class in routes:
            # if it matches the path we're dealing with
            match = regexp.match(environ['PATH_INFO'])
            if match:
                # instantiate the handler class
                handler = handler_class(request)
                # and grab the matched segments
                groups = match.groups()
                break
        
        # if we found a relevant handler
        if handler:
            # try the request method to see if the 
            # handler supports it and if so then
            # call the method
            try:
                method = environ['REQUEST_METHOD']
                if method == 'GET':
                    response = handler.GET(*groups)
                elif method == 'POST':
                    response = handler.POST(*groups)
                elif method == 'HEAD':
                    response = handler.HEAD(*groups)
                elif method == 'OPTIONS':
                    response = handler.OPTIONS(*groups)
                elif method == 'PUT':
                    response = handler.PUT(*groups)
                elif method == 'DELETE':
                    response = handler.DELETE(*groups)
                elif method == 'TRACE':
                    response = handler.TRACE(*groups)
            except Exception, e:
                # capture any exceptions so we can throw a relevant error
                return handler.error(500, e)
        
            
        # eventually return the response, which if we didn't find
        # one will be None
        return response
    
class TokenBasedApplication(WebApplication):
    """
    Example Application using a simple token based scheme for routing.
    This has the advantage of making reversing relatively simple. 
    Routes look like:
    
    routes = (
        ('/', Foo),
        ('/myview/:stuff/', Bar)
    )
    """
    def create_response(self, environ):
        "Takes the environment and returns a response object or None"
        response = None
        groups = []
        request = HttpRequest(environ)
        
        for pair in self.routes:
            route, view = pair
            matches = re.match(self._route_master(route), environ['PATH_INFO'])

            # if we found a match
            if matches:
                groups = matches.groups()
                handler = view(request)
                # try the request method to see if the 
                # handler supports it and if so then
                # call the method
                try:
                    method = environ['REQUEST_METHOD']
                    if method == 'GET':
                        response = handler.GET(*groups)
                    elif method == 'POST':
                        response = handler.POST(*groups)
                    elif method == 'HEAD':
                        response = handler.HEAD(*groups)
                    elif method == 'OPTIONS':
                        response = handler.OPTIONS(*groups)
                    elif method == 'PUT':
                        response = handler.PUT(*groups)
                    elif method == 'DELETE':
                        response = handler.DELETE(*groups)
                    elif method == 'TRACE':
                        response = handler.TRACE(*groups)
                except Exception, e:
                    # capture any exceptions so we can throw a relevant error
                    return handler.error(500, e)
                finally:
                    # once we have a match we can stop looking
                    break
        # eventually return the response, which if we didn't find
        # one will be None
        return response

    def _route_master(self, route):
        "returns a compiled regular expression"
        # chop off leading slash
        if route.startswith('/'):
            route = route[1:]
        
        trailing_slash = False
        # check end slash and remember to keep it
        if route.endswith('/'):
            route = route[:-1]
            trailing_slash = True
        
        # split into path components
        bits = route.split('/')
    
        # compiled match starts with a slash,
        #  so we make it a list so we can join later
        regex = ['']
        for path_component in bits:
            if path_component.startswith(':'):
                # it's a route, so compile
                name = path_component[1:]
                # accept only valid URL characters
                regex.append(r'(?P<%s>[-_a-zA-Z0-9+%%]+)' % name)
            else:
                # just a string/static path component
                regex.append(path_component)
            
        # stick the trailing slash back on
        if trailing_slash:
            regex.append('')
        
        # stitch it back together as a path
        return '^%s$' % '/'.join(regex)

def development_server(application, port=8000):
    "A simple WSGI development server"
    
    server = make_server('', port, application)
    
    print 'MNML now running on http://127.0.0.1:%s\n' % port
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit()
