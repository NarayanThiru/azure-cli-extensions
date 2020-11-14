# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import re
from knack.util import CLIError


def validate_configuration_type(configuration_type):
    if configuration_type.lower() != 'sourcecontrolconfiguration':
        raise CLIError('Invalid configuration-type.  Valid value is "sourceControlConfiguration"')

def validate_configuration_name(namespace):
    if namespace.name:
        __validate_k8s_name(namespace.name, "configuration name", 63)

def validate_operator_namespace(namespace):
    if namespace.operator_namespace:
        __validate_k8s_name(namespace.operator_namespace, "operator namespace", 23)

def validate_operator_instance_name(namespace):
    if namespace.operator_instance_name:
        __validate_k8s_name(namespace.operator_instance_name, "operator instance name", 23)

def __validate_k8s_name(param_value, param_name, max_len):
    if len(param_value) > max_len:
        raise CLIError('Invalid {0} parameter. Valid {0}s can be a maximum of {1} characters'.format(param_name, max_len))
    if not re.match(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$', param_value):
        raise CLIError('Invalid {0} parameter. Valid {0}s must match with the regex [a-z0-9]'
            '([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*'.format(param_name))
