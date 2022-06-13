from functools import cached_property

from Crypto.Hash import keccak
from eth_account.messages import encode_defunct
from web3 import Web3
from web3.middleware import geth_poa_middleware

from . import abi

CONTRACT_PREFERENCES = '0xfDC483EE4ff24d3a8580504a5D04128451972e1e'
CONTRACT_RACE = '0x58B699642f2a4b91Dd10800Ef852427B719dB1f0'
CONTRACT_SLIME = '0x5a15Bdcf9a3A8e799fa4381E666466a516F2d9C8'
CONTRACT_SNAILNFT = '0xec675B7C5471c67E9B203c6D1C604df28A89FB7f'


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
    def slime_contract(self):
        return self.web3.eth.contract(address=self.web3.toChecksumAddress(CONTRACT_SLIME), abi=abi.ACCOUNT)

    @cached_property
    def snailnft_contract(self):
        return self.web3.eth.contract(address=self.web3.toChecksumAddress(CONTRACT_SNAILNFT), abi=abi.ACCOUNT)

    def _bss(self, function_call):
        """build tx, sign it and send it"""
        nonce = self.web3.eth.getTransactionCount(self.wallet)
        tx = function_call.buildTransaction({"nonce": nonce, "from": self.wallet})
        signed_txn = self.web3.eth.account.sign_transaction(tx, private_key=self.__pkey)
        return self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)

    def set_snail_name(self, snail_id: int, new_name: str):
        return self._bss(
            self.preferences_contract.functions.setSnailName(snail_id, new_name)
        )

    def join_daily_mission(
        self,
        race_info: tuple[int, int, str],
        result_size: int,
        results: list[tuple[int, list[str]]],
        timeout: int,
        salt: int,
        signature: str,
    ):
        return self._bss(
            self.race_contract.functions.joinDailyMission(
                race_info,
                result_size,
                results,
                timeout,
                salt,
                signature,
            )
        )

    def claimable_rewards(self):
        return self.race_contract.functions.claimableRewards().call({'from': self.wallet}) / 1000000000000000000

    def balance_of_slime(self):
        return self.slime_contract.functions.balanceOf(self.wallet).call({'from': self.wallet}) / 1000000000000000000

    def balance_of_snails(self):
        return self.snailnft_contract.functions.balanceOf(self.wallet).call({'from': self.wallet})

    def get_balance(self):
        return self.web3.eth.get_balance(self.wallet) / 1000000000000000000

    def sign_daily_mission(self, owner: str, snail_id: int, race_id: int):
        """Generate and sign payload to join a daily mission
        >>> o = Client(private_key='badbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbad0', web3_provider='x')
        >>> o.sign_daily_mission('0xbadbadbadbadbadbadbadbadbadbadbadbadbad0', 1816, 44660)
        '0x66287e0465f644bad50cab950218ee6386f0e19bde3be4fad34f473b33f806c0177718d8ddb4ffe0149e3098b20abc1a382c6c77d7f4b7f61f6f4fa33f8f47641c'
        """
        # TODO: SIGN!!! and join with graphql
        keccak_hash = keccak.new(digest_bits=256)
        keccak_hash.update(
            snail_id.to_bytes(32, "big") + race_id.to_bytes(32, "big") + bytes.fromhex(owner.replace("0x", ""))
        )
        sign_payload = keccak_hash.digest()
        message = encode_defunct(sign_payload)
        return self.web3.eth.account.sign_message(message, private_key=self.__pkey).signature.hex()