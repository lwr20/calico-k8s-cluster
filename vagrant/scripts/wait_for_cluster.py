import time
import json
import sys
import os
from subprocess import check_output

# Max time to wait for nodes to start.
MAX_SECONDS = 60

# Total number of nodes, including the master.
NUM_NODES = 2

kubectl_path = "kubectl"

print("Waiting up to %ss for nodes..." % MAX_SECONDS)
for i in range(MAX_SECONDS):
	nodes = check_output([kubectl_path, "get", "nodes", "--output=json"])
	nodes = json.loads(nodes)["items"]

	# Check if we should exit.
	print("%s node(s) started" % len(nodes))
	if len(nodes) >= NUM_NODES:
		print("All nodes started")
		sys.exit(0)
	if i == MAX_SECONDS:
		print("Failed to start all nodes")
		sys.exit(1)

	# Sleep for 1 second.
	time.sleep(1)
