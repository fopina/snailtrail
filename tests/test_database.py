import tempfile
from pathlib import Path
from unittest import TestCase

from cli import database


class Test(TestCase):
    def test_dump(self):
        db = database.GlobalDB()
        db.add_wallet("x")
        self.assertEqual(db.wallets['x'].global_db, db)
        self.assertEqual(db.model_dump_json(), '{"wallets":{"x":{"slime_won":0.0}}}')

    def test_load(self):
        db = database.GlobalDB(**{"wallets": {"x": {"slime_won": 1.5}}})
        self.assertEqual(db.wallets['x'].global_db, db)
        self.assertEqual(db.wallets['x'].slime_won, 1.5)

    def test_persistence(self):
        with tempfile.NamedTemporaryFile() as tmp_file:
            # load from non-existing file
            db = database.GlobalDB.load_from_file(Path(tmp_file.name))
            self.assertEqual(db.wallets, {})

            wdb = db.add_wallet("x")
            wdb.slime_won = 2
            db.save()

            another_db = database.GlobalDB.load_from_file(Path(tmp_file.name))
            self.assertEqual(another_db.wallets['x'].slime_won, 2)
