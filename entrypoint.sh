#!/bin/sh

sed -i 's/access_log.*/access_log off;/' /etc/nginx/nginx.conf

rm -f /var/log/nginx/access.log /var/log/nginx/error.log
mkdir -p /var/log/nginx
touch /var/log/nginx/access.log /var/log/nginx/error.log
chown nginx:nginx /var/log/nginx/access.log /var/log/nginx/error.log

if [ "$ACTIVE_POOL" = "blue" ]; then
    export BLUE_STATUS=""
    export GREEN_STATUS="backup"
else
    export BLUE_STATUS="backup"
    export GREEN_STATUS=""
fi

envsubst '${BLUE_STATUS} ${GREEN_STATUS}' < /etc/nginx/nginx.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'