# Parameters for the cluster, don't edit these directly, put your changes in
# local-settings.mk.
CLUSTER_SIZE := 2
ETCD_CLUSTER_SIZE := 3
GCE_REGION=us-central1-f
GCE_PROJECT=unique-caldron-775
MASTER_INSTANCE_TYPE=n1-standard-16
NODE_INSTANCE_TYPE=n1-highcpu-4
ETCD_INSTANCE_TYPE=n1-standard-16
PROM_INSTANCE_TYPE=n1-standard-4
PREFIX=kube-scale
NODE_IMAGE=calico/node:v0.19.0
# Whether to use the unpacked CNI plugin (rather than the one-file, packed
# version).  "y" or "n".
USE_UNPACKED_CNI_PLUGIN=n
UNPACKED_CNI_PLUGIN_URL=https://transfer.sh/bw4hX/calico-cni.tgz
PACKED_CNI_PLUGIN_URL=https://circle-artifacts.com/gh/projectcalico/calico-cni/154/artifacts/0/home/ubuntu/calico-cni/dist/calico

-include local-settings.mk

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

# Add on the etcd nodes and master
NODE_NUMBERS += $(ETCD_NODE_SUFFIXES) master
LOG_RETRIEVAL_TARGETS := $(addprefix job,${NODE_NUMBERS})
PODS := 10000

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

# See http://stackoverflow.com/a/12110773/61318
#make -j12 CLUSTER_SIZE=26 pull-plugin-timings
pull-plugin-timings: $(LOG_RETRIEVAL_TARGETS)
	grep TIMING timings/cni*.log > timings/all.timings
	grep -v TIMING timings/cni*.log | grep -v INFO > timings/all.errors
	# -ssh -o LogLevel=quiet core@${PREFIX}-master.${GCE_REGION}.unique-caldron-775 journalctl --no-pager >timings/master.log

$(LOG_RETRIEVAL_TARGETS): job%:
	@mkdir -p timings
	-ssh -A -o LogLevel=quiet core@$(PREFIX)-master.$(GCE_REGION).$(GCE_PROJECT) ssh -o LogLevel=quiet -o StrictHostKeyChecking=no $(PREFIX)-$* sudo tar -cvzf - /var/log/calico > timings/logs-$*.tgz &
	-ssh -A -o LogLevel=quiet core@$(PREFIX)-master.$(GCE_REGION).$(GCE_PROJECT) ssh -o LogLevel=quiet -o StrictHostKeyChecking=no $(PREFIX)-$* cat /var/log/calico/cni/cni.log > timings/cni-$*.log &
	-ssh -A -o LogLevel=quiet core@$(PREFIX)-master.$(GCE_REGION).$(GCE_PROJECT) ssh -o LogLevel=quiet -o StrictHostKeyChecking=no $(PREFIX)-$* journalctl --no-pager > timings/journal-$*.log &
	-gcloud compute instances get-serial-port-output $(PREFIX)-$* > timings/serial-$*.log

.PHONEY: $(LOG_RETRIEVAL_TARGETS)

.PHONEY: render-templates
render-templates: $(TEMPLATED_OUTPUT)

build/calico/calico:
	mkdir -p build/calico
	wget $(PACKED_CNI_PLUGIN_URL) -O build/calico/calico
	chmod +x build/calico/calico

build/calico-cni-unpacked.tgz:
	rm -f build/calico-cni-unpacked.tgz;
	wget $(UNPACKED_CNI_PLUGIN_URL) -O build/calico-cni-unpacked.tgz

build/calico-cni.tgz: Makefile local-settings.mk local-settings.mk build/calico/calico build/calico-cni-unpacked.tgz
	rm -f build/calico-cni.tgz;
	if [ $(USE_UNPACKED_CNI_PLUGIN) = "y" ]; then \
	  cp build/calico-cni-unpacked.tgz build/calico-cni.tgz; \
	else \
	  tar -czf build/calico-cni.tgz --directory build calico; \
	fi

.calico-cni-url: build/calico-cni.tgz
	curl --upload-file build/calico-cni.tgz https://transfer.sh/calico-cni.tgz > .calico-cni-url

gce-create: kubectl calicoctl $(TEMPLATED_OUTPUT)
	-gcloud compute instances create \
	  $(PREFIX)-master \
	  --zone $(GCE_REGION) \
	  --image-project coreos-cloud \
	  --image coreos-alpha-1010-1-0-v20160407 \
	  --machine-type $(MASTER_INSTANCE_TYPE) \
	  --local-ssd interface=scsi \
	  --metadata-from-file user-data=build/master-config-template.yaml

	make --no-print-directory gce-create-etcd

	gcloud compute instances create \
	  $(NODE_NAMES) \
	  --zone $(GCE_REGION) \
	  --image-project coreos-cloud \
	  --image coreos-alpha-1010-1-0-v20160407 \
	  --machine-type $(NODE_INSTANCE_TYPE) \
	  --metadata-from-file user-data=build/node-config-template.yaml \
	  --no-address \
	  --tags no-ip

	gcloud compute instances create \
	  $(PREFIX)-prom \
	  --image-project coreos-cloud \
	  --zone $(GCE_REGION) \
	  --image coreos-alpha-1010-1-0-v20160407 \
	  --machine-type $(PROM_INSTANCE_TYPE) \
	  --metadata-from-file user-data=build/prom-config-template.yaml \
	  --no-address \
	  --tags no-ip

	make --no-print-directory gce-config-ssh
	make --no-print-directory gce-forward-ports
	#make --no-print-directory apply-node-labels

build/%: templates/% Makefile local-settings.mk .calico-cni-url
	mkdir -p "$(@D)"
	cat "$<" | \
	  sed "s~__ETCD_PEER_URLS__~$(ETCD_PEER_URLS)~g" | \
	  sed "s~__ETCD_CLIENT_URLS__~$(ETCD_CLIENT_URLS)~g" | \
	  sed "s~__ETCD_ENDPOINTS__~$(ETCD_ENDPOINTS)~g"  | \
	  sed "s~__CLUSTER_PREFIX__~$(PREFIX)~g" | \
	  sed "s~__FELIXES__~$(PROM_FELIX_ENDPOINTS)~g" | \
	  sed "s~__DRIVERS__~$(PROM_DRIVER_ENDPOINTS)~g" | \
	  sed "s~__PROM_HOSTS__~$(PROM_HOST_ENDPOINTS)~g" | \
	  sed "s~__PROM_ETCD_ENDPOINTS__~$(PROM_ETCD_ENDPOINTS)~g" | \
	  sed "s~__PROM_ETCD_HOST_ENDPOINTS__~$(PROM_ETCD_HOST_ENDPOINTS)~g" | \
	  sed "s~__NODE_IMAGE__~$(NODE_IMAGE)~g"  | \
	  sed "s~__CNI_PLUGIN_URL__~$$(cat .calico-cni-url)~g" > $@;

build/etcd-%: build/etcd-template.yaml
	node_name=`basename $@`; \
	  cat build/etcd-template.yaml | \
	    sed "s/__ETCD_NODE_NAME__/$$node_name/g" > $@;

gce-create-etcd: $(ETCD_CONFIG_FILENAMES)
	for ii in ${ETCD_NODE_NUMBERS}; do \
	  echo "Starting $(PREFIX)-etcd-$$ii"; \
	  gcloud compute instances create \
	    $(PREFIX)-etcd-$$ii \
	    --zone $(GCE_REGION) \
	    --image-project coreos-cloud \
	    --image coreos-alpha-1010-1-0-v20160407 \
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
	ssh -o PasswordAuthentication=no -L 8080:localhost:8080 -L 2379:localhost:2379 -L 4194:localhost:4194 -L 9090:$(PREFIX)-prom:9090 -o LogLevel=quiet -nNT core@$(PREFIX)-master.$(GCE_REGION).$(GCE_PROJECT) &

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
	bash -c 'while [ $$(kubectl get po | grep -P -c "1/1\s+Running\s+0") -ne $(PODS) ] ;  do date; echo "Not enough nodes created - waiting"; kubectl describe rc |grep "Pods Status"; sleep 1;done'
