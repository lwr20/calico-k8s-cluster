# Scale testing Kubernetes + Calico

This repo contains cloud config files for configuring a CoreOS + Kubernetes cluster for scale testing.

While we provide Vagrant and GCE files, only the GCE files have been updated recently so we recommend starting with those.

## Getting started on GCE

These instructions have been tested on Ubuntu 14.04.  They are likely to work with more recent versions too.

* You will need the following pre-requisites installed:
  * GNU make
  * The [Google Cloud SDK](https://cloud.google.com/sdk/downloads).
  * kubectl, at least version 1.2 (this comes with the Cloud SDK).
  * ssh.
* Make sure your cloud SDK is up-to-date: `gcloud components update`.
* Create a GCE project, if you don't have one already and configure gcloud to us it.
* `cd gce`
* Create a file `local-settings.mk` with your preferred editor.  Review the settings at the top of `./Makefile`, copy any that you need to change over to `local-setting.mk` and edit them there.  At the very least, you'll want to change `GCE_PROJECT` to the name of a GCE project that you control.
* Run
  * `make gce-create`, this runs several gcloud commands to start the Kubernetes cluster; then it uses ssh to forward various local ports to the cluster.
  * Configure Kubernetes for the start of the test:
    * Wait for the hosts to check in with Kubernetes: `watch kubectl get nodes`.  You should see an entry in state "Ready" for each compute host.
    * `make prepare-getter` will check that the policy is in place and create all the namespaces, RCs, nginx pods, etc for the test run.
  * Run the test:
    * Either:
      * `make scale-getter` - this will scale the number of getter pods to the value specified in NUM_PODS in either the Makefile or local-settings.mk
      * or do it manually: Scale up the number of "getter" pods, each of which will try to connect to nginx and then record their timings.  We recommend starting at most 100 pods per compute host.  `kubectl scale rc getter --replicas=<num-replicas>`.
    * Wait for all pods to be started.  This command will auto-update, showing only the pods that haven't finished starting yet: `watch kubectl get pods | grep -v Running`.  Note: Kubernetes throttles updates to the pod status so it can take some time for Kubernetes to report the correct state.
    * Pull basic stats and graphs: `make get-results`
    * The test includes a performance dashboard, which is accessible at http://localhost:3000.
  * You can also pull full logs with `make -j24 pull-plugin-timings` for diagnostic purposes.
  * To tear down the cluster, run `make gce-cleanup`.

## Changes to run on Vagrant
This was originally written for vagrant and the changes required for running on vagrant should be minimal.
* Change any instances of kube-scale-master to 172.18.18.101
* Use different commands to create and remove the hosts - e.g. `make create-cluster-vagrant`

The Vagrantfile is designed to be minimal. It just sets up the hosts, gives the master a known IP address and uses the master and node cloud config files.

## Other
The Makefile also contains other experimental features such as running heapster. YMMV.

## Future
* Services and more use of DNS
