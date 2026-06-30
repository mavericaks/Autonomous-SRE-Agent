# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # Use Ubuntu 24.04 (Noble Numbat) for OpenStack Dalmatian 2024.2
  config.vm.box = "ubuntu/noble64"
  
  # Provisioner to setup kolla user and passwords across all nodes
  common_provisioning = <<-SHELL
    # Create kolla user if it doesn't exist
    if ! id -u kolla > /dev/null 2>&1; then
      sudo useradd -m -s /bin/bash kolla
      echo "kolla ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/kolla
    fi
    # Set password for kolla user
    echo "kolla:123" | sudo chpasswd
    
    # Enable password authentication for SSH (needed for initial setup)
    sudo sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
    sudo systemctl restart ssh || sudo systemctl restart sshd
  SHELL

  # ---------------------------------------------------------
  # Node 1: OpenStack Controller
  # ---------------------------------------------------------
  config.vm.define "controller" do |controller|
    controller.vm.hostname = "openstack-controller"
    # Management/Tunneling network (ens34 equivalent)
    controller.vm.network "private_network", ip: "10.10.10.10"
    
    controller.vm.provider "virtualbox" do |vb|
      vb.name = "openstack-controller"
      vb.memory = "10240"
      vb.cpus = 4
      # Enable nested virtualization
      vb.customize ["modifyvm", :id, "--nested-hw-virt", "on"]
    end
    
    controller.vm.provider "vmware_desktop" do |v|
      v.vmx["memsize"] = "10240"
      v.vmx["numvcpus"] = "4"
      v.vmx["vhv.enable"] = "TRUE" # Nested virt
    end

    controller.vm.provision "shell", inline: common_provisioning
  end

  # ---------------------------------------------------------
  # Node 2: OpenStack Compute 1
  # ---------------------------------------------------------
  config.vm.define "compute1" do |compute1|
    compute1.vm.hostname = "openstack-compute1"
    compute1.vm.network "private_network", ip: "10.10.10.11"
    
    compute1.vm.provider "virtualbox" do |vb|
      vb.name = "openstack-compute1"
      vb.memory = "16384"
      vb.cpus = 6
      vb.customize ["modifyvm", :id, "--nested-hw-virt", "on"]
    end
    
    compute1.vm.provider "vmware_desktop" do |v|
      v.vmx["memsize"] = "16384"
      v.vmx["numvcpus"] = "6"
      v.vmx["vhv.enable"] = "TRUE"
    end

    compute1.vm.provision "shell", inline: common_provisioning
  end

  # ---------------------------------------------------------
  # Node 3: OpenStack Compute 2
  # ---------------------------------------------------------
  config.vm.define "compute2" do |compute2|
    compute2.vm.hostname = "openstack-compute2"
    compute2.vm.network "private_network", ip: "10.10.10.12"
    
    compute2.vm.provider "virtualbox" do |vb|
      vb.name = "openstack-compute2"
      vb.memory = "16384"
      vb.cpus = 6
      vb.customize ["modifyvm", :id, "--nested-hw-virt", "on"]
    end
    
    compute2.vm.provider "vmware_desktop" do |v|
      v.vmx["memsize"] = "16384"
      v.vmx["numvcpus"] = "6"
      v.vmx["vhv.enable"] = "TRUE"
    end

    compute2.vm.provision "shell", inline: common_provisioning
  end

end
