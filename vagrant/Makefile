K8S_VERSION=1.2.0

# Which OS version to use for kubectl
# `darwin` or `linux`
OS=darwin

ssl-keys: ssl/admin.pem ssl/apiserver.pem 

# Creates a Kubernetes cluster which passes the k8s conformance tests.
cluster:
	make clean-webserver        # Stop any existing webserver.
	make clean-keys             # Remove any SSL keys.
	make clean-kubectl	    # Remove old kubectl.
	make clean-binaries         # Clean CNI binaries.
	make kubectl                # Get kubectl
	make binaries               # Build the CNI binaries.
	make create-cluster-vagrant # Start the cluster.
	make wait-for-cluster
	make install-addons

# Waits for 3 nodes to have started.
wait-for-cluster:
	python scripts/wait_for_cluster.py

# Installs Kubernetes addons
install-addons:
	./kubectl create -f manifests/namespaces/
	./kubectl create -f manifests/addons/

# Builds calico-cni binaries from submodule.
binaries: 
	make -C calico-cni binary

# Cleans the calico-cni submodule.
clean-binaries:
	make -C calico-cni clean

destroy-cluster-vagrant: 
	-vagrant destroy -f

create-cluster-vagrant: destroy-cluster-vagrant webserver
	vagrant up

webserver: ssl-keys
	python -m SimpleHTTPServer &

clean-webserver: clean-keys
	(sudo killall python) || echo "Server not running"

generate-certs:
	sudo openssl/create_keys.sh

clean-kubectl:
	rm -f kubectl

kubectl: ssl/admin.pem
	wget http://storage.googleapis.com/kubernetes-release/release/v$(K8S_VERSION)/bin/$(OS)/amd64/kubectl
	chmod +x kubectl
	./kubectl config set-cluster default-cluster --server=https://172.18.18.101 --certificate-authority=ssl/ca.pem
	./kubectl config set-credentials default-admin --certificate-authority=ssl/ca.pem --client-key=ssl/admin-key.pem --client-certificate=ssl/admin.pem
	./kubectl config set-context default-system --cluster=default-cluster --user=default-admin
	./kubectl config use-context default-system

calicoctl:
	wget http://www.projectcalico.org/builds/calicoctl
	chmod +x calicoctl

ssl/ca-key.pem:
	openssl genrsa -out ssl/ca-key.pem 2048
	openssl req -x509 -new -nodes -key ssl/ca-key.pem -days 10000 -out ssl/ca.pem -subj "/CN=kube-ca"

ssl/admin.pem: ssl/ca-key.pem 
	openssl genrsa -out ssl/admin-key.pem 2048
	openssl req -new -key ssl/admin-key.pem -out ssl/admin.csr -subj "/CN=kube-admin"
	openssl x509 -req -in ssl/admin.csr -CA ssl/ca.pem -CAkey ssl/ca-key.pem -CAcreateserial -out ssl/admin.pem -days 365

ssl/apiserver.pem: ssl/ca-key.pem 
	openssl genrsa -out ssl/apiserver-key.pem 2048
	openssl req -new -key ssl/apiserver-key.pem -out ssl/apiserver.csr -subj "/CN=kube-apiserver" -config ssl/openssl.cnf
	openssl x509 -req -in ssl/apiserver.csr -CA ssl/ca.pem -CAkey ssl/ca-key.pem -CAcreateserial -out ssl/apiserver.pem -days 365 -extensions v3_req -extfile ssl/openssl.cnf

clean-keys:
	rm -f ssl/*.pem
	rm -f ssl/*.srl
	rm -f ssl/*.csr
