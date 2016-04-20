#!/bin/bash

# Remove all pods, services, and RCs
kubectl delete rc,svc,pod --all
kubectl delete rc,svc,pod --all --namespace=client
kubectl delete rc,svc,pod --all --namespace=management-ui

# Remove isolation on namespaces.
kubectl annotate ns default "net.alpha.kubernetes.io/network-isolation=no" --overwrite=true
kubectl annotate ns client "net.alpha.kubernetes.io/network-isolation=no" --overwrite=true

# Delete policies.
policy delete allow-ui
policy delete allow-ui --namespace=client
policy delete frontend-policy
policy delete backend-policy

# Delete namespaces.
kubectl delete ns client
kubectl delete ns management-ui
