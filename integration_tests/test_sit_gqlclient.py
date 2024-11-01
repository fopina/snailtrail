import os
import sys
import unittest
from pathlib import Path
from unittest import TestCase

import pytest

sys.path.append(str(Path(__file__).absolute().parent.parent))

from cli import DEFAULT_GOTLS_PATH
from snail import gqlclient, proxy

# yes, these are mine, feel free to send avax/slime/eth
TEST_ADDRESS = '0xd991975e1C72E43C5702ced3230dA484442F195a'
TEST_SNAIL = 17796
TEST_ADDRESS2 = '0x9ED8Fbd1af94d34e99119Bee2d64b7b00d637E76'


@pytest.mark.allow_hosts(['127.0.0.1'])
class Test(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.proxy = proxy.Proxy(DEFAULT_GOTLS_PATH)
        cls.proxy.start()
        cls.client = gqlclient.Client(url=cls.proxy.url(), rate_limiter=1, retry=3)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.proxy.stop()

    def test_marketplace_stats(self):
        r = self.client.marketplace_stats()
        self.assertEqual(r['floors'][0]['name'], 'Garden')
        r = self.client.marketplace_stats(market=0)
        self.assertEqual(r['floors'][0]['name'], 'Garden')

    def test_profile(self):
        r = self.client.profile([TEST_ADDRESS, TEST_ADDRESS2])
        self.assertEqual(r['profile0']['address'], TEST_ADDRESS)
        self.assertEqual(r['profile1']['address'], TEST_ADDRESS2)

    def test_get_onboarding_races(self):
        r = self.client.get_onboarding_races(limit=1)
        self.assertEqual(len(r['all']), 1)
        self.assertIn('track', r['all'][0])

    def test_get_mission_races(self):
        r = self.client.get_mission_races(limit=1)
        self.assertEqual(len(r['all']), 1)
        self.assertIn('track', r['all'][0])
        self.assertEqual(r['all'][0]['__typename'], 'Race')

    def test_get_all_snails(self):
        r = self.client.get_all_snails(filters={'id': TEST_SNAIL})
        self.assertEqual(len(r['snails']), 1)
        self.assertFalse(r['snails'][0]['new_born'])

    def test_get_all_snails_marketplace(self):
        r = self.client.get_all_snails_marketplace(limit=1)
        self.assertEqual(len(r['snails']), 1)
        self.assertIsNotNone(r['snails'][0]['market']['on_sale'])

    def test_name_change(self):
        r = self.client.name_change('short')
        self.assertTrue(r['status'])

    def test_join_competitive_races(self):
        with self.assertRaisesRegex(gqlclient.APIError, 'Signature does not match the information.'):
            self.client.join_competitive_races(
                TEST_SNAIL,
                171971,
                TEST_ADDRESS,
                '0x66287e0465f644bad50cab950218ee6386f0e19bde3be4fad34f473b33f806c0177718d8ddb4ffe0149e3098b20abc1a382c6c77d7f4b7f61f6f4fa33f8f47641c',
            )

    def test_join_mission_races(self):
        with self.assertRaisesRegex(gqlclient.APIError, 'Signature does not match the information.'):
            self.client.join_mission_races(
                TEST_SNAIL,
                171971,
                '0x66287e0465f644bad50cab950218ee6386f0e19bde3be4fad34f473b33f806c0177718d8ddb4ffe0149e3098b20abc1a382c6c77d7f4b7f61f6f4fa33f8f47641c',
            )

    def test_get_my_snails_for_ranked(self):
        r = self.client.get_my_snails_for_ranked(TEST_ADDRESS, 5)
        self.assertIn(TEST_SNAIL, {x['id'] for x in r['snails']})

    def test_get_my_snails_for_missions(self):
        r = self.client.get_my_snails_for_missions(TEST_ADDRESS)
        self.assertIn(TEST_SNAIL, {x['id'] for x in r['snails']})

    def test_get_race_history(self):
        with self.assertRaisesRegex(Exception, "Field 'token_id' of required type 'Int!'"):
            self.client.get_race_history()
        r = self.client.get_race_history(limit=1, filters={'token_id': TEST_SNAIL})
        self.assertEqual(len(r['races']), 1)
        self.assertEqual(r['races'][0]['__typename'], 'Race')

    def test_get_finished_races(self):
        r = self.client.get_finished_races(limit=1)
        self.assertEqual(len(r['all']), 1)
        self.assertEqual(r['all'][0]['__typename'], 'Race')


if __name__ == '__main__':
    unittest.main()
