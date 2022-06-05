from Crypto.Hash import keccak
from web3 import Web3
from eth_account.messages import encode_defunct


class Client:
    def __init__(
        self,
        private_key,
        web3_provider,
        web3_provider_class=None,
    ):
        if web3_provider_class is None:
            web3_provider_class = Web3.HTTPProvider
        self.web3 = Web3(web3_provider_class(web3_provider))
        self.__pkey = private_key

    def sign_daily_mission(self, owner: str, snail_id: int, race_id: int):
        """Generate and sign payload to join a daily mission
        >>> o = Client(private_key='badbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbad0', web3_provider='x')
        >>> o.sign_daily_mission('0xbadbadbadbadbadbadbadbadbadbadbadbadbad0', 1816, 44660)
        '0x66287e0465f644bad50cab950218ee6386f0e19bde3be4fad34f473b33f806c0177718d8ddb4ffe0149e3098b20abc1a382c6c77d7f4b7f61f6f4fa33f8f47641c'
        """
        # TODO: SIGN!!! and join with graphql
        keccak_hash = keccak.new(digest_bits=256)
        keccak_hash.update(
            snail_id.to_bytes(32, "big")
            + race_id.to_bytes(32, "big")
            + bytes.fromhex(owner.replace("0x", ""))
        )
        sign_payload = keccak_hash.digest()
        message = encode_defunct(sign_payload)
        return self.web3.eth.account.sign_message(
            message, private_key=self.__pkey
        ).signature.hex()
