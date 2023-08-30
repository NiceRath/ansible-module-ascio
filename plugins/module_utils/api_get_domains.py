from ansible_collections.niceshopsorg.ascio.plugins.module_utils.api_base import ascio_api
from ansible_collections.niceshopsorg.ascio.plugins.module_utils import config as api_config

from sys import exc_info as sys_exc_info
from traceback import format_exc

# for api see:
#   https://aws.ascio.info/api-v3/python/getdomains
#   https://aws.ascio.info/api-v3/python/schema/GetDomainsResponse

# added as utils since this function is used in multiple modules


def ascio_get_domains(params: dict) -> dict:
    # overwriting default parameters with custom supplied ones
    _parameters = api_config.GET_DOMAINS_DEFAULTS.copy()
    _parameters.update(params)

    try:
        response = ascio_api(
            method='GetDomains',
            user=_parameters['user'],
            password=_parameters['password'],
            request={
                "OrderSort": _parameters['order_by'],
                "Status": _parameters['filter_status'],
                "Tlds": {"string": _parameters['filter_tld']},
                "ObjectNames": {"string": _parameters['filter_names']},
                "DomainType": _parameters['filter_type'],
                "DomainComment": _parameters['filter_comment'],
                "ExpireFromDate": _parameters['filter_expire_from'],
                "ExpireToDate": _parameters['filter_expire_to'],
                "PageInfo": {
                    "PageIndex": _parameters['results_page'],
                    "PageSize": _parameters['results'],
                },
                # "Handles": {"string": [""]},
                # "CreationFromDate": "2021-10-12T13:08:56.956+02:00",
                # "CreationToDate": "2021-10-12T13:08:56.956+02:00",
                # "OwnerName": "OwnerNameTest",
                # "OwnerOrganizationName": "OwnerOrganizationNameTest",
                # "OwnerEmail": "OwnerEmailTest",
                # "ContactFirstName": "ContactFirstNameTest",
                # "ContactLastName": "ContactLastNameTest",
                # "ContactOrganizationName": "ContactOrganizationNameTest",
                # "ContactEmail": "ContactEmailTest",
                # "NameServerHostName": "NameServerHostNameTest",
                # "NameServerIPv4": "NameServerIPv4Test",
                # "NameServerIPv6": "NameServerIPv6Test",
                # "CustomerReferenceExternalId": "CustomerReferenceExternalIdTest",
                # "CustomerReferenceDescription": "CustomerReferenceDescriptionTest",
            }
        )
        # todo: remove useless stuff from 'data' => what do we want to do with that data?

        return {
            'DomainInfos': response['DomainInfos'],
            'TotalCount': response['TotalCount'],
            'Errors': response['Errors'],
            'ResultCode': response['ResultCode'],
            'ResultMessage': response['ResultMessage'],
        }

    # pylint: disable=W0718
    except Exception as error:
        exc_type, _, _ = sys_exc_info()
        return {
            'DomainInfos': {},
            'TotalCount': 0,
            'Errors': {'string': [str(exc_type), str(error), str(format_exc())]},
            'ResultCode': 0,
            'ResultMessage': None,
        }
