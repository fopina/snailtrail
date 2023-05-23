from functools import cached_property
from typing import Any, Union
from datetime import datetime
import base64

from Crypto.Hash import keccak
from eth_account.messages import encode_defunct
from web3 import Web3, exceptions  # noqa - for others to import from here
from web3.middleware import geth_poa_middleware

from . import abi

CONTRACT_PREFERENCES = '0xfDC483EE4ff24d3a8580504a5D04128451972e1e'
CONTRACT_RACE = '0x58B699642f2a4b91Dd10800Ef852427B719dB1f0'
CONTRACT_SLIME = '0x5a15Bdcf9a3A8e799fa4381E666466a516F2d9C8'
CONTRACT_SNAILNFT = '0xec675B7C5471c67E9B203c6D1C604df28A89FB7f'
CONTRACT_INCUBATOR = '0x09457e0181dA074610530212A6378605382764b8'
CONTRACT_MEGA_RACE = '0xa65592fC7afa222Ac30a80F273280e6477a274e3'
CONTRACT_WAVAX = '0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7'


class Client:
    def __init__(
        self,
        wallet,
        private_key,
        web3_provider,
        web3_provider_class=None,
    ):
        if web3_provider_class is None:
            web3_provider_class = Web3.HTTPProvider
        self.web3 = Web3(web3_provider_class(web3_provider))
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.__pkey = private_key
        self.wallet = wallet

    @cached_property
    def preferences_contract(self):
        return self.web3.eth.contract(
            address=self.web3.toChecksumAddress(CONTRACT_PREFERENCES),
            abi=abi.PREFERENCES,
        )

    @cached_property
    def race_contract(self):
        return self.web3.eth.contract(address=self.web3.toChecksumAddress(CONTRACT_RACE), abi=abi.RACE)

    @cached_property
    def mega_race_contract(self):
        return self.web3.eth.contract(address=self.web3.toChecksumAddress(CONTRACT_MEGA_RACE), abi=abi.RACE)

    @cached_property
    def slime_contract(self):
        return self.web3.eth.contract(address=self.web3.toChecksumAddress(CONTRACT_SLIME), abi=abi.ACCOUNT)

    @cached_property
    def wavax_contract(self):
        return self.web3.eth.contract(address=self.web3.toChecksumAddress(CONTRACT_WAVAX), abi=abi.ACCOUNT)

    @cached_property
    def snailnft_contract(self):
        return self.web3.eth.contract(address=self.web3.toChecksumAddress(CONTRACT_SNAILNFT), abi=abi.SNAILNFT)

    @cached_property
    def incubator_contract(self):
        return self.web3.eth.contract(address=self.web3.toChecksumAddress(CONTRACT_INCUBATOR), abi=abi.INCUBATOR)

    def _bss(self, function_call: Any, wait_for_transaction_receipt: Union[bool, float] = None, estimate_only=False):
        """build tx, sign it and send it"""
        nonce = self.web3.eth.getTransactionCount(self.wallet)
        tx = function_call.buildTransaction({"nonce": nonce, "from": self.wallet})
        if estimate_only:
            return self.web3.eth.estimate_gas(tx)
        signed_txn = self.web3.eth.account.sign_transaction(tx, private_key=self.__pkey)
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
        return self.race_contract.functions.claimableRewards().call({'from': self.wallet}) / 1000000000000000000

    def balance_of_slime(self, raw=False):
        x = self.slime_contract.functions.balanceOf(self.wallet).call({'from': self.wallet})
        if raw:
            return x
        return x / 1000000000000000000

    def claimable_wavax(self):
        return self.mega_race_contract.functions.claimableRewards().call({'from': self.wallet}) / 1000000000000000000

    def balance_of_wavax(self, raw=False):
        x = self.wavax_contract.functions.balanceOf(self.wallet).call({'from': self.wallet})
        if raw:
            return x
        return x / 1000000000000000000

    def balance_of_snails(self):
        return self.snailnft_contract.functions.balanceOf(self.wallet).call({'from': self.wallet})

    def get_balance(self):
        return self.web3.eth.get_balance(self.wallet) / 1000000000000000000

    def get_current_coefficent(self):
        return (
            self.incubator_contract.functions.getCurrentCoefficent().call({'from': self.wallet}) / 1000000000000000000
        )

    def sign_race_join(self, snail_id: int, race_id: int, owner: str = None):
        """Generate and sign payload to join a daily mission
        >>> o = Client(wallet='0xbadbadbadbadbadbadbadbadbadbadbadbadbad0', private_key='badbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbad0', web3_provider='x')
        >>> o.sign_race_join(1816, 44660)
        '0x66287e0465f644bad50cab950218ee6386f0e19bde3be4fad34f473b33f806c0177718d8ddb4ffe0149e3098b20abc1a382c6c77d7f4b7f61f6f4fa33f8f47641c'
        """
        if owner is None:
            owner = self.wallet
        keccak_hash = keccak.new(digest_bits=256)
        keccak_hash.update(
            snail_id.to_bytes(32, "big") + race_id.to_bytes(32, "big") + bytes.fromhex(owner.replace("0x", ""))
        )
        sign_payload = keccak_hash.digest()
        message = encode_defunct(sign_payload)
        return self.web3.eth.account.sign_message(message, private_key=self.__pkey).signature.hex()

    def auth_token(self, timestamp=None, literal_key=b'snailtrail', owner=None) -> tuple[str, int]:
        """Generate an auth token for GraphQL API
        >>> o = Client(wallet='0xbadbadbadbadbadbadbadbadbadbadbadbadbad0', private_key='badbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbad0', web3_provider='x')
        >>> o.auth_token(timestamp=1684841032263)
        ('MHhlMGM4ZTE3ZjJjYTA4MjExOWU2N2UzYjFmNThkODkwYTY1NWY5NDVmMzAxNmQ4Nzc5YWQ3NWY5N2QwOTMzNWFjMWVmMzBjNjUwYmQ3ODI1ZGY2MjNmNDczYjk2YjM0YWM2MWJjNzExNzYzN2NmNjU0MWM2MTBhNTRiYzIyNWU4MTFiOjB4YmFkYmFkYmFkYmFkYmFkYmFkYmFkYmFkYmFkYmFkYmFkYmFkYmFkMDoxNjg0ODQxMDMyMjYz', 1685445832263)
        """
        if owner is None:
            owner = self.wallet
        if timestamp is None:
            timestamp = int(datetime.utcnow().timestamp() * 1000)
        keccak_hash = keccak.new(digest_bits=256)
        keccak_hash.update(int.to_bytes(timestamp, 32, "big") + literal_key + bytes.fromhex(owner.replace("0x", "")))
        sign_payload = keccak_hash.digest()
        message = encode_defunct(sign_payload)
        signed_payload = self.web3.eth.account.sign_message(message, private_key=self.__pkey).signature.hex()
        return (base64.b64encode(f'{signed_payload}:{owner}:{timestamp}'.encode()).decode(), timestamp + 604800000)

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
