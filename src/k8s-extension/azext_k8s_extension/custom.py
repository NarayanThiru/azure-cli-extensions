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
from .partner_customization import *
from .containerinsights import _get_container_insights_settings
from azure.cli.core.commands.client_factory import get_subscription_id
from msrestazure.azure_exceptions import CloudError
from ._client_factory import cf_resources

logger = get_logger(__name__)


def show_k8s_extension(client, resource_group_name, cluster_name, name, cluster_type):
    """Get an existing K8s Extension.

    """
    # Determine ClusterRP
    cluster_rp = __get_cluster_rp(cluster_type)

    try:
        extension = client.get(resource_group_name,
                               cluster_rp, cluster_type, cluster_name, name)
        return extension
    except ErrorResponseException as ex:
        # Customize the error message for resources not found
        if ex.response.status_code == 404:
            # If Cluster not found
            if ex.message.__contains__("(ResourceNotFound)"):
                message = "{0} Verify that the cluster-type is correct and the resource exists.".format(
                    ex.message)
            # If Configuration not found
            elif ex.message.__contains__("Operation returned an invalid status code 'Not Found'"):
                message = "(ExtensionNotFound) The Resource {0}/{1}/{2}/Microsoft.KubernetesConfiguration/" \
                          "extensions/{3} could not be found!".format(
                              cluster_rp, cluster_type, cluster_name, name)
            else:
                message = ex.message
            raise CLIError(message)


def create_k8s_extension(cmd, client, resource_group_name, cluster_name, name, cluster_type,
                         extension_type, scope='cluster', auto_upgrade_minor_version=None, release_train=None,
                         version=None, target_namespace=None, release_namespace=None, configuration_settings=None,
                         configuration_protected_settings=None, configuration_settings_file=None,
                         configuration_protected_settings_file=None, tags=None):
    """Create a new Extension Instance.

    """
    extension_type_lower = extension_type.lower()

    # Determine ClusterRP
    cluster_rp = __get_cluster_rp(cluster_type)

    # Configuration Settings & Configuration Protected Settings
    if configuration_settings is not None and configuration_settings_file is not None:
        raise CLIError('Error! Both configuration-settings and configuration-settings-file cannot be provided.')

    if configuration_protected_settings is not None and configuration_protected_settings_file is not None:
        raise CLIError('Error! Both configuration-protected-settings and configuration-protected-settings-file '
                       'cannot be provided.')

    config_settings = {}
    config_protected_settings = {}
    create_identity = False
    # Get Configuration Settings from file
    if configuration_settings_file is not None:
        config_settings = __get_config_settings_from_file(configuration_settings_file)

    if configuration_settings is not None:
        for dicts in configuration_settings:
            for key, value in dicts.items():
                config_settings[key] = value

    # Get Configuration Protected Settings from file
    if configuration_protected_settings_file is not None:
        config_protected_settings = __get_config_settings_from_file(configuration_protected_settings_file)

    if configuration_protected_settings is not None:
        for dicts in configuration_protected_settings:
            for key, value in dicts.items():
                config_protected_settings[key] = value

    # Identity is not created by default.  Extension type must specify if identity is required.
    create_identity = False

    extension_instance = None

    # Give Partners a chance to their extensionType specific validations and to set value over-rides.
    if extension_type_lower == 'microsoft.openservicemesh':
        extension_instance, create_identity = \
            microsoft_openservicemesh_create(cmd, client, resource_group_name,
                                             cluster_name, name, cluster_type,
                                             extension_type_lower, scope,
                                             auto_upgrade_minor_version,
                                             release_train, version, target_namespace,
                                             release_namespace, config_settings,
                                             config_protected_settings,
                                             configuration_settings_file,
                                             configuration_protected_settings_file)
    elif extension_type_lower == 'azuremonitor-containers':
        extension_instance, create_identity = \
            azuremonitor_containers_create(cmd, client, resource_group_name,
                                           cluster_name, name, cluster_type,
                                           extension_type_lower, scope,
                                           auto_upgrade_minor_version,
                                           release_train, version, target_namespace,
                                           release_namespace, config_settings,
                                           config_protected_settings,
                                           configuration_settings_file,
                                           configuration_protected_settings_file)
    elif extension_type_lower == 'microsoft.azuredefender.kubernetes':
        extension_instance, create_identity = \
            microsoft_azuredefender_kubernetes_create(cmd, client, resource_group_name,
                                                      cluster_name, name, cluster_type,
                                                      extension_type_lower, scope,
                                                      auto_upgrade_minor_version,
                                                      release_train, version, target_namespace,
                                                      release_namespace, config_settings,
                                                      config_protected_settings,
                                                      configuration_settings_file,
                                                      configuration_protected_settings_file)
    else:
        # Error - unknown extensionType
        CLIError('The extension-type {} is not supported!'.format(extension_type))

    # Now that the values are set by Partners, let us do common validations
    __validate_scope_and_namespace(scope, release_namespace, target_namespace)
    __validate_version_and_auto_upgrade(version, auto_upgrade_minor_version)

    # Create identity, if required
    if create_identity:
        extension_instance.identity, extension_instance.location = \
            __create_identity(cmd, resource_group_name, cluster_name)

    # Try to create the resource
    return client.create(resource_group_name, cluster_rp, cluster_type, cluster_name, name, extension_instance)


def list_k8s_extension(client, resource_group_name, cluster_name, cluster_type):
    cluster_rp = __get_cluster_rp(cluster_type)
    return client.list(resource_group_name, cluster_rp, cluster_type, cluster_name)


def update_k8s_extension(client, resource_group_name, cluster_type, cluster_name, name,
                         auto_upgrade_minor_version='', release_train='', version='', tags=None):

    """Patch an existing Extension Instance.

    """
    # Ensure some values are provided for update
    if auto_upgrade_minor_version is None and release_train is None and version is None:
        message = "No values provided for update. Provide new value(s) for one or more of these properties:" \
                  " auto-upgrade-minor-version, release-train or version."
        CLIError(message)

    # Determine ClusterRP
    cluster_rp = __get_cluster_rp(cluster_type)

    # Get the existing extensionInstance
    extension = client.get(resource_group_name, cluster_rp, cluster_type, cluster_name, name)

    extension_type_lower = extension.extension_type.lower()

    # Give Partners a chance to their extensionType specific validations and to set value over-rides.
    if extension_type_lower == 'microsoft.openservicemesh':
        upd_extension = microsoft_openservicemesh_update(extension, auto_upgrade_minor_version, release_train, version)
    elif extension_type_lower == 'azuremonitor-containers':
        upd_extension = azuremonitor_containers_update(extension, auto_upgrade_minor_version, release_train, version)
    elif extension_type_lower == 'microsoft.azuredefender.kubernetes':
        upd_extension = microsoft_azuredefender_kubernetes_update(extension, auto_upgrade_minor_version, release_train,
                                                                  version)
    else:
        # Error - unknown extensionType
        CLIError('The extension-type {} is not supported!'.format(extension.extension_type))

    __validate_version_and_auto_upgrade(version, auto_upgrade_minor_version)

    upd_extension = ExtensionInstanceUpdate(auto_upgrade_minor_version=auto_upgrade_minor_version,
                                            release_train=release_train, version=version)

    return client.update(resource_group_name, cluster_rp, cluster_type, cluster_name, name, upd_extension)


def delete_k8s_extension(client, resource_group_name, cluster_name, name, cluster_type):
    """Delete an existing Kubernetes Extension.

    """
    # Determine ClusterRP
    cluster_rp = __get_cluster_rp(cluster_type)

    k8s_extension_instance_name = name

    return client.delete(resource_group_name, cluster_rp, cluster_type, cluster_name, k8s_extension_instance_name)


def __create_identity(cmd, resource_group_name, cluster_name):
    subscription_id = get_subscription_id(cmd.cli_ctx)
    resources = cf_resources(cmd.cli_ctx, subscription_id)
    cluster_resource_id = '/subscriptions/{0}/resourceGroups/{1}/providers/Microsoft.Kubernetes/' \
                            'connectedClusters/{2}'.format(subscription_id, resource_group_name, cluster_name)
    try:
        resource = resources.get_by_id(cluster_resource_id, '2020-01-01-preview')
        location = str(resource.location.lower())
    except CloudError as ex:
        raise ex
    identity_type = "SystemAssigned"

    return ConfigurationIdentity(type=identity_type), location


def __get_cluster_rp(cluster_type):
    rp = ""
    if cluster_type.lower() == 'connectedclusters':
        rp = 'Microsoft.Kubernetes'
    elif cluster_type.lower() == 'arcappliances':
        rp = 'Microsoft.ResourceConnector'
    else:
        rp = 'Microsoft.ContainerService'
    return rp


def __validate_scope_and_namespace(scope, release_namespace, target_namespace):
    if scope == 'cluster':
        if target_namespace is not None:
            message = "When Scope is 'cluster', target-namespace must not be given."
            raise CLIError(message)
    else:
        if release_namespace is not None:
            message = "When Scope is 'namespace', release-namespace must not be given."
            raise CLIError(message)


def __validate_version_and_auto_upgrade(version, auto_upgrade_minor_version):
    if version is not None:
        if auto_upgrade_minor_version is not False:
            message = "To pin to specific version, auto-upgrade-minor-version must be set to 'false'."
            raise CLIError(message)


def __get_config_settings_from_file(file_path):
    try:
        config_file = open(file_path,)
        settings = json.load(config_file)
    except ValueError:
        raise Exception("File {} is not a valid JSON file".format(file_path))

    files = len(settings)
    if files == 0:
        raise Exception("File {} is empty".format(file_path))

    return settings
