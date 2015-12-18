all: apply-node-labels deploy-pinger
	

destroy-cluster-vagrant:
	-vagrant destroy -f

create-cluster-vagrant: destroy-cluster-vagrant
	vagrant up

generate-certs:
	sudo openssl/create_keys.sh

kubectl:
	wget http://storage.googleapis.com/kubernetes-release/release/v$(K8S_VERSION)/bin/linux/amd64/kubectl
	chmod +x kubectl

calicoctl:
	wget http://www.projectcalico.org/builds/calicoctl
	chmod +x calicoctl

deploy-heapster: remove-heapster
	kubectl create -f heapster

remove-heapster:
	-kubectl delete service monitoring-grafana --grace-period=1 --namespace=kube-system
	-kubectl delete service monitoring-influxdb --grace-period=1 --namespace=kube-system
	-kubectl delete service heapster --grace-period=1 --namespace=kube-system
	-kubectl delete rc heapster --grace-period=1 --namespace=kube-system
	-kubectl delete rc influxdb-grafana --grace-period=1 --namespace=kube-system

vagrant-ssh:
	vagrant ssh-config > vagrant-ssh

heapster-images: vagrant-ssh
	docker pull kubernetes/heapster_grafana:v2.5.0
	docker pull kubernetes/heapster_influxdb:v0.6
	docker pull kubernetes/heapster:v0.19.0
	docker save kubernetes/heapster_grafana:v2.5.0 | ssh -F vagrant-ssh calico-01 docker load
	docker save kubernetes/heapster_influxdb:v0.6 | ssh -F vagrant-ssh calico-01 docker load
	docker save kubernetes/heapster:canary | ssh -F vagrant-ssh calico-01 docker load

apply-node-labels:
	kubectl label nodes -l 'kubernetes.io/hostname!=172.18.18.101' role=node	

deploy-pinger: remove-pinger
	kubectl create -f pinger

remove-pinger:
	-kubectl delete rc pinger --grace-period=1

scale-pinger:
	kubectl scale --replicas=20 rc/pinger

launch-firefox:
	firefox 'http://172.18.18.101:8080/api/v1/proxy/namespaces/default/services/monitoring-grafana/'


CLUSTER_SIZE := 25
NODE_NUMBERS := $(shell seq -f '%02.0f' 2 ${CLUSTER_SIZE})
LOG_RETRIEVAL_TARGETS := $(addprefix job,${NODE_NUMBERS})

pull-plugin-timings: ${LOG_RETRIEVAL_TARGETS}
	# See http://stackoverflow.com/a/12110773/61318
	#make -j12 CLUSTER_SIZE=2 pull-plugin-timings
	echo "DONE"
	cat timings/*.log > timings/all.timings

${LOG_RETRIEVAL_TARGETS}: job%:
	mkdir -p timings
	ssh -F vagrant-ssh calico-$* grep TIMING  /var/log/calico/kubernetes/calico.log | grep -v status > timings/calico-$*.log

.PHONEY: ${LOG_RETRIEVAL_TARGETS}
