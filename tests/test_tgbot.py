from unittest import TestCase, mock
from cli import tgbot
from telegram.user import User
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class Test(TestCase):
    def setUp(self) -> None:
        self.user = User(999999999, 'John', False, 'Valium', 'jval')
        self.cli = mock.MagicMock(args=mock.MagicMock(wtv=False))
        self.bot = tgbot.Notifier('999999999:abcdef/test', self.user.id)
        self.bot._settings_list = [mock.MagicMock(dest='wtv', help='Whatever')]
        self.bot.register_cli(self.cli)
        self.update = mock.MagicMock(effective_user=self.user)
        self.context = mock.MagicMock()

    def test_authorized(self):
        self.bot.cmd_start(self.update, self.context)
        self.update.message.reply_markdown_v2.assert_called_once_with('Hi [John Valium](tg://user?id=999999999)\\!')
        self.update.reset_mock()
        # test unauthorized
        self.user.id = 123123123
        self.bot.cmd_start(self.update, self.context)
        self.update.message.reply_markdown_v2.assert_not_called()

    def test_help(self):
        self.bot.cmd_help(self.update, self.context)
        self.update.message.reply_text.assert_called_once_with(
            '''/stats - My snails stats
/nextmission - Show time to next daily mission
/balance - Current balance (snail count, avax, slime)
/claim - Claim rewards
/incubate - Show current incubation coefficent
/market - Show marketplace stats - volume, floors and highs
/reloadsnails - Reset snails cache
/settings - Toggle bot settings'''
        )

    def test_settings(self):
        self.bot.cmd_settings(self.update, self.context)
        expected_markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton('🔧 wtv: False', callback_data=f'toggle wtv')],
                [
                    InlineKeyboardButton(f'❌ Niente', callback_data='toggle'),
                    InlineKeyboardButton(f'❔ Help', callback_data='toggle __help'),
                ],
            ]
        )
        self.update.message.reply_markdown.assert_called_once_with('Toggle settings', reply_markup=expected_markup)

        self.update.reset_mock()
        self.bot._settings_list = None
        self.bot.cmd_settings(self.update, self.context)
        self.update.message.reply_markdown.assert_called_once_with('No settings available...')

    def test_handle_buttons_toggle(self):
        self.update.callback_query = mock.MagicMock(data='toggle')
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.update.callback_query.edit_message_text.assert_called_once_with(
            text='Did *nothing*, my favorite action', parse_mode='Markdown'
        )

        self.update.callback_query = mock.MagicMock(data='toggle __help')
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.update.callback_query.edit_message_text.assert_called_once_with(
            text='`wtv` Whatever', parse_mode='Markdown'
        )
