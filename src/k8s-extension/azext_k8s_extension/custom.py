# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
# from docutils.nodes import version
from knack.util import CLIError
from knack.log import get_logger

from azext_k8s_extension.vendored_sdks.models import ExtensionInstance
from azext_k8s_extension.vendored_sdks.models import ExtensionInstanceForCreate
from azext_k8s_extension.vendored_sdks.models import ExtensionInstanceUpdate
from azext_k8s_extension.vendored_sdks.models import ErrorResponseException
from azext_k8s_extension.vendored_sdks.models import ScopeCluster
from azext_k8s_extension.vendored_sdks.models import ScopeNamespace
from azext_k8s_extension.vendored_sdks.models import Scope
from azure.cli.core.commands.client_factory import get_mgmt_service_client, get_subscription_id
from msrestazure.azure_exceptions import CloudError
from azure.cli.core.commands import LongRunningOperation
from azure.cli.core.util import sdk_no_wait
import datetime

from ._client_factory import (
    cf_resources, cf_resource_groups, cf_log_analytics)

logger = get_logger(__name__)


def show_k8s_extension(client, resource_group_name, cluster_name, name, cluster_type):
    """Get an existing K8s Extension.

    """
    # Determine ClusterRP
    cluster_rp = __get_cluster_type(cluster_type)

    try:
        extension = client.get(resource_group_name,
                               cluster_rp, cluster_type, cluster_name, name)
        return extension
    except ErrorResponseException as ex:
        # Customize the error message for resources not found
        if ex.response.status_code == 404:
            # If Cluster not found
            if ex.message.__contains__("(ResourceNotFound)"):
                message = "{0} Verify that the --cluster-type is correct and the resource exists.".format(
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
                         extension_type, scope, auto_upgrade_minor_version=True, release_train='Stable',
                         version=None, target_namespace=None, release_namespace=None, configuration_settings=None,
                         configuration_protected_settings=None, location=None, tags=None):
    """Create a new Extension Instance.

    """
    # Determine ClusterRP
    cluster_rp = __get_cluster_type(cluster_type)

    # Validate scope and namespace
    __validate_scope_and_namespace(scope, release_namespace, target_namespace)

    # Validate version, release_train
    __validate_version_and_release_train(
        version, release_train, auto_upgrade_minor_version)

    # Determine namespace name
    if scope == 'cluster':
        if release_namespace is None:
            release_namespace = name
        scope_cluster = ScopeCluster(release_namespace=release_namespace)
        ext_scope = Scope(cluster=scope_cluster, namespace=None)
    else:
        if target_namespace is None:
            target_namespace = name
        scope_namespace = ScopeNamespace(target_namespace=target_namespace)
        ext_scope = Scope(namespace=scope_namespace, cluster=None)

    if extension_type == 'azuremonitor-containers':
        if not configuration_settings:
            configuration_settings = {}

        if not configuration_protected_settings:
            configuration_protected_settings = {}

        _get_container_insights_settings(cmd, resource_group_name,
                                         cluster_name, configuration_settings, configuration_protected_settings)

    # Get Configuration Settings
    # ##for config_key in configuration_settings:

    # Create Extension Instance object
    extension_instance = ExtensionInstanceForCreate(extension_type=extension_type,
                                                    auto_upgrade_minor_version=auto_upgrade_minor_version,
                                                    release_train=release_train,
                                                    version=version,
                                                    scope=ext_scope,
                                                    configuration_settings=configuration_settings,
                                                    configuration_protected_settings=configuration_protected_settings)

    # Try to create the resource
    return client.create(resource_group_name, cluster_rp, cluster_type, cluster_name, name, extension_instance)


def list_k8s_extension(cmd, client, resource_group_name, cluster_name, cluster_type):
    cluster_rp = __get_cluster_type(cluster_type)
    return client.list(resource_group_name, cluster_rp, cluster_type, cluster_name)


def update_k8s_extension(cmd, client, resource_group_name, cluster_type, cluster_name, name,
                         auto_upgrade_minor_version='', release_train='', version='', tags=None):

    print("In update!")

    # Ensure some values are provided for update
    if auto_upgrade_minor_version is None and release_train is None and version is None:
        message = "No values provided for update. Provide new value(s) for one or more of these properties:" \
                  " auto_upgrade_minor_version, release_train or version."
        CLIError(message)

    # Determine ClusterRP
    cluster_rp = __get_cluster_type(cluster_type)
    upd_extension = ExtensionInstanceUpdate(auto_upgrade_minor_version=auto_upgrade_minor_version,
                                            release_train=release_train, version=version)

    return client.update(resource_group_name, cluster_rp, cluster_type, cluster_name, name, upd_extension)


def delete_k8s_extension(cmd, client, resource_group_name, cluster_name, name, cluster_type, location=None, tags=None):
    """Delete an existing Kubernetes Extension.

    """
    # Determine ClusterRP
    cluster_rp = __get_cluster_type(cluster_type)

    k8s_extension_instance_name = name

    return client.delete(resource_group_name, cluster_rp, cluster_type, cluster_name, k8s_extension_instance_name)


def __get_cluster_type(cluster_type):
    if cluster_type.lower() == 'connectedclusters':
        return 'Microsoft.Kubernetes'
    # Since cluster_type is an enum of only two values, if not connectedClusters, it will be managedClusters.
    return 'Microsoft.ContainerService'


def __validate_scope_and_namespace(scope, release_namespace, target_namespace):
    if scope == 'cluster':
        if target_namespace is not None:
            message = "When Scope is 'cluster', target_namespace must not be given."
            raise CLIError(message)
    else:
        if release_namespace is not None:
            message = "When Scope is 'namespace', release_namespace must not be given."
            raise CLIError(message)


def __validate_version_and_release_train(version, release_train, auto_upgrade_minor_version):
    if version is not None:
        if release_train is not None:
            message = "Both release_train and version cannot be given. To pin to specific version, give only version."
            raise CLIError(message)
        if auto_upgrade_minor_version is True:
            message = "To pin to specific version, auto_upgrade_minor_version must be set to 'false'."
            raise CLIError(message)


def _get_rg_location(ctx, resource_group_name, subscription_id=None):
    groups = cf_resource_groups(ctx, subscription_id=subscription_id)
    # Just do the get, we don't need the result, it will error out if the group doesn't exist.
    rg = groups.get(resource_group_name)
    return rg.location


def _invoke_deployment(cmd, resource_group_name, deployment_name, template, parameters, validate, no_wait,
                       subscription_id=None):
    from azure.cli.core.profiles import ResourceType
    DeploymentProperties = cmd.get_models('DeploymentProperties', resource_type=ResourceType.MGMT_RESOURCE_RESOURCES)
    properties = DeploymentProperties(template=template, parameters=parameters, mode='incremental')
    smc = get_mgmt_service_client(cmd.cli_ctx, ResourceType.MGMT_RESOURCE_RESOURCES,
                                  subscription_id=subscription_id).deployments
    if validate:
        logger.info('==== BEGIN TEMPLATE ====')
        logger.info(json.dumps(template, indent=2))
        logger.info('==== END TEMPLATE ====')

    if cmd.supported_api_version(min_api='2019-10-01', resource_type=ResourceType.MGMT_RESOURCE_RESOURCES):
        Deployment = cmd.get_models('Deployment', resource_type=ResourceType.MGMT_RESOURCE_RESOURCES)
        deployment = Deployment(properties=properties)

        if validate:
            validation_poller = smc.validate(resource_group_name, deployment_name, deployment)
            return LongRunningOperation(cmd.cli_ctx)(validation_poller)
        return sdk_no_wait(no_wait, smc.create_or_update, resource_group_name, deployment_name, deployment)

    if validate:
        return smc.validate(resource_group_name, deployment_name, properties)
    return sdk_no_wait(no_wait, smc.create_or_update, resource_group_name, deployment_name, properties)


def _ensure_default_log_analytics_workspace_for_monitoring(cmd, subscription_id,
                                                           resource_group_name, cluster_name=None):
    # mapping for azure public cloud
    # log analytics workspaces cannot be created in WCUS region due to capacity limits
    # so mapped to EUS per discussion with log analytics team
    AzureCloudLocationToOmsRegionCodeMap = {
        "australiasoutheast": "ASE",
        "australiaeast": "EAU",
        "australiacentral": "CAU",
        "canadacentral": "CCA",
        "centralindia": "CIN",
        "centralus": "CUS",
        "eastasia": "EA",
        "eastus": "EUS",
        "eastus2": "EUS2",
        "eastus2euap": "EAP",
        "francecentral": "PAR",
        "japaneast": "EJP",
        "koreacentral": "SE",
        "northeurope": "NEU",
        "southcentralus": "SCUS",
        "southeastasia": "SEA",
        "uksouth": "SUK",
        "usgovvirginia": "USGV",
        "westcentralus": "EUS",
        "westeurope": "WEU",
        "westus": "WUS",
        "westus2": "WUS2"
    }
    AzureCloudRegionToOmsRegionMap = {
        "australiacentral": "australiacentral",
        "australiacentral2": "australiacentral",
        "australiaeast": "australiaeast",
        "australiasoutheast": "australiasoutheast",
        "brazilsouth": "southcentralus",
        "canadacentral": "canadacentral",
        "canadaeast": "canadacentral",
        "centralus": "centralus",
        "centralindia": "centralindia",
        "eastasia": "eastasia",
        "eastus": "eastus",
        "eastus2": "eastus2",
        "francecentral": "francecentral",
        "francesouth": "francecentral",
        "japaneast": "japaneast",
        "japanwest": "japaneast",
        "koreacentral": "koreacentral",
        "koreasouth": "koreacentral",
        "northcentralus": "eastus",
        "northeurope": "northeurope",
        "southafricanorth": "westeurope",
        "southafricawest": "westeurope",
        "southcentralus": "southcentralus",
        "southeastasia": "southeastasia",
        "southindia": "centralindia",
        "uksouth": "uksouth",
        "ukwest": "uksouth",
        "westcentralus": "eastus",
        "westeurope": "westeurope",
        "westindia": "centralindia",
        "westus": "westus",
        "westus2": "westus2"
    }

    # mapping for azure china cloud
    # currently log analytics supported only China East 2 region
    AzureChinaLocationToOmsRegionCodeMap = {
        "chinaeast": "EAST2",
        "chinaeast2": "EAST2",
        "chinanorth": "EAST2",
        "chinanorth2": "EAST2"
    }
    AzureChinaRegionToOmsRegionMap = {
        "chinaeast": "chinaeast2",
        "chinaeast2": "chinaeast2",
        "chinanorth": "chinaeast2",
        "chinanorth2": "chinaeast2"
    }

    # mapping for azure us governmner cloud
    AzureFairfaxLocationToOmsRegionCodeMap = {
        "usgovvirginia": "USGV"
    }
    AzureFairfaxRegionToOmsRegionMap = {
        "usgovvirginia": "usgovvirginia"
    }

    rg_location = _get_rg_location(cmd.cli_ctx, resource_group_name)
    cloud_name = cmd.cli_ctx.cloud.name

    workspace_region = "eastus"
    workspace_region_code = "EUS"

    # sanity check that locations and clouds match.
    if ((cloud_name.lower() == 'azurecloud' and AzureChinaRegionToOmsRegionMap.get(rg_location, False)) or
            (cloud_name.lower() == 'azurecloud' and AzureFairfaxRegionToOmsRegionMap.get(rg_location, False))):
        raise CLIError('Wrong cloud (azurecloud) setting for region {}, please use "az cloud set ..."'
                       .format(rg_location))

    if ((cloud_name.lower() == 'azurechinacloud' and AzureCloudRegionToOmsRegionMap.get(rg_location, False)) or
            (cloud_name.lower() == 'azurechinacloud' and AzureFairfaxRegionToOmsRegionMap.get(rg_location, False))):
        raise CLIError('Wrong cloud (azurechinacloud) setting for region {}, please use "az cloud set ..."'
                       .format(rg_location))

    if ((cloud_name.lower() == 'azureusgovernment' and AzureCloudRegionToOmsRegionMap.get(rg_location, False)) or
            (cloud_name.lower() == 'azureusgovernment' and AzureChinaRegionToOmsRegionMap.get(rg_location, False))):
        raise CLIError('Wrong cloud (azureusgovernment) setting for region {}, please use "az cloud set ..."'
                       .format(rg_location))

    if cloud_name.lower() == 'azurecloud':
        workspace_region = AzureCloudRegionToOmsRegionMap.get(
            rg_location, "eastus")
        workspace_region_code = AzureCloudLocationToOmsRegionCodeMap.get(
            workspace_region, "EUS")
    elif cloud_name.lower() == 'azurechinacloud':
        workspace_region = AzureChinaRegionToOmsRegionMap.get(
            rg_location, "chinaeast2")
        workspace_region_code = AzureChinaLocationToOmsRegionCodeMap.get(
            workspace_region, "EAST2")
    elif cloud_name.lower() == 'azureusgovernment':
        workspace_region = AzureFairfaxRegionToOmsRegionMap.get(
            rg_location, "usgovvirginia")
        workspace_region_code = AzureFairfaxLocationToOmsRegionCodeMap.get(
            workspace_region, "USGV")
    else:
        logger.error(
            "AKS Monitoring addon not supported in cloud : %s", cloud_name)

    default_workspace_resource_group = 'DefaultResourceGroup-' + workspace_region_code
    default_workspace_name = 'DefaultWorkspace-{0}-{1}'.format(
        subscription_id, workspace_region_code)
    default_workspace_resource_id = '/subscriptions/{0}/resourceGroups/{1}/providers/Microsoft.OperationalInsights' \
        '/workspaces/{2}'.format(subscription_id,
                                 default_workspace_resource_group, default_workspace_name)
    resource_groups = cf_resource_groups(cmd.cli_ctx, subscription_id)
    resources = cf_resources(cmd.cli_ctx, subscription_id)

    # check if default RG exists
    if resource_groups.check_existence(default_workspace_resource_group):
        try:
            resource = resources.get_by_id(
                default_workspace_resource_id, '2015-11-01-preview')
            return resource.id
        except CloudError as ex:
            if ex.status_code != 404:
                raise ex
    else:
        resource_groups.create_or_update(default_workspace_resource_group, {
                                         'location': workspace_region})

    default_workspace_params = {
        'location': workspace_region,
        'properties': {
            'sku': {
                'name': 'standalone'
            }
        }
    }
    async_poller = resources.create_or_update_by_id(default_workspace_resource_id, '2015-11-01-preview',
                                                    default_workspace_params)

    ws_resource_id = ''
    while True:
        result = async_poller.result(15)
        if async_poller.done():
            ws_resource_id = result.id
            break

    return ws_resource_id


def _ensure_container_insights_for_monitoring(cmd, workspace_resource_id):
    # extract subscription ID and resource group from workspace_resource_id URL
    try:
        subscription_id = workspace_resource_id.split('/')[2]
        resource_group = workspace_resource_id.split('/')[4]
    except IndexError:
        raise CLIError('Could not locate resource group in workspace-resource-id URL.')

    # region of workspace can be different from region of RG so find the location of the workspace_resource_id
    resources = cf_resources(cmd.cli_ctx, subscription_id)
    try:
        resource = resources.get_by_id(workspace_resource_id, '2015-11-01-preview')
        location = resource.location
    except CloudError as ex:
        raise ex

    unix_time_in_millis = int(
        (datetime.datetime.utcnow() - datetime.datetime.utcfromtimestamp(0)).total_seconds() * 1000.0)

    solution_deployment_name = 'ContainerInsights-{}'.format(unix_time_in_millis)

    # pylint: disable=line-too-long
    template = {
        "$schema": "https://schema.management.azure.com/schemas/2015-01-01/deploymentTemplate.json#",
        "contentVersion": "1.0.0.0",
        "parameters": {
            "workspaceResourceId": {
                "type": "string",
                "metadata": {
                    "description": "Azure Monitor Log Analytics Resource ID"
                }
            },
            "workspaceRegion": {
                "type": "string",
                "metadata": {
                    "description": "Azure Monitor Log Analytics workspace region"
                }
            },
            "solutionDeploymentName": {
                "type": "string",
                "metadata": {
                    "description": "Name of the solution deployment"
                }
            }
        },
        "resources": [
            {
                "type": "Microsoft.Resources/deployments",
                "name": "[parameters('solutionDeploymentName')]",
                "apiVersion": "2017-05-10",
                "subscriptionId": "[split(parameters('workspaceResourceId'),'/')[2]]",
                "resourceGroup": "[split(parameters('workspaceResourceId'),'/')[4]]",
                "properties": {
                    "mode": "Incremental",
                    "template": {
                        "$schema": "https://schema.management.azure.com/schemas/2015-01-01/deploymentTemplate.json#",
                        "contentVersion": "1.0.0.0",
                        "parameters": {},
                        "variables": {},
                        "resources": [
                            {
                                "apiVersion": "2015-11-01-preview",
                                "type": "Microsoft.OperationsManagement/solutions",
                                "location": "[parameters('workspaceRegion')]",
                                "name": "[Concat('ContainerInsights', '(', split(parameters('workspaceResourceId'),'/')[8], ')')]",
                                "properties": {
                                    "workspaceResourceId": "[parameters('workspaceResourceId')]"
                                },
                                "plan": {
                                    "name": "[Concat('ContainerInsights', '(', split(parameters('workspaceResourceId'),'/')[8], ')')]",
                                    "product": "[Concat('OMSGallery/', 'ContainerInsights')]",
                                    "promotionCode": "",
                                    "publisher": "Microsoft"
                                }
                            }
                        ]
                    },
                    "parameters": {}
                }
            }
        ]
    }

    params = {
        "workspaceResourceId": {
            "value": workspace_resource_id
        },
        "workspaceRegion": {
            "value": location
        },
        "solutionDeploymentName": {
            "value": solution_deployment_name
        }
    }

    deployment_name = 'aks-monitoring-{}'.format(unix_time_in_millis)
    # publish the Container Insights solution to the Log Analytics workspace
    return _invoke_deployment(cmd, resource_group, deployment_name, template, params,
                              validate=False, no_wait=False, subscription_id=subscription_id)

def _get_container_insights_settings(cmd, resource_group_name,
                                     cluster_name, configuration_settings, configuration_protected_settings):
    from msrestazure.tools import parse_resource_id  # pylint: disable=import-error

    subscription_id = get_subscription_id(cmd.cli_ctx)
    workspace_resource_id = ''
    if 'loganalyticsworkspaceresourceid' in configuration_settings:
        configuration_settings['logAnalyticsWorkspaceResourceID'] = configuration_settings.pop(
                'loganalyticsworkspaceresourceid')
        workspace_resource_id = configuration_settings['omsagent.secret.logAnalyticsWorkspaceResourceID']

    if not workspace_resource_id:
        workspace_resource_id = _ensure_default_log_analytics_workspace_for_monitoring(
            cmd, subscription_id, resource_group_name, cluster_name)

    workspace_resource_id = workspace_resource_id.strip()

    if not workspace_resource_id.startswith('/'):
        workspace_resource_id = '/' + workspace_resource_id

    if workspace_resource_id.endswith('/'):
        workspace_resource_id = workspace_resource_id.rstrip('/')

    _ensure_container_insights_for_monitoring(cmd, workspace_resource_id)

    # extract subscription ID and resource group from workspace_resource_id URL
    parsed = parse_resource_id(workspace_resource_id)
    workspace_sub_id, workspace_rg_name, workspace_name = parsed["subscription"], parsed["resource_group"], parsed["name"]

    log_analytics_client = cf_log_analytics(cmd.cli_ctx, workspace_sub_id)
    log_analytics_workspace = log_analytics_client.workspaces.get(workspace_rg_name, workspace_name)
    if not log_analytics_workspace:
        raise CLIError(
            'Fails to retrieve workspace by {}'.format(workspace_name))

    shared_keys = log_analytics_client.shared_keys.get_shared_keys(
        workspace_rg_name, workspace_name)
    if not shared_keys:
        raise CLIError('Fails to retrieve shared key for workspace {}'.format(
            log_analytics_workspace))
    configuration_settings['omsagent.secret.wsid'] = log_analytics_workspace.customer_id
    configuration_protected_settings['omsagent.secret.key'] = shared_keys.primary_shared_key
