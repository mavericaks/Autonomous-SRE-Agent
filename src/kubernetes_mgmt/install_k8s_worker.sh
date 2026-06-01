#!/bin/bash
set -ex

# Pre-staged keys from master
sudo cp /tmp/k8s-key.gpg /etc/apt/keyrings/kubernetes-apt-keyring.gpg

# Add K8s repo
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.29/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list

# Allow insecure HTTPS for K8s repo (captive portal intercepts certs)
echo 'Acquire::https::pkgs.k8s.io::Verify-Peer "false";' | sudo tee /etc/apt/apt.conf.d/99k8s-noverify
echo 'Acquire::https::prod-cdn.packages.k8s.io::Verify-Peer "false";' | sudo tee -a /etc/apt/apt.conf.d/99k8s-noverify

sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl

kubeadm version
