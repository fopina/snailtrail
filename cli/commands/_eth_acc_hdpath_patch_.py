from functools import lru_cache

from eth_account.hdaccount import ETHEREUM_DEFAULT_PATH, seed_from_mnemonic
from eth_account.hdaccount._utils import hmac_sha512
from eth_account.hdaccount.deterministic import HDPath, Node, derive_child_key


class PrecomputedHDPath(HDPath):
    """
    attempt to slightly improve
        w3.eth.account.from_mnemonic(namespace.wallet_seed, account_path=f"m/44'/60'/0'/0/{ind}").key
    by containing seed_from_mnemonic() in same class as path derivation
    AND pre-computing all nodes UP TO last (wallet index)
    """

    def __init__(self, mnemonic: str, passphrase=''):
        super().__init__(ETHEREUM_DEFAULT_PATH)
        self._seed = seed_from_mnemonic(mnemonic, passphrase)
        del self._path[-1]
        self.pre_derive()

    def pre_derive(self):
        """
        re-implement `derive` WITHOUT USING LAST NODE
        """
        master_node = hmac_sha512(b"Bitcoin seed", self._seed)
        key = master_node[:32]
        chain_code = master_node[32:]
        for node in self._path:
            key, chain_code = derive_child_key(key, chain_code, node)
        self._cache = (key, chain_code)

    def derive(self, index: int) -> bytes:
        last_node = Node.decode(str(index))
        key, _ = derive_child_key(self._cache[0], self._cache[1], last_node)
        return key


@lru_cache
def cached_path(mnemonic, passphrase=''):
    return PrecomputedHDPath(mnemonic, passphrase=passphrase)
