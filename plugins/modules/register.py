#!/usr/bin/python

# Copyright: (c) 2021, Rene Rath <rene.rath@niceshops.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.niceshopsorg.ascio.plugins.module_utils.api_get_domains import ascio_get_domains
from ansible_collections.niceshopsorg.ascio.plugins.module_utils.api_base import ascio_api
from ansible_collections.niceshopsorg.ascio.plugins.module_utils import config as api_config
from ansible_collections.niceshopsorg.ascio.plugins.module_utils.tldkit import TLD

from sys import exc_info as sys_exc_info
from traceback import format_exc
from re import match as regex_match

# see: https://docs.ansible.com/ansible/latest/dev_guide/developing_program_flow_modules.html#ansiblemodule

DOCUMENTATION = "https://github.com/niceshops/ansible-module-ascio"
EXAMPLES = "https://github.com/niceshops/ansible-module-ascio"
RETURN = "https://github.com/niceshops/ansible-module-ascio"


class Register:
    DIFF_COMPARE_FILTER = {
        # we will remove all field received from the get-call if they are not listed here
        #   else there will always be a difference
        'nameservers': ['HostName'],
        'contacts': [
            'FirstName', 'LastName', 'OrgName', 'Address1', 'Address2', 'City', 'State', 'PostalCode', 'CountryCode',
            'Phone', 'Email', 'Type', 'Details', 'OrganisationNumber', 'Number', 'VatNumber'
        ]
    }
    OWNER_CHANGE_FIELDS = ['FirstName', 'LastName', 'OrganisationNumber', 'Email']
    MODULE_API_CONTACT_MAPPING = {
        'contact_owner': 'Owner',
        'contact_admin': 'Admin',
        'contact_tech': 'Tech',
        'contact_billing': 'Billing',
    }

    HIDE_WHOIS_TLDs = ['com', 'cc', 'tv']  # .net did not work
    KNOWN_ERRORS = {
        'pending': 'FO405',
        'update_pending': "Order rejected because of '.*?' order '.*?' on same object",  # ..Object status prohibits operation
        'balance_exceeded': 'Partner (.*?) blocked',
    }

    TRADEMARK_COUNTRY_TLDs = ['it']  # tld's that need the trademark country to be set (will be the owners country)

    def __init__(self, module: AnsibleModule):
        self.module = module
        self.nameservers = None
        self.result = {
            'failed': False,
            'errors': [],
            'premium': False,
            'price': None,
            'price_currency': None,
            'available': False,
            'msg': False,
            'changed': False,
            'order': None,
            'owner': False,
            'diff': {
                'before': {},
                'after': {},
            },
        }

    def check(self) -> dict:
        # checking if
        #   we have registered the domain already
        #   if the domain is available
        #   if the relevant domain config has been changed

        self.nameservers = self._build_nameservers(ns_list=self.module.params['nameservers'])

        # get existing domains to check if we already registered the requested domain
        response = ascio_get_domains(
            params={
                'user': self.module.params['user'],
                'password': self.module.params['password'],
                'filter_names': [self.module.params['domain']],
            },
        )
        self.result['msg'] = response['ResultMessage']

        if response['ResultCode'] not in api_config.RESULT_CODE_SUCCESS or len(response['Errors']['string']) > 0:
            # fail if we were not able to retrieve the data
            self.result['failed'] = True
            self.result['errors'].extend(response['Errors']['string'])

        else:
            if response['TotalCount'] == 0:
                self.result['changed'] = True

            else:
                self.result['owner'] = True
                self._compare_config(response=response)

            self._get_availability()

        if self.module.check_mode:
            # output infos regarding documentation requirements
            if not self.result['owner']:
                self._docs_required(
                    action='REGISTER',
                    msg='Documentation is required to register this TLD! Execution can be forced.'
                )

            elif self.result['changed']:
                self._docs_required(
                    action='NAMESERVER UPDATE',
                    msg='Documentation is required to update nameservers for this TLD! Execution can be forced.'
                )
                self._docs_required(
                    action='OWNER CHANGE',
                    msg='Documentation is required to update the owner for this TLD! Execution can be forced.'
                )
                if self._contacts_permitted():
                    self._docs_required(
                        action='CONTACT UPDATE',
                        msg='Documentation is required to update the contacts for this TLD! Execution can be forced.'
                    )

        return self.result

    def set(self) -> dict:
        # run 'check-mode' tasks to find out if the state has changed
        self.check()

        # run action if check succeeded and action is required
        if not self.result['failed'] and self.result['changed']:
            if self.module.params['max_price'] is not None and self.result['price'] is not None and \
                    self.result['price'] > self.module.params['max_price']:
                # if we defined a maximum price and the price is higher
                self.result['errors'].append('Domain price was higher than you allowed it to be!')
                self.result['failed'] = True
                return self.result

            if self.result['premium'] and not self.module.params['premium']:
                # if domain is premium and we don't allow registration of premium domains
                self.result['errors'].append(
                    "Domain is listed as 'premium' but you did not allow premium domains to be registered!"
                )
                self.result['failed'] = True
                return self.result

            if not self.result['available'] and not self.result['owner']:
                # if the domain is owned by someone else
                self.result['errors'].append("Domain is not available for registration!")
                self.result['failed'] = True
                return self.result

            # run the actual tasks to register the domain
            if not self.result['owner']:
                if not self._docs_required(
                        action='REGISTER',
                        msg='Documentation is required to register this TLD! Execution can be forced.'
                ):
                    self._create_call()

            else:
                self._update_call()

        self._error_check()
        return self.result

    def _error_check(self):
        # replacing generic error messages with ones that actually have a meaning
        new_errors = []

        for error in self.result['errors']:
            if regex_match(f".*{self.KNOWN_ERRORS['pending']}.*", error) is not None:
                new_errors.append('Domain is in Status PENDING => no changes can be made!')

            elif regex_match(f".*{self.KNOWN_ERRORS['update_pending']}.*", error) is not None:
                new_errors.append(
                    'After contact/owner-updates it can take some minutes before another change can be performed!'
                )

            elif regex_match(f".*{self.KNOWN_ERRORS['balance_exceeded']}.*", error) is not None:
                new_errors.append(
                    'The monthly account-balance has exceeded a maximum threshold! '
                    'You need to transfer some money to ASCIO to unblock your account!'
                )

            else:
                new_errors.append(error)

        self.result['errors'] = new_errors

    def _update_call(self):
        # update calls
        #   update nameservers
        if self.result['diff']['before']['nameservers'] != self.result['diff']['after']['nameservers']:
            if not self._docs_required(
                    action='NAMESERVER UPDATE',
                    msg='Documentation is required to update nameservers for this TLD! Execution can be forced.'
            ):
                response = ascio_api(
                    method='CreateOrder',
                    user=self.module.params['user'],
                    password=self.module.params['password'],
                    request={
                        'Type': 'NameserverUpdate',
                        'Domain': {
                            'Name': self.module.params['domain'],
                            'NameServers': self.nameservers,
                        }
                    },
                    request_type='v3:DomainOrderRequest',
                )

                self.result['msg'] = response['ResultMessage']
                self.result['errors'].extend(response['Errors']['string'])

                if response['ResultCode'] not in api_config.RESULT_CODE_SUCCESS:
                    self.result['failed'] = True

        if not self.module.params['update_only_ns']:
            #   update contacts
            contact_update = False

            if self.result['diff']['before']['contact_billing'] != self.result['diff']['after']['contact_billing'] or \
                    self.result['diff']['before']['contact_admin'] != self.result['diff']['after']['contact_admin'] or \
                    self.result['diff']['before']['contact_tech'] != self.result['diff']['after']['contact_tech']:

                if not self._docs_required(
                        action='CONTACT UPDATE',
                        msg='Documentation is required to update the contacts for this TLD! Execution can be forced.'
                ) and self._contacts_permitted():
                    contact_update = True
                    response = ascio_api(
                        method='CreateOrder',
                        user=self.module.params['user'],
                        password=self.module.params['password'],
                        request={
                            'Type': 'ContactUpdate',
                            'Domain': {
                                'Name': self.module.params['domain'],
                                'Admin': self.module.params['contact_admin'],
                                'Tech': self.module.params['contact_tech'],
                                'Billing': self.module.params['contact_billing'],
                            }
                        },
                        request_type='v3:DomainOrderRequest',
                    )

                    self.result['msg'] = response['ResultMessage']
                    self.result['errors'].extend(response['Errors']['string'])

                    if response['ResultCode'] not in api_config.RESULT_CODE_SUCCESS:
                        self.result['failed'] = True

            #   update registrant
            owner_change = False
            owner_details = False

            if self.result['diff']['before']['contact_owner'] != self.result['diff']['after']['contact_owner']:
                if contact_update:
                    self.result['errors'].append(
                        'The contacts and owner cannot be changed at the same time => '
                        'you need to run the update again after the current changes have been completed.'
                    )

                elif not self._docs_required(
                        action='OWNER CHANGE',
                        msg='Documentation is required to update the owner for this TLD! Execution can be forced.'
                ):
                    # first we check if a owner-change is needed

                    for field in self.result['diff']['before']['contact_owner']:
                        if field in self.OWNER_CHANGE_FIELDS and \
                                self.result['diff']['before']['contact_owner'][field] != self.result['diff']['after']['contact_owner'][field]:

                            owner_change = True

                        elif self.result['diff']['before']['contact_owner'][field] != self.result['diff']['after']['contact_owner'][field]:
                            owner_details = True

                    if owner_change:
                        response = ascio_api(
                            method='CreateOrder',
                            user=self.module.params['user'],
                            password=self.module.params['password'],
                            request=self._registration_special_cases({
                                'Type': 'OwnerChange',
                                'Domain': {
                                    'Name': self.module.params['domain'],
                                    'Owner': self.module.params['contact_owner'],
                                }
                            }),
                            request_type='v3:DomainOrderRequest',
                        )

                    else:
                        response = ascio_api(
                            method='CreateOrder',
                            user=self.module.params['user'],
                            password=self.module.params['password'],
                            request=self._registration_special_cases({
                                'Type': 'RegistrantDetailsUpdate',
                                'Domain': {
                                    'Name': self.module.params['domain'],
                                    'Owner': self.module.params['contact_owner'],
                                }
                            }),
                            request_type='v3:DomainOrderRequest',
                        )

                    if owner_details and owner_change:
                        self.result['errors'].append(
                            'The owner cannot be changed and updated at the same time => '
                            'you need to run the update again after the current changes have been completed.'
                        )

                    self.result['msg'] = response['ResultMessage']
                    self.result['errors'].extend(response['Errors']['string'])

                    if response['ResultCode'] not in api_config.RESULT_CODE_SUCCESS:
                        self.result['failed'] = True

    def _create_call(self):
        # register/create call
        request = self._registration_special_cases({
            'Type': 'Register',
            'Domain': {
                'Name': self.module.params['domain'],
                'Owner': self.module.params['contact_owner'],
                'Admin': self.module.params['contact_admin'],
                'Tech': self.module.params['contact_tech'],
                'Billing': self.module.params['contact_billing'],
                'NameServers': self.nameservers,
            }
        })

        response = ascio_api(
            method='CreateOrder',
            user=self.module.params['user'],
            password=self.module.params['password'],
            request=request,
            request_type='v3:DomainOrderRequest',
        )

        self.result['order'] = response['OrderInfo']
        self.result['msg'] = response['ResultMessage']
        self.result['errors'].extend(response['Errors']['string'])

        if response['ResultCode'] not in api_config.RESULT_CODE_SUCCESS:
            self.result['failed'] = True

    def _get_availability(self):
        # check availability of domain and its price
        response = ascio_api(
            method='AvailabilityInfo',
            user=self.module.params['user'],
            password=self.module.params['password'],
            request={
                "DomainName": self.module.params['domain'],
                "Quality": "QualityTest",
            }
        )

        self.result['msg'] = response['ResultMessage']
        if response['ResultMessage'] == api_config.DOMAIN_AVAILABLE_RESULT:
            self.result['available'] = True

        if response['ResultCode'] in api_config.RESULT_CODE_SUCCESS and len(response['Errors']['string']) == 0:
            if response['DomainType'] != api_config.DOMAIN_TYPE_STANDARD:
                self.result['premium'] = True

            for info in response['Prices']['PriceInfo']:
                if info['Product']['OrderType'] == 'Register':
                    self.result['price'] = float(info['Price'])

            self.result['price_currency'] = response['Currency']

        else:
            self.result['errors'].extend(response['Errors']['string'])
            self.result['failed'] = True

    def _registration_special_cases(self, request: dict) -> dict:
        _tld = request['Domain']['Name'].rsplit('.', 1)[1]

        if self.module.params['whois_hide'] and _tld in self.HIDE_WHOIS_TLDs:
            request['Domain']['DiscloseSocialData'] = 'false'

        if self.module.params['lp'] and TLD(
                user=self.module.params['user'],
                password=self.module.params['password'],
                domain=self.module.params['domain'],
                tld_cache=self.module.params['tld_cache'],
        ).lp_offered():
            request['Domain']['LocalPresence'] = 'true'

        if _tld in self.TRADEMARK_COUNTRY_TLDs:
            request['Domain']['Trademark'] = {'Country': request['Domain']['Owner']['CountryCode']}

        return request

    def _contacts_permitted(self):
        # some tld's don't support contact-data
        result = TLD(
                user=self.module.params['user'],
                password=self.module.params['password'],
                domain=self.module.params['domain'],
                action='CONTACT UPDATE',
                tld_cache=self.module.params['tld_cache'],
        ).contacts_permitted()

        if not result:
            self.module.warn('You cannot update contact-data of this TLD.')

        return result

    def _docs_required(self, action: str, msg: str):
        # checking if documentation is required for the current action or it has been forced
        if TLD(
                user=self.module.params['user'],
                password=self.module.params['password'],
                domain=self.module.params['domain'],
                action=action,
                tld_cache=self.module.params['tld_cache'],
        ).docs_required() and not self.module.params['force']:
            self.result['errors'].append(msg)
            self.result['failed'] = True
            return True

        return False

    def _compare_config(self, response: dict):
        # build comparison dict from received settings
        existing_config = response['DomainInfos']['DomainInfo'][0]

        self.result['diff']['before'] = {key: {} for key in self.MODULE_API_CONTACT_MAPPING}
        self.result['diff']['after'] = {key: {} for key in self.MODULE_API_CONTACT_MAPPING}

        for attribute in self.DIFF_COMPARE_FILTER['contacts']:
            for module_key, api_key in self.MODULE_API_CONTACT_MAPPING.items():
                if attribute in existing_config[api_key]:
                    self.result['diff']['before'][module_key][attribute] = existing_config[api_key][attribute]

                else:
                    self.result['diff']['before'][module_key][attribute] = None

                if attribute in self.module.params[module_key]:
                    self.result['diff']['after'][module_key][attribute] = self.module.params[module_key][attribute]

                else:
                    self.result['diff']['after'][module_key][attribute] = None

        _before_nameservers = []

        for value in existing_config['NameServers'].values():
            _before_nameservers.append(value[self.DIFF_COMPARE_FILTER['nameservers'][0]])

        self.result['diff']['before']['nameservers'] = self._build_nameservers(ns_list=_before_nameservers)
        self.result['diff']['after']['nameservers'] = self.nameservers

        if self.result['diff']['before'] != self.result['diff']['after']:
            self.result['changed'] = True

    @staticmethod
    def _build_nameservers(ns_list: list) -> dict:
        # build nameserver-dict from supplied list
        nameservers = {}

        for i in range(1, len(ns_list) + 1):
            _server = ns_list[i - 1]

            if _server is not None:
                if _server.endswith('.'):
                    _server = _server[:-1]

                nameservers[f'NameServer{i}'] = {'HostName': _server}

        return nameservers


def run_module():
    # arguments we expect
    module_args = dict(
        user=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True),
        nameservers=dict(type='list', required=True),
        contact_owner=dict(type='dict', required=True),
        contact_tech=dict(type='dict', required=True),
        contact_admin=dict(type='dict', required=True),
        contact_billing=dict(type='dict', required=True),
        domain=dict(type='str', required=True, description='Domain to register'),
        premium=dict(type='bool', default=False, description='If premium domains should be registered (higher costs)'),
        max_price=dict(type='float', default=None, description='Set the maximal price of the domain'),
        whois_hide=dict(type='bool', default=False, description='If the contact data should be hidden in whois lookups'),
        update_only_ns=dict(type='bool', default=False, description='If only nameservers should be updated'),
        force=dict(type='bool', default=False, description='Force changes if documentation is required'),
        tld_cache=dict(type='str', required=True, description='Directory used to cache the TLDKit configurations'),
        lp=dict(type='bool', default=False, description='If ascio should be used as a local presence'),
    )
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )

    # custom conversion
    module.params['domain'] = module.params['domain'].encode('idna').decode('utf-8')

    # custom argument validation => might be possible to do this in a cleaner way..
    if 13 < len(module.params['nameservers']) < 2:
        module.fail_json(
            msg='You need to supply between 2 and 13 nameservers for the domain!',
            result=dict(
                failed=True,
            )
        )

    # run check or do actual work
    try:
        if module.check_mode:
            result = Register(module=module).check()

        else:
            result = Register(module=module).set()

        # return status and changes to user
        if result['failed']:
            result['msg'] = 'The ASCIO-API returned an error!'

        module.exit_json(**result)

    # pylint: disable=W0718
    except Exception as error:
        exc_type, _, _ = sys_exc_info()
        module.fail_json(
            msg='Got an error while processing the registration!',
            errors=[str(exc_type), str(error), str(format_exc())],
        )


def main():
    run_module()


if __name__ == '__main__':
    main()
