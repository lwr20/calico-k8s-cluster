import os
import numpy
import matplotlib.pyplot as pylab
import json
import subprocess
import re
import Queue
import datetime
import time
import threading
from dateutil import parser
from subprocess import check_output

SAVE_GRAPHS = True
DISPLAY_GRAPHS = False

filename_prefix = time.strftime("%Y%m%d-%H%M%S")

# Various regexes.
queue_time_re = re.compile(
    "INFO \('default', '(.*)'\) time on the queue: ([0-9\.]+)")
proc_time_re = re.compile(
    "INFO \('default', '(.*)'\) total process time: ([0-9]+\.[0-9]+)")
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
    # Get all pod names in kube-system.
    print "Getting all pods in kube-system namespace"
    all_pods = check_output(["kubectl", "get",
                             "pods", "--namespace=kube-system",
                             "-o", "json"])
    all_pods = json.loads(all_pods)["items"]

    # Get calico-policy-controller (agent) pod metadata if it is running.
    pod_name = ""
    for p in all_pods:
        if "calico-policy-controller" in p["metadata"]["name"]:
            pod_name = str(p["metadata"]["name"])
    
    # Extract logs.
    if pod_name:
        print "Getting calico policy controller logs"
        calico_logs = check_output(["kubectl", "logs", "--namespace=kube-system",
                                    pod_name, "-c", "calico-policy-controller"])
        write_data("kube-system", all_pods)

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
    pods = {str(p["metadata"]["name"]): p for p in all_pods if "getter" in
            p["metadata"]["name"]}

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
                print "Getting logs for %s (remaining: %s)" % (
                    pod_name, pod_names_q.qsize())
                logs = check_output(["kubectl", "logs", pod_name])
            except subprocess.CalledProcessError:
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
            pod_name, logs = pod_logs_q.get_nowait()
        except Queue.Empty:
            break
        else:
            logs_by_pod[pod_name] = logs

    print "Parsing results"
    for pod_name, logs in logs_by_pod.iteritems():
        print "Pod %s \n%s" % (pod_name, logs.splitlines()[-5:])
        pod = pods.get(pod_name)
        try:
            # Format: 2016-04-11T21:04:15Z
            fmt = "%Y-%m-%dT%H:%M:%SZ"
            start_dt = pod["status"]["startTime"]
            start_time = datetime.datetime.strptime(start_dt, fmt)
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
    if SAVE_GRAPHS:
        pylab.savefig('testdata/%s_ttfp_relative.png' % filename_prefix,
                      bbox_inches='tight')
    if DISPLAY_GRAPHS:
        pylab.show()

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
    startup_time = (max_x - min_x).seconds
    if startup_time != 0:  
        print "Time to start %s pods: %s seconds (%s pods/s)" % (len(x),
                                                         startup_time,
                                                         len(x)/startup_time)
    else: 
        print "Time to start %s pods: %s seconds" % (len(x), startup_time)
    
    print "99th percentile: %s" % percentile
    print "Average elapsed time: %s" % average

    # Plot data.
    pylab.plot(x, elapsed_times, 'bo')
    pylab.xlabel('time(s)')
    pylab.ylabel('Time to first connectivity (s)')
    if SAVE_GRAPHS:
        pylab.savefig('testdata/%s_ttfp_absolute.png' % filename_prefix,
                      bbox_inches='tight')
    if DISPLAY_GRAPHS:
        pylab.show()

    if agent_process_times:
        # Plot agent process time versus pod started time.
        pylab.plot(x, agent_process_times, "ro")
        pylab.xlabel('pod start time')
        pylab.ylabel('Time spent in agent')
    if SAVE_GRAPHS:
        pylab.savefig('testdata/%s_agent_time.png' % filename_prefix,
                      bbox_inches='tight')
    if DISPLAY_GRAPHS:
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
    if SAVE_GRAPHS:
        pylab.savefig('testdata/%s_agent_q_length.png' % filename_prefix,
                      bbox_inches='tight')
    if DISPLAY_GRAPHS:
        pylab.show()


def write_data(filename, data):
    # Write to file.
    filename = "%s_%s" % (filename_prefix, filename)
    print "Writing to file: %s" % filename
    check_output(["mkdir", "-p", "testdata"])
    with open("testdata/%s" % filename, "a") as f:
        f.write(json.dumps(data))

if __name__ == "__main__":
    collect_data()
    display_data()
