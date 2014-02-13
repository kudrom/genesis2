VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  # Run /vagrant box add Arch <url>/ to add the Arch box the first time.
  # You can use the boxes in http://vagrant.srijn.net
  config.vm.box = "Arch"
  config.vm.network "forwarded_port", guest: 8000, host: 8082
  config.vm.network "forwarded_port", id: "ssh", guest: 22, host:2223
  config.vm.provision "shell", path: "provision.sh"
end
