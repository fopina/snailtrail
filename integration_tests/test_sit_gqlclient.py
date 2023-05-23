import sys
from pathlib import Path
import unittest
from unittest import TestCase
import os

sys.path.append(str(Path(__file__).absolute().parent.parent))

from snail import gqlclient, proxy

# yes, it's mine, feel free to send avax/slime/eth
TEST_ADDRESS = '0xd991975e1C72E43C5702ced3230dA484442F195a'
TEST_SNAIL = 8813


class Test(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        preset_proxy = os.getenv('SNAIL_TEST_PROXY')
        if preset_proxy:
            print('using existing proxy', preset_proxy)
            proxy_url = preset_proxy
            cls.proxy = None
        else:
            print('starting proxy')
            cls.proxy = proxy.Proxy()
            cls.proxy.start()
            proxy_url = cls.proxy.url()
        cls.client = gqlclient.Client(proxy=proxy_url, rate_limiter=1, retry=3)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.proxy is not None:
            print('stopping proxy')
            cls.proxy.stop()

    def test_marketplace_stats(self):
        r = self.client.marketplace_stats()
        self.assertEqual(r['floors'][0]['name'], 'Garden')
        r = self.client.marketplace_stats(market=0)
        self.assertEqual(r['floors'][0]['name'], 'Garden')

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
