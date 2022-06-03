import requests
import json


class Client(requests.Session):
    URL = 'https://api.snailtrail.art/graphql/'

    def __init__(self, http_token=None, proxy=None):
        super().__init__()
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:91.0) Gecko/20100101 Firefox/91.0',
        })
        if http_token:
            self.headers.update({'authorization': f'Basic {http_token}'})
        if proxy:
            self.proxies = {
                'http': proxy,
                'https': proxy,
            }
            # TODO: fetch mitmproxy CA and use it
            self.verify = False
    
    def request(self, method, url, *args, **kwargs):
        return super().request(method, self.URL, *args, **kwargs)

    def get_all_snails(self, offset=0, filters={}):
        r = self.post(
            '',
            json={
                "operationName": "getAllSnail",
                "variables": {
                    "filters": filters
                },
                "query": """
                    query getAllSnail($filters: SnailFilters) {
                        marketplace_promise(limit: 20, offset: """ + str(offset) + """, order: 1, filters: $filters) {
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

    def iterate_all_snails(self, filters={}):
        c = 0
        while True:
            snails = self.get_all_snails(offset=c, filters=filters)
            if not snails['marketplace_promise']['snails']:
                break
            yield from snails['marketplace_promise']['snails']
            c += 20
