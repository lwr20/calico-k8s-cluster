# Creating the Cluster
Set the correct `OS=` variable in `Makefile` - either `darwin` if you're running this on Mac, or `linux` if running on Linux.

You can start a cluster with:
```
make cluster
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
