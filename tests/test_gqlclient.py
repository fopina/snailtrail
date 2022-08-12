from unittest import TestCase, mock
from snail import gqlclient
import gql
from graphql.error.syntax_error import GraphQLSyntaxError
from pathlib import Path


class Test(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        schema_file = Path(__file__).parent / 'schema.graphql'
        cls.gql = gql.Client(schema=schema_file.read_text())

    def setUp(self) -> None:
        self.client = gqlclient.Client()
        self.req_mock = mock.MagicMock()
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
