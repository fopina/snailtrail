from unittest import TestCase, mock
from cli import tgbot
from telegram.user import User
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class Test(TestCase):
    def setUp(self) -> None:
        self.user = User(999999999, 'John', False, 'Valium', 'jval')
        self.cli = mock.MagicMock(
            args=mock.MagicMock(wtv=False),
            owner='0x2fff',
        )
        self.cli.name = '0x2f'
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
/swapsend - Send all slime to one account (for single swaps)
/incubate - Show current incubation coefficent
/market - Show marketplace stats - volume, floors and highs
/racereview - Review all races to join (that were already notified)
/racepending - View pending races (that you joined)
/reloadsnails - Reset snails cache
/settings - Toggle bot settings
/usethisformissions - Use this chat for mission join notifications'''
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

    def test_swapsend(self):
        self.cli.client.web3.balance_of_slime = lambda: 1
        self.cli.client.web3.get_balance = lambda: 2
        cli2 = mock.MagicMock(
            owner='0x3fff',
            args=mock.MagicMock(wtv=False),
        )
        cli2.name = '0x3f'
        cli2.client.web3.balance_of_slime = lambda: 3
        cli2.client.web3.get_balance = lambda: 4
        self.bot.register_cli(cli2)

        self.bot.cmd_swapsend(self.update, self.context)
        expected_markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton('💰 0x2f: 1.00 / 2.00', callback_data=f'swapsend 0x2fff')],
                [InlineKeyboardButton('💰 0x3f: 3.00 / 4.00', callback_data=f'swapsend 0x3fff')],
                [InlineKeyboardButton(f'❌ Niente', callback_data='toggle')],
            ]
        )
        self.update.message.reply_markdown.assert_called_once()
        self.assertEqual(self.update.message.reply_markdown.call_args_list[0][0], ('Choose a wallet',))
        self.assertEqual(
            str(self.update.message.reply_markdown.call_args_list[0][1]['reply_markup']),
            str(expected_markup),
        )

    def test_handle_buttons_swapsend(self):
        self.cli.client.web3.balance_of_slime = lambda raw=True: 1
        self.cli.client.web3.get_balance = lambda: 2
        self.cli.client.web3.transfer_slime = lambda *a, **b: {'logs': [{'data': '0x1'}]}
        self.cli.client.web3.web3.eth.wait_for_transaction_receipt = lambda *a, **b: {'logs': [{'data': '0x1'}]}
        cli2 = mock.MagicMock(
            owner='0x3fff',
            args=mock.MagicMock(wtv=False),
        )
        cli2.name = '0x3f'
        cli2.client.web3.balance_of_slime = lambda raw=True: 3
        cli2.client.web3.get_balance = lambda: 4
        cli2.client.web3.transfer_slime = lambda *a, **b: {'logs': [{'data': '0x3'}]}
        cli2.client.web3.web3.eth.wait_for_transaction_receipt = lambda *a, **b: {'logs': [{'data': '0x3'}]}
        self.bot.register_cli(cli2)

        self.update.callback_query = mock.MagicMock(data='swapsend')
        self.update.callback_query.message.text = ''
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.update.callback_query.edit_message_reply_markup.assert_called_once_with()

        self.update.callback_query.reset_mock()
        self.update.callback_query = mock.MagicMock(data='swapsend 0x1')
        self.update.callback_query.message.text = ''
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.update.callback_query.edit_message_reply_markup.assert_called_once_with()

        self.update.callback_query.reset_mock()
        self.update.callback_query = mock.MagicMock(data='swapsend 0x2fff')
        self.update.callback_query.message.text = ''
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.assertEqual(len(self.update.callback_query.edit_message_text.call_args_list), 4)
        self.assertEqual(self.update.callback_query.edit_message_text.call_args_list[0][0][0], '*Sending to 0x2f*')
        self.assertEqual(
            self.update.callback_query.edit_message_text.call_args_list[-1][0][0],
            '*Sending to 0x2f*\n0x3f: sent 3e-18 SLIME',
        )

    def test_cmd_balance(self):
        self.cli.client.web3.claimable_slime.return_value = 1
        self.cli.client.web3.balance_of_slime.return_value = 1
        self.cli.client.web3.claimable_wavax.return_value = 1
        self.cli.client.web3.balance_of_wavax.return_value = 1
        self.cli.client.web3.get_balance.return_value = 1
        self.cli.client.web3.balance_of_snails.return_value = 1
        self.bot.cmd_balance(self.update, self.context)
        self.update.message.reply_markdown.assert_called_once_with('Loading balances...')
        self.assertEqual(
            self.update.message.reply_markdown.return_value.edit_text.call_args_list,
            [
                mock.call(text='...Loading...', parse_mode='Markdown'),
                mock.call(
                    text='''\
*SLIME*: 1 / 1.000
*WAVAX*: 1 / 1
*AVAX*: 1.000 / *SNAILS*: 1''',
                    parse_mode='Markdown',
                ),
            ],
        )

    def test_cmd_balance_multi(self):
        cli2 = mock.MagicMock(
            owner='0x3fff',
            args=mock.MagicMock(wtv=False),
        )
        cli2.name = '0x3f'
        self.bot.register_cli(cli2)
        self.cli.client.web3.claimable_slime.return_value = 1
        self.cli.client.web3.balance_of_slime.return_value = 1
        self.cli.client.web3.claimable_wavax.return_value = 1
        self.cli.client.web3.balance_of_wavax.return_value = 1
        self.cli.client.web3.get_balance.return_value = 1
        self.cli.client.web3.balance_of_snails.return_value = 1
        cli2.client.web3.claimable_slime.return_value = 2
        cli2.client.web3.balance_of_slime.return_value = 2
        cli2.client.web3.claimable_wavax.return_value = 2
        cli2.client.web3.balance_of_wavax.return_value = 2
        cli2.client.web3.get_balance.return_value = 2
        cli2.client.web3.balance_of_snails.return_value = 2
        self.bot.cmd_balance(self.update, self.context)
        self.update.message.reply_markdown.assert_called_once_with('Loading balances...')
        reply = self.update.message.reply_markdown.return_value
        self.assertEqual(len(reply.edit_text.call_args_list), 5)
        self.assertEqual(
            reply.edit_text.call_args_list[-1],
            mock.call(
                text='''\
`0x2f`
*SLIME*: 1 / 1.000
*WAVAX*: 1 / 1
*AVAX*: 1.000 / *SNAILS*: 1
`0x3f`
*SLIME*: 2 / 2.000
*WAVAX*: 2 / 2
*AVAX*: 2.000 / *SNAILS*: 2
`Total`
*SLIME*: 6.000
*AVAX*: 9.000
*SNAILS*: 3''',
                parse_mode='Markdown',
            ),
        )
