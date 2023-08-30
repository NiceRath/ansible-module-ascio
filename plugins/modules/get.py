#!/usr/bin/python

# Copyright: (c) 2021, Rene Rath <rene.rath@niceshops.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.niceshopsorg.ascio.plugins.module_utils.api_get_domains import ascio_get_domains
from ansible_collections.niceshopsorg.ascio.plugins.module_utils import config as api_config

# see: https://docs.ansible.com/ansible/latest/dev_guide/developing_program_flow_modules.html#ansiblemodule
# for api see:
#   https://aws.ascio.info/api-v3/python/getdomains
#   https://aws.ascio.info/api-v3/python/schema/GetDomainsResponse

DOCUMENTATION = "https://github.com/niceshops/ansible-module-ascio"
EXAMPLES = "https://github.com/niceshops/ansible-module-ascio"
RETURN = "https://github.com/niceshops/ansible-module-ascio"


def nice_check(module: AnsibleModule, params: dict = None) -> dict:
    # params var can be used to import this function from other modules
    if params is None and AnsibleModule is not None:
        params = module.params

    elif params is None:
        return {}

    # run 'check-mode' tasks to find out if the state has changed
    failed = False

    # get data from existing item and build its dataset for comparison
    response = ascio_get_domains(params=params)

    # fail if we were not able to retrieve the data
    if response['ResultCode'] not in api_config.RESULT_CODE_SUCCESS or len(response['Errors']['string']) > 0:
        failed = True

    return {
        'failed': failed,
        'data': response['DomainInfos'],
        'count': response['TotalCount'],
        'errors': response['Errors']['string'],
    }


def run_module():
    # arguments we expect
    module_args = dict(
        user=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True),
        order_by=dict(
            type='str',
            description='How to sort the response entries',
            default=api_config.GET_DOMAINS_DEFAULTS['order_by'],
        ),
        filter_tld=dict(
            type='list', description='TLDs to filter on',
            default=api_config.GET_DOMAINS_DEFAULTS['filter_tld'],
        ),
        filter_names=dict(
            type='list',
            description='Domain Names to filter on',
            default=api_config.GET_DOMAINS_DEFAULTS['filter_names'],
        ),
        filter_type=dict(
            type='str',
            description='DomainTypes to filter on',
            default=api_config.GET_DOMAINS_DEFAULTS['filter_type'],
            choices=['Premium', 'Standard'],
        ),
        filter_comment=dict(
            type='str',
            description='Comment to filter on',
            default=api_config.GET_DOMAINS_DEFAULTS['filter_comment'],
        ),
        filter_status=dict(
            type='str',
            description='Domain Status to filter on',
            default=api_config.GET_DOMAINS_DEFAULTS['filter_status'],
            choices=[
                'All', 'All Except Deleted', 'Active', 'Expiring', 'Pending Verification', 'Parked', 'Pending Auction',
                'Queued', 'Lock', 'Transfer Lock', 'Update Lock', 'Delete Lock', 'Deleted'
            ]
        ),
        filter_expire_from=dict(
            type='str',
            description='Expiration date start to filter on, Format: 2021-10-12T13:08:56.956+02:00',
            default=api_config.GET_DOMAINS_DEFAULTS['filter_expire_from'],
        ),
        filter_expire_to=dict(
            type='str',
            description='Expiration date stop to filter on, Format: 2021-10-12T15:08:56.956+02:00',
            default=api_config.GET_DOMAINS_DEFAULTS['filter_expire_to'],
        ),
        results=dict(
            type='int',
            default=api_config.GET_DOMAINS_DEFAULTS['results'],
            description='How many results should be returned by the response'
        ),
        results_page=dict(
            type='int',
            default=api_config.GET_DOMAINS_DEFAULTS['results_page'],
            description="If more entries than 'results' exist => you can change the page"
        ),
    )
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )

    # set default results
    result = dict(
        failed=False,
        data=None,
        count=0,
        errors=[],
    )

    # custom conversion
    module.params['filter_names'] = [name.encode('idna').decode('utf-8') for name in module.params['filter_names']]
    module.params['filter_tld'] = [tld.encode('idna').decode('utf-8') for tld in module.params['filter_tld']]

    # run check or do actual work
    _task_result = nice_check(module=module)

    # return status and changes to user
    if _task_result['failed']:
        module.fail_json(
            msg='The ASCIO-API returned an error!',
            result=dict(
                errors=_task_result['errors'],
                failed=True,
            )
        )

    else:
        result['data'] = _task_result['data']
        result['errors'] = _task_result['errors']
        result['count'] = _task_result['count']

        module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
