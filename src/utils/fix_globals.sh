#!/bin/bash
# Fix globals.yml - quote all enable values
cd /etc/kolla
sed -i 's/^enable_cinder:  yes$/enable_cinder: "yes"/' globals.yml
sed -i 's/^enable_cinder_backend_lvm: yes$/enable_cinder_backend_lvm: "yes"/' globals.yml
sed -i 's/^enable_swift: yes$/enable_swift: "yes"/' globals.yml
sed -i 's/^enable_ceilometer: yes$/enable_ceilometer: "yes"/' globals.yml
sed -i 's/^enable_gnocchi: yes$/enable_gnocchi: "yes"/' globals.yml
sed -i 's/^enable_redis: yes$/enable_redis: "yes"/' globals.yml
echo "Fixed globals.yml:"
tail -8 globals.yml
