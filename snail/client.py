import requests
from Crypto.Hash import keccak
from web3 import Web3
from eth_account.messages import encode_defunct


class Client(requests.Session):
    URL = 'https://api.snailtrail.art/graphql/'

    def __init__(self, http_token=None, proxy=None, private_key=None, web3_provider=None, web3_provider_class=Web3.HTTPProvider):
        super().__init__()
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:91.0) Gecko/20100101 Firefox/91.0',
        })
        self.trust_env = False
        if http_token:
            self.headers.update({'authorization': f'Basic {http_token}'})
        if proxy:
            self.proxies = {
                'http': proxy,
                'https': proxy,
            }
            # TODO: fetch mitmproxy CA and use it
            self.verify = False
        if private_key and web3_provider:
            self.web3 = Web3(web3_provider_class(web3_provider))
            self.__pkey = private_key

    def request(self, method, url, *args, **kwargs):
        return super().request(method, self.URL, *args, **kwargs)

    def get_all_snails_marketplace(self, offset=0, filters={}):
        r = self.post(
            '',
            json={
                "operationName": "getAllSnail",
                "variables": {
                    "filters": filters,
                    "offset": offset,
                },
                "query": """
                    query getAllSnail($filters: SnailFilters, $offset: Int) {
                        marketplace_promise(limit: 20, offset: $offset, order: 1, filters: $filters) {
                            ... on Snails {
                            snails {
                                id
                                adaptations
                                name
                                market {
                                price
                                item_id
                                on_sale
                                price_wei
                                last_sale
                                __typename
                                }
                                gender {
                                id
                                __typename
                                }
                                breeding {
                                breed_status {
                                    cycle_total
                                    cycle_remaining
                                    cycle_end
                                    __typename
                                }
                                __typename
                                }
                                __typename
                            }
                            count
                            __typename
                            }
                            __typename
                        }
                        }
                """
            }
        )
        r.raise_for_status()
        return r.json()['data']

    def iterate_all_snails_marketplace(self, filters={}):
        c = 0
        while True:
            snails = self.get_all_snails_marketplace(offset=c, filters=filters)
            if not snails['marketplace_promise']['snails']:
                break
            yield from snails['marketplace_promise']['snails']
            c += 20

    def get_all_snails(self, offset=0, filters={}):
        r = self.post(
            '',
            json={
                "operationName": "getAllSnail",
                "variables": {
                    "filters": filters,
                    "offset": offset,
                },
                "query": """
                    query getAllSnail($filters: SnailFilters, $offset: Int) {
                        snails_promise(limit: 20, offset: $offset, order: 1, filters: $filters) {
                            ... on Snails {
                            snails {
                                id
                                adaptations
                                name
                                gender {
                                id
                                }
                                stats {
                                    experience {level, remaining}
                                }
                            }
                            count
                            }
                        }
                        }
                """
            }
        )
        r.raise_for_status()
        return r.json()['data']

    def iterate_all_snails(self, filters={}):
        c = 0
        while True:
            snails = self.get_all_snails(offset=c, filters=filters)
            if not snails['snails_promise']['snails']:
                break
            yield from snails['snails_promise']['snails']
            c += 20

    def get_mission_races(self, offset=0, filters={}):
        r = self.post(
            '',
            json={
                "operationName": "getMissionRaces",
                "variables": {
                    "filters": filters,
                    "limit": 20,
                    "offset": offset,
                },
                "query": """
                    query getMissionRaces($limit: Int, $offset: Int, $filters: RaceFilters) {
                        mission_races_promise(limit: $limit, offset: $offset, filters: $filters) {
                            ... on Problem {
                            problem
                            __typename
                            }
                            ... on Races {
                            all {
                                id
                                conditions
                                distance
                                athletes
                                track
                                participation
                                __typename
                            }
                            __typename
                            }
                            __typename
                        }
                        }
                """
            }
        )
        r.raise_for_status()
        return r.json()['data']

    def iterate_mission_races(self, filters={}):
        c = 0
        while True:
            snails = self.get_mission_races(offset=c, filters=filters)
            if not snails['mission_races_promise']['all']:
                break
            yield from snails['mission_races_promise']['all']
            c += 20

    def get_my_snails_for_missions(self, owner, offset=0, ):
        r = self.post(
            '',
            json={
                "operationName": "getMySnailsForMissions",
                "variables": {
                    "owner": owner,
                    "limit": 20,
                    "offset": offset,
                },
                "query": """
                    query getMySnailsForMissions($limit: Int, $offset: Int, $owner: String!) {
                        my_snails_mission_promise(limit: $limit, offset: $offset, owner: $owner) {
                            ... on Problem {
                            problem
                            __typename
                            }
                            ... on Snails {
                            snails {
                                id
                                adaptations
                                image_headshot
                                name
                                queueable_at
                                stats {
                                mission_tickets
                                __typename
                                }
                                __typename
                            }
                            count
                            __typename
                            }
                            __typename
                        }
                        }
                """
            }
        )
        r.raise_for_status()
        return r.json()['data']

    def iterate_my_snails_for_missions(self, owner):
        c = 0
        while True:
            snails = self.get_my_snails_for_missions(owner, offset=c)
            if not snails['my_snails_mission_promise']['snails']:
                break
            yield from snails['my_snails_mission_promise']['snails']
            c += 20

    def join_daily_mission(self, owner, snail, race):
        """Join a daily mission (non-last spot)
        >>> o = Client(private_key='badbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbad0', web3_provider='x')
        >>> o.join_daily_mission('0xbadbadbadbadbadbadbadbadbadbadbadbadbad0', 1816, 44660)
        '0x66287e0465f644bad50cab950218ee6386f0e19bde3be4fad34f473b33f806c0177718d8ddb4ffe0149e3098b20abc1a382c6c77d7f4b7f61f6f4fa33f8f47641c'
        """
        # TODO: SIGN!!! and join with graphql
        keccak_hash = keccak.new(digest_bits=256)
        keccak_hash.update(snail.to_bytes(32, 'big') + race.to_bytes(32, 'big') + bytes.fromhex(owner.replace('0x', '')))
        sign_payload = keccak_hash.digest()
        message = encode_defunct(sign_payload)
        return self.web3.eth.account.sign_message(message, private_key=self.__pkey).signature.hex()
