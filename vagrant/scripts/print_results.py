import json
import sys
from isodate import parse_datetime

# pipe

obj = json.load(sys.stdin)

times = []

for item in obj['items']:
    pod_ip = item['status']['podIP']
    status = item['status']['phase']
    pod_name = item['metadata']['name']
    if not "busybox" in pod_name:
        continue
    start_time = parse_datetime(item['status']['startTime'])
    started_at = parse_datetime(item['status']['containerStatuses'][0]['state']['running']['startedAt'])

    startup_time = (started_at - start_time).seconds
    times.append(startup_time)

    print "%s,%s,%s,%s" % (pod_name, pod_ip, status, startup_time)


print ""
print "Min(%s) Max(%s) Avg(%s)" % (min(times), max(times), sum(times)/float(len(times)))