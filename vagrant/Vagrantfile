# Size of the cluster created by Vagrant
num_instances=3

# Change basename of the VM
instance_name_prefix="k8s"

# Official CoreOS channel from which updates should be downloaded
update_channel='stable'

Vagrant.configure("2") do |config|
  # always use Vagrants insecure key
  config.ssh.insert_key = false

  config.vm.box = "coreos-%s" % update_channel
  config.vm.box_url = "http://%s.release.core-os.net/amd64-usr/current/coreos_production_vagrant.json" % update_channel

  config.vm.provider :virtualbox do |v|
    # On VirtualBox, we don't have guest additions or a functional vboxsf
    # in CoreOS, so tell Vagrant that so it can be smarter.
    v.check_guest_additions = false
    v.memory = 2048 
    v.cpus = 2
    v.functional_vboxsf     = false
  end

  # Set up each box
  (1..num_instances).each do |i|
    # Determine the VM's name.
    if i == 1
      vm_name = "%s-%s" % [instance_name_prefix, "master"]
    else
      vm_name = "%s-node-%02d" % [instance_name_prefix, i-1]
    end

    config.vm.define vm_name do |host|
      host.vm.hostname = vm_name 

      ip = "172.18.18.#{i+100}"
      host.vm.network :private_network, ip: ip

      # Use a different cloud-init on the first server.
      if i == 1
	config.vm.provider :virtualbox do |v|
	  v.memory = 2048 
	  v.cpus = 2
	end

	# Pre-fetch docker images.
        host.vm.provision :docker, images: ["calico/node:v0.18.0"]

	# Install the demos folder.
        host.vm.provision :file, :source => "demos", :destination => "/home/core/demos"

        # Install cloud-config.
        host.vm.provision :file, :source => "cloud-config/master-config-template.yaml", :destination => "/tmp/vagrantfile-user-data"
        host.vm.provision :shell, :inline => "mv /tmp/vagrantfile-user-data /var/lib/coreos-vagrant/", :privileged => true
      else
	config.vm.provider :virtualbox do |v|
	  v.memory = 2048 
	  v.cpus = 2
	end

        # Pre-fetch Docker images.
        host.vm.provision :docker, images: ["calico/node:v0.18.0", "gcr.io/google_containers/pause:latest"]

	# Install cloud-config.
        host.vm.provision :file, :source => "cloud-config/node-config-template.yaml", :destination => "/tmp/vagrantfile-user-data"
        host.vm.provision :shell, :inline => "mv /tmp/vagrantfile-user-data /var/lib/coreos-vagrant/", :privileged => true
      end
    end
  end
end
