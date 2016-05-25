# Parameters for the cluster, don't edit these directly, put your changes in
# local-settings.mk.
CLUSTER_SIZE:=2
ETCD_CLUSTER_SIZE:=3
NUM_PODS:=300
GCE_REGION:=us-central1-f
GCE_PROJECT:=unique-caldron-775
GCE_IMAGE_NAME:=coreos-alpha-1010-1-0-v20160407
MASTER_INSTANCE_TYPE:=n1-standard-16
NODE_INSTANCE_TYPE:=n1-highcpu-4
ETCD_INSTANCE_TYPE:=n1-standard-16
PROM_INSTANCE_TYPE:=n1-standard-4
RR_INSTANCE_TYPE:=n1-standard-4
PREFIX:=kube-scale
NODE_IMAGE:=calico/node:v0.19.0
GETTER_IMAGE:=caseydavenport/scale-tester:latest

# Whether to use the unpacked CNI plugin (rather than the one-file, packed
# version).  "y" or "n".  Note: this URL is for an experimental, unreleased
# version of the plugin.  The purpose of this flag is to test whether using
# an unpacked version of the plugin improves scale.
USE_UNPACKED_CNI_PLUGIN:=n
UNPACKED_CNI_PLUGIN_URL:=https://storage.googleapis.com/calico-scale-testing-files/calico-cni-unpacked-a1c2749-libcalico-f0f9f33.tgz
# URL of the standard (packed) version of the CNI plugin.
PACKED_CNI_PLUGIN_URL:=https://github.com/projectcalico/calico-cni/releases/download/v1.3.0/calico
# URL of pre-configured Grafana DB.  Currently, this is empty apart from
# having Prometheus pre-configured as the default data source.
GRAFANA_DB_URL:=https://storage.googleapis.com/calico-scale-testing-files/grafana.db

-include local-settings.mk

# GCE bucket we use to store files we need to transfer to hosts.
GCE_BUCKET:=$(PREFIX)-data
# Number of nginx pod instances to create
NGINX_INSTANCES:=$(shell echo ${CLUSTER_SIZE}/10 + 1 | bc)

# Generate node names.
NODE_NUMBERS := $(shell seq -f '%02.0f' 1 $(CLUSTER_SIZE))
NODE_NAMES := $(addprefix $(PREFIX)-,$(NODE_NUMBERS))
ETCD_NODE_NUMBERS := $(shell seq -f '%02.0f' 1 $(ETCD_CLUSTER_SIZE))
ETCD_NODE_SUFFIXES := $(addprefix etcd-,$(ETCD_NODE_NUMBERS))
ETCD_NODE_NAMES := $(addprefix $(PREFIX)-,$(ETCD_NODE_SUFFIXES))
ETCD_CONFIG_FILENAMES := $(addprefix build/etcd-,$(ETCD_NODE_NUMBERS))

# Figure out what files need templating.
INPUT_TEMPLATES := $(shell find templates/ -type f)
TEMPLATED_OUTPUT := $(patsubst templates/%, build/%, $(INPUT_TEMPLATES))

# Calculate template substitutions.
ETCD_PEER_URLS := $(shell python -c 'print ",".join(["etcd-%02d=http://$(PREFIX)-etcd-%02d:2380" % (i, i) for i in range(1, $(ETCD_CLUSTER_SIZE)+1)])')
ETCD_CLIENT_URLS := $(shell python -c 'print ",".join(["etcd-%02d=http://$(PREFIX)-etcd-%02d:2379" % (i, i) for i in range(1, $(ETCD_CLUSTER_SIZE)+1)])')
ETCD_ENDPOINTS := $(shell python -c 'print ",".join(["http://$(PREFIX)-etcd-%02d.c.$(GCE_PROJECT).internal:2379" % i for i in range(1, $(ETCD_CLUSTER_SIZE)+1)])')
PROM_FELIX_ENDPOINTS := $(shell python -c 'print str(["$(PREFIX)-%02d:9091" % n for n in range(1, $(CLUSTER_SIZE)+1)])')
PROM_DRIVER_ENDPOINTS := $(shell python -c 'print str(["$(PREFIX)-%02d:9092" % n for n in range(1, $(CLUSTER_SIZE)+1)])')
PROM_HOST_ENDPOINTS := $(shell python -c 'print str(["$(PREFIX)-%02d:9100" % n for n in range(1, $(CLUSTER_SIZE)+1)])')
PROM_ETCD_ENDPOINTS := $(shell python -c 'print str(["$(PREFIX)-etcd-%02d:2379" % n for n in range(1, $(ETCD_CLUSTER_SIZE)+1)])')
PROM_ETCD_HOST_ENDPOINTS := $(shell python -c 'print str(["$(PREFIX)-etcd-%02d:9100" % n for n in range(1, $(ETCD_CLUSTER_SIZE)+1)])')

# Figure out what OS we're on (OSX or Linux) and lowercase it
OS := $(shell uname -s | tr A-Z a-z)

# get current directory
CURRENT_DIR := $(shell pwd)

# Make a list of diags targets
DIAGS_TARGETS := $(NODE_NUMBERS) $(ETCD_NODE_SUFFIXES) master prom rr1 rr2
LOG_RETRIEVAL_TARGETS := $(addprefix job,${DIAGS_TARGETS})

kubectl:
	wget http://storage.googleapis.com/kubernetes-release/release/v1.2.0/bin/$(OS)/amd64/kubectl
	chmod +x kubectl

calicoctl-status:
	-ssh -o LogLevel=quiet core@${PREFIX}-master.${GCE_REGION}.unique-caldron-775 sudo ETCD_AUTHORITY=kube-scale-etcd-01:2379 calicoctl status

calicoctl:
	wget http://www.projectcalico.org/builds/calicoctl
	chmod +x calicoctl

deploy-heapster: remove-heapster $(TEMPLATED_OUTPUT)
	kubectl create -f build/heapster

remove-heapster:
	-kubectl delete -f build/heapster/ --grace-period=1

# Node selectors in the pod specs don't allow negation, so apply a label that can be used as-is here.
apply-node-labels:
	bash -c 'while [ $$(kubectl get no |grep role=node -c) -ne $(CLUSTER_SIZE) ] ;  do kubectl label --overwrite=true nodes -l kubernetes.io/hostname!=127.0.0.1 role=node; done'
	kubectl get no
	@echo "Number of labeled nodes: "
	@make --no-print-directory gce-list-nodes-count

deploy-pinger: remove-pinger $(TEMPLATED_OUTPUT)
	kubectl create -f build/pinger
	kubectl get rc
	kubectl get po

remove-pinger:
	-kubectl delete rc pinger --grace-period=1

scale-pinger:
	kubectl scale --replicas=10000 rc/pinger

prepare-getter:
	# Make sure policy is applied by attempting to create it again
	-cd $(CURRENT_DIR)/policy-scale-test && ./policy create -f nginx-policy.yaml
	# Create all the namespaces and RCs
	cd $(CURRENT_DIR)/policy-scale-test && ./start.sh
	$(MAKE) --no-print-directory scale-nginx

scale-nginx:
	kubectl scale rc nginx-server --replicas=$(NGINX_INSTANCES)
	echo 'Now use make "gce-successful-pods" to check they are all running'

scale-getter:
	echo 'Scaling up number of getter pods to $(NUM_PODS)'
	kubectl scale rc getter --replicas=$(NUM_PODS)
	echo 'Now use "make gce-successful-pods" to check they are all running'

get-results:
	bash -c 'source ../env/bin/activate && cd $(CURRENT_DIR)/policy-scale-test && python get-data.py | tee testdata/result.txt'

# See http://stackoverflow.com/a/12110773/61318
#make -j12 get-diags
get-diags: describe-nodes describe-pods describe-services describe-rc describe-ep get-prom-data $(LOG_RETRIEVAL_TARGETS) get-pod-logs

get-prom-data:
	-ssh -A -o LogLevel=quiet core@$(PREFIX)-master.$(GCE_REGION).$(GCE_PROJECT) ssh -o LogLevel=quiet -o StrictHostKeyChecking=no $(PREFIX)-prom sudo tar -cvzf - /var/log/prom_data > timings/prom_data.tgz

get-pod-logs:
	-kubectl get pods | grep getter | cut -f 1 -d " " | xargs -iPOD sh -c 'kubectl logs POD | gzip > timings/POD.log.gz &'

$(LOG_RETRIEVAL_TARGETS): job%:
	@mkdir -p timings
	-ssh -A -o LogLevel=quiet core@$(PREFIX)-master.$(GCE_REGION).$(GCE_PROJECT) ssh -o LogLevel=quiet -o StrictHostKeyChecking=no $(PREFIX)-$* journalctl --no-pager > timings/journal-$*.log &
	-ssh -A -o LogLevel=quiet core@$(PREFIX)-master.$(GCE_REGION).$(GCE_PROJECT) ssh -o LogLevel=quiet -o StrictHostKeyChecking=no $(PREFIX)-$* sudo /home/core/getcdiags.sh > timings/diags-$*.tgz &
	-gcloud compute instances get-serial-port-output $(PREFIX)-$* > timings/serial-$*.log

describe-nodes:
	-kubectl describe nodes > timings/describe-nodes.log

describe-pods:
	-kubectl describe pods > timings/describe-pods.log

describe-services:
	-kubectl describe services > timings/describe-services.log

describe-rc:
	-kubectl describe rc > timings/describe-rc.log

describe-ep:
	-kubectl describe ep > timings/describe-ep.log

.PHONY: $(LOG_RETRIEVAL_TARGETS)

.PHONY: render-templates
render-templates: $(TEMPLATED_OUTPUT)

build/$(GCE_BUCKET).created:
	-gsutil mb -p $(GCE_PROJECT) gs://$(GCE_BUCKET)
	touch build/$(GCE_BUCKET).created

# Download the packed CNI plugin binary.
build/calico/calico:
	mkdir -p build/calico
	wget $(PACKED_CNI_PLUGIN_URL) -O build/calico/calico
	chmod +x build/calico/calico

build/calico-cni-unpacked.tgz:
	rm -f build/calico-cni-unpacked.tgz;
	wget $(UNPACKED_CNI_PLUGIN_URL) -O build/calico-cni-unpacked.tgz

# Takes the bare calico executable and packages it in a tgz so that its
# structure matches the unpacked plugin.
build/calico-cni-packed.tgz: Makefile local-settings.mk build/calico/calico
	tar -czf build/calico-cni-packed.tgz --directory build calico

build/calico-cni-packed-url: build/calico-cni-packed.tgz build/$(GCE_BUCKET).created
	gsutil cp build/calico-cni-packed.tgz gs://$(GCE_BUCKET)/calico-cni-packed.tgz
	gsutil acl ch -u AllUsers:R gs://$(GCE_BUCKET)/calico-cni-packed.tgz
	echo "https://storage.googleapis.com/$(GCE_BUCKET)/calico-cni-packed.tgz" > build/calico-cni-packed-url

ifeq ($(USE_UNPACKED_CNI_PLUGIN), y)
build/calico-cni-url: Makefile local-settings.mk
	echo "$(UNPACKED_CNI_PLUGIN_URL)" > build/calico-cni-url
else
build/calico-cni-url: build/calico-cni-packed-url Makefile local-settings.mk
	cp build/calico-cni-packed-url build/calico-cni-url
endif

run-local-prom:
	# Prometheus needs a config file, but a blank one will do
	echo "" > $(CURRENT_DIR)/timings/prometheus.yml
	# Extract the prometheus data saved off from the cloud
	-tar --overwrite -xvzf $(CURRENT_DIR)/timings/prom_data.tgz -C $(CURRENT_DIR)/timings/
	# Run prometheus, using the extracted database.
	docker run --rm --name prometheus -p 9090:9090 -v $(CURRENT_DIR)/timings/prometheus.yml:/etc/prometheus.yml -v $(CURRENT_DIR)/timings/var/log/prom_data:/prometheus prom/prometheus -config.file=/etc/prometheus.yml -storage.local.path=/prometheus &

run-local-grafana:
	mkdir -p $(CURRENT_DIR)/timings/etc/grafana/dashboards
	cp local_grafana.ini $(CURRENT_DIR)/timings/etc/grafana/grafana.ini
	wget -N -P $(CURRENT_DIR)/timings/etc/grafana/ $(GRAFANA_DB_URL)
	cp templates/dashboards/* $(CURRENT_DIR)/timings/etc/grafana/dashboards/
	docker run --rm --name grafana --net=host -v $(CURRENT_DIR)/timings/etc/grafana/:/etc/grafana/ grafana/grafana &

view-diags:
	$(MAKE) --no-print-directory run-local-prom
	$(MAKE) --no-print-directory run-local-grafana
	sleep 2
	@echo "- Grafana dashboard at http://localhost:3000/dashboard/file/grafana-dash.json"
	@echo "- Prometheus at http://localhost:9090/"

view-diags-stop:
	-docker stop grafana
	-docker stop prometheus
	sudo rm -rf timings/etc

build/dashboards.tgz:
	tar -cvzf build/dashboards.tgz -C templates/dashboards/ .

build/grafana-json-url: Makefile local-settings.mk templates/dashboards/*.json build/dashboards.tgz
	gsutil cp build/dashboards.tgz gs://$(GCE_BUCKET)/dashboards.tgz
	gsutil setmeta \
	  -h "Cache-Control:private, max-age=0, no-transform" \
	  gs://$(GCE_BUCKET)/dashboards.tgz
	gsutil acl ch -u AllUsers:R gs://$(GCE_BUCKET)/dashboards.tgz
	echo "https://storage.googleapis.com/$(GCE_BUCKET)/dashboards.tgz" > build/grafana-json-url

build/prom-conf-url: Makefile local-settings.mk build/prometheus.yml
	gsutil cp build/prometheus.yml gs://$(GCE_BUCKET)/prometheus.yml
	gsutil setmeta \
	  -h "Cache-Control:private, max-age=0, no-transform" \
	  gs://$(GCE_BUCKET)/prometheus.yml
	gsutil acl ch -u AllUsers:R gs://$(GCE_BUCKET)/prometheus.yml
	echo "https://storage.googleapis.com/$(GCE_BUCKET)/prometheus.yml" > build/prom-conf-url

gce-create: kubectl calicoctl $(TEMPLATED_OUTPUT)
	$(MAKE) --no-print-directory deploy-master
	$(MAKE) --no-print-directory deploy-prom
	$(MAKE) --no-print-directory deploy-etcd
	$(MAKE) --no-print-directory deploy-rr
	$(MAKE) --no-print-directory deploy-nodes
	$(MAKE) --no-print-directory gce-config-ssh
	$(MAKE) --no-print-directory gce-forward-ports
	#$(MAKE) --no-print-directory apply-node-labels

deploy-master:
	-gcloud compute instances create \
	  $(PREFIX)-master \
	  --zone $(GCE_REGION) \
	  --image-project coreos-cloud \
	  --image $(GCE_IMAGE_NAME) \
	  --machine-type $(MASTER_INSTANCE_TYPE) \
	  --local-ssd interface=scsi \
	  --metadata-from-file user-data=build/master-config-template.yaml & \
	  echo "Waiting for creation of master node to finish..."; \
	  wait; \
	  echo "master node started."

deploy-nodes:
	echo $(NODE_NAMES) | xargs -n250 | xargs -I{} sh -c 'gcloud compute instances create \
	  {} \
	  --zone $(GCE_REGION) \
	  --image-project coreos-cloud \
	  --image $(GCE_IMAGE_NAME) \
	  --machine-type $(NODE_INSTANCE_TYPE) \
	  --metadata-from-file user-data=build/node-config-template.yaml \
	  --no-address \
	  --tags no-ip & \
	  echo "Waiting for creation of this batch of worker nodes to finish..."; \
		wait; \
		echo "Batch of nodes created. Waiting 120s for cluster to settle down..."; \
	  sleep 120;'

deploy-prom:
	-gcloud compute instances create \
	  $(PREFIX)-prom \
	  --image-project coreos-cloud \
	  --zone $(GCE_REGION) \
	  --image $(GCE_IMAGE_NAME) \
	  --machine-type $(PROM_INSTANCE_TYPE) \
	  --metadata-from-file user-data=build/prom-config-template.yaml \
	  --no-address \
	  --tags no-ip & \
	  echo "Waiting for creation of prometheus node to finish..."; \
	  wait; \
	  echo "prometheus node started."

deploy-rr:
	-gcloud compute instances create \
	  $(PREFIX)-rr1 $(PREFIX)-rr2  \
	  --image-project coreos-cloud \
	  --zone $(GCE_REGION) \
	  --image $(GCE_IMAGE_NAME) \
	  --machine-type $(RR_INSTANCE_TYPE) \
	  --metadata-from-file user-data=build/rr-template.yaml \
	  --no-address \
	  --tags no-ip & \
	  echo "Waiting for creation of route reflector node to finish..."; \
	  wait; \
	  echo "route reflector node started."

remove-prom:
	gcloud compute instances delete --zone $(GCE_REGION) $(PREFIX)-prom

# build/prometheus.yml needs its own templating to avoid a circular dependency.
build/prometheus.yml: templates/prometheus.yml Makefile local-settings.mk
	mkdir -p "$(@D)"
	cat "$<" | \
	  sed "s~__CLUSTER_PREFIX__~$(PREFIX)~g" | \
	  sed "s~__FELIXES__~$(PROM_FELIX_ENDPOINTS)~g" | \
	  sed "s~__DRIVERS__~$(PROM_DRIVER_ENDPOINTS)~g" | \
	  sed "s~__PROM_HOSTS__~$(PROM_HOST_ENDPOINTS)~g" | \
	  sed "s~__PROM_ETCD_ENDPOINTS__~$(PROM_ETCD_ENDPOINTS)~g" | \
	  sed "s~__PROM_ETCD_HOST_ENDPOINTS__~$(PROM_ETCD_HOST_ENDPOINTS)~g" > $@;

build/%: templates/% Makefile local-settings.mk build/calico-cni-url build/grafana-json-url build/prom-conf-url
	mkdir -p "$(@D)"
	cat "$<" | \
	  sed "s~__ETCD_PEER_URLS__~$(ETCD_PEER_URLS)~g" | \
	  sed "s~__ETCD_CLIENT_URLS__~$(ETCD_CLIENT_URLS)~g" | \
	  sed "s~__ETCD_ENDPOINTS__~$(ETCD_ENDPOINTS)~g"  | \
	  sed "s~__CLUSTER_PREFIX__~$(PREFIX)~g" | \
	  sed "s~__GCE_PROJECT__~$(GCE_PROJECT)~g" | \
	  sed "s~__NODE_IMAGE__~$(NODE_IMAGE)~g" | \
	  sed "s~__GETTER_IMAGE__~$(GETTER_IMAGE)~g" | \
	  sed "s~__CNI_PLUGIN_URL__~$$(cat build/calico-cni-url)~g" | \
	  sed "s~__GRAFANA_DB_URL__~$(GRAFANA_DB_URL)~g" | \
	  sed "s~__GRAFANA_DASH_JSON_URL__~$$(cat build/grafana-json-url)~g" | \
	  sed "s~__PROMETHEUS_CONFIG_URL__~$$(cat build/prom-conf-url)~g" > $@;

build/etcd-%: build/etcd-template.yaml
	node_name=`basename $@`; \
	  cat build/etcd-template.yaml | \
	    sed "s/__ETCD_NODE_NAME__/$$node_name/g" > $@;

deploy-etcd: $(ETCD_CONFIG_FILENAMES)
	for ii in ${ETCD_NODE_NUMBERS}; do \
	  echo "Starting $(PREFIX)-etcd-$$ii"; \
	  gcloud compute instances create \
	    $(PREFIX)-etcd-$$ii \
	    --zone $(GCE_REGION) \
	    --image-project coreos-cloud \
	    --image $(GCE_IMAGE_NAME) \
	    --machine-type $(ETCD_INSTANCE_TYPE) \
	    --local-ssd interface=scsi \
	    --no-address \
	    --metadata-from-file user-data=build/etcd-$$ii \
	    --tags no-ip & \
	done; \
	echo "Waiting for creation of etcd nodes to finish..."; \
	wait; \
	echo "etcd nodes started."

gce-cleanup:
	gcloud compute instances list --zones $(GCE_REGION) -r '$(PREFIX).*' | \
	  tail -n +2 | cut -f1 -d' ' | xargs gcloud compute instances delete --zone $(GCE_REGION)

gce-forward-ports:
	@-pkill -f '8080:localhost:8080'
	bash -c 'until ssh -o LogLevel=quiet -o PasswordAuthentication=no core@$(PREFIX)-master.$(GCE_REGION).$(GCE_PROJECT) date; do echo "Trying to forward ports"; sleep 1; done'
	ssh -o PasswordAuthentication=no \
	    -L 8080:localhost:8080 \
	    -L 2379:localhost:2379 \
	    -L 4194:localhost:4194 \
	    -L 9090:$(PREFIX)-prom:9090 \
	    -L 3000:$(PREFIX)-prom:3000 \
	    -o LogLevel=quiet -nNT \
	    core@$(PREFIX)-master.$(GCE_REGION).$(GCE_PROJECT) &
	@echo
	@echo "Forwarded ports:"
	@echo "- Grafana dashboard at http://localhost:3000/dashboard/file/grafana-dash.json"
	@echo "- Prometheus at http://localhost:9090/"
	@echo "- Kubernetes' etcd at http://localhost:2379/"
	@echo "- Kubernetes' API at http://localhost:8080/"

gce-redeploy: build/master-config-template.yaml build/node-config-template.yaml
	gcloud compute instances add-metadata $(PREFIX)-master --metadata-from-file=user-data=build/master-config-template.yaml
	gcloud compute instances add-metadata $(NODE_NAMES) --metadata-from-file=user-data=build/node-config-template.yaml
#	gcloud compute ssh $(PREFIX)-master sudo reboot

gce-config-ssh:
	gcloud compute config-ssh

gce-ssh-master:
	ssh -A core@$(PREFIX)-master.$(GCE_REGION).$(GCE_PROJECT)

gce-bgp-status:
	ssh core@$(PREFIX)-master.$(GCE_REGION).$(GCE_PROJECT) /opt/bin/calicoctl status

gce-bgp-status-count:
	ssh core@$(PREFIX)-master.$(GCE_REGION).$(GCE_PROJECT) /opt/bin/calicoctl status |grep -c Established

gce-list-nodes:
	kubectl get no --no-headers -l 'kubernetes.io/hostname!=127.0.0.1'

gce-list-nodes-count:
	@kubectl get no --no-headers -l 'kubernetes.io/hostname!=127.0.0.1' | wc -l

gce-successful-pods:
	kubectl get po | grep -P -c '1/1\s+Running\s+0'

gce-failed-pods:
	kubectl get po |grep -v Pending |grep -v Running

gce-wait-for-pod-creation:
	bash -c 'while [ $$(kubectl get po | grep -P -c "1/1\s+Running\s+0") -ne $(NUM_PODS) ] ;  do date; echo "Not enough nodes created - waiting"; kubectl describe rc |grep "Pods Status"; sleep 1;done'
