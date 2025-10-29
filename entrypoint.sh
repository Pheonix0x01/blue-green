#!/bin/sh

if [ "$ACTIVE_POOL" = "blue" ]; then
    export BLUE_STATUS=""
    export GREEN_STATUS="backup"
else
    export BLUE_STATUS="backup"
    export GREEN_STATUS=""
fi

envsubst '${BLUE_STATUS} ${GREEN_STATUS}' < /etc/nginx/nginx.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'