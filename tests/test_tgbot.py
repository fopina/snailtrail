from unittest import TestCase, mock

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.user import User

from cli import tgbot


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
        self.bot._read_only_settings = [mock.MagicMock(dest='wtv_other', help='Whatever Other')]
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
            '''/nextmission - Show time to next daily mission
/balance - Current balance (snail count, avax, slime)
/guild - Guild stats and balance
/css - Claim, send and swap all slime
/claim - Claim rewards
/swapsend - Send all slime to one account (for single swaps)
/incubate - Show current incubation coefficent
/burn - Show current burn coefficent
/market - Show marketplace stats - volume, floors and highs
/racereview - Review all races to join (that were already notified)
/racepending - View pending races (that you joined)
/inventory - Inventory items
/stats - My snails stats
/balancebalance - Balance all accounts with 1.2 AVAX
/reloadsnails - Reset snails cache
/settings - Toggle bot settings
/usethisformissions - Use this chat for mission join notifications'''
        )

    def test_settings(self):
        self.bot.cmd_settings(self.update, self.context)
        expected_markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton('🔧 🔴 wtv', callback_data=f'toggle wtv')],
                [
                    InlineKeyboardButton(f'📇 Show all', callback_data='toggle __all'),
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

        self.assertEqual(self.cli.args.wtv, False)
        expected_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        '🟢 Enable',
                        callback_data='toggle it wtv',
                    )
                ],
                [InlineKeyboardButton(f'❌ Niente', callback_data='toggle')],
            ]
        )
        self.update.callback_query = mock.MagicMock(data='toggle wtv')
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.update.callback_query.edit_message_text.assert_called_once_with(
            text='`wtv` 🔴\nWhatever', reply_markup=expected_markup, parse_mode='Markdown'
        )
        self.assertEqual(self.cli.args.wtv, False)

        self.assertEqual(self.cli.args.wtv, False)
        self.update.callback_query = mock.MagicMock(data='toggle it wtv')
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.update.callback_query.edit_message_text.assert_called_once_with(
            text='Toggled *wtv* to *True*', parse_mode='Markdown'
        )
        self.assertEqual(self.cli.args.wtv, True)

        self.update.callback_query = mock.MagicMock(data='toggle __help')
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.update.callback_query.edit_message_text.assert_called_once_with(
            text='`wtv` 🟢 Whatever', parse_mode='Markdown'
        )

        self.update.callback_query = mock.MagicMock(data='toggle __all')
        self.cli.args.wtv_other = 2
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.update.callback_query.edit_message_text.assert_called_once_with(
            text='`wtv_other` = `2`\nWhatever Other', parse_mode='Markdown'
        )

    def test_claim(self):
        self.cli.client.web3.balance_of_slime = lambda: 1
        self.cli.client.web3.claimable_slime = lambda: 1
        self.cli.client.web3.get_balance = lambda: 2
        cli2 = mock.MagicMock(
            owner='0x3fff',
            args=mock.MagicMock(wtv=False),
        )
        cli2.name = '0x3f'
        cli2.client.web3.balance_of_slime = lambda: 3
        cli2.client.web3.claimable_slime = lambda: 3
        cli2.client.web3.get_balance = lambda: 4
        self.bot.register_cli(cli2)

        self.bot.cmd_claim(self.update, self.context)
        expected_markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton('💰 0x2f: 1', callback_data=f'claim 0x2fff')],
                [InlineKeyboardButton('💰 0x3f: 3', callback_data=f'claim 0x3fff')],
                [InlineKeyboardButton('All', callback_data='claim')],
                [InlineKeyboardButton(f'❌ Niente', callback_data='toggle')],
            ]
        )
        self.update.message.reply_markdown.assert_called_once()
        self.assertEqual(self.update.message.reply_markdown.call_args_list[0][0], ('Choose an option',))
        self.assertEqual(
            str(self.update.message.reply_markdown.call_args_list[0][1]['reply_markup']),
            str(expected_markup),
        )

    def test_handle_buttons_claim(self):
        self.cli.client.web3.balance_of_slime = lambda raw=True: 1
        self.cli.client.web3.get_balance = lambda: 2
        self.cli.client.web3.claim_rewards = lambda *a, **b: {'logs': [{'data': '0x1'}]}
        self.cli.client.web3.web3.eth.wait_for_transaction_receipt = lambda *a, **b: {
            'status': 1,
            'logs': [{'data': '0x1'}],
        }
        cli2 = mock.MagicMock(
            owner='0x3fff',
            args=mock.MagicMock(wtv=False),
        )
        cli2.name = '0x3f'
        cli2.client.web3.balance_of_slime = lambda raw=True: 3
        cli2.client.web3.get_balance = lambda: 4
        cli2.client.web3.claim_rewards = lambda *a, **b: {'logs': [{'data': '0x3'}]}
        cli2.client.web3.web3.eth.wait_for_transaction_receipt = lambda *a, **b: {
            'status': 2,
            'logs': [{'data': '0x3'}],
        }
        self.bot.register_cli(cli2)

        self.update.callback_query.reset_mock()
        self.update.callback_query = mock.MagicMock(data='claim 0x1')
        self.update.callback_query.message.text = ''
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.update.callback_query.edit_message_reply_markup.assert_called_once_with()

        self.update.callback_query.reset_mock()
        self.update.callback_query = mock.MagicMock(data='claim 0x2fff')
        self.update.callback_query.message.text = ''
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.assertEqual(len(self.update.callback_query.edit_message_text.call_args_list), 3)
        self.assertEqual(self.update.callback_query.edit_message_text.call_args_list[0][0][0], 'claiming from 0x2f...')
        self.assertEqual(
            self.update.callback_query.edit_message_text.call_args_list[-1][0][0],
            'claimed 1e-18 from 0x2f\n*Total claimed*: 1e-18',
        )

        self.update.callback_query.reset_mock()
        self.update.callback_query = mock.MagicMock(data='claim')
        self.update.callback_query.message.text = ''
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.assertEqual(len(self.update.callback_query.edit_message_text.call_args_list), 5)
        self.assertEqual(self.update.callback_query.edit_message_text.call_args_list[0][0][0], 'claiming from 0x2f...')
        self.assertEqual(
            self.update.callback_query.edit_message_text.call_args_list[1][0][0],
            'claiming from 0x2f...\nclaiming from 0x3f...',
        )
        self.assertEqual(
            self.update.callback_query.edit_message_text.call_args_list[-1][0][0],
            'claimed 1e-18 from 0x2f\nclaim FAILED for 0x3f\n*Total claimed*: 1e-18',
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
            '*Sending to 0x2f*\n0x3f: sent 3e-18 SLIME\n*Total sent*: 3e-18',
        )

    def test_css(self):
        cli2 = mock.MagicMock(
            owner='0x3fff',
            args=mock.MagicMock(wtv=False),
        )
        cli2.name = '0x3f'
        self.bot.register_cli(cli2)

        self.bot.cmd_css(self.update, self.context)
        expected_markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton('0x2f', callback_data=f'css 0x2fff')],
                [InlineKeyboardButton('0x3f', callback_data=f'css 0x3fff')],
                [InlineKeyboardButton(f'❌ Niente', callback_data='toggle')],
            ]
        )
        self.update.message.reply_markdown.assert_called_once()
        self.assertEqual(self.update.message.reply_markdown.call_args_list[0][0], ('Choose an option',))
        self.assertEqual(
            str(self.update.message.reply_markdown.call_args_list[0][1]['reply_markup']),
            str(expected_markup),
        )

    def test_handle_buttons_css(self):
        self.cli.client.web3.balance_of_slime = lambda raw=True: 1500000000000000000
        self.cli.client.web3.get_balance = lambda: 2
        self.cli.client.web3.claim_rewards = lambda *a, **b: {'logs': [{'data': '0x1'}]}
        self.cli.client.web3.transfer_slime = lambda *a, **b: {'logs': [{'data': '0x1'}]}
        self.cli.client.web3.web3.eth.wait_for_transaction_receipt.side_effect = [
            {
                'status': 1,
                'logs': [{'data': '0x1'}],
            },
            {'logs': [{'data': '0x1'}]},
        ]
        cli2 = mock.MagicMock(
            owner='0x3fff',
            args=mock.MagicMock(wtv=False),
        )
        self.cli.client.web3.swap_slime_avax.return_value = 10000000000000000
        cli2.name = '0x3f'
        cli2.client.web3.balance_of_slime = lambda raw=True: 3000000000000000000
        cli2.client.web3.get_balance = lambda: 4
        cli2.client.web3.claim_rewards = lambda *a, **b: {'logs': [{'data': '0x3'}]}
        cli2.client.web3.transfer_slime = lambda *a, **b: {'logs': [{'data': '0x3'}]}
        cli2.client.web3.web3.eth.wait_for_transaction_receipt.side_effect = [
            {
                'status': 2,
                'logs': [{'data': '0x3'}],
            },
            {'logs': [{'data': '0x3'}]},
        ]
        self.bot.register_cli(cli2)

        self.update.callback_query.reset_mock()
        self.update.callback_query = mock.MagicMock(data='css')
        self.update.callback_query.message.text = ''
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.update.callback_query.edit_message_reply_markup.assert_called_once_with()

        self.update.callback_query.reset_mock()
        self.update.callback_query = mock.MagicMock(data='css 0x1')
        self.update.callback_query.message.text = ''
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.update.callback_query.edit_message_reply_markup.assert_called_once_with()

        self.update.callback_query.reset_mock()
        self.update.callback_query = mock.MagicMock(data='css 0x2fff')
        self.update.callback_query.message.text = ''
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.assertEqual(len(self.update.callback_query.edit_message_text.call_args_list), 10)
        self.assertEqual(self.update.callback_query.edit_message_text.call_args_list[0][0][0], 'claiming from 0x2f...')
        self.assertEqual(
            self.update.callback_query.edit_message_text.call_args_list[-1][0][0],
            '''claimed 1e-18 from 0x2f
claim FAILED for 0x3f
*Total claimed*: 1e-18

0x3f: sent 3e-18 SLIME
*Total sent*: 3e-18

Swapped 1.50 SLIME for 0.01 AVAX ✅''',
        )

    def test_cmd_balance(self):
        self.cli.client.web3.claimable_slime.return_value = 1
        self.cli.client.web3.claimable_wavax.return_value = 1
        self.cli.client.web3.get_balance.return_value = 1
        self.cli.client.web3.multicall_balances.return_value = {self.cli.owner: [1, 1, 1]}
        # mock value taken from test_cli::test_balance
        self.cli._balance.return_value = {'SLIME': (1, 1), 'WAVAX': (1, 1), 'AVAX': 1, 'SNAILS': 1}
        self.bot.cmd_balance(self.update, self.context)
        self.update.message.reply_markdown.assert_called_once_with('Loading balances...')
        self.assertEqual(
            self.update.message.reply_markdown.return_value.edit_text.call_args_list,
            [
                mock.call(text='...Loading...', parse_mode='Markdown'),
                mock.call(
                    text='''\
🧪 1 / 1.000
*WAVAX*: 1 / 1
🔺 1.000 / 🐌 1''',
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
        self.cli.client.web3.claimable_wavax.return_value = 1
        self.cli.client.web3.get_balance.return_value = 1
        self.cli.client.web3.multicall_balances.return_value = {self.cli.owner: [1, 1, 1], cli2.owner: [2, 2, 2]}
        # mock value taken from test_cli::test_balance
        self.cli._balance.return_value = {'SLIME': (1, 1), 'WAVAX': (1, 1), 'AVAX': 1, 'SNAILS': 1}
        cli2.client.web3.claimable_slime.return_value = 2
        cli2.client.web3.claimable_wavax.return_value = 2
        cli2.client.web3.get_balance.return_value = 2
        cli2._balance.return_value = {'SLIME': (2, 2), 'WAVAX': (2, 2), 'AVAX': 2, 'SNAILS': 2}
        self.bot.cmd_balance(self.update, self.context)
        self.update.message.reply_markdown.assert_called_once_with('Loading balances...')
        reply = self.update.message.reply_markdown.return_value
        self.assertEqual(len(reply.edit_text.call_args_list), 5)
        self.assertEqual(
            reply.edit_text.call_args_list[-1],
            mock.call(
                text='''\
`0x2f`
🧪 1 / 1.000
*WAVAX*: 1 / 1
🔺 1.000 / 🐌 1
`0x3f`
🧪 2 / 2.000
*WAVAX*: 2 / 2
🔺 2.000 / 🐌 2
`Total`
🧪 6.000
🔺 9.000
🐌 3''',
                parse_mode='Markdown',
            ),
        )
