import requests


class Client(requests.Session):
    URL = "https://api.snailtrail.art/graphql/"

    def __init__(
        self,
        http_token=None,
        proxy=None,
    ):
        super().__init__()
        self.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:91.0) Gecko/20100101 Firefox/91.0",
            }
        )
        self.trust_env = False
        if http_token:
            self.headers.update({"authorization": f"Basic {http_token}"})
        if proxy:
            self.proxies = {
                "http": proxy,
                "https": proxy,
            }
            # TODO: fetch mitmproxy CA and use it
            self.verify = False

    def query(self, operation, variables, query):
        r = self.post(
            self.URL,
            json={
                'operationName': operation,
                'variables': variables,
                'query': query,
            },
        )
        r.raise_for_status()
        r = r.json()
        if r.get('data') is None:
            raise Exception(r)
        return r["data"]

    def get_all_snails_marketplace(self, offset=0, filters={}):
        return self.query(
            "getAllSnail",
            {
                "filters": filters,
                "offset": offset,
            },
            """
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
            """,
        )['marketplace_promise']

    def get_all_snails(self, offset=0, filters={}):
        return self.query(
            "getAllSnail",
            {
                "filters": filters,
                "offset": offset,
            },
            """
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
            """,
        )['snails_promise']

    def get_mission_races(self, offset=0, filters={}):
        return self.query(
            "getMissionRaces",
            {
                "filters": filters,
                "limit": 20,
                "offset": offset,
            },
            """
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
            """,
        )['mission_races_promise']

    def get_my_snails_for_missions(
        self,
        owner,
        offset=0,
    ):
        return self.query(
            "getMySnailsForMissions",
            {
                "owner": owner,
                "limit": 20,
                "offset": offset,
            },
            """
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
            """,
        )['my_snails_mission_promise']

    def join_mission_races(
        self, snail_id: int, race_id: int, address: str, signature: str
    ):
        return self.query(
            "joinMissionRaces",
            {
                "params": {
                    "token_id": snail_id,
                    "race_id": race_id,
                    "signature": signature,
                    "address": address,
                }
            },
            """
            mutation joinMissionRaces($params: JoinRaceParams) {
                join_mission_promise(params: $params) {
                    ... on Problem {
                    problem
                    __typename
                    }
                    ... on JoinRaceResponse {
                    status
                    message
                    signature
                    payload {
                        ... on MissionPayload {
                        race_id
                        token_id
                        address
                        athletes
                        owners
                        size
                        timeout
                        salt
                        completed_races {
                            race_id
                            owners
                            __typename
                        }
                        __typename
                        }
                        __typename
                    }
                    __typename
                    }
                    __typename
                }
            }
            """,
        )['join_mission_promise']

    def name_change(self, name):
        return self.query(
            "nameChange",
            {
                "name": name,
            },
            """
            query nameChange($name: String!) {
                name_status_promise(name: $name) {
                    ... on Problem {
                    problem
                    __typename
                    }
                    ... on NameStatus {
                    status
                    message
                    __typename
                    }
                    __typename
                }
            }
            """,
        )['name_status_promise']
