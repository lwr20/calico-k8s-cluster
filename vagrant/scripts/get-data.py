import os
import numpy
import matplotlib.pyplot as pylab
import json
import subprocess
import re
import datetime
from dateutil import parser
from subprocess import check_output

# Various regexes.
queue_time_re = re.compile("INFO \('default', '(.*)'\) time on the queue: ([0-9\.]+)")
proc_time_re = re.compile("INFO \('default', '(.*)'\) total process time: ([0-9]+\.[0-9]+)")
start_re = re.compile("Started: ([0-9]+\.[0-9]+)")
end_re = re.compile("Completed: ([0-9]+\.[0-9]+)")
elapsed_re = re.compile("Elapsed: ([0-9]+\.[0-9]+)")
time_re = re.compile("\d\d:\d\d:\d\d")
qlen_re = re.compile("Pod: (.*) to queue \((.*)\) \((.*)\)")

# Stores the collected data for plotting, etc.
data_by_pod = {}

# Get all pod names in calico-system.
all_pods = check_output(["kubectl", "get", 
                         "pods", "--namespace=calico-system", 
                         "-o", "json"])
all_pods = json.loads(all_pods)["items"]
pod = all_pods[0]

# Get calico-k8s-policy-agent pod metadata.
pod_name = str(all_pods[0]["metadata"]["name"])

# Extract logs.
calico_logs = check_output(["kubectl", "logs", "--namespace=calico-system", pod_name])

# Extract queue / total processing times from the logs.
queue_times = queue_time_re.findall(calico_logs)
process_times = proc_time_re.findall(calico_logs)

# Store the time spent in queue per-pod.
for pod, time in queue_times:
    data_by_pod.setdefault(pod, {})["queue_time"] = float(time)

# Store the total process time per-pod.
for pod, time in process_times:
    data_by_pod.setdefault(pod, {})["process_time"] = float(time)

# Get queue lengths and CPU, MEM usage.
qlengths = qlen_re.findall(calico_logs)
for _pod, length, t in qlengths:
    data_by_pod.setdefault("qlengths", []).append(length)
    data_by_pod.setdefault("time", []).append(float(t))

# Stores mapping of start time to elapsed time list.
elapsed_by_start_time = {}

# Get all pod names.
all_pods = check_output(["kubectl", "get", "pods", "-o", "json"])
all_pods = json.loads(all_pods)["items"]

# Get all "getter" pod names.
pods = {str(p["metadata"]["name"]): p for p in all_pods
                if "getter" in p["metadata"]["name"]}

# Those that we fail to parse.
failed = []

# Arrays for scatter plots.
start_times = []
elapsed_times = []
end_times = []
agent_process_times = []

# For each pod, get its logs.
i = 0
for pod_name, pod in pods.iteritems():
    # Get node name for this pod.
    node_name = pod["spec"].get("nodeName", None)
    pod_id = "%s: %s" % (node_name, pod_name)

    print "Getting logs for %s, #%s" % (pod_id, i)
    i += 1

    try:
        logs = check_output(["kubectl", "logs", pod_name])
    except subprocess.CalledProcessError, e:
        print "Error getting logs for: %s" % pod_id
        failed.append((pod, "", e))
        continue

    try:
        start_time = float(start_re.findall(logs)[0])
    except IndexError:
        print "pod has not started yet: %s" % pod_id
        failed.append((pod, logs, None))
        continue

    try:
        end_time = float(end_re.findall(logs)[0])
    except IndexError:
        print "No end time for pod: %s" % pod_id
        failed.append((pod, logs, None))
        continue

    try:
        elapsed = float(elapsed_re.findall(logs)[0])
    except IndexError:
        print "No elapsed time for pod: %s" % pod_id
        failed.append((pod, logs, None))
        continue

    # Determine the elapsed time and store in the mapping dict.
    # elapsed = end_time - start_time 
    times = elapsed_by_start_time.setdefault(start_time, [])
    times.append(elapsed)

    # Store the X,Y arrays - start time, elapsed time, respectively.
    start_times.append(start_time)
    elapsed_times.append(elapsed)
    end_times.append(end_time)

    if pod_name in data_by_pod:
        agent_process_times.append(data_by_pod[pod_name]["process_time"])

    # Store data.
    data_by_pod.setdefault(pod_name, {}).update({
            "times": time_re.findall(logs),
            "start_time": start_time,
            "end_time": end_time,
            "logs": logs,
            "node": node_name,
            "raw": pod
    })

# Sort all of the start/end times into an array.
ordered_start_times = sorted(start_times) 
ordered_end_times = sorted(end_times) 

print "%s failed to get logs" % len(failed)

# Create histogram of elapsed time-to-connect.
vals = []
for _, l in elapsed_by_start_time.iteritems():
    vals += l
pylab.hist(vals)
pylab.xlabel('time to first connectivity')
pylab.ylabel('Number of pods')
pylab.show()

# Calculate start times, shifted to account
# for the first pod to start.
min_x = ordered_start_times[0]
max_x = ordered_start_times[-1]
min_y = ordered_end_times[0]
max_y = ordered_end_times[-1]
x = [(t-min_x) for t in start_times]

# Calculate 99th percentile time to first ping.
ordered_elapsed_times = sorted(elapsed_times)
index = int(.99 * len(ordered_start_times))
percentile = ordered_elapsed_times[index]
average = sum(elapsed_times) / len(elapsed_times)

# Print out some data.
print "Time to start %s pods: %s" % (len(x), max_x - min_x)
print "First-pod to full connectivity: %s" % (max_y - min_x)
print "Last-pod to full connectivity: %s" % (max_y - max_x)
print "99th percentile: %s" % percentile
print "Average elapsed time: %s" % average

# Plot data.
pylab.plot(x, elapsed_times, 'bo')
pylab.xlabel('time(s)')
pylab.ylabel('Time to first connectivity (s)')
pylab.show()

if agent_process_times:
    # Plot agent process time versus pod started time.
    pylab.plot(x, agent_process_times, "ro") 
    pylab.xlabel('pod start time')
    pylab.ylabel('Time spent in agent')
    pylab.show()
    
# Plot queue length over time, compared with total 
# API events and agent CPU usage.
qlens = data_by_pod["qlengths"]
qlen_x = data_by_pod["time"]
qlen_x = [i - min(qlen_x) for i in qlen_x]

# Calculate number of received events.
event_count = range(len(qlen_x))

pylab.plot(qlen_x, event_count, "ro",
           qlen_x, qlens, "bs")

pylab.xlabel('time')
pylab.ylabel('Agent Queue Length')
pylab.show()

# Write to file.
filename = "%s-pods-%s" % (len(elapsed_times), datetime.datetime.now())
print "Writing results to file: %s" % filename
with open("testdata/%s" % filename, "a") as f:
    f.write(json.dumps(data_by_pod))
