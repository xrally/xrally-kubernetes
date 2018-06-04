# xrally-kubernetes

xRally plugins for `Kubernetes <https://kubernetes.io/>`_ platform.

## Status ot this package

Work in progress. The active phase of development.

## Getting started

First of all, you need to create rally env for kubernetes. Use spec from
`samples/platforms/cert-spec.yaml` to create env:

```console
rally env create --name kubernetes --spec samples/platforms/cert-spec.yaml
```

and check it after that:

```console
rally env check
```

Also you could use kubernetes token auth. You need to get API key and use
api-key spec to create env:

```console
rally env create --name kubernetes --spec samples/platforms/apikey-spec.yaml
``` 

## Where the tasks and bugs are tracked ?!

The primary tracking system is `Issues at GitHub
<https://github.com/xrally/xrally-kubernetes/issues>`_

For Rally framework related issues look at `Launchpad
<https://bugs.launchpad.net/rally>`_
