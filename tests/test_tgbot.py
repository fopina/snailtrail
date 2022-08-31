from unittest import TestCase, mock
from cli import tgbot
from telegram.user import User
from telegram import Update, constants, InlineKeyboardButton, InlineKeyboardMarkup
from pathlib import Path


class Test(TestCase):
    def setUp(self) -> None:
        self.user = User(999999999, 'John', False, 'Valium', 'jval')
        self.bot = tgbot.Notifier('999999999:abcdef/test', self.user.id)
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
/incubate - Show current incubation coefficent
/market - Show marketplace stats - volume, floors and highs
/reloadsnails - Reset snails cache
/settings - Toggle bot settings'''
        )

    def test_settings(self):
        self.bot.cmd_settings(self.update, self.context)
        self.update.message.reply_markdown.assert_called_once_with('No settings available...')

        self.update.reset_mock()
        self.bot.clis[0] = mock.MagicMock(args=mock.MagicMock(wtv=False))
        self.bot._settings_list = [mock.MagicMock(dest='wtv')]
        self.bot.cmd_settings(self.update, self.context)
        expected_markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton('🔧 wtv: False', callback_data=f'toggle wtv')],
                [InlineKeyboardButton(f'❌ Niente', callback_data='toggle')],
            ]
        )
        self.update.message.reply_markdown.assert_called_once_with('Toggle settings', reply_markup=expected_markup)
