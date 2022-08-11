from unittest import TestCase, mock
import cli
from . import data


class Test(TestCase):
    def test_join_missing(self):
        args = cli.build_parser().parse_args(['bot'], config_file_contents='')
        c = cli.cli.CLI(cli.cli.Wallet('wallet1', 'pkey1'), 'http://localhost:99999', args, True)
        c.client.gql = mock.MagicMock()
        c.client.gql.get_my_snails_for_missions.return_value = data.GQL_MISSION_SNAILS
        c.client.gql.get_mission_races.side_effect = [data.GQL_MISSION_RACES, {'all': []}]
        c.client.web3 = mock.MagicMock()
        c.join_missions()
        self.assertEqual(1, 1)

    def test_set_queue(self):
        q = cli.cli.SetQueue(capacity=5)
        # add works (and it is ordered)
        self.assertEqual(list(q), [])
        q.add(2)
        q.add(5)
        q.add(1)
        self.assertEqual(list(q), [2, 5, 1])
        # remove works
        q.remove(5)
        self.assertEqual(list(q), [2, 1])
        # add repeated moves it to last
        q.add(2)
        self.assertEqual(list(q), [1, 2])
        # add above capacity, truncates it
        q.add(5)
        q.add(6)
        q.add(7)
        q.add(8)
        self.assertEqual(list(q), [2, 5, 6, 7, 8])
