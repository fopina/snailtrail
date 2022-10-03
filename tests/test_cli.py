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
        self.cli = c

    def test_masked_owner(self):
        self.assertEqual(self.cli.masked_wallet, '0x76e8...44ff')

    def test_join_missing(self):
        self.cli.client.gql.get_my_snails_for_missions.return_value = data.GQL_MISSION_SNAILS
        self.cli.client.gql.get_mission_races.side_effect = [data.GQL_MISSION_RACES, {'all': []}]
        self.cli.join_missions()
        self.assertEqual(1, 1)

    def test_cached_snail_history(self):
        self.cli.client.gql.get_race_history.side_effect = [
            # gold league
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
            # platinum league
            {'races': [], 'count': 0},
        ]
        r = self.cli._snail_history.get(1, 50)
        self.assertEqual(r[1][27], [1, 0, 0, 1])
        self.assertEqual(self.cli.client.gql.get_race_history.call_count, 2)

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
