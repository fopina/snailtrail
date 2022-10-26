import contextlib
import copy
import io
import tempfile
from unittest import TestCase, mock

import cli
from snail.gqltypes import Race

from . import data


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
        c = cli.cli.CLI(
            cli.cli.Wallet('0x76e83242f32721952eba2df6c72aa27b63bd44ff', 'pkey1'), 'http://localhost:99999', args, True
        )
        c.client.gql = mock.MagicMock()
        c.client.web3 = mock.MagicMock()
        c.notifier = mock.MagicMock()
        self.cli = c

    def test_masked_owner(self):
        self.assertEqual(self.cli.masked_wallet, '0x76e...4ff')

    def test_join_missions(self):
        self.cli.client.gql.get_my_snails_for_missions.return_value = data.GQL_MISSION_SNAILS
        self.cli.client.gql.get_mission_races.side_effect = [data.GQL_MISSION_RACES, {'all': []}]
        self.cli.client.web3.sign_race_join.return_value = 'signed'
        self.cli.join_missions()
        self.assertEqual(
            self.cli.client.gql.join_mission_races.call_args_list,
            [
                mock.call(8922, 169405, self.cli.owner, 'signed'),
                mock.call(8851, 169406, self.cli.owner, 'signed'),
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
                mock.call(8922, 169405, self.cli.owner, 'signed'),
                mock.call(9104, 169406, self.cli.owner, 'signed'),
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
                mock.call(8667, 169396, self.cli.owner, 'signed'),
                mock.call(8851, 169399, self.cli.owner, 'signed'),
                mock.call(8416, 169400, self.cli.owner, 'signed'),
                mock.call(9104, 169401, self.cli.owner, 'signed'),
                mock.call(8267, 169402, self.cli.owner, 'signed'),
                mock.call(8663, 169403, self.cli.owner, 'signed'),
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
        r = self.cli._snail_history.get(1, 50)
        self.assertEqual(r[1][27], [1, 0, 0, 1])
        self.assertEqual(self.cli.client.gql.get_race_history.call_count, 1)

        self.cli.client.gql.get_race_history.reset_mock()
        r = self.cli._snail_history.get(1, 50)
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
        r = self.cli._snail_history.get(1, 50)
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
        r = self.cli._snail_history.get(1, 50)
        self.assertEqual(r[1][10], [0, 1, 0, 1])
        r = self.cli._snail_history.get_all(1)
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
        r = self.cli._snail_history.get(1, 100)
        self.assertEqual(r[1][10], [0, 1, 0, 1])
        r = self.cli._snail_history.get_all(1)
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
        self.cli.notifier.notify.assert_called_once_with('Coefficent drop to *1.0000* (from *3*)')

    def test_balance(self):
        self.cli.args.claim = False
        self.cli.args.send = None
        self.cli.client.web3.claimable_slime.return_value = 1
        self.cli.client.web3.balance_of_slime.return_value = 1
        self.cli.client.web3.claimable_wavax.return_value = 1
        self.cli.client.web3.balance_of_wavax.return_value = 1
        self.cli.client.web3.get_balance.return_value = 1
        self.cli.client.web3.balance_of_snails.return_value = 1
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            self.assertIsNone(self.cli.cmd_balance())
        self.assertEqual(
            f.getvalue(),
            '''\
SLIME: 1 / 1.000
WAVAX: 1 / 1
AVAX: 1.000 / SNAILS: 1
''',
        )

    def test_find_races_over(self):
        self.cli.args.first_run_over = True
        self.cli.args.races_over = True
        self.cli.client.gql.get_finished_races.return_value = data.GQL_FINISHED_RACES
        self.cli.client.gql.get_all_snails.return_value = data.GQL_MISSION_SNAILS
        self.cli.find_races_over()
        # called just for first snail found, on non-mega, as there can only be one
        self.cli.notifier.notify.assert_called_once_with('🥉 Snail #9104 number 3 in Hockenheimring, for 50, reward 4')

        self.cli.notifier.notify.reset_mock()
        mega_race = copy.deepcopy(data.GQL_FINISHED_RACES)
        mega_race['own'][0]['distance'] = 'Mega Run'
        mega_race['own'][0]['id'] = 999
        self.cli.client.gql.get_finished_races.return_value = mega_race
        self.cli.client.gql.get_all_snails.return_value = data.GQL_MISSION_SNAILS
        self.cli.find_races_over()
        # called for both owned snails in the mega race, as these can have multiple at same time
        self.assertEqual(
            self.cli.notifier.notify.call_args_list,
            [
                mock.call('🥉 Snail #9104 number 3 in Hockenheimring, for Mega Run, reward 4'),
                mock.call('💩 Powerpuff (#8267) number 8 in Hockenheimring, for Mega Run, reward 0'),
            ],
        )
