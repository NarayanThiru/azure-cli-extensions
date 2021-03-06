# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.cli.core.azclierror import InvalidArgumentValueError


def _build_criteria(condition, condition_query):
    from .vendored_sdks.azure_mgmt_scheduled_query.models import (ScheduledQueryRuleCriteria,
                                                                  ConditionFailingPeriods)
    for cond in condition:
        if condition_query and cond.query in condition_query:
            # replace query placeholder
            placeholder = cond.query
            cond.query = condition_query[placeholder]
        if cond.failing_periods is None:
            cond.failing_periods = ConditionFailingPeriods(
                min_failing_periods_to_alert=1,
                number_of_evaluation_periods=1
            )
        else:
            if cond.failing_periods.min_failing_periods_to_alert > cond.failing_periods.number_of_evaluation_periods:
                raise InvalidArgumentValueError('EvaluationPeriod must be greater than or equals to MinTimeToFail.')
    return ScheduledQueryRuleCriteria(all_of=condition)


def create_scheduled_query(client, resource_group_name, rule_name, scopes, condition, condition_query=None,
                           disabled=False, description=None, tags=None, location=None, display_name=None,
                           auto_mitigate=True, skip_query_validation=False, check_workspace_alerts_storage=False,
                           actions=None, severity=2, window_size='5m', evaluation_frequency='5m',
                           target_resource_type=None, mute_actions_duration=None):
    from .vendored_sdks.azure_mgmt_scheduled_query.models import ScheduledQueryRuleResource
    criteria = _build_criteria(condition, condition_query)
    kwargs = {
        'display_name': display_name,
        'description': description,
        'severity': severity,
        'enabled': not disabled,
        'scopes': scopes,
        'evaluation_frequency': evaluation_frequency,
        'window_size': window_size,
        'criteria': criteria,
        'target_resource_types': [target_resource_type] if target_resource_type else None,
        'actions': actions,
        'tags': tags,
        'location': location,
        'mute_actions_duration': mute_actions_duration,
        'check_workspace_alerts_storage_configured': check_workspace_alerts_storage,
        'skip_query_validation': skip_query_validation,
        'auto_mitigate': auto_mitigate,
    }
    return client.create_or_update(resource_group_name, rule_name, ScheduledQueryRuleResource(**kwargs))


def list_scheduled_query(client, resource_group_name=None):
    if resource_group_name:
        return client.list_by_resource_group(resource_group_name=resource_group_name)
    return client.list_by_subscription()


def update_scheduled_query(cmd, instance, tags=None, disabled=None, condition=None, condition_query=None,
                           description=None, actions=None, severity=None, window_size=None, display_name=None,
                           auto_mitigate=None, evaluation_frequency=None, mute_actions_duration=None,
                           skip_query_validation=None, check_workspace_alerts_storage=None):
    with cmd.update_context(instance) as c:
        c.set_param('tags', tags)
        c.set_param('display_name', display_name)
        if disabled is not None:
            c.set_param('enabled', not disabled)
        if auto_mitigate is not None:
            c.set_param('auto_mitigate', auto_mitigate)
        c.set_param('skip_query_validation', skip_query_validation)
        c.set_param('check_workspace_alerts_storage_configured', check_workspace_alerts_storage)
        c.set_param('description', description)
        c.set_param('actions', actions)
        c.set_param('severity', severity)
        c.set_param('window_size', window_size)
        c.set_param('evaluation_frequency', evaluation_frequency)
        c.set_param('mute_actions_duration', mute_actions_duration)
        if condition is not None:
            criteria = _build_criteria(condition, condition_query)
            c.set_param('criteria', criteria)
    return instance
