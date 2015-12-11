<!-- BEGIN MUNGE: UNVERSIONED_WARNING -->

<!-- BEGIN STRIP_FOR_RELEASE -->

<img src="http://kubernetes.io/img/warning.png" alt="WARNING"
     width="25" height="25">
<img src="http://kubernetes.io/img/warning.png" alt="WARNING"
     width="25" height="25">
<img src="http://kubernetes.io/img/warning.png" alt="WARNING"
     width="25" height="25">
<img src="http://kubernetes.io/img/warning.png" alt="WARNING"
     width="25" height="25">
<img src="http://kubernetes.io/img/warning.png" alt="WARNING"
     width="25" height="25">

<h2>PLEASE NOTE: This document applies to the HEAD of the source tree</h2>

If you are using a released version of Kubernetes, you should
refer to the docs that go with that version.

<strong>
The latest release of this document can be found
[here](http://releases.k8s.io/release-1.1/docs/getting-started-guides/coreos/bare_metal_calico.md).

Documentation for other releases can be found at
[releases.k8s.io](http://releases.k8s.io).
</strong>
--

<!-- END STRIP_FOR_RELEASE -->

<!-- END MUNGE: UNVERSIONED_WARNING -->

Bare Metal Kubernetes on CoreOS with Calico Networking
------------------------------------------
This document describes how to deploy Kubernetes with Calico networking on _bare metal_ CoreOS. For more information on Project Calico, visit [projectcalico.org](http://projectcalico.org) and the [calico-docker repository](https://github.com/projectcalico/calico-docker).

To install Calico on an existing Kubernetes cluster, or for more information on deploying Calico with Kubernetes in a number of other environments take a look at our supported [deployment guides](https://github.com/projectcalico/calico-docker/tree/master/docs/kubernetes).

Specifically, this guide will have you do the following:
- Deploy a Kubernetes master node on CoreOS using cloud-config
- Deploy two Kubernetes compute nodes with Calico Networking using cloud-config

## Prerequisites

1. At least three bare-metal machines (or VMs) to work with. This guide will configure them as follows:
  - 1 Kubernetes Master
  - 2 Kubernetes Nodes
2. Your nodes should have IP connectivity.

## Cloud-config

This guide will use [cloud-config](https://coreos.com/docs/cluster-management/setup/cloudinit-cloud-config/) to configure each of the nodes in our Kubernetes cluster.

We'll use two cloud-config files:
- `master-config.yaml`: Cloud-config for the Kubernetes master
- `node-config.yaml`: Cloud-config for each Kubernetes node

## Download CoreOS

Let's download the CoreOS bootable ISO.  We'll use this image to boot and install CoreOS on each server.

```
wget http://stable.release.core-os.net/amd64-usr/current/coreos_production_iso_image.iso
```

> You can also download the ISO from the [CoreOS website](https://coreos.com/docs/running-coreos/platforms/iso/).

## Configure the Kubernetes Master

Once you've downloaded the image, use it to boot your Kubernetes master.  Once booted, you should be automatically logged in as the `core` user.

*On another machine*, download the `calico-kubernetes` repository, which contains the necessary cloud-config files for this guide, and make a copy of the file `master-config-template.yaml`.

```
wget -O master-config.yaml https://raw.githubusercontent.com/projectcalico/calico-kubernetes/master/config/cloud-config/master-config-template.yaml
```

You'll need to replace the following variables in the `master-config.yaml` file.
- `<SSH_PUBLIC_KEY>`: The public key you will use for SSH access to this server.

Move the edited `master-config.yaml` to your Kubernetes master machine.  The CoreOS bootable ISO comes with a tool called `coreos-install` which will allow us to install CoreOS and configure the machine using a cloud-config file.  The following command will download and install stable CoreOS using the `master-config.yaml` file we just created for configuration.  Run this on the Kubernetes master.

```
sudo coreos-install -d /dev/sda -C stable -c master-config.yaml
```

Once complete, restart the server and boot into `/dev/sda`. When it comes back up, you should have SSH access as the `core` user using the public key provided in the `master-config.yaml` file.

Next, you will need to configure your cluster's TLS assets. To get started with Kubernetes client certificate authentication, follow the [CoreOS guide to generating Kubernetes TLS assets using OpenSSL](https://coreos.com/kubernetes/docs/latest/openssl.html).

On your master, you will need to move your client and apiserver certificates to the `/etc/kubernetes/ssl/` folder with the appropriate permissions.
```
sudo mv -t /etc/kubernetes/ssl/ ca.pem apiserver.pem apiserver-key.pem

# Set Permissions
sudo chmod 600 /etc/kubernetes/ssl/apiserver-key.pem
sudo chown root:root /etc/kubernetes/ssl/apiserver-key.pem
```

If your apiserver did not restart to pick up these certificates, you can restart your kubelet to trigger a container refresh.
```
sudo systemctl restart kubelet
```

Before you configure the rest of your nodes, you will need to create an authentication token for Calico to access the API. Run the following command on your master or workstation and save the result.
```
kubectl create -f - <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: calico
EOF
export AUTH_TOKEN=$(kubectl describe secret calico-token | grep token: | cut -f 2)
```


## Configure the compute hosts

>The following steps will set up a single Kubernetes node for use as a compute host.  Run these steps to deploy each Kubernetes node in your cluster.

First, boot up the node machine using the bootable ISO we downloaded earlier.  You should be automatically logged in as the `core` user.

Make a copy of the `node-config-template.yaml` for this machine.

```
wget -O node-config.yaml https://raw.githubusercontent.com/projectcalico/calico-kubernetes/master/config/cloud-config/node-config-template.yaml
```

You'll need to replace the following variables in the `node-config.yaml` file to match your deployment.
- `<HOSTNAME>`: Hostname for this node (e.g. kube-node1, kube-node2)
- `<SSH_PUBLIC_KEY>`: The public key you will use for SSH access to this server.
- `<KUBERNETES_MASTER>`: The IPv4 address of the Kubernetes master.
- `<AUTH_TOKEN>`: The API authentication token generated in the previous step.

Next, you will need to add the certificates generated in the previous step to the cloud-config. Replace the following placeholders with your TLS assests.
- `<CA_CERT>`: Complete contents of `ca.pem`
- `<WORKER_CERT>`: Complete contents of `worker.pem`
- `<WORKER_KEY>`: Complete contents of `worker-key.pem`

Move the modified `node-config.yaml` to your Kubernetes node machine and install and configure CoreOS on the node using the following command.

```
sudo coreos-install -d /dev/sda -C stable -c node-config.yaml
```

Once complete, restart the server and boot into `/dev/sda`. When it comes back up, you should have SSH access as the `core` user using the public key provided in the `node-config.yaml` file.  It will take some time for the node to be fully configured.

## Configure Kubeconfig
To administrate your cluster from a separate host, you will need the client and admin certificates generated earlier (`ca.pem`, `admin.pem`, `admin-key.pem`). With certificates in place, run the following commands with the appropriate filepaths.
```
kubectl config set-cluster calico-cluster --server=https://<KUBERNETES_MASTER> --certificate-authority=<CA_CERT_PATH>
kubectl config set-credentials calico-admin --certificate-authority=<CA_CERT_PATH> --client-key=<ADMIN_KEY_PATH> --client-certificate=<ADMIN_CERT_PATH>
kubectl config set-context calico --cluster=calico-cluster --user=calico-admin
kubectl config use-context calico
```

Check your work with `kubectl get nodes`.

## Install the DNS Addon

Most Kubernetes deployments will require the DNS addon for service discovery. To install DNS, create the skydns service and replication controller provided.

```
wget https://raw.githubusercontent.com/projectcalico/calico-kubernetes/master/config/master/dns/skydns.yaml
kubectl create -f skydns.yaml
```

## Launch other Services With Calico-Kubernetes

At this point, you have a fully functioning cluster running on Kubernetes with a master and two nodes networked with Calico. You can now follow any of the [standard documentation](../../examples/) to set up other services on your cluster.

## Connectivity to outside the cluster

Because containers in this guide have private `192.168.0.0/16` IPs, you will need NAT to allow connectivity between containers and the internet. However, in a production data center deployment, NAT is not always necessary, since Calico can peer with the data center's border routers over BGP.

### NAT on the nodes

The simplest method for enabling connectivity from containers to the internet is to use an `iptables` masquerade rule. This is the standard mechanism recommended in the [Kubernetes GCE environment](../../docs/admin/networking.md#google-compute-engine-gce).

We need to NAT traffic that has a destination outside of the cluster. Cluster-internal traffic includes the Kubernetes master/nodes, and the traffic within the container IP subnet. A suitable masquerade chain would follow this pattern below, replacing the following variables:
- `CONTAINER_SUBNET`: The cluster-wide subnet from which container IPs are chosen. Run `ETCD_AUTHORITY=127.0.0.1:6666 calicoctl pool show` on the Kubernetes master to find your configured container subnet.
- `KUBERNETES_HOST_SUBNET`: The subnet from which Kubernetes node / master IP addresses have been chosen.
- `HOST_INTERFACE`: The interface on the Kubernetes node which is used for external connectivity.

```
sudo iptables -t nat -N KUBE-OUTBOUND-NAT
sudo iptables -t nat -A KUBE-OUTBOUND-NAT -d <CONTAINER_SUBNET> -o <HOST_INTERFACE> -j RETURN
sudo iptables -t nat -A KUBE-OUTBOUND-NAT -d <KUBERNETES_HOST_SUBNET> -o <HOST_INTERFACE> -j RETURN
sudo iptables -t nat -A KUBE-OUTBOUND-NAT -j MASQUERADE
sudo iptables -t nat -A POSTROUTING -j KUBE-OUTBOUND-NAT
```

This chain should be applied on the master and all nodes. In production, these rules should be persisted, e.g. with `iptables-persistent`.

### NAT at the border router

In a data center environment, it is recommended to configure Calico to peer with the border routers over BGP. This means that the container IPs will be routable anywhere in the data center, and so NAT is not needed on the nodes (though it may be enabled at the data center edge to allow outbound-only internet connectivity).

<!-- BEGIN MUNGE: GENERATED_ANALYTICS -->
[![Analytics](https://kubernetes-site.appspot.com/UA-36037335-10/GitHub/docs/getting-started-guides/coreos/bare_metal_calico.md?pixel)]()
<!-- END MUNGE: GENERATED_ANALYTICS -->
