from csv import DictWriter


class FilterModule(object):

    def filters(self):
        return {
            "filter_results": self.filter_results,
            "write_domain_csv": self.write_domain_csv,
        }

    @staticmethod
    def filter_results(result: dict) -> dict:
        # will only output domain and its nameservers (cleaned)
        domains = {}

        if 'data' not in result:
            return domains

        for domain in result['data']['DomainInfo']:
            _namesservers = []

            for ns in domain['NameServers'].values():
                if ns['HostName'] is not None:
                    _namesservers.append(ns['HostName'])

            domains[domain['DomainName']] = {
                'ns': _namesservers,
                'owner': f"{domain['Owner']['FirstName']} {domain['Owner']['LastName']} {domain['Owner']['OrgName']} {domain['Owner']['Email']}",
                'admin': f"{domain['Admin']['FirstName']} {domain['Admin']['LastName']} {domain['Admin']['OrgName']} {domain['Admin']['Email']}",
                'tech': f"{domain['Tech']['FirstName']} {domain['Tech']['LastName']} {domain['Tech']['OrgName']} {domain['Tech']['Email']}",
            }

        return domains

    @staticmethod
    def write_domain_csv(data: dict, file: str) -> bool:
        columns = ['Domain', 'NameServers', 'Owner', 'Admin', 'Tech']

        data_list = []
        for key, value in data.items():
            data_list.append({columns[0]: key, columns[1]: value['ns'], columns[2]: value['owner'], columns[3]: value['admin'], columns[4]: value['tech']})

        try:
            with open(file, 'w', encoding='uft-8') as target:
                writer = DictWriter(target, fieldnames=columns)
                writer.writeheader()
                for entry in data_list:
                    writer.writerow(entry)

            return True

        except IOError:
            return False
