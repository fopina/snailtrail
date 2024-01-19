from unittest import TestCase

from cli import templates
from snail.gqlclient import types as gtypes


class Test(TestCase):
    def test_cheap_soon_join(self):
        self.assertEqual(
            templates.render_cheap_soon_join(gtypes.Snail({'name': 'x', 'id': 1}), gtypes.Race({'id': 2})),
            'Joined cheap last spot without need - x (#1) on 2',
        )
