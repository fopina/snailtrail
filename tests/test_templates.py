from unittest import TestCase

from cli import templates
from snail.gqlclient import types as gtypes
from snail.web3client import web3_types


class TestMissions(TestCase):
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


class TestBalances(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self._data = [
            (
                '0x01',
                {
                    'SLIME': (1, 2),
                    'WAVAX': (0, 2),
                    'AVAX': 5,
                    'SNAILS': 10,
                },
            )
        ]

    def test_tgbot_balances_multi(self):
        self._data.append(
            (
                '0x02',
                {
                    'SLIME': (3.4, 0),
                    'WAVAX': (1.6543, 0),
                    'AVAX': 4.12,
                    'SNAILS': 7,
                },
            )
        )
        self.assertEqual(
            templates.render_tgbot_balances(self._data),
            '''\
`>> 0x01`
🧪 1 / 2
*WAVAX*: 0 / 2
🔺 5 / 🐌 10
`>> 0x02`
🧪 3.4 / 0
*WAVAX*: 1.654 / 0
🔺 4.12 / 🐌 7
`Total`
🧪 6.4
🔺 12.774
🐌 17
''',
        )

    def test_tgbot_balances_single(self):
        self.assertEqual(
            templates.render_tgbot_balances(self._data),
            '''\
🧪 1 / 2
*WAVAX*: 0 / 2
🔺 5 / 🐌 10
''',
        )

    def test_tgbot_balances_no_slime(self):
        self._data[0][1]['SLIME'] = (0, 0)
        self.assertEqual(
            templates.render_tgbot_balances(self._data),
            '''\
*WAVAX*: 0 / 2
🔺 5 / 🐌 10
''',
        )
        self._data[0][1]['WAVAX'] = (0, 0)
        self.assertEqual(
            templates.render_tgbot_balances(self._data),
            '''\
🔺 5 / 🐌 10
''',
        )
