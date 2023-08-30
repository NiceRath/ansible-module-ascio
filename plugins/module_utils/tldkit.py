from requests import get
from json import dumps as json_dumps
from json import loads as json_loads
from datetime import datetime
from os import path, mkdir

TLDKIT_BASE_URL = 'https://tldkit.ascio.com/api/v1/Tldkit'
CACHE_DIR = '~/.cache/ansible-module-ascio'
MAX_CACHE_AGE = 180


class TLD:
    def __init__(self, user: str, password: str, domain: str, action: str = '', tld_cache: str = CACHE_DIR):
        self.user = user
        self.password = password
        self.tld = domain.rsplit('.', 1)[1]
        self.action = action.upper()
        # REGISTER, DELETE, CONTACT UPDATE, NAMESERVER UPDATE, OWNER CHANGE, RENEW, TRANSFER, AUTORENEW, RESTORE
        # EXPIRE, REGISTRANT DETAILS UPDATE, TRANSFER AWAY
        self.cache_dir = tld_cache
        self.cache_file = f'{tld_cache}/{self.tld}.json'

    def docs_required(self) -> bool:
        req = self._get_action_attribute(attribute='DocumentationRequired')
        return False if req is None else req

    def contacts_permitted(self) -> bool:
        bad_list = ['not permitted', 'not supported', 'Contact roles does not exist']
        update_todo = self._get_action_attribute(attribute='Procedure', action='CONTACT UPDATE')
        permitted = True

        if update_todo is not None:
            for bad in bad_list:
                if update_todo.find(bad) != -1:
                    permitted = False
                    break

        return permitted

    def _get_info_online(self) -> dict:
        return get(
            f"{TLDKIT_BASE_URL}/{self.tld}", auth=(self.user, self.password),
            timeout=90,
        ).json()

    def _cache_valid(self) -> bool:
        if path.exists(self.cache_file):
            cache_update_time = datetime.fromtimestamp(path.getmtime(self.cache_file))
            cache_age = datetime.now() - cache_update_time

            if cache_age.days > MAX_CACHE_AGE:
                return False

            return True

        return False

    def _cache_write(self, data: dict) -> bool:
        with open(self.cache_file, 'w', encoding='utf-8') as cache:
            cache.write(json_dumps(data))
            return True

    def _cache_read(self) -> dict:
        with open(self.cache_file, 'r', encoding='utf-8') as cache:
            return json_loads(cache.read())

    def _get_info(self) -> dict:
        if self._cache_valid():
            return self._cache_read()

        data = self._get_info_online()

        if not path.exists(self.cache_dir):
            mkdir(self.cache_dir)

        self._cache_write(data=data)
        return data

    def _get_action_attribute(self, attribute: str, action: str = None):
        if action is None:
            action = self.action

        for process in self._get_info()['Processes']:
            if process['Command'] == action:
                return process[attribute]

        return None

    def lp_needed(self):
        # not used since it is set to 'false' on some domains that require a LP.. don't know why that is
        return self._get_info()['LocalPresenceRequired']

    def lp_offered(self):
        return self._get_info()['LocalPresenceOffered']


if __name__ == '__main__':
    result = TLD(
        user=input('Provide the ASCIO API-User:\n > '),
        password=input('Provide the ASCIO API-Password:\n > '),
        domain=input('Provide the domain to check:\n > '),
        action=input('Provide the action:\n > '),
    ).docs_required()

    print(f"\nResult: {result}")
