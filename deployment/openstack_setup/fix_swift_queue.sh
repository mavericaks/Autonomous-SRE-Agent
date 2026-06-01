#!/bin/bash
# Fix Swift + Ceilometer queue conflict
set -x

# 1. Stop all swift proxy servers
for HOST in 10.10.10.10 10.10.10.11 10.10.10.12; do
    ssh kolla@$HOST "echo '123' | sudo -S docker stop swift_proxy_server 2>/dev/null" &
done
wait

# 2. Delete ALL notification queues
docker exec rabbitmq rabbitmqctl delete_queue notifications.info 2>/dev/null
docker exec rabbitmq rabbitmqctl delete_queue notifications.audit 2>/dev/null
docker exec rabbitmq rabbitmqctl delete_queue notifications.error 2>/dev/null
docker exec rabbitmq rabbitmqctl delete_queue notifications.sample 2>/dev/null
docker exec rabbitmq rabbitmqctl delete_queue notifications.debug 2>/dev/null
docker exec rabbitmq rabbitmqctl delete_queue notifications.critical 2>/dev/null
docker exec rabbitmq rabbitmqctl delete_queue notifications.warn 2>/dev/null
echo "All queues deleted"

# 3. Restart ceilometer to recreate queues with durable=true
docker restart ceilometer_notification
sleep 5

# 4. Patch all swift proxy configs and restart
for HOST in 10.10.10.10 10.10.10.11 10.10.10.12; do
    ssh kolla@$HOST "echo '123' | sudo -S bash -c '
        CONF=/etc/kolla/swift-proxy-server/proxy-server.conf
        if ! grep -q rabbit_durable_queues \$CONF; then
            sed -i \"/^log_level = WARN/a rabbit_durable_queues = True\" \$CONF
        fi
        docker start swift_proxy_server
    '" &
done
wait
echo "All swift proxies restarted"
