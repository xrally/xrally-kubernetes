# xrally-kubernetes

xRally plugins for [Kubernetes](https://kubernetes.io/) platform.

## Status ot this package

Work in progress. The active phase of development.

## Getting started

First of all, you need to create rally env for Kubernetes. There are two main
ways to communicate to Kubernetes cluster - specifying auth-token or
certifications. Choose what is suitable for your case and use one of the
following samples.

To create env using certifications, use spec `samples/platforms/cert-spec.yaml`:

```console
rally env create --name kubernetes --spec samples/platforms/cert-spec.yaml
```

For using Kubernetes token authentication, you need to get API key and use
`samples/platforms/apikey-spec.yaml` spec to create env:

```console
rally env create --name kubernetes --spec samples/platforms/apikey-spec.yaml
``` 


Check env availbility by the following command:

```console
rally env check
```
 
## Where the tasks and bugs are tracked ?!

The primary tracking system is
[Issues at GitHub](https://github.com/xrally/xrally-kubernetes/issues).

For Rally framework related issues look at
[Launchpad](https://bugs.launchpad.net/rally).
