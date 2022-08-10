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
