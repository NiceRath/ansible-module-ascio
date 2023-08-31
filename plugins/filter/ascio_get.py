from csv import DictWriter


class FilterModule(object):

    def filters(self):
        return {
            "ascio_filter_results": self.filter_results,
            "ascio_write_domain_csv": self.write_domain_csv,
        }

    @staticmethod
    def filter_results(result: dict, remove_fields: list = None) -> dict:
        # will only output domain and its nameservers (cleaned)
        domains = {}
        if remove_fields is None:
            remove_fields = []

        remove_fields.append('DomainName')

        if 'data' not in result:
            return domains

        for domain_raw in result['data']['DomainInfo']:
            domain_simple = {**domain_raw, 'NameServers': []}
            for field in remove_fields:
                try:
                    domain_simple.pop(field)

                except KeyError:
                    pass

            for ns in domain_raw['NameServers'].values():
                for ns_field in ['HostName', 'IpAddress', 'IpV6Address']:
                    if ns[ns_field] is not None:
                        domain_simple['NameServers'].append(ns[ns_field])

            domains[domain_raw['DomainName']] = domain_simple

        return domains

    @staticmethod
    def write_domain_csv(data: dict, file: str) -> bool:
        data_list = []
        for domain, values in data.items():
            data_list.append({'DomainName': domain, **values})

        try:
            columns = list(data_list[0].keys())

            with open(file, 'w', encoding='uft-8') as target:
                writer = DictWriter(target, fieldnames=columns)
                writer.writeheader()
                for entry in data_list:
                    writer.writerow(entry)

            return True

        except IOError:
            return False
