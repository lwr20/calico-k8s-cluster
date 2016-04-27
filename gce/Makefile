# Cluster parameters go here.
CLUSTER_SIZE := 2
ETCD_CLUSTER_SIZE := 3
GCE_REGION=us-central1-f
MASTER_INSTANCE_TYPE=n1-standard-16
NODE_INSTANCE_TYPE=n1-highcpu-4
ETCD_INSTANCE_TYPE=n1-standard-16
PROM_INSTANCE_TYPE=n1-standard-4
PREFIX=smc-kube-scale

# Generate node names.
NODE_NUMBERS := $(shell seq -f '%02.0f' 1 ${CLUSTER_SIZE})
NODE_NAMES := $(addprefix ${PREFIX}-,${NODE_NUMBERS})
ETCD_NODE_NUMBERS := $(shell seq -f '%02.0f' 1 ${ETCD_CLUSTER_SIZE})
ETCD_NODE_NAMES := $(addprefix ${PREFIX}-etcd-,${ETCD_NODE_NUMBERS})
ETCD_CONFIG_FILENAMES := $(addprefix build/etcd-,${ETCD_NODE_NUMBERS})

# Figure out what OS we're on (OSX or Linux) and lowercase it
OS := $(shell uname -s | tr A-Z a-z)

LOG_RETRIEVAL_TARGETS := $(addprefix job,${NODE_NUMBERS})
PODS := 10000

kubectl:
	wget http://storage.googleapis.com/kubernetes-release/release/v1.2.0/bin/${OS}/amd64/kubectl
	chmod +x kubectl

calicoctl:
	wget http://www.projectcalico.org/builds/calicoctl
	chmod +x calicoctl

deploy-heapster: remove-heapster
	kubectl create -f heapster

remove-heapster:
	-kubectl delete -f ./heapster/ --grace-period=1

# Node selectors in the pod specs don't allow negation, so apply a label that can be used as-is here.
apply-node-labels:
	bash -c 'while [ $$(kubectl get no |grep role=node -c) -ne ${CLUSTER_SIZE} ] ;  do kubectl label --overwrite=true nodes -l kubernetes.io/hostname!=127.0.0.1 role=node; done'
	kubectl get no
	@echo "Number of labeled nodes: "
	@make --no-print-directory gce-list-nodes-count

deploy-pinger: remove-pinger
	kubectl create -f pinger
	kubectl get rc
	kubectl get po

remove-pinger:
	-kubectl delete rc pinger --grace-period=1

scale-pinger:
	kubectl scale --replicas=10000 rc/pinger

# See http://stackoverflow.com/a/12110773/61318
#make -j12 CLUSTER_SIZE=26 pull-plugin-timings
pull-plugin-timings: ${LOG_RETRIEVAL_TARGETS}
	grep TIMING timings/cni*.log > timings/all.timings
	grep -v TIMING timings/cni*.log | grep -v INFO > timings/all.errors
	-ssh -o LogLevel=quiet core@${PREFIX}-master.${GCE_REGION}.unique-caldron-775 journalctl --no-pager >timings/master.log

${LOG_RETRIEVAL_TARGETS}: job%:
	@mkdir -p timings
	-ssh -A -o LogLevel=quiet core@${PREFIX}-master.${GCE_REGION}.unique-caldron-775 ssh -o LogLevel=quiet -o StrictHostKeyChecking=no ${PREFIX}-$* sudo tar -cvzf - /var/log/calico > timings/logs-$*.tgz
	-ssh -A -o LogLevel=quiet core@${PREFIX}-master.${GCE_REGION}.unique-caldron-775 ssh -o LogLevel=quiet -o StrictHostKeyChecking=no ${PREFIX}-$* cat /var/log/calico/cni/cni.log > timings/cni-$*.log
	-ssh -A -o LogLevel=quiet core@${PREFIX}-master.${GCE_REGION}.unique-caldron-775 ssh -o LogLevel=quiet -o StrictHostKeyChecking=no ${PREFIX}-$* journalctl --no-pager > timings/journal-$*.log

.PHONEY: ${LOG_RETRIEVAL_TARGETS}

gce-create: kubectl calicoctl build/prometheus.yaml
	-gcloud compute instances create \
  	${PREFIX}-master \
  	--zone ${GCE_REGION} \
  	--image-project coreos-cloud \
  	--image coreos-alpha-1010-1-0-v20160407 \
  	--machine-type ${MASTER_INSTANCE_TYPE} \
  	--local-ssd interface=scsi \
  	--metadata-from-file user-data=master-config-template.yaml

	make --no-print-directory gce-create-etcd

	gcloud compute instances create \
  	${NODE_NAMES} \
  	--zone ${GCE_REGION} \
  	--image-project coreos-cloud \
  	--image coreos-alpha-1010-1-0-v20160407 \
  	--machine-type ${NODE_INSTANCE_TYPE} \
  	--metadata-from-file user-data=node-config-template.yaml \
	--no-address \
	--tags no-ip

	gcloud compute instances create \
	  ${PREFIX}-prom \
	  --image-project coreos-cloud \
	  --zone ${GCE_REGION} \
	  --image coreos-alpha-1010-1-0-v20160407 \
	  --machine-type ${PROM_INSTANCE_TYPE} \
	  --metadata-from-file user-data=build/prometheus.yaml \
	  --no-address \
	  --tags no-ip

	make --no-print-directory gce-config-ssh
	make --no-print-directory gce-forward-ports
	#make --no-print-directory apply-node-labels

build/etcd-%: etcd-template.yaml
	mkdir -p build
	etcd_peers="";\
	delim="";\
	for ii in ${ETCD_NODE_NUMBERS}; do \
	  etcd_peers=$$etcd_peers$${delim}etcd-$$ii=http://${PREFIX}-etcd-$$ii:2380; \
	  delim=","; \
	done;\
	echo "Etcd peers $${etcd_peers}"; \
	node_name=`basename $@`; \
	cat etcd-template.yaml | sed "s~__ETCD_PEERS__~$$etcd_peers~g" | sed "s/__ETCD_NODE_NAME__/$$node_name/g" > $@;

build/prometheus.yaml: prom-config-template.yaml Makefile
	mkdir -p build
	felixes="[";\
	drivers="[";\
	delim="";\
	for ii in ${NODE_NAMES}; do \
	  felixes="$$felixes$$delim'$$ii:9091'"; \
	  drivers="$$drivers$$delim'$$ii:9092'"; \
	  delim=", "; \
	done;\
	echo "Felixes $${felixes}"; \
	echo "Drivers $${drivers}"; \
	cat prom-config-template.yaml | sed "s~__FELIXES__~$$felixes]~g" | sed "s/__DRIVERS__/$$drivers]/g" > $@;

gce-create-etcd: ${ETCD_CONFIG_FILENAMES} Makefile
	for ii in ${ETCD_NODE_NUMBERS}; do \
	  echo "Starting ${PREFIX}-etcd-$$ii"; \
	  gcloud compute instances create \
        ${PREFIX}-etcd-$$ii \
        --zone ${GCE_REGION} \
        --image-project coreos-cloud \
        --image coreos-alpha-1010-1-0-v20160407 \
        --machine-type ${ETCD_INSTANCE_TYPE} \
        --local-ssd interface=scsi \
        --no-address \
        --metadata-from-file user-data=build/etcd-$$ii & \
	done; \
	echo "Waiting for creation of etcd nodes to finish..."; \
	wait; \
	echo "etcd nodes started."

gce-cleanup:
	gcloud compute instances list --zones ${GCE_REGION} -r '${PREFIX}.*' |tail -n +2 |cut -f1 -d' ' |xargs gcloud compute instances delete --zone ${GCE_REGION}

gce-forward-ports:
	@-pkill -f '8080:localhost:8080'
	bash -c 'until ssh -o LogLevel=quiet -o PasswordAuthentication=no core@${PREFIX}-master.${GCE_REGION}.unique-caldron-775 date; do echo "Trying to forward ports"; sleep 1; done'
	ssh -o PasswordAuthentication=no -L 8080:localhost:8080 -L 2379:localhost:2379 -L 4194:localhost:4194 -L 9090:${PREFIX}-prom:9090 -o LogLevel=quiet -nNT core@${PREFIX}-master.${GCE_REGION}.unique-caldron-775 &

gce-redeploy:
	gcloud compute instances add-metadata ${PREFIX}-master --metadata-from-file=user-data=master-config-template.yaml
	gcloud compute instances add-metadata ${NODE_NAMES} --metadata-from-file=user-data=node-config-template.yaml
#	gcloud compute ssh ${PREFIX}-master sudo reboot

gce-config-ssh:
	gcloud compute config-ssh

gce-ssh-master:
	ssh core@${PREFIX}-master.${GCE_REGION}.unique-caldron-775

gce-bgp-status:
	ssh core@${PREFIX}-master.${GCE_REGION}.unique-caldron-775 /opt/bin/calicoctl status

gce-bgp-status-count:
	ssh core@${PREFIX}-master.${GCE_REGION}.unique-caldron-775 /opt/bin/calicoctl status |grep -c Established

gce-list-nodes:
	kubectl get no --no-headers -l 'kubernetes.io/hostname!=127.0.0.1'

gce-list-nodes-count:
	@kubectl get no --no-headers -l 'kubernetes.io/hostname!=127.0.0.1' | wc -l

gce-successful-pods:
	kubectl get po | grep -P -c '1/1\s+Running\s+0'

gce-failed-pods:
	kubectl get po |grep -v Pending |grep -v Running

gce-wait-for-pod-creation:
	bash -c 'while [ $$(kubectl get po | grep -P -c "1/1\s+Running\s+0") -ne ${PODS} ] ;  do date; echo "Not enough nodes created - waiting"; kubectl describe rc |grep "Pods Status"; sleep 1;done'


