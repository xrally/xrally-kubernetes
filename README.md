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

For initialization `Rally environment` to communicate to existing Kubernetes
cluster you can also use system environment variables instead of making
specification json/yaml file. See the list of available options:

* As like regular kubernetes client (kubectl) Rally can read kubeconfig file.
  Call `rally env create --name kubernetes-created --from-sys-env` and Rally
  with check `$HOME/.kube/config` file to the available configuration. Also,
  you can specify `KUBECONFIG` variable with a path different to the default
  `$HOME/.kube/config`.

* Despite the fact that `kubectl` doesn't support specifying Kubernetes
  credentials via separated system environment variables per separate option
  (auth_url, api_key, etc) like other platforms support (OpenStack, Docker,
  etc), Rally team provides this way. Check [existing@kubernetes plugin documentation](https://xrally.org/plugins/kubernetes/plugins/#existing-platform)
  for the list of all available variables. Here is a simple example of this feature:

  ```console
  # the URL to the Kubernetes host.
  export KUBERNETES_HOST="https://example.com:3030" 
  #  a path to a file containing TLS certificate to use when connecting to the Kubernetes host.
  export KUBERNETES_CERT_AUTH="~/.kube/cert_auth_file"
  # client API key to use as token when connecting to the Kubernetes host.
  export KUBERNETES_API_KEY="foo"
  # client API key prefix to use in token when connecting to the Kubernetes host.
  export KUBERNETES_API_KEY_PREFIX="bar"
  
  # finally create a Rally environment
  rally env create --name my-kubernetes --from-sysenv
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
