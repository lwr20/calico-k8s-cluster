# Calico + Kubernetes on Vagrant
This directory contains the scripts to start a fully conformant Kubernetes cluster using vagrant.

These scripts can be run on OSX or Linux, and are currently used by Jenkins to deploy its test cluster.

### Getting Started
To start the cluster:
```
# OS can be either 'linux' or 'darwin'
make OS=linux cluster
```

This will spin up 1 Kubernetes master and 3 minions.  Creating the cluster downloads a `kubectl` binary and configures TLS, so you can run the following locally once the cluster is running:
```
kubectl get pods --all-namespaces 
```  

You should see the following output (or similar):
```
illium:kube-cluster cd4$ ./kubectl get pods --all-namespaces
NAMESPACE       NAME                        READY     STATUS    RESTARTS   AGE
calico-system   calico-policy-agent-1s1f4   1/1       Running   0          1m
kube-system     kube-dns-v9-dtay6           4/4       Running   0          1m
kube-system     kube-ui-v4-cs8ya            1/1       Running   0          1m
```

You can ssh into any of the nodes:
```
# Show running nodes.
vagrant status

# SSH into the master.
vagrant ssh k8s-master

# SSH into a node.
vagrant ssh k8s-node-01
```

### Jenkins

Jenkins uses this cluster to run its e2e tests.  The jenkins entrypoint is located at `scripts/build-cluster-jenkins.sh`.
