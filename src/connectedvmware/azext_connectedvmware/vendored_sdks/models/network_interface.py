# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
#
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from msrest.serialization import Model


class NetworkInterface(Model):
    """Network Interface model.

    Variables are only populated by the server, and will be ignored when
    sending a request.

    :param name: Gets or sets the name of the network interface.
    :type name: str
    :ivar label: Gets or sets the label of the virtual network in vCenter that
     the nic is connected to.
    :vartype label: str
    :ivar ip_addresses: Gets or sets the nic ip addresses.
    :vartype ip_addresses: list[str]
    :ivar mac_address: Gets or sets the NIC MAC address.
    :vartype mac_address: str
    :param network_id: Gets or sets the ARM Id of the network resource to
     connect the virtual machine.
    :type network_id: str
    :param nic_type: NIC type. Possible values include: 'vmxnet3', 'vmxnet2',
     'vmxnet', 'e1000', 'e1000e', 'pcnet32'
    :type nic_type: str or
     ~azure.mgmt.vmware.v2020_10_01_preview.models.NICType
    :param power_on_boot: Gets or sets the power on boot. Possible values
     include: 'enabled', 'disabled'
    :type power_on_boot: str or
     ~azure.mgmt.vmware.v2020_10_01_preview.models.PowerOnBootOption
    :ivar network_mo_ref_id: Gets or sets the vCenter MoRef (Managed Object
     Reference) ID of the virtual network
     that the nic is connected to.
    :vartype network_mo_ref_id: str
    :ivar network_mo_name: Gets or sets the name of the virtual network in
     vCenter that the nic is connected to.
    :vartype network_mo_name: str
    :param device_key: Gets or sets the device key value.
    :type device_key: int
    :param ip_settings: Gets or sets the ipsettings.
    :type ip_settings:
     ~azure.mgmt.vmware.v2020_10_01_preview.models.NicIPSettings
    """

    _validation = {
        'label': {'readonly': True},
        'ip_addresses': {'readonly': True},
        'mac_address': {'readonly': True},
        'network_mo_ref_id': {'readonly': True},
        'network_mo_name': {'readonly': True},
    }

    _attribute_map = {
        'name': {'key': 'name', 'type': 'str'},
        'label': {'key': 'label', 'type': 'str'},
        'ip_addresses': {'key': 'ipAddresses', 'type': '[str]'},
        'mac_address': {'key': 'macAddress', 'type': 'str'},
        'network_id': {'key': 'networkId', 'type': 'str'},
        'nic_type': {'key': 'nicType', 'type': 'str'},
        'power_on_boot': {'key': 'powerOnBoot', 'type': 'str'},
        'network_mo_ref_id': {'key': 'networkMoRefId', 'type': 'str'},
        'network_mo_name': {'key': 'networkMoName', 'type': 'str'},
        'device_key': {'key': 'deviceKey', 'type': 'int'},
        'ip_settings': {'key': 'ipSettings', 'type': 'NicIPSettings'},
    }

    def __init__(self, **kwargs):
        super(NetworkInterface, self).__init__(**kwargs)
        self.name = kwargs.get('name', None)
        self.label = None
        self.ip_addresses = None
        self.mac_address = None
        self.network_id = kwargs.get('network_id', None)
        self.nic_type = kwargs.get('nic_type', None)
        self.power_on_boot = kwargs.get('power_on_boot', None)
        self.network_mo_ref_id = None
        self.network_mo_name = None
        self.device_key = kwargs.get('device_key', None)
        self.ip_settings = kwargs.get('ip_settings', None)
