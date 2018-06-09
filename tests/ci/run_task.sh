#!/usr/bin/env bash

# stop on any failure
set -e
# print commands
set -o xtrace

SPEC_FILE=$(mktemp)
CA=${CA:-"~/.minikube/ca.crt"}
CERT=${CERT:-"~/.minikube/client.crt"}
KEY=${KEY:-"~/.minikube/client.key"}

# ensure that Kubernetes is Up and we can reach it
kubectl config view
kubectl cluster-info

# create a Rally database and setup spec for the K8s platform
rally db ensure

# create a spec

cat >$SPEC_FILE <<EOF
{
    "existing@kubernetes": {
        "server": "https://localhost:8443",
        "certificate-authority": "$CA",
        "client-certificate": "$CERT",
        "client-key": "$KEY"
    }
}
EOF

# create a database entry
rally env create --name test_env --spec $SPEC_FILE

# check that Rally is able to reach K8s cluster
rally env info

# Run actual task
rally task start "$XRALLY_TASK"
