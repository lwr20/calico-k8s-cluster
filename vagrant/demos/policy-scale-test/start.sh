#!/bin/bash

# Ensure isolation is on.
echo "Enabling isolation on default namespace"
kubectl annotate ns default "net.alpha.kubernetes.io/network-isolation=yes" --overwrite=true

# Start the nginx ReplicationController and Service
echo "Starting nginx Service"
kubectl create -f nginx-server.yaml

echo "Applying policy to nginx Service"
./policy create -f nginx-policy.yaml

echo "Start getter ReplicationController"
kubectl create -f getter.yaml
