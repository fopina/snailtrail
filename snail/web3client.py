from functools import cached_property
from typing import Any, Optional, Union
from datetime import datetime
import base64

from Crypto.Hash import keccak
from eth_account.messages import encode_defunct
from web3 import Web3, Account, exceptions  # noqa - for others to import from here
from web3.middleware import geth_poa_middleware

from . import contracts

DECIMALS = 1000000000000000000


class Client:
    def __init__(
        self,
        wallet: str,
        web3_provider: str,
        web3_account: Optional[Account] = None,
        web3_provider_class: Any = None,
    ):
        if web3_provider_class is None:
            web3_provider_class = Web3.HTTPProvider
        self.web3 = Web3(web3_provider_class(web3_provider))
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.account: Account = web3_account
        self.wallet = wallet

    def _contract(self, module):
        return self.web3.eth.contract(
            address=self.web3.toChecksumAddress(module.CONTRACT),
            abi=module.ABI,
        )

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
    def marketplace_contract(self):
        return self._contract(contracts.snail_gene_marketplace)

    def _bss(self, function_call: Any, wait_for_transaction_receipt: Union[bool, float] = None, estimate_only=False):
        """build tx, sign it and send it"""
        nonce = self.web3.eth.getTransactionCount(self.wallet)
        if isinstance(function_call, dict):
            # raw transaction
            tx = {k: v for k, v in function_call.items()}
            gas_price = int(0.000000025 * DECIMALS)
            tx.update(
                {
                    'nonce': nonce,
                    'from': self.wallet,
                    'gas': 21000,
                    'maxFeePerGas': gas_price,
                    'maxPriorityFeePerGas': gas_price,
                    'chainId': 43114,
                }
            )
        else:
            # function call
            tx = function_call.buildTransaction({'nonce': nonce, 'from': self.wallet})
        if estimate_only:
            return self.web3.eth.estimate_gas(tx)
        signed_txn = self.account.sign_transaction(tx)
        tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
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
        calls = []
        contracts = [self.snailnft_contract, self.wavax_contract, self.slime_contract]
        for w in wallets:
            for contract in contracts:
                calls.append(
                    (contract.address, contract.encodeABI('balanceOf', args=(w,))),
                )
        x = self.multicall_contract.functions.aggregate(calls).call({'from': self.wallet})
        w_ind = 0
        results = {}
        for y in range(0, len(x[1]), 3):
            results[wallets[w_ind]] = [
                self.web3.to_int(x[1][y]),
                self.web3.to_int(x[1][y + 1]) / DECIMALS,
                self.web3.to_int(x[1][y + 2]) / DECIMALS,
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

    def _sign_values(self, *values, owner: str = None):
        """Hash and sign typed values
        >>> a = Account.from_key('badbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbad0')
        >>> o = Client(wallet='0xbadbadbadbadbadbadbadbadbadbadbadbadbad0', web3_account=a, web3_provider='x')
        >>> o._sign_values(1816)
        '0xd608d3c0adde23a7ddeb94e3f15f742887249b87cae9e6c98c95422e72e9945410c5029efd815efc0d95c80dd05b119b8ac2b82b19b14e51580a9385356ed6881c'
        """
        if owner is None:
            owner = self.wallet

        keccak_hash = keccak.new(digest_bits=256)
        for value in values:
            if isinstance(value, int):
                keccak_hash.update(value.to_bytes(32, "big"))
            elif isinstance(value, str):
                keccak_hash.update(value.encode())
            elif isinstance(value, bytes):
                keccak_hash.update(value)
            else:
                raise NotImplementedError(type(value), 'not supported')
        keccak_hash.update(bytes.fromhex(owner.replace("0x", "")))

        sign_payload = keccak_hash.digest()
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

    def approve_all_snails_for_bulk(
        self, remove=False, wait_for_transaction_receipt: Union[bool, float] = None, **kwargs
    ):
        current = self.snailnft_contract.functions.isApprovedForAll(
            self.wallet, self.bulk_transfer_contract.address
        ).call()
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
        return self.incubator_contract.functions.getCurrentNonce(self.wallet).call()
