#!/usr/bin/env python

import subprocess
from mnml import RegexBasedApplication, \
                 RequestHandler, HttpResponse, HttpResponseRedirect, \
                 development_server

class Gmetric(RequestHandler):
    def GET(self, name, value):
        """
        we want to call the local gmetric command
        if that succeeds then return a 200, if it doesn't return 
        a 500 
        """

        # the return code will be 0 if we succeed and non zero if we don't
        try:
            subprocess.check_call(
                'gmetric -n %s -v %s -t float -u Seconds' % (name, value),
                    shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return HttpResponse("Success")
        except subprocess.CalledProcessError:
            return self.error(500)

class Heartbeat(RequestHandler):
    def GET(self):
        """
        A simple endpoint that will return a 200 response code
        We use this to verify that the service is alive
        """
        return HttpResponse("Alive")


class NotFoundPageHandler(RequestHandler):
    def GET(self):
        return self.error(404)
            
routes = (
    (r'/heartbeat', Heartbeat),
    (r'^/([A-Za-z0-9_]+)/([0-9]+)/$', Gmetric),
    ('/.*', NotFoundPageHandler),
)
application = RegexBasedApplication(routes)

if __name__ == '__main__':
    development_server(application, port=8079)
