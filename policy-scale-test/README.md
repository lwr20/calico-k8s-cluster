This "demo" is actually a simple scale test for the Calico policy agent (current testing caseydavenport/k8s-policy-agent:latest).

Create a cluster using `make cluster`.

To set up the demo, run 'demos/policy-scale-test/start.sh' on the `k8s-master` machine. 
```
vagrant ssh k8s-master
cd demos/policy-scale-test
./start.sh
```

This will do the following:
 - Enable isolation on the default namespace. 
 - Create an nginx ReplicationController / Service with a single nginx pod.
 - Apply nginx-policy, which allows traffic from pods with label "role: getter" 
 - Create a ReplicationController for the "getter" pods, with replicas=0.

The "getter" pods will log their start time, and the time they gain access to the nginx service.  You can see this with `kubectl logs <podname>`. 

First, you must scale the ReplicationController to the desired scale, e.g:
```
kubectl scale rc getter --replicas=100
```

Once all pods have gone to "Running" state, you can run the following command in the root of this repo to produce plots.
```
python -i scripts/get-data.py
```

This will produce a few plots, namely:
- Histogram of getter connection times.
- Scatter plot: pod start time vs. elapsed time to connection. 
- Scatter plot: pod start time vs. time spent processing by policy agent
- Scatter plot: time vs agent queue length / total events from k8s
