import tempfile
from unittest import TestCase, mock

from cli import helpers


class Test(TestCase):
    def test_set_queue(self):
        q = helpers.SetQueue(capacity=5)
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
