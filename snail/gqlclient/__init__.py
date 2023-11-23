import time
from typing import List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .errors import APIError
from .helper import GQL, GQLUnion


class Client(requests.Session):
    def __init__(
        self,
        http_token=None,
        proxy=None,
        rate_limiter=None,
        retry=None,
        url='https://api.snailtrail.art/graphql/',
    ):
        """
        >>> Client(retry=3).rate_limiter
        >>>
        """
        super().__init__()
        self.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:103.0) Gecko/20100101 Firefox/103.0",
                "accept-language": "en-GB,en;q=0.5",
                "referer": "https://api.snailtrail.art/graphql/",
                "origin": "https://api.snailtrail.art",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "pragma": "no-cache",
                "cache-control": "no-cache",
                "te": "trailers",
            }
        )
        self.trust_env = False
        if http_token:
            self.headers.update({"authorization": f"Basic {http_token}"})
        if retry:
            retry_adapter = HTTPAdapter(
                max_retries=Retry(
                    total=retry,
                    backoff_factor=1,
                    status_forcelist=[502, 504],
                    allowed_methods=['POST'],
                    raise_on_status=False,
                )
            )
            self.mount('http://', retry_adapter)
            self.mount('https://', retry_adapter)
        if proxy:
            self.proxies = {
                "http": proxy,
                "https": proxy,
            }
            # ignore certificates, as either burp or mitmproxy are expected...
            self.verify = False
        self.rate_limiter = rate_limiter
        self._last_query = 0
        self.url = url

    def query(self, operation, variables, query, auth=None):
        if self.rate_limiter is not None:
            delta = time.time() - self._last_query - self.rate_limiter
            if delta < 0:
                time.sleep(self.rate_limiter)
        if auth:
            headers = {'auth': auth}
        else:
            headers = None
        r = self.post(
            self.url,
            headers=headers,
            json={
                'operationName': operation,
                'variables': variables,
                'query': query,
            },
        )
        self._last_query = time.time()
        r.raise_for_status()
        r = r.json()
        if 'errors' in r:
            raise APIError.make([[v.get('extensions', {'code': '-'})['code'], v['message']] for v in r['errors']])
        if r.get('data') is None:
            raise Exception(r)
        problems = [v['problem'] for v in r['data'].values() if v and 'problem' in v]
        if problems:
            raise APIError.make(problems)
        return r["data"]

    def get_all_genes_marketplace(self, offset=0, limit=24, filters={}):
        return GQL(
            'gene_market_promise',
            '''
                ... on Problem {
                    problem
                }
                ... on Snails {
                    snails {
                        id
                        adaptations
                        name
                        image
                        purity
                        gene_market {
                        price
                        item_id
                        on_sale
                        price_wei
                        }
                        stats {
                        experience {
                            level
                        }
                        }
                    }
                    count
                    }
            ''',
            {
                "filters": ('SnailFilters', filters),
                "offset": ('Int', offset),
                "limit": ('Int', limit),
            },
            'getAllSnail',
        ).execute(self)['gene_market_promise']

    def get_all_snails_marketplace(self, offset=0, limit=20, filters={}):
        return GQL(
            'marketplace_promise',
            '''
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
                        }
                        gender {
                        id
                        }
                        breeding {
                        breed_detail {
                            cycle_end
                            monthly_breed_available
                            breed_count_total
                        }
                        }
                    }
                    count
                    }
            ''',
            {
                "filters": ('SnailFilters', filters),
                "offset": ('Int', offset),
                "limit": ('Int', limit),
            },
            'getAllSnail',
        ).execute(self)['marketplace_promise']

    def get_all_snails(self, offset: int = 0, filters={}, more_stats=False):
        more_stats_query = (
            """
        more_stats(seasons: [1]) {
            id
            name
            data {
            id
            name
            data {
                id
                name
                data {
                ... on CounterStat {
                    name
                    count
                }
                ... on MeanStat {
                    name
                    count
                    min
                    mean
                    max
                    std
                }
                }
            }
            }
        }
        """
            if more_stats
            else ''
        )
        return GQL(
            'snails_promise',
            '''
            ... on Snails {
                    snails {
                        id
                        adaptations
                        name
                        gender {
                        id
                        can_change_at
                        }
                        new_born
                        genome
                        klass
                        family
                        work_boost
                        slime_boost
                        purity
                        breeding {
                        breed_detail {
                            cycle_end
                            monthly_breed_available
                            monthly_breed_limit
                            breed_count_total
                        }
                        }
                        stats {
                            elo
                            experience {level, xp, remaining}
                            mission_tickets
                            earned_token
                            earned_avax
                        }
                        %s
                    }
                    count
                    }
            '''
            % (more_stats_query,),
            {
                "filters": ('SnailFilters', filters),
                "offset": ('Int', offset),
            },
            'getAllSnail',
        ).execute(self)['snails_promise']

    def get_mission_races(self, offset=0, limit=20, filters={}):
        return GQL(
            'mission_races_promise',
            '''
            ... on Problem {
                    problem
            }
                    ... on Races {
                    all {
                        id
                        conditions
                        distance
                        athletes
                        track
                        participation
                    }
                    }
            ''',
            {
                "filters": ('RaceFilters', filters),
                "limit": ('Int', limit),
                "offset": ('Int', offset),
            },
            'getMissionRaces',
        ).execute(self)['mission_races_promise']

    def get_onboarding_races(self, offset=0, limit=20, filters={}):
        return GQL(
            'onboarding_races_promise',
            '''
            ... on Problem {
                    problem
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
                        schedules_at
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
                        schedules_at
                    }
                    }
            ''',
            {
                "filters": ('RaceFilters', filters),
                "limit": ('Int', limit),
                "offset": ('Int', offset),
            },
            'getOnboardingRaces',
        ).execute(self)['onboarding_races_promise']

    def get_finished_races(self, offset=0, limit=20, filters={}, own=False):
        return GQL(
            'finished_races_promise',
            '''
            ... on Problem {
                    problem
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
                        }
                        rewards {
                        final_distribution
                        }
                        track
                        starts_at
                        prize_pool
                    }
                    }
            '''
            % ('own' if own else 'all'),
            {
                "filters": ('RaceFilters', filters),
                "limit": ('Int', limit),
                "offset": ('Int', offset),
            },
            'getFinishedRaces',
        ).execute(self)['finished_races_promise']

    def get_race_history(self, offset=0, limit=20, filters={}):
        return GQL(
            'race_history_promise',
            '''
            ... on Problem {
                problem
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
                    rewards {
                    final_distribution
                    }
                    results {
                    token_id
                    time
                    }
                    track
                    prize_pool
                    starts_at
                }
                count
                }
            ''',
            {
                "filters": ('RaceHistoryFilters', filters),
                "limit": ('Int', limit),
                "offset": ('Int', offset),
            },
            'getRaceHistory',
        ).execute(self)['race_history_promise']

    def get_my_snails_for_missions(
        self,
        owner,
        offset=0,
        limit=20,
        adaptations=None,
    ):
        if adaptations is None:
            adaptations = [1, 1, 1]
        return GQL(
            'my_snails_mission_promise',
            '''... on Problem {
                    problem
                    }
                    ... on Snails {
                    snails {
                        id
                        adaptations
                        purity
                        name
                        queueable_at
                        stats {
                        mission_tickets
                        experience {level, xp, remaining}
                        }
                    }
                    count
                    }
            ''',
            {
                "owner": ('String!', owner),
                "limit": ('Int', limit),
                "offset": ('Int', offset),
                "adaptations": ('[Int]', adaptations),
            },
            'getMySnailsForMissions',
        ).execute(self)['my_snails_mission_promise']

    def get_my_snails_for_ranked(
        self,
        owner,
        league,
        limit=20,
        offset=0,
    ):
        return GQL(
            'my_snails_ranked_promise',
            '''... on Problem {
                    problem
                    }
                    ... on Snails {
                    snails {
                        id
                        adaptations
                        name
                        queueable_at
                    }
                    count
                    }
            ''',
            {
                "owner": ('String!', owner),
                "limit": ('Int', limit),
                "offset": ('Int', offset),
                "league": ('Int!', league),
            },
            'getMySnailsForRanked',
        ).execute(self)['my_snails_ranked_promise']

    def get_my_snails(
        self,
        owner,
        limit=20,
        offset=0,
        filters=None,
    ):
        return GQL(
            'my_snails_promise',
            '''... on Problem {
                problem
                }
                ... on Snails {
                snails {
                    id
                    name
                    purity
                    gender {
                        id
                        can_change_at
                    }
                    new_born
                    adaptations
                    genome
                    klass
                    family
                    work_boost
                    slime_boost
                    purity
                    breeding {
                        breed_detail {
                            cycle_end
                            monthly_breed_available
                            monthly_breed_limit
                            breed_count_total
                        }
                    }
                    stats {
                        elo
                        experience {level, xp, remaining}
                        mission_tickets
                        earned_token
                        earned_avax
                    }
                }
                count
                }''',
            {
                "filters": ('SnailFilters', filters),
                "limit": ('Int', limit),
                "offset": ('Int', offset),
                "owner": ('String!', owner),
            },
            'my_snails_promise',
        ).execute(self)['my_snails_promise']

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
                            race_type
                            owners
                            rewards_wei
                            results
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
                            race_type
                            owners
                            rewards_wei
                            results
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
        return GQL(
            'marketplace_stats_promise',
            """
            ... on Problem {
            problem
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
            }
            }
            """,
            {
                "market": ('Int', market),
            },
            operation_name="marketplaceStats",
        ).execute(self)['marketplace_stats_promise']

    def tournament(self, address):
        return self.query(
            "tournament_promise",
            {
                "address": address,
            },
            '''
            query tournament_promise($tournament_id: Int, $address: String) {
                tournament_promise(tournament_id: $tournament_id, address: $address) {
                    ... on Problem {
                    problem
                    }
                    ... on Tournament {
                    id
                    current_week
                    name
                    current_day
                    guild_count
                    weeks {
                        starts_at
                        team_select_ends_at
                        ends_at
                        week
                        days {
                        races {
                            id
                        }
                        family
                        race_date
                        order
                        result {
                            entries {
                            snail {
                                id
                                name
                                family
                                adaptations
                                purity
                                klass
                                gender {id}
                                stats {
                                    experience {level, xp, remaining}
                                }
                            }
                            guild {
                                name
                                id
                            }
                            points
                            timer
                            order
                            race_id
                            }
                        }
                        }
                        conditions
                        distance
                        guild_count
                    }
                    prize_pool {
                        id
                        name
                        symbol
                        amount
                    }
                    scheduled_at
                    }
                }
            }
            ''',
        )['tournament_promise']

    def profile(self, addresses: list[str]):
        gqls = GQLUnion(
            *[
                GQL(
                    'profile_promise',
                    '''
            ... on Profile {
                address
                username
                guild {
                    id
                    name
                }
            }
            ''',
                    {'address': ('String!', address)},
                    'profile_promise',
                )
                for address in addresses
            ],
            prefix='profile',
        )

        return gqls.execute(self)

    def guild_details(self, guild_id, member=None):
        if member:
            membership_query = (
                '''
            membership(address: "%s") {
                rank
            }
            '''
                % member
            )
            reward_query = (
                '''
            reward(address: "%s") {
                has_reward
                next_reward_at
                amount
            }
            '''
                % member
            )
        else:
            reward_query = membership_query = ''

        query = '''
        query research_center_reward($guild_id: Int!) {
            guild_promise(guild_id: $guild_id) {
                ... on Problem {
                    problem
                }
                ... on Guild {
                    %s
                    name
                    treasury {
                        resources {
                            id
                            symbol

                            amount
                        }
                    }
                    research {
                        buildings {
                            id
                            name
                            type
                            level
                            %s
                        }
                        stats {
                            worker_count
                            tomato_ph
                        }
                    }
                    stats {
                        snail_count
                        member_count
                        level
                    }
                }
            }
        }
        ''' % (
            membership_query,
            reward_query,
        )
        return self.query(
            "research_center_reward",
            {
                "guild_id": guild_id,
            },
            query,
        )['guild_promise']

    def guild_roster(self, guild_id):
        query = '''
        query guildRoster($guild_id: Int!) {
            guild_promise(guild_id: $guild_id) {
                ... on Problem {
                problem
                }
                ... on Guild {
                roster {
                    members {
                    count
                    users {
                        id
                        profile {
                        username
                        address
                        }
                        rank
                        reputation
                        status
                        stats {
                        votes_pos
                        votes_pob
                        workers
                        ph_primary
                        total_primary
                        }
                    }
                    }
                }
                }
            }
        }
        '''
        return self.query(
            "guildRoster",
            {
                "guild_id": guild_id,
            },
            query,
        )['guild_promise']

    def tournament_guild_stats(self, member, tournament_id=None):
        return self.query(
            "tournamentMyGuildLeaderboard",
            {
                "tournament_id": tournament_id,
                "address": member,
            },
            '''
            query tournamentMyGuildLeaderboard($tournament_id: Int, $address: String) {
                tournament_promise(tournament_id: $tournament_id, address: $address) {
                    ... on Tournament {
                    id
                    leaderboard(cursor: 0) {
                        my_guild {
                        order
                        points
                        }
                    }
                    }
                }
            }
            ''',
        )['tournament_promise']

    def get_inventory(
        self,
        address,
        limit=24,
        offset=0,
    ):
        return self.query(
            "inventory_promise",
            {
                "address": address,
                "filters": {"flag": "ALL"},
                "limit": limit,
                "offset": offset,
            },
            """
            query inventory_promise(
            $address: String!
            $limit: Int
            $offset: Int
            $filters: InventoryFilters
            ) {
            inventory_promise(
                address: $address
                limit: $limit
                offset: $offset
                filters: $filters
            ) {
                ... on Problem {
                problem
                }
                ... on Inventory {
                count
                items {
                    id
                    type_id
                    name
                    description
                    count
                    expires_at
                    coef
                }
                }
            }
            }
            """,
        )['inventory_promise']

    def incubate(
        self,
        address,
        female_id,
        male_id,
        nonce,
        use_scroll=False,
        gql_token=None,
    ):
        return self.query(
            "incubate_promise",
            {
                "params": {
                    "fid": female_id,
                    "mid": male_id,
                    "item_id": 0,
                    "use_scroll": use_scroll,
                    "market_price_wei": "0",
                    "nonce": nonce,
                    "owner": address,
                }
            },
            """
            query incubate_promise($params: IncubateParams) {
                incubate_promise(params: $params) {
                    ... on Problem {
                    problem
                    __typename
                    }
                    ... on Incubate {
                    payload {
                        owner
                        item_id
                        base_fee_wei
                        market_price_wei
                        nonce
                        fid
                        mid
                        timeout
                        salt
                        __typename
                    }
                    signature
                    __typename
                    }
                    __typename
                }
            }
            """,
            auth=gql_token,
        )['incubate_promise']

    def apply_pressure(
        self,
        address,
        token_id,
        scroll_id,
        signature,
        gql_token=None,
    ):
        return self.query(
            "apply_pressure_promise",
            {
                "params": {
                    "address": address,
                    "items": [{"id": scroll_id, "count": 1}],
                    "token_id": token_id,
                    "signature": signature,
                }
            },
            """
            mutation apply_pressure_promise($params: PressureParams) {
                apply_pressure_promise(params: $params) {
                    ... on Problem {
                    problem
                    }
                    ... on Pressure {
                    snail {
                        id
                    }
                    items {
                        id
                        type_id
                        name
                        description
                        count
                        expires_at
                        coef
                    }
                    changes {
                        name
                        description
                        _from
                        _to
                        src
                        src_type
                    }
                    }
                }
            }
            """,
            auth=gql_token,
        )['apply_pressure_promise']

    def stake_snails(self, guild_id: int, snail_ids: List[int], gql_token=None):
        return self.query(
            "send_workers_promise",
            {
                "guild_id": guild_id,
                "token_ids": snail_ids,
            },
            """
            mutation send_workers_promise($guild_id: Int!, $token_ids: [Int]) {
                send_workers_promise(guild_id: $guild_id, token_ids: $token_ids) {
                    ... on Problem {
                    problem
                    __typename
                    }
                    ... on GenericResponse {
                    status
                    message
                    signature
                    payload {
                        ... on WorkerPayload {
                        order_id
                        token_ids
                        owner
                        timeout
                        salt
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
            auth=gql_token,
        )['send_workers_promise']

    def guild_research(self, guild_ids: list[int]):
        query = ''
        vars = {}

        for i, guild in enumerate(guild_ids):
            query += '''
            guild_promise%d: guild_promise(guild_id: $guild%d) {
                ... on Guild {
                    research {
                        buildings {
                            type
                            level
                        }
                    }
                }
            }
            ''' % (
                i,
                i,
            )
            vars['guild%d' % i] = guild

        return self.query(
            "research_center_reward",
            vars,
            """
            query research_center_reward(%s) {
            %s
            }
            """
            % (
                ','.join([f'${v}: Int!' for v in vars]),
                query,
            ),
        )

    def guild_messages(
        self,
        guild_id,
        cursor=0,
    ):
        return self.query(
            "guildTreasuryLedger",
            {
                "guild_id": guild_id,
                "cursor": cursor,
            },
            """
            query guildTreasuryLedger($guild_id: Int!, $cursor: Int!) {
                guild_promise(guild_id: $guild_id) {
                    ... on Problem {
                        problem
                    }
                    ... on Guild {
                    treasury {
                        ledger(cursor: $cursor) {
                        total_count
                        page_info {
                            has_next_page
                            end_cursor
                        }
                        messages {
                            id
                            cursor
                            content
                            created_at
                            topic
                            subjects {
                                type
                                value
                                hidden
                            }
                        }
                        }
                    }
                    }
                }
                }
            """,
        )['guild_promise']
