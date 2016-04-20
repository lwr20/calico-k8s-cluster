#!/bin/sh

for i in `seq 1 5`;
do
	fmt_no=$(seq -f '%02.0f' $i $i)
	name="scale-route-${fmt_no}"
	cidr="192.168.$i.0/24"
	nh="kube-scale-${fmt_no}"
	gcloud compute routes create ${name} --destination-rage ${cidr} --next-hop=${nh}
	echo ${nh} ${cidr} ${name}
done
