# Changelog

<!-- 
  Changelogs are for humans, not machines. The end users of Rally project are
  human beings who care about what's is changing, why and how it affects them.
  Please leave these notes as much as possible human oriented.

  Each release can use the next sections:
   - **Added** for new features.
   - **Changed** for changes in existing functionality.
   - **Deprecated** for soon-to-be removed features/plugins.
   - **Removed** for now removed features/plugins.
   - **Fixed** for any bug fixes.

  Release notes for existing releases are MUTABLE! If there is something that
  was missed or can be improved, feel free to change it!
 
-->

## [Unreleased] - n/a

**Added**

* [scenario plugin] Kubernetes.create_and_delete_emptydir_volume
* [scenario plugin] Kubernetes.create_check_and_delete_emptydir_volume
* [context plugin] namespaces - create number of namespaces (with
  non-default serviceAccounts optionally)
* [scenario plugin] Kubernetes.create_and_delete_pod
* [scenario plugin] Kubernetes.create_and_delete_replication_controller
* [scenario plugin] Kubernetes.create_scale_and_delete_replication_controller

## [1.0.0] - 2018-06-26

The start. Initial release. Have fun! ;)
