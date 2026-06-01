#!/bin/bash
# Remove ceilometer from Swift proxy pipeline and restart
CONF="/etc/kolla/swift-proxy-server/proxy-server.conf"

# Remove 'ceilometer' from the pipeline
sed -i 's/ ceilometer proxy-server$/ proxy-server/' "$CONF"
echo "Pipeline after fix:"
grep pipeline "$CONF"

docker restart swift_proxy_server
echo "Swift proxy restarted"
