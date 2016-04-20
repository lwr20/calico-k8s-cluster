import os
import numpy
import matplotlib.pyplot as pylab
import json
import subprocess
import re
import Queue
import datetime
import threading
from dateutil import parser
from subprocess import check_output

print "Getting all pods"
all_pods = check_output(["kubectl", "get", "pods", "-o", "json"])
all_pods = json.loads(all_pods)["items"]

# Get all "getter" pod names.
pods = {str(p["metadata"]["name"]): p for p in all_pods
                if "getter" in p["metadata"]["name"]}

# Generate a queue for threads to read from.
pod_queue = Queue.Queue()

for pod_name, pod in pods.iteritems():
    pod_queue.put(pod_name)

def label_pods():
    while True:
        try:
            pod_name = pod_queue.get_nowait()
        except Queue.Empty:
            break


        print "Relabeling pod: %s" % pod_name
        check_output(["kubectl", "label", "pod", pod_name, "calico=cat", "--overwrite=true"])

print "Labeling pods on 100 threads"
threads = []
start_time = datetime.datetime.now()
for i in range(100):
    t = threading.Thread(target=label_pods)
    t.daemon = True
    t.start()
    threads.append(t)

for t in threads:
    t.join()
end_time = datetime.datetime.now()

num_pods = len(pods) 
total_time = (end_time - start_time).seconds
rate = num_pods / total_time
print "Labeled %s pods in %s seconds (%s pods/s)" % (num_pods, total_time, rate)
