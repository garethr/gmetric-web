#!/bin/sh
cd /srv/gmetric-web/releases/current
source /srv/gmetric-web/bin/activate
spawn -t 1 -p 8079 app.application --stderr=/srv/gmetric-web/shared/error.log --no-keepalive -l /srv/gmetric-web/shared/access.log --pidfile /srv/gmetric-web/shared/gmetric-web.pid -d