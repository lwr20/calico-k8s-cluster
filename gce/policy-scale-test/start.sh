#!/bin/bash

# Create DNS.
kubectl create -f ../build/manifests/addons/dns-addon.yaml

# Start the nginx ReplicationController and Service
echo "Starting nginx Service"
kubectl create -f nginx-server.yaml

echo "Start getter ReplicationController"
kubectl create -f ../build/getter.yaml
