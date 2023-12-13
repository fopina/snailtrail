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
        self.assertEqual(db.model_dump_json(), '{}')
        self.assertEqual(
            w.model_dump(),
            {
                "slime_won": 0,
                "notify_auto_claim": None,
                "notified_races": {},
                "notified_races_over": {},
                "joins_last": {},
                "joins_normal": {},
                'slime_won_last': 0,
                'slime_won_normal': 0,
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
