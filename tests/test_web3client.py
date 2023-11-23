from unittest import TestCase, mock

from snail.web3client import Client

from .test_cli import TEST_WALLET, TEST_WALLET_WALLET


class Test(TestCase):
    def setUp(self) -> None:
        self.cli = Client(TEST_WALLET, 'x', TEST_WALLET_WALLET.account)
        self.web3mock = mock.MagicMock()
        self.cli.web3 = self.web3mock
        self.cli.web3.eth.getTransactionCount.return_value = 1
        self.cli.web3.eth.chain_id = 40000
        self.cli.reset_cache_gas_price()

    def test_fee(self):
        transfer_mock = self.cli.web3.eth.contract.return_value.functions.transfer
        transfer_mock.return_value = {}
        self.cli.web3.eth.gasPrice = 25000000000
        self.cli.web3.eth.estimate_gas.return_value = 10
        tx = self.cli.transfer_slime(TEST_WALLET, 1000, estimate_only=True)
        transfer_mock.assert_called_once_with(TEST_WALLET, 1000)
        self.cli.web3.eth.send_raw_transaction.assert_not_called()
        self.cli.web3.eth.estimate_gas.assert_called_once_with(
            {
                'nonce': 1,
                'from': TEST_WALLET,
                'gas': 21000,
                'maxFeePerGas': 25000000000,
                'maxPriorityFeePerGas': 0,
                'chainId': 40000,
            }
        )
        self.assertEqual(tx, {'gasUsed': 10, 'effectiveGasPrice': 25000000000})
