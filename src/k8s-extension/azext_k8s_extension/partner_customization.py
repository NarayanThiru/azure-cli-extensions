# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import json
from knack.util import CLIError
from knack.log import get_logger

from azext_k8s_extension.vendored_sdks.models import ExtensionInstanceForCreate
from azext_k8s_extension.vendored_sdks.models import ConfigurationIdentity
from azext_k8s_extension.vendored_sdks.models import ExtensionInstanceUpdate
from azext_k8s_extension.vendored_sdks.models import ErrorResponseException
from azext_k8s_extension.vendored_sdks.models import ScopeCluster
from azext_k8s_extension.vendored_sdks.models import ScopeNamespace
from azext_k8s_extension.vendored_sdks.models import Scope
from .containerinsights import _get_container_insights_settings
from azure.cli.core.commands.client_factory import get_subscription_id
from msrestazure.azure_exceptions import CloudError
from ._client_factory import cf_resources

logger = get_logger(__name__)

def azuremonitor_containers_create(cmd, client, resource_group_name, cluster_name, name, cluster_type, extension_type,
                                   scope, auto_upgrade_minor_version, release_train, version, target_namespace,
                                   release_namespace, configuration_settings, configuration_protected_settings,
                                   configuration_settings_file, configuration_protected_settings_file):
    """ExtensionType 'microsoft.azuredefender.kubernetes' specific validations & defaults for Create
       Must create and return a valid 'ExtensionInstanceForCreate' object.

    """
    # NOTE-1: Replace default scope creation with your customization!
    scope = None
    # Scope is always cluster
    scope_cluster = ScopeCluster(release_namespace=release_namespace)
    scope = Scope(cluster=scope_cluster, namespace=None)

    # Hardcoding name, release_namespace and scope since container-insights only supports one instance and cluster scope
    # and platform doesnt have support yet extension specific constraints like this
    name = 'azuremonitor-containers'
    release_namespace = 'azuremonitor-containers'
    is_ci_extension_type = True

    logger.warning('Ignoring name, release-namespace and scope parameters since %s '
                   'only supports cluster scope and single instance of this extension', extension_type)

    _get_container_insights_settings(cmd, resource_group_name, cluster_name, configuration_settings,
                                     configuration_protected_settings, is_ci_extension_type)

    # NOTE-2: Return a valid ExtensionInstanceForCreate object and flag for Identity
    create_identity = True
    extension_instance = ExtensionInstanceForCreate(extension_type=extension_type,
                                                    auto_upgrade_minor_version=auto_upgrade_minor_version,
                                                    release_train=release_train,
                                                    version=version,
                                                    scope=scope,
                                                    configuration_settings=configuration_settings,
                                                    configuration_protected_settings=configuration_protected_settings,
                                                    identity=None,
                                                    location="")
    return extension_instance, create_identity


def azuremonitor_containers_update(extension, auto_upgrade_minor_version, release_train, version):
    """ExtensionType 'azuremonitor-containers' specific validations & defaults for Update
       Must create and return a valid 'ExtensionInstanceUpdate' object.

    """
    return ExtensionInstanceUpdate(auto_upgrade_minor_version=auto_upgrade_minor_version,
                                   release_train=release_train,
                                   version=version)


def microsoft_azuredefender_kubernetes_create(cmd, client, resource_group_name, cluster_name, name, cluster_type,
                                              extension_type, scope, auto_upgrade_minor_version, release_train, 
                                              version, target_namespace, release_namespace, configuration_settings,
                                              configuration_protected_settings, configuration_settings_file,
                                              configuration_protected_settings_file):
    """ExtensionType 'microsoft.azuredefender.kubernetes' specific validations & defaults for Create
       Must create and return a valid 'ExtensionInstanceForCreate' object.

    """
    # NOTE-1: Replace default scope creation with your customization!
    scope = None
    # Scope is always cluster
    scope_cluster = ScopeCluster(release_namespace=release_namespace)
    scope = Scope(cluster=scope_cluster, namespace=None)

    # Hardcoding  name, release_namespace and scope since ci only supports one instance and cluster scope
    # and platform doesnt have support yet extension specific constraints like this
    name = extension_type.lower()
    release_namespace = "microsoft-azuredefender-kubernetes"
    is_ci_extension_type = False

    logger.warning('Ignoring name, release-namespace and scope parameters since %s '
                   'only supports cluster scope and single instance of this extension', extension_type)

    _get_container_insights_settings(cmd, resource_group_name, cluster_name, configuration_settings,
                                     configuration_protected_settings, is_ci_extension_type)

    # NOTE-2: Return a valid ExtensionInstanceForCreate object and flag for Identity
    create_identity = True
    return ExtensionInstanceForCreate(extension_type,
                                      auto_upgrade_minor_version,
                                      release_train,
                                      version,
                                      scope,
                                      configuration_settings,
                                      configuration_protected_settings,
                                      identity=None,
                                      location=""), create_identity


def microsoft_azuredefender_kubernetes_update(extension, auto_upgrade_minor_version, release_train, version):
    """ExtensionType 'microsoft.azuredefender.kubernetes' specific validations & defaults for Update
       Must create and return a valid 'ExtensionInstanceUpdate' object.

    """
    return ExtensionInstanceUpdate(auto_upgrade_minor_version=auto_upgrade_minor_version,
                                   release_train=release_train,
                                   version=version)


def microsoft_openservicemesh_create(cmd, client, resource_group_name, cluster_name, name, cluster_type,
                                     extension_type, scope, auto_upgrade_minor_version, release_train, version, 
                                     target_namespace, release_namespace, configuration_settings,
                                     configuration_protected_settings, configuration_settings_file,
                                     configuration_protected_settings_file):
    """ExtensionType 'microsoft.openservicemesh' specific validations & defaults for Create
       Must create and return a valid 'ExtensionInstanceForCreate' object.

    """
    # NOTE-1: Replace default scope creation with your customization, if required
    scope = None
    if scope == 'cluster':
        scope_cluster = ScopeCluster(release_namespace=release_namespace)
        scope = Scope(cluster=scope_cluster, namespace=None)
    else:
        scope_namespace = ScopeNamespace(target_namespace=target_namespace)
        scope = Scope(namespace=scope_namespace, cluster=None)

    # If the release-train is 'staging' or 'pilot' then auto-upgrade-minor-version MUST be set to False
    if release_train.lower() in 'staging' 'pilot':
        if auto_upgrade_minor_version or auto_upgrade_minor_version is None:
            auto_upgrade_minor_version = False
            logger.warning("Setting auto-upgrade-minor-version to False since release-train is '%s'", release_train)

    # NOTE-2: Return a valid ExtensionInstanceForCreate object and flag for Identity
    create_identity = False
    return ExtensionInstanceForCreate(extension_type,
                                      auto_upgrade_minor_version,
                                      release_train,
                                      version,
                                      scope,
                                      configuration_settings,
                                      configuration_protected_settings,
                                      identity=None,
                                      location=""), create_identity


def microsoft_openservicemesh_update(extension, auto_upgrade_minor_version, release_train, version):
    """ExtensionType 'microsoft.openservicemesh' specific validations & defaults for Update
       Must create and return a valid 'ExtensionInstanceUpdate' object.

    """
    #  auto-upgrade-minor-version MUST be set to False if release_train is staging or pilot
    if release_train.lower() in 'staging' 'pilot':
        if auto_upgrade_minor_version or auto_upgrade_minor_version is None:
            auto_upgrade_minor_version = False
            # Set version to None to always get the latest version - user cannot override
            version = None
            logger.warning("Setting auto-upgrade-minor-version to False since release-train is '%s'",
                           release_train)

    return ExtensionInstanceUpdate(auto_upgrade_minor_version=auto_upgrade_minor_version,
                                   release_train=release_train,
                                   version=version)
