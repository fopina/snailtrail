import base64
import logging
from datetime import datetime
from functools import cached_property
from typing import Any, Optional, Union

from Crypto.Hash import keccak
from eth_account.messages import encode_defunct
from web3 import Account, Web3, constants, exceptions  # noqa - for others to import from here
from web3.middleware import geth_poa_middleware

from scommon.decorators import cached_property_with_ttl

from . import contracts

DECIMALS = 1000000000000000000
GWEI_DECIMALS = 1000000000
BOTTOM_BASE_FEE = 25 * GWEI_DECIMALS

logger = logging.getLogger(__name__)


class Web3Error(Exception):
    """For expected web3 errors"""

    @classmethod
    def make(cls, error):
        if 'insufficient funds' in str(error) and error.args[0]['code'] == -32000:
            return InsufficientFundsWeb3Error(error.args[0]['message'])
        if 'replacement transaction underpriced' in str(error) and error.args[0]['code'] == -32000:
            return TransactionUnderpricedWeb3Error(error.args[0]['message'])
        return cls(error)


class InsufficientFundsWeb3Error(Web3Error):
    """Not enough balance to complete transaction"""


class TransactionUnderpricedWeb3Error(Web3Error):
    """Replacement transaction underpriced"""


class Client:
    def __init__(
        self,
        wallet: str,
        web3_provider: str,
        web3_account: Optional[Account] = None,
        web3_provider_class: Any = None,
        max_fee: Optional[float] = None,
        max_priority_fee: Optional[float] = None,
    ):
        if web3_provider_class is None:
            web3_provider_class = Web3.HTTPProvider
        self.web3 = Web3(web3_provider_class(web3_provider))
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.account: Account = web3_account
        self.wallet = wallet
        self._max_fee = max_fee
        self._max_priority_fee = max_priority_fee

    def _contract(self, module):
        return self.web3.eth.contract(
            address=self.web3.toChecksumAddress(module.CONTRACT),
            abi=module.ABI,
        )

    @cached_property
    def chain_id(self):
        return self.web3.eth.chain_id

    @cached_property
    def preferences_contract(self):
        return self._contract(contracts.snail_preference)

    @cached_property
    def race_contract(self):
        return self._contract(contracts.snail_race)

    @cached_property
    def mega_race_contract(self):
        return self._contract(contracts.snail_mega_race)

    @cached_property
    def slime_contract(self):
        return self._contract(contracts.snail_token)

    @cached_property
    def wavax_contract(self):
        return self._contract(contracts.wavax)

    @cached_property
    def snailnft_contract(self):
        return self._contract(contracts.snail_nft)

    @cached_property
    def snaillab_contract(self):
        return self._contract(contracts.snail_lab)

    @cached_property
    def incubator_contract(self):
        return self._contract(contracts.snail_incubator)

    @cached_property
    def snailguild_contract(self):
        return self._contract(contracts.snail_guild)

    @cached_property
    def bulk_transfer_contract(self):
        return self._contract(contracts.bulk_transfer)

    @cached_property
    def multicall_contract(self):
        return self._contract(contracts.multicall)

    @cached_property
    def traderjoe_contract(self):
        return self._contract(contracts.traderjoe)

    @cached_property
    def marketplace_contract(self):
        return self._contract(contracts.snail_gene_marketplace)

    def _bss(
        self,
        function_call: Any,
        wait_for_transaction_receipt: Union[bool, float] = None,
        estimate_only=False,
        priority_fee=None,
    ):
        """build tx, sign it and send it"""
        nonce = self.web3.eth.getTransactionCount(self.wallet)
        # expected value in nAVAX
        gas_price = self.gas_price
        if priority_fee is None:
            priority_fee = self._max_priority_fee or 0
        if self._max_fee is None:
            max_fee = int(BOTTOM_BASE_FEE * (100 + priority_fee) / 100)
        else:
            max_fee = int(self._max_fee * GWEI_DECIMALS)

        mf = int(gas_price * (100 + priority_fee) / 100)
        if mf > max_fee:
            logger.error('Required max fee of %d exceeds allowed max fee of %d', mf, max_fee)
            mf = max_fee
        # put everything as priority fee - network will use for base fee if required!
        mpf = mf - BOTTOM_BASE_FEE
        if isinstance(function_call, dict):
            # raw transaction
            tx = {k: v for k, v in function_call.items()}
            tx.update(
                {
                    'nonce': nonce,
                    'from': self.wallet,
                    'gas': 21000,
                    'maxFeePerGas': mf,
                    'maxPriorityFeePerGas': mpf,
                    'chainId': self.chain_id,
                }
            )
        else:
            # function call
            tx = function_call.buildTransaction({'nonce': nonce, 'from': self.wallet})
            tx.update(
                {
                    'maxFeePerGas': mf,
                    'maxPriorityFeePerGas': mpf,
                }
            )
        if estimate_only:
            gas = self.web3.eth.estimate_gas(tx)
            return {'gasUsed': gas, 'effectiveGasPrice': self.gas_price}
        signed_txn = self.account.sign_transaction(tx)
        try:
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        except ValueError as e:
            raise Web3Error.make(e)

        if wait_for_transaction_receipt is False:
            return tx_hash
        return self.web3.eth.wait_for_transaction_receipt(
            tx_hash,
            # if wait_for_transaction_receipt is None, use 120
            timeout=wait_for_transaction_receipt or 120,
        )

    def set_snail_name(self, snail_id: int, new_name: str, wait_for_transaction_receipt: Union[bool, float] = None):
        return self._bss(
            self.preferences_contract.functions.setSnailName(snail_id, new_name),
            wait_for_transaction_receipt=wait_for_transaction_receipt,
        )

    def join_daily_mission(
        self,
        race_info: tuple[int, int, str],
        result_size: int,
        results: list[tuple[int, list[str]]],
        timeout: int,
        salt: int,
        signature: str,
        wait_for_transaction_receipt: Union[bool, float] = None,
        **kwargs,
    ):
        return self._bss(
            self.race_contract.functions.joinDailyMission(
                race_info,
                result_size,
                results,
                timeout,
                salt,
                signature,
            ),
            wait_for_transaction_receipt=wait_for_transaction_receipt,
            **kwargs,
        )

    def join_competitive_race(
        self,
        race_info: tuple[int, int, str, int, int],
        results: tuple[tuple[int, list[str]]],
        timeout: int,
        salt: int,
        signature: str,
        wait_for_transaction_receipt: Union[bool, float] = None,
        **kwargs,
    ):
        return self._bss(
            self.race_contract.functions.joinCompetitiveRace(
                race_info,
                results,
                timeout,
                salt,
                signature,
            ),
            wait_for_transaction_receipt=wait_for_transaction_receipt,
            **kwargs,
        )

    def claim_rewards(self, wait_for_transaction_receipt: Union[bool, float] = None, **kwargs):
        return self._bss(
            self.race_contract.functions.claimRewards(),
            wait_for_transaction_receipt=wait_for_transaction_receipt,
            **kwargs,
        )

    def claimable_slime(self):
        return self.race_contract.functions.claimableRewards().call({'from': self.wallet}) / DECIMALS

    def balance_of_slime(self, raw=False):
        x = self.slime_contract.functions.balanceOf(self.wallet).call({'from': self.wallet})
        if raw:
            return x
        return x / DECIMALS

    def claimable_wavax(self):
        return self.mega_race_contract.functions.claimableRewards().call({'from': self.wallet}) / DECIMALS

    def balance_of_wavax(self, raw=False):
        x = self.wavax_contract.functions.balanceOf(self.wallet).call({'from': self.wallet})
        if raw:
            return x
        return x / DECIMALS

    def balance_of_snails(self):
        return self.snailnft_contract.functions.balanceOf(self.wallet).call({'from': self.wallet})

    def multicall_balances(self, wallets: list[str]):
        """
        return multiple balances in one single web3 (multi)call:
        snails, wavax, slime, avax, claimable slime, claimable wavax
        """
        calls = []
        contracts = [self.snailnft_contract, self.wavax_contract, self.slime_contract]
        for w in wallets:
            for contract in contracts:
                calls.append(
                    (contract.address, contract.encodeABI('balanceOf', args=(w,))),
                )
            calls.append(
                (self.multicall_contract.address, self.multicall_contract.encodeABI('getEthBalance', args=(w,)))
            )
            calls.append((self.race_contract.address, self.race_contract.encodeABI('dailyRewardTracker', args=(w,))))
            calls.append(
                (self.mega_race_contract.address, self.mega_race_contract.encodeABI('rewardTracker', args=(w,)))
            )
        x = self.multicall_contract.functions.aggregate(calls).call({'from': self.wallet})
        w_ind = 0
        results = {}
        for y in range(0, len(x[1]), 6):
            results[wallets[w_ind]] = [
                # balanceOf for all 3 contracts
                self.web3.to_int(x[1][y]),
                self.web3.to_int(x[1][y + 1]) / DECIMALS,
                self.web3.to_int(x[1][y + 2]) / DECIMALS,
                # avax balance
                self.web3.to_int(x[1][y + 3]) / DECIMALS,
                # claimable rewards: slime
                self.web3.to_int(x[1][y + 4]) / DECIMALS,
                # claimable rewards: wavax
                self.web3.to_int(x[1][y + 5]) / DECIMALS,
            ]
            w_ind += 1
        return results

    def get_balance(self):
        return self.web3.eth.get_balance(self.wallet) / DECIMALS

    def get_current_coefficent(self, raw=False):
        r = self.incubator_contract.functions.getCurrentCoefficent().call({'from': self.wallet})
        if raw:
            return r
        return r / DECIMALS

    def sign_race_join(self, snail_id: int, race_id: int, owner: str = None):
        """Generate and sign payload to join a daily mission
        >>> a = Account.from_key('badbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbad0')
        >>> o = Client(wallet='0xbadbadbadbadbadbadbadbadbadbadbadbadbad0', web3_account=a, web3_provider='x')
        >>> o.sign_race_join(1816, 44660)
        '0x66287e0465f644bad50cab950218ee6386f0e19bde3be4fad34f473b33f806c0177718d8ddb4ffe0149e3098b20abc1a382c6c77d7f4b7f61f6f4fa33f8f47641c'
        """
        return self._sign_values(snail_id, race_id)

    def _hash_values(self, *values, owner: str = None):
        """
        >>> a = Account.from_key('badbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbad0')
        >>> o = Client(wallet='0xbadbadbadbadbadbadbadbadbadbadbadbadbad0', web3_account=a, web3_provider='x')
        >>> o._hash_values(17802,[9183],[1],"pressure", owner="0xbd8EFe62b5D14aa4f81Fd02fc7b0920885B31A17").hex()
        '1f2b1dfe97454bf32dd9dd3eb5a18134b9d301b220454c1c3b2968aa295a5817'
        """
        if owner is None:
            owner = self.wallet

        keccak_hash = keccak.new(digest_bits=256)

        def _add_value(value):
            if isinstance(value, int):
                keccak_hash.update(value.to_bytes(32, "big"))
            elif isinstance(value, str):
                keccak_hash.update(value.encode())
            elif isinstance(value, bytes):
                keccak_hash.update(value)
            elif isinstance(value, (list, tuple)):
                for value_i in value:
                    _add_value(value_i)
            else:
                raise NotImplementedError(type(value), 'not supported')

        _add_value(values)
        keccak_hash.update(bytes.fromhex(owner.replace("0x", "")))

        return keccak_hash.digest()

    def _sign_values(self, *values, owner: str = None):
        """Hash and sign typed values
        >>> a = Account.from_key('badbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbad0')
        >>> o = Client(wallet='0xbadbadbadbadbadbadbadbadbadbadbadbadbad0', web3_account=a, web3_provider='x')
        >>> o._sign_values(1816)
        '0xd608d3c0adde23a7ddeb94e3f15f742887249b87cae9e6c98c95422e72e9945410c5029efd815efc0d95c80dd05b119b8ac2b82b19b14e51580a9385356ed6881c'
        """

        sign_payload = self._hash_values(*values, owner=owner)
        message = encode_defunct(sign_payload)

        return self.account.sign_message(message).signature.hex()

    def sign_burn(self, snails: list[int], owner: str = None):
        """Generate and sign payload to join a daily mission
        >>> a = Account.from_key('badbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbad0')
        >>> o = Client(wallet='0xbadbadbadbadbadbadbadbadbadbadbadbadbad0', web3_account=a, web3_provider='x')
        >>> o.sign_burn([1816])
        '0xb2e129e5e5b38243486394aa50247101c6c078f177b3362d672bc1739687e92a4de54ef9d522a6567e6e54b93ddd44a8ccf4463cab0ab053102f675171f793691b'
        """
        return self._sign_values(*snails, b'microwave', owner=owner)

    def sign_pot(self, snail_id: int, scroll_id: int, owner: str = None):
        """Generate and sign payload to join a daily mission
        >>> a = Account.from_key('badbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbad0')
        >>> o = Client(wallet='0xbadbadbadbadbadbadbadbadbadbadbadbadbad0', web3_account=a, web3_provider='x')
        >>> o.sign_pot(17802, 9183)
        '0xf48fb9377cd38324e2073015a03e6c7e11b28155f5153544a8dc3066b65ba49f4bc8a1154f0af94feb913b0cafecbae464f3c8f281a7cdbafbfd658d8e7b4b0c1c'
        """
        return self._sign_values(snail_id, [scroll_id], [1], b'pressure', owner=owner)

    def auth_token(self, timestamp=None, owner=None) -> tuple[str, int]:
        """Generate an auth token for GraphQL API
        >>> a = Account.from_key('badbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbad0')
        >>> o = Client(wallet='0xbadbadbadbadbadbadbadbadbadbadbadbadbad0', web3_account=a, web3_provider='x')
        >>> o.auth_token(timestamp=1684841032263)[:2]
        ('MHhlMGM4ZTE3ZjJjYTA4MjExOWU2N2UzYjFmNThkODkwYTY1NWY5NDVmMzAxNmQ4Nzc5YWQ3NWY5N2QwOTMzNWFjMWVmMzBjNjUwYmQ3ODI1ZGY2MjNmNDczYjk2YjM0YWM2MWJjNzExNzYzN2NmNjU0MWM2MTBhNTRiYzIyNWU4MTFiOjB4YmFkYmFkYmFkYmFkYmFkYmFkYmFkYmFkYmFkYmFkYmFkYmFkYmFkMDoxNjg0ODQxMDMyMjYz', 1685445832263)
        """
        if owner is None:
            owner = self.wallet
        if timestamp is None:
            timestamp = int(datetime.utcnow().timestamp() * 1000)
        signed_payload = self._sign_values(timestamp, b'snailtrail', owner=owner)
        expires_on = timestamp + 604800000
        return (
            base64.b64encode(f'{signed_payload}:{owner}:{timestamp}'.encode()).decode(),
            expires_on,
            # is_expired function, some buffer (1h) to renew
            lambda: int(datetime.utcnow().timestamp() * 1000) > (expires_on - 3600000),
        )

    def transfer(self, to: str, amount: float, wait_for_transaction_receipt: Union[bool, float] = None, **kwargs):
        transaction = {
            'to': to,
            'value': int(amount * DECIMALS),
        }
        return self._bss(
            transaction,
            wait_for_transaction_receipt=wait_for_transaction_receipt,
            **kwargs,
        )

    def transfer_slime(self, to: str, amount: int, wait_for_transaction_receipt: Union[bool, float] = None, **kwargs):
        return self._bss(
            self.slime_contract.functions.transfer(to, amount),
            wait_for_transaction_receipt=wait_for_transaction_receipt,
            **kwargs,
        )

    def transfer_snail(
        self, _from: str, to: str, token_id: int, wait_for_transaction_receipt: Union[bool, float] = None, **kwargs
    ):
        return self._bss(
            self.snailnft_contract.functions.transferFrom(_from, to, token_id),
            wait_for_transaction_receipt=wait_for_transaction_receipt,
            **kwargs,
        )

    def unstake_snails(
        self,
        snail_ids: list[int],
        wait_for_transaction_receipt: Union[bool, float] = None,
        **kwargs,
    ):
        return self._bss(
            self.snailguild_contract.functions.unstakeSnails(snail_ids),
            wait_for_transaction_receipt=wait_for_transaction_receipt,
            **kwargs,
        )

    def approve_all_snails_for_stake(
        self, remove=False, wait_for_transaction_receipt: Union[bool, float] = None, **kwargs
    ):
        current = self.snailnft_contract.functions.isApprovedForAll(self.wallet, self.snailguild_contract.address).call(
            {'from': self.wallet}
        )
        target = not remove
        if current is target:
            return
        return self._bss(
            self.snailnft_contract.functions.setApprovalForAll(self.snailguild_contract.address, target),
            wait_for_transaction_receipt=wait_for_transaction_receipt,
            **kwargs,
        )

    def approve_all_snails_for_lab(
        self, remove=False, wait_for_transaction_receipt: Union[bool, float] = None, **kwargs
    ):
        current = self.snailnft_contract.functions.isApprovedForAll(self.wallet, self.snaillab_contract.address).call(
            {'from': self.wallet}
        )
        target = not remove
        if current is target:
            return
        return self._bss(
            self.snailnft_contract.functions.setApprovalForAll(self.snaillab_contract.address, target),
            wait_for_transaction_receipt=wait_for_transaction_receipt,
            **kwargs,
        )

    def stake_snails(
        self,
        order_id: int,
        snail_ids: list[int],
        timeout: int,
        salt: int,
        signature: str,
        wait_for_transaction_receipt: Union[bool, float] = None,
        **kwargs,
    ):
        return self._bss(
            self.snailguild_contract.functions.stakeSnails(
                (
                    order_id,
                    self.wallet,
                    snail_ids,
                    timeout,
                    salt,
                ),
                signature,
            ),
            wait_for_transaction_receipt=wait_for_transaction_receipt,
            **kwargs,
        )

    def approve_all_snails_for_bulk(
        self, remove=False, wait_for_transaction_receipt: Union[bool, float] = None, **kwargs
    ):
        current = self.snailnft_contract.functions.isApprovedForAll(
            self.wallet, self.bulk_transfer_contract.address
        ).call({'from': self.wallet})
        target = not remove
        if current is target:
            return
        return self._bss(
            self.snailnft_contract.functions.setApprovalForAll(self.bulk_transfer_contract.address, target),
            wait_for_transaction_receipt=wait_for_transaction_receipt,
            **kwargs,
        )

    def bulk_transfer_snails(
        self, to: str, token_ids: list[int], wait_for_transaction_receipt: Union[bool, float] = None, **kwargs
    ):
        return self._bss(
            self.bulk_transfer_contract.functions.bulkTransfer721Lite(self.snailnft_contract.address, to, token_ids),
            wait_for_transaction_receipt=wait_for_transaction_receipt,
            **kwargs,
        )

    def snail_metadata(self, snail_id):
        return self.snailnft_contract.functions.tokenURI(snail_id).call({'from': self.wallet})

    def snail_gender(
        self, snail_id, new_gender: int = None, wait_for_transaction_receipt: Union[bool, float] = None, **kwargs
    ):
        """
        gender mapping: 0 - undefined, 1 - female, 2 - male
        (same as GraphQL)
        """
        return self.marketplace_contract.functions.getSnailGender(snail_id).call({'from': self.wallet})

    def set_snail_gender(
        self, snail_id, new_gender: int, wait_for_transaction_receipt: Union[bool, float] = None, **kwargs
    ):
        """
        gender mapping: 0 - undefined, 1 - female, 2 - male
        (same as GraphQL)
        """
        current = self.marketplace_contract.functions.getSnailGender(snail_id).call({'from': self.wallet})
        if current == new_gender:
            return None
        return self._bss(
            self.marketplace_contract.functions.setGender(snail_id, new_gender),
            wait_for_transaction_receipt=wait_for_transaction_receipt,
            **kwargs,
        )

    def incubate_snails(
        self,
        item_id,
        base_fee,
        market_price,
        coefficent,
        female_id,
        male_id,
        timeout,
        salt,
        signature,
        wait_for_transaction_receipt: Union[bool, float] = None,
        **kwargs,
    ):
        return self._bss(
            self.incubator_contract.functions.incubateSnails(
                self.wallet,
                item_id,
                base_fee,
                market_price,
                coefficent,
                female_id,
                male_id,
                timeout,
                salt,
                signature,
            ),
            wait_for_transaction_receipt=wait_for_transaction_receipt,
            **kwargs,
        )

    def incubate_nonce(self):
        return self.incubator_contract.functions.getCurrentNonce(self.wallet).call({'from': self.wallet})

    def approve_slime_for_incubator(
        self, remove=False, wait_for_transaction_receipt: Union[bool, float] = None, **kwargs
    ):
        current = self.slime_contract.functions.allowance(self.wallet, self.incubator_contract.address).call(
            {'from': self.wallet}
        )
        target = 0 if remove else int(constants.MAX_INT, 16)
        if current == target:
            return
        return self._bss(
            self.slime_contract.functions.approve(self.incubator_contract.address, target),
            wait_for_transaction_receipt=wait_for_transaction_receipt,
            **kwargs,
        )

    def swap_slime_avax(
        self,
        amount_in=None,
        amount_out=None,
        deadline=None,
        preview=False,
        wait_for_transaction_receipt: Union[bool, float] = None,
    ):
        if deadline is None:
            # 2 hours deadline like website
            deadline = int(datetime.utcnow().timestamp()) + 3600 * 2

        if amount_in is None:
            amount_in = 1 * DECIMALS

        call_args = [
            amount_in,
            amount_out,
            (
                [0x0],
                [0x0],
                ['0x5a15Bdcf9a3A8e799fa4381E666466a516F2d9C8', '0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7'],
            ),
            self.wallet,
            deadline,
        ]

        if preview or amount_out is None:
            call_args[1] = 0
            out_min = self.traderjoe_contract.functions.swapExactTokensForNATIVE(*call_args).call({'from': self.wallet})
            if preview:
                return out_min
            call_args[1] = out_min

        return self._bss(
            self.traderjoe_contract.functions.swapExactTokensForNATIVE(*call_args),
            wait_for_transaction_receipt=wait_for_transaction_receipt,
        )

    @cached_property_with_ttl(60)
    def gas_price(self):
        return self.gas_price_not_cached

    @property
    def gas_price_not_cached(self):
        r = self.web3.eth.gasPrice
        if r != BOTTOM_BASE_FEE:
            logger.info('Median fee: %d', r)
        return r

    def use_lab(
        self,
        order_id: int,
        size: int,
        fee: int,
        snail_ids: list[int],
        timeout: int,
        salt: int,
        signature: str,
        wait_for_transaction_receipt: Union[bool, float] = None,
        **kwargs,
    ):
        return self._bss(
            self.snaillab_contract.functions.useLab(
                (
                    order_id,
                    size,
                    snail_ids,
                    self.wallet,
                    fee,
                    timeout,
                    salt,
                ),
                signature,
            ),
            wait_for_transaction_receipt=wait_for_transaction_receipt,
            **kwargs,
        )
