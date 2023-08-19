from enum import Enum
from typing import Generator
import requests
from time import time
from datetime import datetime

from . import gqlclient, gqltypes, web3client


class League(int, Enum):
    GOLD = 5
    PLATINUM = 6
    TOURNAMENT = 10


class ClientError(Exception):
    """Client raised error"""

    def __str__(self) -> str:
        return super().__str__()


class RequiresTransactionClientError(ClientError):
    """
    Client raised error when action requires transaction

    >>> e = RequiresTransactionClientError('requires_transaction')
    >>> str(e)
    'requires_transaction'
    >>> e = RequiresTransactionClientError('requires_transaction', {'x': 1})
    >>> str(e)
    'requires_transaction (size: ?)'
    >>> e = RequiresTransactionClientError('requires_transaction', {'payload': {'size': 2}})
    >>> str(e)
    'requires_transaction (size: 2)'
    """

    def __str__(self) -> str:
        if len(self.args) > 1:
            size = self.args[1].get('payload', {}).get('size', '?')
            return f'{self.args[0]} (size: {size})'
        return self.args[0]


class Client:
    def __init__(
        self,
        http_token=None,
        proxy=None,
        wallet=None,
        web3_account=None,
        web3_provider=None,
        web3_provider_class=None,
        web3_base_fee=25,
        web3_priority_fee=0,
        rate_limiter=None,
        gql_retry=None,
    ):
        self.gql = gqlclient.Client(http_token=http_token, proxy=proxy, rate_limiter=rate_limiter, retry=gql_retry)
        if wallet and web3_provider:
            self.web3 = web3client.Client(
                wallet,
                web3_provider,
                web3_account=web3_account,
                web3_provider_class=web3_provider_class,
                web3_base_fee=web3_base_fee,
            )
        self._gql_token = None
        self._priority_fee = web3_priority_fee

    @property
    def gql_token(self):
        if self._gql_token is None or self._gql_token[2]():
            self._gql_token = self.web3.auth_token()
        return self._gql_token[0]

    def _iterate_pages(self, method, key, klass=None, args=None, kwargs=None, max_calls=None):
        args = args or []
        kwargs = kwargs or {}
        c = 0
        calls = 0
        while True:
            kwargs['offset'] = c
            objs = method(*args, **kwargs)
            if not objs[key]:
                break
            total = objs.get('count')
            _r = map(klass, objs[key]) if klass else objs[key]
            yield from _r
            c += len(objs[key])
            if total is not None and c >= total:
                break
            calls += 1
            if max_calls and calls >= max_calls:
                break

    def iterate_all_genes_marketplace(self, filters={}) -> Generator[gqltypes.Snail, None, None]:
        yield from self._iterate_pages(
            self.gql.get_all_genes_marketplace, 'snails', klass=gqltypes.Snail, kwargs={'filters': filters}
        )

    def iterate_all_snails_marketplace(self, filters={}) -> Generator[gqltypes.Snail, None, None]:
        yield from self._iterate_pages(
            self.gql.get_all_snails_marketplace, 'snails', klass=gqltypes.Snail, kwargs={'filters': filters}
        )

    def iterate_all_snails(self, filters={}, more_stats=False) -> Generator[gqltypes.Snail, None, None]:
        yield from self._iterate_pages(
            self.gql.get_all_snails,
            'snails',
            klass=gqltypes.Snail,
            kwargs={'filters': filters, 'more_stats': more_stats},
        )

    def iterate_my_snails_for_missions(self, owner, adaptations=None) -> Generator[gqltypes.Snail, None, None]:
        yield from self._iterate_pages(
            self.gql.get_my_snails_for_missions,
            'snails',
            klass=gqltypes.Snail,
            args=[owner],
            kwargs={'adaptations': adaptations},
        )

    def iterate_my_snails_for_ranked(self, owner, league):
        yield from self._iterate_pages(
            self.gql.get_my_snails_for_ranked, 'snails', klass=gqltypes.Snail, args=[owner, league]
        )

    def iterate_my_snails(self, owner, **kwargs):
        yield from self._iterate_pages(
            self.gql.get_my_snails, 'snails', klass=gqltypes.Snail, args=[owner], kwargs=kwargs
        )

    def iterate_inventory(self, address, adaptations=None) -> Generator[gqltypes.InventoryItem, None, None]:
        yield from self._iterate_pages(
            self.gql.get_inventory,
            'items',
            klass=gqltypes.InventoryItem,
            args=[address],
        )

    def iterate_mission_races(self, filters={}, max_calls=None) -> Generator[gqltypes.Race, None, None]:
        yield from self._iterate_pages(
            self.gql.get_mission_races,
            'all',
            klass=gqltypes.Race,
            kwargs={'filters': filters},
            max_calls=max_calls,
        )

    def iterate_onboarding_races(self, own=False, filters={}) -> Generator[gqltypes.Race, None, None]:
        k = 'own' if own else 'all'
        yield from self._iterate_pages(
            self.gql.get_onboarding_races, k, klass=gqltypes.Race, kwargs={'filters': filters}
        )

    def iterate_finished_races(self, filters={}, own=False, max_calls=None) -> Generator[gqltypes.Race, None, None]:
        k = 'own' if own else 'all'
        yield from self._iterate_pages(
            self.gql.get_finished_races,
            k,
            klass=gqltypes.Race,
            kwargs={'filters': filters, 'own': own},
            max_calls=max_calls,
        )

    def iterate_race_history(self, filters={}) -> Generator[gqltypes.Race, None, None]:
        yield from self._iterate_pages(
            self.gql.get_race_history, 'races', klass=gqltypes.Race, kwargs={'filters': filters}
        )

    def rejoin_mission_races(self, gql_payload, **kwargs):
        return self.web3.join_daily_mission(
            (
                gql_payload['payload']['race_id'],
                gql_payload['payload']['token_id'],
                gql_payload['payload']['address'],
            ),
            gql_payload['payload']['size'],
            [
                (x['race_id'], x['race_type'], x['owners'], list(map(int, x['rewards_wei'])))
                for x in gql_payload['payload']['completed_races']
            ],
            gql_payload['payload']['timeout'],
            gql_payload['payload']['salt'],
            gql_payload['signature'],
            priority_fee=self._priority_fee,
            **kwargs,
        )

    def join_mission_races(self, snail_id: int, race_id: int, allow_last_spot=False):
        """join mission race - signature is generated by `sign_race_join`"""
        signature = self.web3.sign_race_join(snail_id, race_id)
        r = self.gql.join_mission_races(snail_id, race_id, self.web3.wallet, signature)
        if r.get('status') == 0:
            return r, None
        elif r.get('status') == 1:
            if allow_last_spot:
                return r, self.rejoin_mission_races(r)
            else:
                raise RequiresTransactionClientError('requires_transaction', r)
        else:
            raise ClientError('unknown status', r)

    def join_competitive_races(self, snail_id: int, race_id: int, address: str):
        """join mission race - signature is generated by `sign_race_join`"""
        signature = self.web3.sign_race_join(address, snail_id, race_id)
        r = self.gql.join_competitive_races(snail_id, race_id, address, signature)
        if r.get('status') != 1:
            raise ClientError('unknown status', r)

        m = [
            (x['race_id'], x['race_type'], x['owners'], list(map(int, x['rewards_wei'])))
            for x in r['payload']['completed_races']
        ]
        return r, self.web3.join_competitive_race(
            (
                r['payload']['race_id'],
                r['payload']['token_id'],
                r['payload']['address'],
                int(r['payload']['entry_fee_wei']),
                r['payload']['size'],
            ),
            m[0],
            r['payload']['timeout'],
            r['payload']['salt'],
            r['signature'],
        )

    def marketplace_stats(self, market=1):
        d = self.gql.marketplace_stats(market=market)
        r = {
            'volume': d['volume'],
            'prices': {},
        }
        for l in d['floors']:
            r['prices'][l['name']] = [l['value'], None]
        for l in d['highs']:
            r['prices'][l['name']][1] = l['value']
        return r

    def microwave_snails_preview(self, snails: list[int]):
        signature = self.web3.sign_burn(snails)
        return self.gql.query(
            "microwave_promise",
            {'params': {'token_ids': snails, 'signature': signature, 'address': self.web3.wallet, 'use_scroll': False}},
            """
            query microwave_promise($params: MicrowaveParams) {
            microwave_promise(params: $params) {
                ... on Problem {
                problem
                }
                ... on GenericResponse {
                status
                message
                signature
                payload {
                    ... on MicrowavePayload {
                    owner
                    order_id
                    size
                    token_ids
                    timeout
                    salt
                    fee_wei
                    fee_details
                    coef
                    }
                }
                }
            }
            }
            """,
            auth=self.gql_token,
        )['microwave_promise']

    def microwave_snails(self, snails: list[int]):
        r = self.microwave_snails_preview(snails)
        raise NotImplementedError('code it before you use it')

    def rename_account(self, new_name: str):
        return self.gql.query(
            "update_profile_promise",
            {
                'params': {
                    "address": self.web3.wallet,
                    "username": new_name,
                }
            },
            """
            mutation update_profile_promise($params: ProfileParams) {
                update_profile_promise(params: $params) {
                    ... on Problem {
                    problem
                    }
                    ... on Response {
                    success
                    }
                }
            }
            """,
            auth=self.gql_token,
        )['update_profile_promise']

    def claim_tomato(self, guild_id: int):
        return self.gql.query(
            "collect_primary_promise",
            {'guild_id': guild_id},
            """
            mutation collect_primary_promise($guild_id: Int!) {
            collect_primary_promise(guild_id: $guild_id) {
                ... on Problem {
                problem
                }
                ... on GenericResponse {
                status
                message
                signature
                }
            }
            }
            """,
            auth=self.gql_token,
        )['collect_primary_promise']

    def claim_building(self, guild_id: int, building: str):
        return self.gql.query(
            "claim_building_reward_promise",
            {
                'guild_id': guild_id,
                'building': building,
            },
            '''
            mutation claim_building_reward_promise(
                $guild_id: Int!
                $building: BuildingType
                ) {
                claim_building_reward_promise(guild_id: $guild_id, building: $building) {
                    ... on Problem {
                    problem
                    __typename
                    }
                    ... on BuildingRewards {
                    changes {
                        name
                        description
                        src
                        src_type
                        _from
                        _to
                        __typename
                    }
                    __typename
                    }
                    __typename
                }
            }
            ''',
            auth=self.gql_token,
        )['claim_building_reward_promise']

    def breed_snails(self, female_id, male_id):
        nonce = self.web3.incubate_nonce()
        data = self.gql.incubate(self.web3.wallet, female_id, male_id, nonce, gql_token=self.gql_token)
        payload = data['payload']
        return self.web3.incubate_snails(
            payload['item_id'],
            int(payload['base_fee_wei']),
            int(payload['market_price_wei']),
            self.web3.get_current_coefficent(raw=True),
            female_id,
            male_id,
            payload['timeout'],
            payload['salt'],
            data['signature'],
        )

    def apply_pressure(self, token_id, scroll_id):
        signature = self.web3.sign_pot(token_id, scroll_id)
        data = self.gql.apply_pressure(self.web3.wallet, token_id, scroll_id, signature, gql_token=self.gql_token)
        return data

    def slime_avax_candles(
        self,
        first=1000,
        period=3600,
        skip=0,
        days=7,
        token0="0x5a15bdcf9a3a8e799fa4381e666466a516f2d9c8",
        token1="0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7",
    ):
        startTime = int(time()) - (days * 3600 * 24)
        r = requests.post(
            'https://api.thegraph.com/subgraphs/name/traderjoe-xyz/dex-candles-v2',
            json={
                "query": "\n  query dexCandlesV2Query(\n    $token0: String!\n    $token1: String!\n    $period: Int!\n    $first: Int!\n    $skip: Int!\n    $startTime: Int!\n  ) {\n    candles(\n      first: $first\n      skip: $skip\n      orderBy: time\n      orderDirection: asc\n      where: {\n        token0: $token0\n        token1: $token1\n        period: $period\n        time_gt: $startTime\n      }\n    ) {\n      time\n      open\n      low\n      high\n      close\n    }\n  }\n",
                "variables": {
                    "first": first,
                    "period": period,
                    "skip": skip,
                    "startTime": startTime,
                    "token0": token0,
                    "token1": token1,
                },
                "operationName": "dexCandlesV2Query",
            },
        )
        r.raise_for_status()
        return r.json()['data']['candles']
