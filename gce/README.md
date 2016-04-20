# Scale testing Kubernetes + Calico

This repo contains cloud config files for configuring a simple CoreOS + Kubernetes cluster.

It can be deployed using vagrant (see the included Vagrantfile) or to GCE using the commands in the Makefile.

It was most recently run on GCE so some changes will be required to get it to run on Vagrant again.

## Getting started

* Run
  * `make gce-create`
    * Runs two gloud commands.
      * Master - Create a high CPU server with an external IP, a local SSD and using the master cloud config (see below)
      * Nodes - Create many servers without a external IPs using the node cloud config (see below)
  * `make gce-forward-ports`
    * After the master node has booted, run this target to get kubectl, etcdctl and calicoctl access on localhost.
  * `make apply-node-labels`
    * This labels the nodes so the pingers won't run on the master. See the pinger.yaml for more detail
  * `make deploy-pinger`
    * This creates a replication controller for the pinger task
  * `make scale-pinger`

  * `make -j24 pull-plugin-timings`
    * Pull down the timing
    * Can scale the replication controller to 0 if you want deletion times too.
    * Can analyse the results with e.g.
      * `grep DEL all.csv | cut -d, -f 6   | ./histogram.py`
  * `make gce-cleanup`
    * Removes all the VMs
  
## Changes to run on Vagrant
This was originally written for vagrant and the changes required for running on vagrant should be minimal.
* Change any instances of kube-scale-master to 172.18.18.101
* Use different commands to create and remove the hosts - e.g. `make create-cluster-vagrant`

The Vagrantfile is designed to be minimal. It just sets up the hosts, gives the master a known IP address and uses the master and node cloud config files.

## Other
The Makefile also contains other experimental features such as running heapster. YMMV.

## Future
* Route reflector
* Etcd cluster + different etcd for kubernetes and calico
* Services and more use of DNS
