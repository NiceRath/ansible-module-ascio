# for hardcoded config parameters
RESULT_CODE_SUCCESS = [200, 201]
DOMAIN_TYPE_STANDARD = 'Standard'
DOMAIN_AVAILABLE_RESULT = 'Available'
GET_DOMAINS_DEFAULTS = {
    'order_by': 'CreatedAsc',
    'filter_status': 'All',
    'filter_tld': [],
    'filter_names': [],
    'filter_type': None,
    'filter_comment': None,
    'filter_expire_from': None,
    'filter_expire_to': None,
    'results_page': 1,
    'results': 1000,
}
WHOIS_GDPR_TLDs = ['com', 'net', 'cc', 'tv']  # see: https://aws.ascio.info/gdpr-api.html
