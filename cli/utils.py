from typing import TYPE_CHECKING

from snail.web3client import DECIMALS

if TYPE_CHECKING:
    from . import cli


def balance_balance(clis, limit, stop, callback, force=False):
    if limit <= stop:
        raise Exception('stop must be lower than limit')
    balances = []
    clis = list(clis)
    main_c = clis[0]
    wallets = [c.owner for c in clis]
    balances_d = main_c.client.web3.multicall_balances(wallets)
    for c in clis:
        # ignore wallets with 0 snails, no need for balance...
        if balances_d[c.owner][0] > 0:
            balances.append((balances_d[c.owner][3], c))
    balances.sort(key=lambda x: x[0], reverse=True)
    donor: tuple[float, 'cli.CLI'] = balances[0]
    poor: list[tuple[float, 'cli.CLI']] = [(x, limit - x, z) for (x, z) in balances if x < stop]
    total_transfer = sum(y for _, y, _ in poor)
    total_fees = 0
    if donor[0] - limit < total_transfer:
        callback(f'Donor has not enough balance: {total_transfer} required but only {donor[0]} available')
        return
    for p in poor:
        callback(f'{donor[1].name} to {p[2].name}: {p[1]}')
        if force:
            tx = donor[1].client.web3.transfer(p[2].owner, p[1])
            fee = tx['gasUsed'] * tx['effectiveGasPrice'] / DECIMALS
            total_fees += fee
            callback(f'> fee: {fee}')
    callback(f'> Total transfer: {total_transfer}')
    if total_fees:
        callback(f'> Total fees: {total_fees}')
