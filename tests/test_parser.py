from unittest import TestCase, mock

from cli import commands, tempconfigparser


class Test(TestCase):
    def setUp(self) -> None:
        self.exit_patch = mock.patch('sys.exit')
        self.exit_mock = self.exit_patch.start()

    def tearDown(self) -> None:
        self.exit_patch.stop()

    def test_parser(self):
        p = tempconfigparser.ArgumentParser()
        p.add_argument('--rental', action=commands.SetRentalAction)
        p.add_argument('--whatever', action=commands.NoRentalStoreTrueAction)
        args = p.parse_args(['--rental'])
        self.assertTrue(args.rental)
        self.assertFalse(args.whatever)
        self.exit_mock.assert_not_called()

        commands.NoRentalStoreTrueAction.IS_RENTAL = False
        args = p.parse_args(['--whatever'])
        self.assertFalse(args.rental)
        self.assertTrue(args.whatever)
        self.exit_mock.assert_not_called()

        commands.NoRentalStoreTrueAction.IS_RENTAL = False
        args = p.parse_args(['--rental', '--whatever'])
        self.exit_mock.assert_called_with(2)

    def test_append(self):
        # not covering custom code, but just to debug behavior
        p = tempconfigparser.ArgumentParser()
        p.add_argument('--wtv', action='append', type=int)
        args = p.parse_args(['--wtv', '2', '--wtv', '3'])
        self.assertEqual(args.wtv, [2, 3])
        self.exit_mock.assert_not_called()

    def test_nargs(self):
        # not covering custom code, but just to debug behavior
        p = tempconfigparser.ArgumentParser()
        p.add_argument('--wtv', nargs=2, type=int)
        args = p.parse_args(['--wtv', '2', '3'])
        self.assertEqual(args.wtv, [2, 3])
        self.exit_mock.assert_not_called()
