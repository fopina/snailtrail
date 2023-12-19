import tempfile
from pathlib import Path
from unittest import TestCase

from cli import database
from cli.helpers import SetQueue


class Test(TestCase):
    def test_dump(self):
        db = database.GlobalDB()
        w = db.add_wallet("x")
        self.assertEqual(w.notified_races.__class__, SetQueue)
        self.assertEqual(db.wallets['x'].global_db, db)
        self.assertEqual(db.model_dump(), {"fee_spike_start": None, "fee_spike_notified": False})
        self.assertEqual(
            w.model_dump(),
            {
                "slime_won": 0,
                'notify_burn_coefficent': None,
                'notify_fee_monitor': None,
                "notified_races": [],
                "notified_races_over": [],
                "joins_last": [],
                "joins_normal": [],
                'slime_won_last': 0,
                'slime_won_normal': 0,
                'tournament_market_cache': {},
            },
        )

    def test_load(self):
        db = database.GlobalDB(**{"wallets": {"x": {"slime_won": 1.5, "notified_races": {1: None}}}})
        self.assertEqual(db.wallets['x'].global_db, db)
        self.assertEqual(db.wallets['x'].slime_won, 1.5)
        self.assertEqual(db.wallets['x'].notified_races, {1: None})
        self.assertEqual(db.wallets['x'].notified_races.__class__, SetQueue)

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_file = tmp_path / 'db.json'

            # load from non-existing file
            db = database.GlobalDB.load_from_file(db_file)
            self.assertEqual(db.wallets, {})

            wdb = db.add_wallet("x")
            wdb.slime_won = 2
            wdb.save()

            another_db = database.GlobalDB.load_from_file(db_file)
            another_db.add_wallet('x')
            self.assertEqual(another_db.wallets['x'].slime_won, 2)

    def test_dict_defaults(self):
        db = database.GlobalDB()
        self.assertEqual(db.wallets, {})
        db.wallets['x'] = 2
        db2 = database.GlobalDB()
        self.assertEqual(db2.wallets, {})

    def test_set_queue_defaults(self):
        db = database.WalletDB()
        db.notified_races.add(1)
        self.assertEqual(db.notified_races, {1: None})

        db2 = database.WalletDB()
        self.assertEqual(db2.notified_races, {})

    def test_set_queue_int_key_issue(self):
        """
        notified_races_over is (was?) not working properly due to SetQueue being serialized with string keys
        found bigger issue with SetQueue in general - resolution = serialize SetQueue as list instead of dict
        cleaner and more flexible
        """
        with tempfile.NamedTemporaryFile() as t:
            t = Path(t.name)
            db = database.WalletDB(save_file=t)
            db.notified_races_over.add(1)
            self.assertEqual(db.notified_races_over, {1: None})
            self.assertIn(1, db.notified_races_over)
            self.assertEqual(db.model_dump()['notified_races_over'], [1])
            self.assertTrue(db.save())

            db_copy = database.WalletDB.load_from_file(t)
            self.assertEqual(db_copy.notified_races_over, {1: None})
            self.assertIn(1, db_copy.notified_races_over)

            t.write_text('{"notified_races_over": [2]}')
            db_copy = database.WalletDB.load_from_file(t)
            self.assertEqual(db_copy.notified_races_over, {2: None})

            # test retrocompatibility
            t.write_text('{"notified_races_over": {"2": null}}')
            db_copy = database.WalletDB.load_from_file(t)
            db_copy.notified_races_over.add(2)
            # FIXME: after the datafix is removed, uncomment this again
            # self.assertEqual(db_copy.notified_races_over, {'2': None, 2: None})
            self.assertEqual(db_copy.notified_races_over, {2: None})
            # self.assertEqual(db_copy.model_dump()['notified_races_over'], ['2', 2])
            self.assertEqual(db_copy.model_dump()['notified_races_over'], [2])

    def test_dict_key_issue(self):
        """
        as with test_set_queue_int_key_issue, make sure dict fields with int keys also work
        """
        with tempfile.NamedTemporaryFile() as t:
            t = Path(t.name)
            db = database.WalletDB(save_file=t)
            db.tournament_market_cache[1] = ('a', 1, 2)
            self.assertEqual(db.tournament_market_cache, {1: ('a', 1, 2)})
            self.assertIn(1, db.tournament_market_cache)
            self.assertEqual(db.model_dump()['tournament_market_cache'], {1: ('a', 1, 2)})
            self.assertTrue(db.save())

            db_copy = database.WalletDB.load_from_file(t)
            self.assertEqual(db_copy.tournament_market_cache, {1: ('a', 1, 2)})
            self.assertIn(1, db_copy.tournament_market_cache)

            # test retrocompatibility
            t.write_text('{"tournament_market_cache": {"1": ["a", 1, 2]}}')
            db_copy = database.WalletDB.load_from_file(t)
            self.assertEqual(db_copy.tournament_market_cache, {1: ('a', 1, 2)})
            self.assertIn(1, db_copy.tournament_market_cache)
