from unittest import TestCase

from cli import utils
from snail.web3client import web3_types


class Test(TestCase):
    def test_tx_fee(self):
        tx = web3_types.TxReceipt({'gasUsed': 10000000, 'effectiveGasPrice': 250000000})
        self.assertEqual(
            utils.tx_fee(tx),
            0.0025,
        )
