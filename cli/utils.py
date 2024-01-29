import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Union

from snail.gqlclient.types import Race, Snail
from snail.web3client import DECIMALS, web3_types

if TYPE_CHECKING:
    from . import cli

logger = logging.getLogger(__name__)


def tznow():
    return datetime.now(tz=timezone.utc)


def tx_fee(tx: web3_types.TxReceipt) -> float:
    return tx['gasUsed'] * tx['effectiveGasPrice'] / DECIMALS


def balance_balance(clis: 'list[cli.CLI]', limit, stop, callback, force=False):
    if limit <= stop:
        raise Exception('stop must be lower than limit')
    balances = []
    clis = list(clis)
    main_c = clis[0]
    wallets = [c.owner for c in clis]
    balances_d = main_c.client.web3.multicall_balances(wallets, _all=False, snails=True, avax=True)
    for c in clis:
        # ignore wallets with 0 snails, no need for balance...
        if balances_d[c.owner].snails > 0:
            balances.append((balances_d[c.owner].avax, c))
    if not balances:
        callback('No wallets in need')
        return False
    balances.sort(key=lambda x: x[0], reverse=True)
    donor: tuple[float, 'cli.CLI'] = balances[0]
    poor: list[tuple[float, 'cli.CLI']] = [(x, limit - x, z) for (x, z) in balances if x < stop]
    total_transfer = sum(y for _, y, _ in poor)
    total_fees = 0
    if (donor[0] - limit) < total_transfer:
        callback(f'Donor has not enough balance: {total_transfer} required but only {donor[0]} available')
        return False
    for p in poor:
        callback(f'{donor[1].name} to {p[2].name}: {p[1]}')
        if force:
            tx = donor[1].client.web3.transfer(p[2].owner, p[1])
            fee = tx_fee(tx)
            total_fees += fee
            callback(f'> fee: {fee}')
    callback(f'> Total transfer: {total_transfer}')
    if total_fees:
        callback(f'> Total fees: {total_fees}')
    return True


class CachedSnailHistory:
    def __init__(self, cli: 'cli.CLI'):
        self.cli = cli
        self._cache = {}

    @staticmethod
    def race_stats(snail_id, race):
        for p, i in enumerate(race.results):
            if i['token_id'] == snail_id:
                break
        else:
            logger.error('snail not found, NOT POSSIBLE')
            return None, None, None
        time_on_first = race.results[0]['time'] * 100 / race.results[p]['time']
        time_on_third = race.results[2]['time'] * 100 / race.results[p]['time']
        p += 1
        return time_on_first, time_on_third, p

    def get(self, snail_id: Union[int, Snail], limit=None):
        """
        Return snail race history plus a stats summary
        """
        if isinstance(snail_id, Snail):
            snail_id = snail_id.id
        # FIXME: make this prettier with a TTLed lru_cache
        key = (snail_id, limit)
        data, last_update = self._cache.get(key, (None, 0))
        _now = time.time()
        # re-fetch only once per 30min
        # TODO: make configurable? update only once and use race notifications to keep it up to date?
        if _now - last_update < 1800:
            return data

        races = []
        stats = defaultdict(lambda: [0, 0, 0, 0])
        total = 0

        for race in self.cli.client.iterate_race_history(filters={'token_id': snail_id, 'category': 3}):
            time_on_first, time_on_third, p = self.race_stats(snail_id, race)
            if time_on_first is None:
                continue
            if p < 4:
                stats[race.distance][p - 1] += 1
            stats[race.distance][3] += 1
            races.append((race, p, time_on_first, time_on_third))
            total += 1
            if limit and total >= limit:
                break

        data = (races, stats)
        self._cache[(snail_id, limit)] = (data, _now)
        return self._cache[key][0]

    def update(self, snail_id: Union[int, Snail], race: Race, limit=None):
        if isinstance(snail_id, Snail):
            snail_id = snail_id.id

        key = (snail_id, limit)
        data, last_update = self._cache.get(key, (None, 0))
        _now = time.time()
        if _now - last_update >= 1800:
            # do not update anything as cache already expired
            return False

        time_on_first, time_on_third, p = self.race_stats(snail_id, race)
        if time_on_first is None:
            return False

        races, stats = data
        if p < 4:
            stats[race.distance][p - 1] += 1
        stats[race.distance][3] += 1
        races.append((race, p, time_on_first, time_on_third))
        return True
