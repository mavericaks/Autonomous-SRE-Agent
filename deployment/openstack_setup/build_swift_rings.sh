#!/bin/bash
set -ex

KOLLA_SWIFT_BASE_IMAGE="kolla/ubuntu-source-swift-base:2024.2"
KOLLA_INTERNAL_VIP=10.10.10.200
PARTITION_POWER=10
REPLICAS=3
MIN_PART_HOURS=1

cd /etc/kolla/config/swift

# Build account ring
swift-ring-builder account.builder create ${PARTITION_POWER} ${REPLICAS} ${MIN_PART_HOURS}
swift-ring-builder account.builder add --region 1 --zone 1 --ip 10.10.10.10 --port 6002 --device KOLLA_SWIFT_DATA --weight 100
swift-ring-builder account.builder add --region 1 --zone 2 --ip 10.10.10.11 --port 6002 --device KOLLA_SWIFT_DATA --weight 100
swift-ring-builder account.builder add --region 1 --zone 3 --ip 10.10.10.12 --port 6002 --device KOLLA_SWIFT_DATA --weight 100
swift-ring-builder account.builder rebalance

# Build container ring
swift-ring-builder container.builder create ${PARTITION_POWER} ${REPLICAS} ${MIN_PART_HOURS}
swift-ring-builder container.builder add --region 1 --zone 1 --ip 10.10.10.10 --port 6001 --device KOLLA_SWIFT_DATA --weight 100
swift-ring-builder container.builder add --region 1 --zone 2 --ip 10.10.10.11 --port 6001 --device KOLLA_SWIFT_DATA --weight 100
swift-ring-builder container.builder add --region 1 --zone 3 --ip 10.10.10.12 --port 6001 --device KOLLA_SWIFT_DATA --weight 100
swift-ring-builder container.builder rebalance

# Build object ring
swift-ring-builder object.builder create ${PARTITION_POWER} ${REPLICAS} ${MIN_PART_HOURS}
swift-ring-builder object.builder add --region 1 --zone 1 --ip 10.10.10.10 --port 6000 --device KOLLA_SWIFT_DATA --weight 100
swift-ring-builder object.builder add --region 1 --zone 2 --ip 10.10.10.11 --port 6000 --device KOLLA_SWIFT_DATA --weight 100
swift-ring-builder object.builder add --region 1 --zone 3 --ip 10.10.10.12 --port 6000 --device KOLLA_SWIFT_DATA --weight 100
swift-ring-builder object.builder rebalance

echo "=== Ring files created ==="
ls -la *.ring.gz *.builder
