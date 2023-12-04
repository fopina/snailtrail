from unittest import TestCase, mock

from cli import commands, tempconfigparser


class Test(TestCase):
    @mock.patch('sys.exit')
    def test_parser(self, exit_mock):
        p = tempconfigparser.ArgumentParser()
        p.add_argument('--rental', action=commands.SetRentalAction)
        p.add_argument('--whatever', action=commands.NoRentalStoreTrueAction)
        args = p.parse_args(['--rental'])
        self.assertTrue(args.rental)
        self.assertFalse(args.whatever)
        exit_mock.assert_not_called()

        commands.NoRentalStoreTrueAction.IS_RENTAL = False
        args = p.parse_args(['--whatever'])
        self.assertFalse(args.rental)
        self.assertTrue(args.whatever)
        exit_mock.assert_not_called()

        commands.NoRentalStoreTrueAction.IS_RENTAL = False
        args = p.parse_args(['--rental', '--whatever'])
        exit_mock.assert_called_with(2)
