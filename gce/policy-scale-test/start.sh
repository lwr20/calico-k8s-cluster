#!/bin/bash

# Create namespaces.
kubectl create -f ../build/manifests/namespaces/

# Create DNS.
kubectl create -f ../build/manifests/addons/dns-addon.yaml

# Ensure isolation is on.
echo "Enabling isolation on default namespace"
kubectl annotate ns default "net.alpha.kubernetes.io/network-isolation=yes" --overwrite=true

# Start the nginx ReplicationController and Service
echo "Starting nginx Service"
kubectl create -f nginx-server.yaml

echo "Start getter ReplicationController"
kubectl create -f ../build/getter.yaml
