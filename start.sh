#!/bin/sh

set -e

ARGS=
if test -n "$SSL_CERT" -a -n "SSL_KEY"; then
    ARGS="--ssl-cert=$SSL_CERT --ssl-key=$SSL_KEY"
fi
if test "$DEBUG" = 1; then
    ARGS="$ARGS -d"
fi
exec /app/virtualenv/bin/eventstreamd -c /app/docker.conf $ARGS
