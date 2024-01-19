from unittest import TestCase

from cli import templates
from snail.gqlclient import types as gtypes
from snail.web3client import web3_types


class Test(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self._snail = gtypes.Snail({'name': 'x', 'id': 1, 'stats': {'experience': {'level': 1}}})
        self._race = gtypes.Race({'id': 2})
        self._tx = web3_types.TxReceipt(
            {'gasUsed': 1000000, 'effectiveGasPrice': 250000000, 'transactionHash': web3_types.HexBytes('0xd34db33f')}
        )

    def test_cheap_soon_join(self):
        self.assertEqual(
            templates.render_cheap_soon_join(self._snail, self._race),
            'Joined cheap last spot without need - x (#1) on 2',
        )

    def test_mission_joined(self):
        self.assertEqual(
            templates.render_mission_joined(self._snail),
            '`x (#1)` (L1 - ) joined mission',
        )

    def test_mission_joined_last_spot(self):
        self.assertEqual(
            templates.render_mission_joined(self._snail, tx=self._tx, cheap=True),
            '`x (#1)` (L1 - ) joined mission LAST SPOT (cheap) - tx: 0xd34db33f - fee: 0.00025',
        )

    def test_mission_joined_last_spot_telegram(self):
        self.assertEqual(
            templates.render_mission_joined(self._snail, tx=self._tx, cheap=False, telegram=True),
            '`x (#1)` (L1 - ) joined mission 💸💰',
        )

    def test_mission_joined_reverted(self):
        self.assertEqual(
            templates.render_mission_joined_reverted(self._snail, tx=self._tx),
            'Last spot transaction reverted - tx: 0xd34db33f - fee: 0.00025',
        )
