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

# Stores mapping of start time to elapsed time list.
elapsed_by_start_time = {}

# Those that we fail to parse.
failed = []

# Arrays for scatter plots.
agent_process_times = []

# Logs queue.
pod_names_q = Queue.Queue()
pod_logs_q = Queue.Queue()

def collect_data():
    # Get all pod names in calico-system.
    print "Getting all pods in calico-system namespace"
    all_pods = check_output(["kubectl", "get",
                             "pods", "--namespace=calico-system",
                             "-o", "json"])
    all_pods = json.loads(all_pods)["items"]
    pod = all_pods[0]

    # Get calico-k8s-policy-agent pod metadata.
    pod_name = str(all_pods[0]["metadata"]["name"])

    # Extract logs.
    print "Getting calico policy agent logs"
    calico_logs = check_output(["kubectl", "logs", "--namespace=calico-system",
                                 pod_name, "-c", "k8s-policy-agent"])

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

    # Get all pod names.
    print "Getting all pods in default namespace"
    all_pods = check_output(["kubectl", "get", "pods", "-o", "json"])
    all_pods = json.loads(all_pods)["items"]

    # Get all "getter" pod names.
    pods = {str(p["metadata"]["name"]): p for p in all_pods
                    if "getter" in p["metadata"]["name"]}

    print "Generating queue of pod names"
    for pod_name, pod in pods.iteritems():
        pod_names_q.put((pod_name, pod))

    def get_logs():
        while True:
            try:
                pod_name, pod = pod_names_q.get_nowait()
            except Queue.Empty:
                break

            try:
                print "Getting logs for %s (remaining: %s)" % (pod_name, pod_names_q.qsize())
                logs = check_output(["kubectl", "logs", pod_name])
            except subprocess.CalledProcessError, e:
                print "Error getting logs for: %s" % pod_name
                continue
            else:
                pod_logs_q.put((pod_name, logs))

    print "Starting threads to get logs"
    threads = []
    for i in range(100):
        t = threading.Thread(target=get_logs)
        t.daemon = True
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print "Finished getting logs, parsing"
    logs_by_pod = {}
    while True:
        try:
            pod_name, logs =  pod_logs_q.get_nowait()
        except Queue.Empty:
            break
        else:
            logs_by_pod[pod_name] = logs

    print "Parsing results"
    for pod_name, logs in logs_by_pod.iteritems():
        print "Pod %s \n%s" % (pod_name, logs)
        pod = pods.get(pod_name)
        try:
            # Format: 2016-04-11T21:04:15Z
            fmt = "%Y-%m-%dT%H:%M:%SZ"
            start_dt = pod["status"]["startTime"]
            start_time = datetime.datetime.strptime(start_dt, fmt)
            #start_time = float(start_re.findall(logs)[0])
        except IndexError:
            print "pod has not started yet: %s" % pod_name
            failed.append((pod, logs, None))
            continue

        try:
            end_time = float(end_re.findall(logs)[0])
        except IndexError:
            print "No end time for pod: %s" % pod_name
            failed.append((pod, logs, None))
            continue

        try:
            elapsed = float(elapsed_re.findall(logs)[0])
        except IndexError:
            print "No elapsed time for pod: %s" % pod_name
            failed.append((pod, logs, None))
            continue

        # Determine the elapsed time and store in the mapping dict.
        times = elapsed_by_start_time.setdefault(start_time, [])
        times.append(elapsed)

        if pod_name in data_by_pod:
            agent_process_times.append(data_by_pod[pod_name]["process_time"])

        # Store data.
        data_by_pod.setdefault(pod_name, {}).update({
                "times": time_re.findall(logs),
                "start_time": start_time,
                "elapsed_time": elapsed,
                "logs": logs,
                "raw": pod
        })

def display_data():
    # Extract data to display.
    start_times = []
    elapsed_times = []
    for k, v in data_by_pod.iteritems():
        if "getter" in k:
            # Some of the keys aren't actually pods, because this
            # scripts is a hack.
            start_times.append(v["start_time"])
            elapsed_times.append(v["elapsed_time"])

    # Order the start times.
    ordered_start_times = sorted(start_times)

    print "%s failed to get logs" % len(failed)

    # Create histogram of elapsed time-to-connect.
    vals = []
    for _, l in elapsed_by_start_time.iteritems():
        vals += l
    pylab.hist(vals)
    pylab.xlabel('time to first connectivity')
    pylab.ylabel('Number of pods')
    #pylab.show()
    pylab.savefig('ttfp_relative.png', bbox_inches='tight')


    # Calculate start times, shifted to account
    # for the first pod to start.
    min_x = ordered_start_times[0]
    max_x = ordered_start_times[-1]
    x = [(t-min_x).seconds for t in start_times]

    # Calculate 99th percentile time to first ping.
    ordered_elapsed_times = sorted(elapsed_times)
    index = int(.99 * len(ordered_start_times))
    percentile = ordered_elapsed_times[index]
    average = sum(elapsed_times) / len(elapsed_times)

    # Print out some data.
    startup_time = (ordered_start_times[-1] - ordered_start_times[0]).seconds
    print "Time to start %s pods: %s (%s pods/s)" % (len(x),
                                                     startup_time,
                                                     len(x)/startup_time)
    print "99th percentile: %s" % percentile
    print "Average elapsed time: %s" % average

    # Plot data.
    pylab.plot(x, elapsed_times, 'bo')
    pylab.xlabel('time(s)')
    pylab.ylabel('Time to first connectivity (s)')
    #pylab.show()
    pylab.savefig('ttfp_absolute.png', bbox_inches='tight')

    if agent_process_times:
        # Plot agent process time versus pod started time.
        pylab.plot(x, agent_process_times, "ro")
        pylab.xlabel('pod start time')
        pylab.ylabel('Time spent in agent')
        pylab.savefig('agent_time.png', bbox_inches='tight')
        #pylab.show()

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
    pylab.savefig('agent_q_length.png', bbox_inches='tight')
    #pylab.show()

def write_data():
    # Write to file.
    filename = "%s-pods-%s" % (len(elapsed_times), datetime.datetime.now())
    print "Writing results to file: %s" % filename
    with open("testdata/%s" % filename, "a") as f:
        f.write(json.dumps(data_by_pod))

if __name__ == "__main__":
    collect_data()
    display_data()
