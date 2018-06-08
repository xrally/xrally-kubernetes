# The code base of xRally plugins for Kubernetes platform

## Project structure

The root module of __xrally_kubernetes__ project should not be overloaded, so let's 
keep it as simple as possible.
 
* __env__ module  
  a location of plugins for Environment xRally component 
  (ex Deployment component).
 
* __task__ module
  a location of plugins for Task xRally component (i.e scenario, context, sla, 
  etc, plugins).
 
* __verify__ module
  a location of plugins for Verification xRally component.

* __service.py__ module
  a python module with a helper class which simplify usage of kubernetes client.

* __common__ module
  a set of different helpers for inner use which does not not relate to any 
  particular component and which should not be exposed to the end user