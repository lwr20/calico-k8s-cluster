# Kubernetes clusters for Calico CNI testing

This repository contains scripts for starting Kubernetes with Calico, as well as 
running some tests against the created clusters. 

If you are looking for guides to install Calico on Kubernetes, we recommend starting 
with the Calico [getting started documentation](https://github.com/projectcalico/calico-containers/blob/master/docs/cni/kubernetes/README.md) instead of this repository.

This repository includes two means of creating a cluster:
- [Vagrant](vagrant/README.md): Cluster setup / scripts for CNI plugin dev / test.
- [GCE](gce/README.md): Cluster setup / scripts for simple CNI plugin scale testing.
