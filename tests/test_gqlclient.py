from pathlib import Path
from unittest import TestCase, mock

import gql
from graphql.error.syntax_error import GraphQLSyntaxError

from snail import gqlclient


class Test(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        schema_file = Path(__file__).parent / 'schema.graphql'
        cls.gql = gql.Client(schema=schema_file.read_text())

    def setUp(self) -> None:
        self.client = gqlclient.Client()
        self.req_mock = mock.MagicMock(errors=None)
        self.client.request = self.req_mock

    def assertValidGQL(self, gql_string):
        try:
            doc = gql.gql(gql_string)
            self.gql.validate(doc)
        except GraphQLSyntaxError as e:
            self.fail('invalid GQL query syntax: %s' % e)

    def test_init_proxies(self):
        self.assertEqual(self.client.proxies, {})
        c = gqlclient.Client(proxy='http://1.1.1.1:1234')
        self.assertEqual(c.proxies, {'http': 'http://1.1.1.1:1234', 'https': 'http://1.1.1.1:1234'})

    def test_init_token(self):
        self.assertNotIn('authorization', self.client.headers)
        c = gqlclient.Client(http_token='x')
        self.assertIn('authorization', c.headers)

    def test_init_retry(self):
        self.assertEqual(self.client.adapters['https://'].max_retries.total, 0)
        c = gqlclient.Client(retry=5)
        self.assertEqual(c.adapters['https://'].max_retries.total, 5)

    def test_get_all_genes_marketplace(self):
        self.client.get_all_genes_marketplace()
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'getAllSnail',
        )
        self.assertEqual(
            data['variables']['limit'],
            24,
        )
        self.assertValidGQL(data['query'])

    def test_marketplace_stats(self):
        self.client.marketplace_stats(1)
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'marketplaceStats',
        )
        self.assertEqual(
            data['variables']['market'],
            1,
        )
        self.assertValidGQL(data['query'])

    def test_tournament(self):
        self.client.tournament('x')
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'tournament_promise',
        )
        self.assertEqual(
            data['variables']['address'],
            'x',
        )
        self.assertValidGQL(data['query'])

    def test_profile(self):
        self.client.profile(['x', 'y'])
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'profile_promise',
        )
        self.assertEqual(
            data['variables']['address0'],
            'x',
        )
        self.assertValidGQL(data['query'])

    def test_guild_details(self):
        self.client.guild_details(1, member='x')
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'research_center_reward',
        )
        self.assertEqual(
            data['variables']['guild_id'],
            1,
        )
        self.assertValidGQL(data['query'])

    def test_guild_roster(self):
        self.client.guild_roster(1)
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'guildRoster',
        )
        self.assertEqual(
            data['variables']['guild_id'],
            1,
        )
        self.assertValidGQL(data['query'])

    def test_tournament_guild_stats(self):
        self.client.tournament_guild_stats('x')
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'tournamentMyGuildLeaderboard',
        )
        self.assertEqual(
            data['variables']['address'],
            'x',
        )
        self.assertValidGQL(data['query'])

    def test_get_inventory(self):
        self.client.get_inventory('x')
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'inventory_promise',
        )
        self.assertEqual(
            data['variables']['address'],
            'x',
        )
        self.assertValidGQL(data['query'])

    def test_incubate(self):
        self.client.incubate('x', 1, 2, 'x')
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'incubate_promise',
        )
        self.assertEqual(
            data['variables']['params']['fid'],
            1,
        )
        self.assertValidGQL(data['query'])

    def test_apply_pressure(self):
        self.client.apply_pressure('x', 1, 2, 'x')
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'apply_pressure_promise',
        )
        self.assertEqual(
            data['variables']['params']['address'],
            'x',
        )
        self.assertValidGQL(data['query'])

    def test_stake_snails(self):
        self.client.stake_snails(1, [1, 2])
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'send_workers_promise',
        )
        self.assertEqual(
            data['variables']['guild_id'],
            1,
        )
        self.assertValidGQL(data['query'])

    def test_guild_research(self):
        self.client.guild_research([1, 2])
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'research_center_reward',
        )
        self.assertEqual(
            data['variables']['guild_id0'],
            1,
        )
        self.assertValidGQL(data['query'])

    def test_guild_messages(self):
        self.client.guild_messages(1)
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'guildTreasuryLedger',
        )
        self.assertEqual(
            data['variables']['guild_id'],
            1,
        )
        self.assertValidGQL(data['query'])

    def test_get_onboarding_races(self):
        self.client.get_onboarding_races(1)
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'getOnboardingRaces',
        )
        self.assertValidGQL(data['query'])

    def test_get_mission_races(self):
        self.client.get_mission_races(1)
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'getMissionRaces',
        )
        self.assertValidGQL(data['query'])

    def test_get_all_snails(self):
        self.client.get_all_snails(1)
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'getAllSnail',
        )
        self.assertValidGQL(data['query'])

    def test_get_all_snails_marketplace(self):
        self.client.get_all_snails_marketplace(1)
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'getAllSnail',
        )
        self.assertValidGQL(data['query'])

    def test_name_change(self):
        self.client.name_change('x')
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'nameChange',
        )
        self.assertEqual(
            data['variables']['name'],
            'x',
        )
        self.assertValidGQL(data['query'])

    def test_join_competitive_races(self):
        self.client.join_competitive_races(1, 2, '3', '4')
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'joinCompetitiveRaces',
        )
        self.assertEqual(
            data['variables']['params']['token_id'],
            1,
        )
        self.assertValidGQL(data['query'])

    def test_join_mission_races(self):
        self.client.join_mission_races(1, 2, 'x', 'y')
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'joinMissionRaces',
        )
        self.assertEqual(
            data['variables']['params']['token_id'],
            1,
        )
        self.assertValidGQL(data['query'])

    def test_get_my_snails_for_ranked(self):
        self.client.get_my_snails_for_ranked('x', 1)
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'getMySnailsForRanked',
        )
        self.assertEqual(
            data['variables']['owner'],
            'x',
        )
        self.assertValidGQL(data['query'])

    def test_get_my_snails(self):
        self.client.get_my_snails('x')
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'my_snails_promise',
        )
        self.assertEqual(
            data['variables']['owner'],
            'x',
        )
        self.assertValidGQL(data['query'])

    def test_get_my_snails_for_missions(self):
        self.client.get_my_snails_for_missions('x')
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'getMySnailsForMissions',
        )
        self.assertEqual(
            data['variables']['owner'],
            'x',
        )
        self.assertValidGQL(data['query'])

    def test_get_race_history(self):
        self.client.get_race_history()
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'getRaceHistory',
        )
        self.assertEqual(
            data['variables']['limit'],
            20,
        )
        self.assertValidGQL(data['query'])

    def test_get_finished_races(self):
        self.client.get_finished_races()
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data['operationName'],
            'getFinishedRaces',
        )
        self.assertEqual(
            data['variables']['limit'],
            20,
        )
        self.assertValidGQL(data['query'])

    def test_helper_gql(self):
        gql = gqlclient.GQL('name', 'snail {name}', {'id': ('Int', 1)})
        gql.execute(self.client)
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data,
            {
                'operationName': 'query',
                'query': '''
            query query($id: Int) {
                name(id: $id) {
                snail {name}
                }
            }
            ''',
                'variables': {'id': 1},
            },
        )

    def test_helper_gqlunion(self):
        gql = gqlclient.GQL('name', 'snail {name}', {'id': ('Int', 1)})
        gql2 = gqlclient.GQL('name', 'snail {name}', {'id': ('Int', 2)})
        qgls = gql + gql2

        qgls.execute(self.client)
        self.req_mock.assert_called_once()
        data = self.req_mock.call_args_list[0][1]['json']
        self.assertEqual(
            data,
            {
                'operationName': 'query',
                'query': '''
            query query($id0: Int, $id1: Int) {
            
            q0: name(id: $id0) {
            snail {name}
            }
            
            q1: name(id: $id1) {
            snail {name}
            }
            
            }
            ''',
                'variables': {'id0': 1, 'id1': 2},
            },
        )
