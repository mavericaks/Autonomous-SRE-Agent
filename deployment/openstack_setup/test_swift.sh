#!/bin/bash
source /etc/kolla/admin-openrc.sh
TOKEN=$(openstack token issue -f value -c id)
PROJECT=$(openstack token issue -f value -c project_id)
echo "TOKEN=$TOKEN"
echo "PROJECT=$PROJECT"
echo "--- Testing Swift API directly ---"
curl -s -w '\nHTTP_CODE=%{http_code}\n' -H "X-Auth-Token: $TOKEN" http://10.10.10.200:8080/v1/AUTH_$PROJECT
echo "--- Pipeline check ---"
docker exec swift_proxy_server grep pipeline /etc/swift/proxy-server.conf
echo "--- Swift proxy logs (last 5 non-STDERR lines) ---"
docker logs swift_proxy_server 2>&1 | grep -v STDERR | tail -5
