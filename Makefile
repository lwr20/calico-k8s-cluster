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
	-kubectl delete service monitoring-grafana --grace-period=1
	-kubectl delete service monitoring-influxdb --grace-period=1
	-kubectl delete service heapster --grace-period=1
	-kubectl delete rc heapster --grace-period=1
	-kubectl delete rc influxdb-grafana --grace-period=1

vagrant-ssh:
	vagrant ssh-config > vagrant-ssh

heapster-images: vagrant-ssh
	docker pull kubernetes/heapster_grafana:v2.5.0
	docker pull kubernetes/heapster_influxdb:v0.6
	docker pull kubernetes/heapster:v0.19.0
	docker save kubernetes/heapster_grafana:v2.5.0 | ssh -F vagrant-ssh calico-01 docker load
	docker save kubernetes/heapster_influxdb:v0.6 | ssh -F vagrant-ssh calico-01 docker load
	docker save kubernetes/heapster:canary | ssh -F vagrant-ssh calico-01 docker load
	
launch-firefox:
	firefox 'http://172.18.18.101:8080/api/v1/proxy/namespaces/default/services/monitoring-grafana/'
