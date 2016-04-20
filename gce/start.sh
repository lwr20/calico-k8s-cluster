#!/bin/bash


kubectl create -f manifests/addons/NetworkPolicy.yaml
kubectl create -f manifests/addons/dns-addon.yaml
kubectl create -f manifests/namespaces/
