import requests
import time


class APIError(Exception):
    """API expected errors"""


class Client(requests.Session):
    URL = "https://api.snailtrail.art/graphql/"

    def __init__(
        self,
        http_token=None,
        proxy=None,
        rate_limiter=None,
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
        self.rate_limiter = rate_limiter
        self._last_query = 0

    def query(self, operation, variables, query):
        if self.rate_limiter is not None:
            delta = time.time() - self._last_query - self.rate_limiter
            if delta < 0:
                time.sleep(self.rate_limiter)

        r = self.post(
            self.URL,
            json={
                'operationName': operation,
                'variables': variables,
                'query': query,
            },
        )
        self._last_query = time.time()
        r.raise_for_status()
        r = r.json()
        if r.get('data') is None:
            raise Exception(r)
        if 'problem' in r['data']:
            raise APIError(r['data']['problem'])
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
                        breed_detail {
                            cycle_end
                            monthly_breed_available
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

    def get_all_snails(self, offset: int = 0, filters={}):
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
                        new_born
                        genome
                        klass
                        family
                        purity
                        breeding {
                        breed_detail {
                            cycle_end
                            monthly_breed_available
                        }
                        }
                        stats {
                            elo
                            experience {level, xp, remaining}
                            mission_tickets
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

    def get_onboarding_races(self, offset=0, filters={}):
        return self.query(
            "getOnboardingRaces",
            {
                "filters": filters,
                "limit": 20,
                "offset": offset,
            },
            """
            query getOnboardingRaces($limit: Int, $offset: Int, $filters: RaceFilters) {
                onboarding_races_promise(limit: $limit, offset: $offset, filters: $filters) {
                    ... on Problem {
                    problem
                    __typename
                    }
                    ... on Races {
                    all {
                        id
                        conditions
                        distance
                        league
                        status
                        race_type
                        starts_at
                        athletes
                        prize_pool
                        track
                        athletes
                        participation
                        __typename
                    }
                    own {
                        id
                        conditions
                        distance
                        league
                        status
                        race_type
                        starts_at
                        athletes
                        prize_pool
                        track
                        athletes
                        participation
                        __typename
                    }
                    __typename
                    }
                    __typename
                }
            }
            """,
        )['onboarding_races_promise']

    def get_finished_races(self, offset=0, filters={}, own=False):
        return self.query(
            "getFinishedRaces",
            {
                "filters": filters,
                "limit": 20,
                "offset": offset,
            },
            """
            query getFinishedRaces($filters: RaceFilters, $limit: Int, $offset: Int) {
                finished_races_promise(limit: $limit, offset: $offset, filters: $filters) {
                    ... on Problem {
                    problem
                    __typename
                    }
                    ... on Races {
                    %s {
                        id
                        conditions
                        distance
                        league
                        race_type
                        status
                        athletes
                        results {
                        token_id
                        time
                        __typename
                        }
                        track
                        starts_at
                        prize_pool
                        __typename
                    }
                    __typename
                    }
                    __typename
                }
            }
            """
            % ('own' if own else 'all'),
        )['finished_races_promise']

    def get_race_history(self, offset=0, filters={}):
        return self.query(
            "getRaceHistory",
            {
                "filters": filters,
                "limit": 20,
                "offset": offset,
            },
            """
            query getRaceHistory($limit: Int, $offset: Int, $filters: RaceHistoryFilters) {
            race_history_promise(limit: $limit, offset: $offset, filters: $filters) {
                ... on Problem {
                problem
                __typename
                }
                ... on RaceHistory {
                races {
                    id
                    conditions
                    distance
                    league
                    status
                    athletes
                    race_type
                    results {
                    token_id
                    time
                    __typename
                    }
                    track
                    prize_pool
                    starts_at
                    __typename
                }
                count
                __typename
                }
                __typename
            }
            }
            """,
        )['race_history_promise']

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
                        name
                        queueable_at
                        stats {
                        mission_tickets
                        experience {level, xp, remaining}
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

    def get_my_snails_for_ranked(
        self,
        owner,
        league,
        offset=0,
    ):
        return self.query(
            "getMySnailsForRanked",
            {
                "owner": owner,
                "limit": 20,
                "offset": offset,
                "league": league,
            },
            """
            query getMySnailsForRanked(
                $limit: Int
                $offset: Int
                $owner: String!
                $league: Int!
            ) {
                my_snails_ranked_promise(
                    limit: $limit
                    offset: $offset
                    owner: $owner
                    league: $league
                ) {
                    ... on Problem {
                    problem
                    __typename
                    }
                    ... on Snails {
                    snails {
                        id
                        adaptations
                        name
                        queueable_at
                        __typename
                    }
                    count
                    __typename
                    }
                    __typename
                }
            }
            """,
        )['my_snails_ranked_promise']

    def join_mission_races(self, snail_id: int, race_id: int, address: str, signature: str):
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

    def join_competitive_races(self, snail_id: int, race_id: int, address: str, signature: str):
        return self.query(
            "joinCompetitiveRaces",
            {
                "params": {
                    "token_id": snail_id,
                    "race_id": race_id,
                    "signature": signature,
                    "address": address,
                }
            },
            """
            mutation joinCompetitiveRaces($params: JoinRaceParams) {
                join_competitive_promise(params: $params) {
                    ... on Problem {
                    problem
                    __typename
                    }
                    ... on JoinRaceResponse {
                    status
                    message
                    signature
                    payload {
                        ... on CompetitivePayload {
                        race_id
                        token_id
                        address
                        entry_fee_wei
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
        )['join_competitive_promise']

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

    def marketplace_stats(
        self,
        market=1,
    ):
        return self.query(
            "marketplaceStats",
            {
                "market": market,
            },
            """
            query marketplaceStats($market: Int) {
            marketplace_stats_promise(market: $market) {
                ... on Problem {
                problem
                __typename
                }
                ... on MarketplaceStats {
                volume
                highs {
                    id
                    name
                    value
                }
                floors {
                    id
                    name
                    value
                    __typename
                }
                __typename
                }
                __typename
            }
            }
            """,
        )['marketplace_stats_promise']
