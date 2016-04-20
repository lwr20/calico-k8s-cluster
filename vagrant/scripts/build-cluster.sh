#!/bin/bash 

set -e

# Clean
make clean-webserver
make clean-keys
make clean-binaries
docker rmi -f calico/build || echo "calico/build not present"

# Get right kube-cluster branch
git fetch
git checkout $CLUSTER_BRANCH
git pull origin $CLUSTER_BRANCH

# Make sure submodule update to date.
git submodule init
git submodule update

# Checkout correct calico-cni branch.
cd calico-cni
git fetch
git checkout -f $CALICO_CNI_BRANCH
git pull -f origin $CALICO_CNI_BRANCH
cd ..

# Build the cluster.
make cluster

set +e
