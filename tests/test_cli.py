import contextlib
import copy
import io
import tempfile
from datetime import datetime, timezone
from unittest import TestCase, mock

import cli
from cli import types
from snail.gqltypes import Race

from . import data

TEST_WALLET = '0xbad43dfb19C6Ab77D9eC30704b89879F1e6d3081'
TEST_WALLET_PKEY = 'bacc489be509e5463399feb27097af41580344053c7e62c70d1d2a2291d032e0'
TEST_WALLET_WALLET = types.Wallet.from_private_key(TEST_WALLET_PKEY)


class Test(TestCase):
    def test_bot_settings(self):
        with tempfile.NamedTemporaryFile() as f:
            args = cli.build_parser().parse_args(
                ['--notify', '123:a', '2', 'bot', '--settings', f.name, '-c'], config_file_contents=''
            )
            c = cli.cli.CLI(cli.cli.Wallet('wallet1', 'pkey1'), 'http://localhost:99999', args, True)
            self.assertTrue(args.coefficent)
            self.assertFalse(args.market)
            args.market = True
            c.save_bot_settings()

            args = cli.build_parser().parse_args(
                ['--notify', '123:a', '2', 'bot', '--settings', f.name, '-c'], config_file_contents=''
            )
            c = cli.cli.CLI(cli.cli.Wallet('wallet1', 'pkey1'), 'http://localhost:99999', args, True)
            self.assertTrue(args.coefficent)
            self.assertFalse(args.market)
            c.load_bot_settings()
            self.assertTrue(args.market)


class TestBot(TestCase):
    def setUp(self) -> None:
        args = cli.build_parser().parse_args(['bot'], config_file_contents='')
        wallet = cli.cli.Wallet(TEST_WALLET, 'pkey1')
        self._wallet = wallet
        c = cli.cli.CLI(wallet, 'http://localhost:99999', args, True)
        c.client.gql = mock.MagicMock()
        c.client.web3 = mock.MagicMock(wallet=wallet)
        c._profile = {'guild': {'id': 69, 'name': 'SlimeBots'}}
        c.notifier = mock.MagicMock()
        self.cli = c

    def test_masked_owner(self):
        self.assertEqual(self.cli.masked_wallet, '0xbad...081')

    def test_join_missions(self):
        self.cli.client.gql.get_my_snails_for_missions.return_value = data.GQL_MISSION_SNAILS
        self.cli.client.gql.get_mission_races.side_effect = [data.GQL_MISSION_RACES, {'all': []}]
        self.cli.client.web3.sign_race_join.return_value = 'signed'
        self.cli.join_missions()
        self.assertEqual(
            self.cli.client.gql.join_mission_races.call_args_list,
            [
                mock.call(8922, 169405, self._wallet, 'signed'),
                mock.call(8851, 169406, self._wallet, 'signed'),
            ],
        )
        self.cli.client.web3.join_daily_mission.assert_not_called()

    def test_join_missions_no_adaptations(self):
        self.cli.client.gql.get_my_snails_for_missions.return_value = data.GQL_MISSION_SNAILS
        self.cli.client.gql.get_mission_races.side_effect = [data.GQL_MISSION_RACES, {'all': []}]
        self.cli.client.web3.sign_race_join.return_value = 'signed'
        self.cli.args.mission_matches = 0
        self.cli.join_missions()
        self.assertEqual(
            self.cli.client.gql.join_mission_races.call_args_list,
            [
                mock.call(8922, 169405, self._wallet, 'signed'),
                mock.call(9104, 169406, self._wallet, 'signed'),
            ],
        )
        self.cli.client.web3.join_daily_mission.assert_not_called()

    def test_join_missions_max_adaptations(self):
        self.cli.client.gql.get_my_snails_for_missions.return_value = data.GQL_MISSION_SNAILS
        self.cli.client.gql.get_mission_races.side_effect = [data.GQL_MISSION_RACES, {'all': []}]
        self.cli.client.web3.sign_race_join.return_value = 'signed'
        self.cli.args.mission_matches = 3
        self.cli.join_missions()
        self.cli.client.gql.join_mission_races.assert_not_called()
        self.cli.client.web3.join_daily_mission.assert_not_called()

    def test_join_missions_boosted(self):
        self.cli.client.gql.get_my_snails_for_missions.return_value = data.GQL_MISSION_SNAILS
        self.cli.client.gql.get_mission_races.side_effect = [data.GQL_MISSION_RACES, {'all': []}]
        self.cli.client.web3.sign_race_join.return_value = 'signed'
        self.cli.args.boost = [int(s['id']) for s in data.GQL_MISSION_SNAILS['snails']]
        self.cli.join_missions()
        self.assertEqual(
            self.cli.client.gql.join_mission_races.call_args_list,
            [
                mock.call(8667, 169396, self._wallet, 'signed'),
                mock.call(8851, 169399, self._wallet, 'signed'),
                mock.call(8416, 169400, self._wallet, 'signed'),
                mock.call(9104, 169401, self._wallet, 'signed'),
                mock.call(8267, 169402, self._wallet, 'signed'),
                mock.call(8663, 169403, self._wallet, 'signed'),
            ],
        )
        self.cli.client.web3.join_daily_mission.assert_not_called()

    def test_join_missions_boosted_wallet(self):
        self.cli.client.gql.get_my_snails_for_missions.return_value = data.GQL_MISSION_SNAILS
        self.cli.client.gql.get_mission_races.side_effect = [data.GQL_MISSION_RACES, {'all': []}]
        self.cli.client.web3.sign_race_join.return_value = 'signed'
        self.cli.args.boost_wallet = [self._wallet]
        self.cli.join_missions()
        self.assertEqual(
            self.cli.client.gql.join_mission_races.call_args_list,
            [
                mock.call(8667, 169396, self._wallet, 'signed'),
                mock.call(8851, 169399, self._wallet, 'signed'),
                mock.call(8416, 169400, self._wallet, 'signed'),
                mock.call(9104, 169401, self._wallet, 'signed'),
                mock.call(8267, 169402, self._wallet, 'signed'),
                mock.call(8663, 169403, self._wallet, 'signed'),
            ],
        )
        self.cli.client.web3.join_daily_mission.assert_not_called()

    def test_join_missions_boosted_to_15(self):
        from copy import deepcopy

        msnails = deepcopy(data.GQL_MISSION_SNAILS)
        for s in msnails['snails']:
            if s['id'] == 8667:
                s['stats']['experience']['level'] = 15
        self.cli.client.gql.get_my_snails_for_missions.return_value = msnails
        self.cli.client.gql.get_mission_races.side_effect = [data.GQL_MISSION_RACES, {'all': []}]
        self.cli.client.web3.sign_race_join.return_value = 'signed'
        self.cli.args.boost = [int(s['id']) for s in data.GQL_MISSION_SNAILS['snails']]
        self.cli.args.boost_to = 15
        self.cli.join_missions()
        self.assertEqual(
            self.cli.client.gql.join_mission_races.call_args_list,
            [
                mock.call(8851, 169399, self._wallet, 'signed'),
                mock.call(8416, 169400, self._wallet, 'signed'),
                mock.call(9104, 169401, self._wallet, 'signed'),
                mock.call(8267, 169402, self._wallet, 'signed'),
                mock.call(8663, 169403, self._wallet, 'signed'),
                mock.call(8667, 169405, self._wallet, 'signed'),
            ],
        )
        self.cli.client.web3.join_daily_mission.assert_not_called()

    def test_cached_snail_history(self):
        self.cli.client.gql.get_race_history.side_effect = [
            {
                'races': [
                    {
                        'id': 11111,
                        'race_type': '50',
                        'distance': 27,
                        'results': [
                            {'token_id': 1, 'time': 1},
                            {'token_id': 2, 'time': 2},
                            {'token_id': 3, 'time': 3},
                            {'token_id': 4, 'time': 4},
                            {'token_id': 5, 'time': 5},
                            {'token_id': 6, 'time': 6},
                            {'token_id': 7, 'time': 7},
                            {'token_id': 8, 'time': 8},
                            {'token_id': 9, 'time': 9},
                            {'token_id': 10, 'time': 10},
                        ],
                    },
                ],
                'count': 1,
            },
        ]
        r = self.cli._snail_history.get(1)
        self.assertEqual(r[1][27], [1, 0, 0, 1])
        self.assertEqual(self.cli.client.gql.get_race_history.call_count, 1)

        self.cli.client.gql.get_race_history.reset_mock()
        r = self.cli._snail_history.get(1)
        self.assertEqual(r[1][10], [0, 0, 0, 0])
        # already cached, API not called
        self.cli.client.gql.get_race_history.assert_not_called()

        r = self.cli._snail_history.update(
            1,
            Race(
                {
                    'id': 11111,
                    'race_type': '50',
                    'distance': 27,
                    'results': [
                        {'token_id': 2, 'time': 1},
                        {'token_id': 1, 'time': 2},
                        {'token_id': 3, 'time': 3},
                        {'token_id': 4, 'time': 4},
                        {'token_id': 5, 'time': 5},
                        {'token_id': 6, 'time': 6},
                        {'token_id': 7, 'time': 7},
                        {'token_id': 8, 'time': 8},
                        {'token_id': 9, 'time': 9},
                        {'token_id': 10, 'time': 10},
                    ],
                }
            ),
        )
        self.assertTrue(r)
        r = self.cli._snail_history.get(1)
        self.assertEqual(r[1][27], [1, 1, 0, 2])
        # already cached (and updated), API not called
        self.cli.client.gql.get_race_history.assert_not_called()

        r = self.cli._snail_history.update(
            1,
            Race(
                {
                    'id': 11111,
                    'race_type': '50',
                    'distance': 10,
                    'results': [
                        {'token_id': 2, 'time': 1},
                        {'token_id': 1, 'time': 2},
                        {'token_id': 3, 'time': 3},
                        {'token_id': 4, 'time': 4},
                        {'token_id': 5, 'time': 5},
                        {'token_id': 6, 'time': 6},
                        {'token_id': 7, 'time': 7},
                        {'token_id': 8, 'time': 8},
                        {'token_id': 9, 'time': 9},
                        {'token_id': 10, 'time': 10},
                    ],
                }
            ),
        )
        self.assertTrue(r)
        r = self.cli._snail_history.get(1)
        self.assertEqual(r[1][10], [0, 1, 0, 1])
        # already cached (and updated), API not called
        self.cli.client.gql.get_race_history.assert_not_called()

        r = self.cli._snail_history.update(
            1,
            Race(
                {
                    'id': 11111,
                    'race_type': '100',
                    'distance': 10,
                    'results': [
                        {'token_id': 2, 'time': 1},
                        {'token_id': 1, 'time': 2},
                        {'token_id': 3, 'time': 3},
                        {'token_id': 4, 'time': 4},
                        {'token_id': 5, 'time': 5},
                        {'token_id': 6, 'time': 6},
                        {'token_id': 7, 'time': 7},
                        {'token_id': 8, 'time': 8},
                        {'token_id': 9, 'time': 9},
                        {'token_id': 10, 'time': 10},
                    ],
                }
            ),
        )
        # cache miss, not updated
        self.assertTrue(r)
        r = self.cli._snail_history.get(1)
        self.assertEqual(r[1][10], [0, 2, 0, 2])
        # cached, API not called
        self.cli.client.gql.get_race_history.assert_not_called()

    def test_bot_coefficent(self):
        self.cli.client.web3.get_current_coefficent.side_effect = [2, 3, 1]
        self.cli._bot_coefficent()
        self.cli.notifier.notify.assert_not_called()

        self.cli._bot_coefficent()
        self.cli.notifier.notify.assert_not_called()

        self.cli.notifier.notify.reset_mock()
        self.cli._bot_coefficent()
        self.cli.notifier.notify.assert_called_once_with('🍆 Coefficent drop to *1.0000* (from *3*)')

    def test_balance(self):
        self.cli.args.claim = False
        self.cli.args.send = None
        self.cli.client.web3.claimable_slime.return_value = 1
        self.cli.client.web3.claimable_wavax.return_value = 1
        self.cli.client.web3.multicall_balances.return_value = {self.cli.owner: [1, 1, 1, 1]}
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            self.assertEqual(
                self.cli.cmd_balance(),
                {'SLIME': (1, 1), 'WAVAX': (1, 1), 'AVAX': 1, 'SNAILS': 1},
            )
        self.assertEqual(
            f.getvalue(),
            '''\
SLIME: 1 / 1.000
WAVAX: 1 / 1
AVAX: 1.000 / SNAILS: 1
''',
        )

    def test_find_races_over_normal(self):
        self.cli.args.first_run_over = True
        self.cli.args.races_over = True
        self.cli.client.gql.get_finished_races.return_value = data.GQL_FINISHED_RACES
        self.cli.client.gql.get_all_snails.return_value = data.GQL_MISSION_SNAILS
        self.cli.find_races_over()
        # called just for first snail found, on non-mega, as there can only be one
        self.cli.notifier.notify.assert_called_once_with('🥉 Snail #9104 number 3 in Hockenheimring, for 50, reward 4')

    def test_find_races_over_mega(self):
        self.cli.args.first_run_over = True
        self.cli.args.races_over = True
        mega_race = copy.deepcopy(data.GQL_FINISHED_RACES)
        self.cli.client.gql.get_all_snails.return_value = data.GQL_MISSION_SNAILS
        mega_race['own'][0]['distance'] = 'Mega Run'
        mega_race['own'][0]['id'] = 999
        self.cli.client.gql.get_finished_races.return_value = mega_race
        self.cli.find_races_over()
        # called for both owned snails in the mega race, as these can have multiple at same time
        self.assertEqual(
            self.cli.notifier.notify.call_args_list,
            [
                mock.call('🥉 Snail #9104 number 3 in Hockenheimring, for Mega Run, reward 4'),
                mock.call('💩 Powerpuff (#8267) number 8 in Hockenheimring, for Mega Run, reward 0'),
            ],
        )

    def test_find_races_over_tournament(self):
        self.cli.args.first_run_over = True
        self.cli.args.races_over = True
        self.cli._profile = {'guild': {'name': 'myGuild'}}
        self.cli.notifier.notify.reset_mock()
        self.cli.client.gql.get_finished_races.return_value = data.GQL_FINISHED_TOURNAMENT_RACES
        self.cli.client.gql.get_all_snails.return_value = data.GQL_MISSION_SNAILS
        self.cli.find_races_over()
        # called for both owned snails in the mega race, as these can have multiple at same time
        self.assertEqual(
            self.cli.notifier.notify.call_args_list,
            [
                mock.call('🥅 Snail #9104 (myGuild) in Temple of Slime, for 27, time 107.49s'),
            ],
        )

    def test_incubate_lazy_plan(self):
        self.cli.args.first_run_over = True
        self.cli.args.races_over = True
        self.cli.client.gql.get_finished_races.return_value = data.GQL_FINISHED_RACES
        self.cli.client.gql.get_all_snails.return_value = data.GQL_MISSION_SNAILS
        r = self.cli.cmd_incubate_fee_lazy_plan(data.TYPED_SNAIL_FEES)
        self.assertEqual(
            [(f, x1.id, x2.id) for f, x1, x2 in r],
            [
                (988.9882025935879, 15253, 14315),
                (997.4410932140458, 15253, 15254),
                (1146.2119681341069, 15253, 11663),
                (1432.4831971469516, 11665, 11724),
                (1455.5877648428702, 11665, 11789),
                (1461.504788277191, 11665, 11824),
                (1497.0069288831148, 12426, 13678),
                (1515.6032882481222, 12426, 11263),
                (1532.79083250972, 12426, 10519),
                (1538.4260929233587, 11823, 11825),
                (1562.094186660641, 11823, 11829),
                (1573.9282335292824, 11823, 10204),
            ],
        )

    @mock.patch('cli.cli.datetime')
    def test_bot_tournament(self, now_mock):
        now_mock.now.return_value = datetime(2023, 7, 11, 15, tzinfo=timezone.utc)
        self.cli.client.gql.tournament.return_value = data.TOURNAMENT_PROMISE_DATA
        self.cli.client.gql.tournament_guild_stats.return_value = {
            'leaderboard': {
                'my_guild': {
                    'points': 1,
                    'order': 10,
                }
            }
        }
        self.cli._bot_tournament()
        self.cli.client.gql.tournament_guild_stats.assert_called_once_with(self.cli.owner)
        self.assertEqual(
            self.cli._notify_tournament,
            (
                datetime(2023, 7, 11, 17, 25, 35, 50170, tzinfo=timezone.utc),
                {'points': 1, 'order': 10},
                datetime(2023, 7, 11, 17, 25, 35, 50170, tzinfo=timezone.utc),
            ),
        )
        self.cli.notifier.notify.assert_not_called()

        # 1 hour later, still before race start
        now_mock.now.return_value = datetime(2023, 7, 11, 16, tzinfo=timezone.utc)
        self.cli.client.gql.tournament_guild_stats.reset_mock()
        self.cli._bot_tournament()
        self.cli.client.gql.tournament_guild_stats.assert_not_called()

        # 2h later, race is over
        now_mock.now.return_value = datetime(2023, 7, 11, 18, tzinfo=timezone.utc)
        self.cli.client.gql.tournament_guild_stats.reset_mock()
        self.cli._bot_tournament()
        self.cli.client.gql.tournament_guild_stats.assert_called_once_with(self.cli.owner)
        self.cli.client.gql.tournament_guild_stats.return_value = {
            'leaderboard': {
                'my_guild': {
                    'points': 20,
                    'order': 3,
                }
            }
        }
        # nothing changes, race is "ongoing"
        self.assertEqual(
            self.cli._notify_tournament,
            (
                datetime(2023, 7, 11, 17, 25, 35, 50170, tzinfo=timezone.utc),
                {'points': 1, 'order': 10},
                datetime(2023, 7, 11, 17, 25, 35, 50170, tzinfo=timezone.utc),
            ),
        )
        self.cli.notifier.notify.assert_not_called()

        # check again few seconds after - and terminate race
        now_mock.now.return_value = datetime(2023, 7, 11, 18, 1, tzinfo=timezone.utc)
        self.cli.client.gql.tournament.return_value = copy.deepcopy(data.TOURNAMENT_PROMISE_DATA)
        for _e in self.cli.client.gql.tournament.return_value['weeks'][0]['days'][1]['result']['entries']:
            _e['points'] = 1
        self.cli.client.gql.tournament_guild_stats.reset_mock()
        self.cli._bot_tournament()
        self.cli.client.gql.tournament_guild_stats.assert_called_once_with(self.cli.owner)
        # next check updated for next race and notification sent with changed data
        self.assertEqual(
            self.cli._notify_tournament,
            (
                datetime(2023, 7, 12, 17, 25, 35, 50170, tzinfo=timezone.utc),
                {'points': 20, 'order': 3},
                datetime(2023, 7, 12, 17, 25, 35, 50170, tzinfo=timezone.utc),
            ),
        )
        self.cli.notifier.notify.assert_called_once_with(
            '''\
`SlimeBots` leaderboard:
*position* 10🏆3
*points* 1📈20
'''
        )


class TestMain(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.wallet_file = tempfile.NamedTemporaryFile(mode='w+')
        self.wallet_file.write(TEST_WALLET_PKEY)
        self.wallet_file.seek(0)
        self.config_file = tempfile.NamedTemporaryFile(mode='w+')
        self.config_file.write(
            f'''
wallet: [{self.wallet_file.name}]
'''
        )
        self.config_file.seek(0)
        self.proxy_patch = mock.patch('snail.proxy.Proxy')
        self.proxy_mock = self.proxy_patch.start()
        self.proxy_mock.return_value.url.return_value = ''

    def tearDown(self) -> None:
        self.config_file.close()
        self.proxy_patch.stop()
        super().tearDown()

    @mock.patch('cli.multicli.MultiCLI')
    def test_main(self, multi_mock: mock.MagicMock):
        cli.main(['-c', self.config_file.name, 'missions'])
        multi_mock.assert_called_once_with(wallets=[TEST_WALLET_WALLET], proxy_url=None, args=mock.ANY)

    def test_just_empty_wallet_no_action(self):
        cli.main(['--wallet', [], 'missions'])

    @mock.patch('cli.multicli.MultiCLI')
    def test_tg_bot_owner(self, multi_mock: mock.MagicMock):
        cli.main(['-c', self.config_file.name, 'missions'])
        multi_mock.assert_called_once_with(wallets=[TEST_WALLET_WALLET], proxy_url=None, args=mock.ANY)

    @mock.patch('cli.multicli.MultiCLI')
    def test_default_wallet(self, multi_mock: mock.MagicMock):
        # hardcoded filename, shortcut and then assert call
        with mock.patch('cli.commands.FileOrString') as wallet_mock:
            wallet_mock.return_value = TEST_WALLET_PKEY
            cli.main(['-c', '', 'missions'])
        multi_mock.assert_called_once_with(wallets=[TEST_WALLET_WALLET], proxy_url=None, args=mock.ANY)
        wallet_mock.assert_called_with('pkey.conf')
