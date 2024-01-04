from unittest import TestCase, mock

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.user import User

from cli import tempconfigparser, tgbot


class Test(TestCase):
    def setUp(self) -> None:
        self.user = User(999999999, 'John', False, 'Valium', 'jval')
        mparser = tempconfigparser.ArgumentParser()
        parsers = mparser.add_subparsers(title='cmd', dest='cmd')
        parser = parsers.add_parser('bot')
        parser.add_argument('--css-minimum', type=int, help='css')
        parser.add_argument('--wtv', action='store_true', help='Whatever')
        parser.add_argument('--css-fee', nargs=2, type=int, help='Whatever Other')
        parser.add_argument('--choose', type=int, choices=(1, 2), default=1, help='Whatever Other')
        parser.add_argument('--wtv-list', type=float, action='append', help='Whatever List')
        args = mparser.parse_args(['bot', '--css-minimum', '0'], config_file_contents='')
        self.main_parser = mparser
        self.bot_parser = parser
        self.cli = mock.MagicMock(
            args=args,
            owner='0x2fff',
        )
        self.cli.name = '0x2f'
        self.bot = tgbot.Notifier('999999999:abcdef/test', self.user.id)
        self.bot.cli_parser = mparser
        self.bot.register_cli(self.cli)
        self.update = mock.MagicMock(effective_user=self.user)
        self.update.message.chat.id = self.user.id
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
/boosted - List currently boosted snails
/stats - My snails stats
/fee - Display current avalanche fees
/botstats - Display current bot statistics
/markettournament - Show market great buys for this month's tournament
/balancebalance - Distribute AVAX balance from richest wallet to the others
/reloadsnails - Reset snails cache (and reload wallet guilds)
/settings - Toggle bot settings
/usethisformissions - Use this chat for mission join notifications'''
        )

    def test_exposed_settings(self):
        from cli import build_parser

        # load all the real settings
        p = build_parser()
        self.cli.args = p.parse_args(['bot', '--css-minimum', '0'])
        self.bot.cli_parser = p
        self.update.callback_query = mock.MagicMock(data='toggle __help')
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.update.callback_query.edit_message_text.assert_called_once()
        self.assertEqual(
            self.update.callback_query.edit_message_text.mock_calls[0][2]['parse_mode'],
            'Markdown',
        )
        settings = [
            line.split('`')[1]
            for line in self.update.callback_query.edit_message_text.mock_calls[0][2]['text'].splitlines()
        ]
        self.assertEqual(
            settings,
            [
                'missions',
                'mission_chat_id',
                'exclude',
                'boost',
                'boost_pure',
                'boost_to',
                'boost_not_cheap',
                'minimum_tickets',
                'cheap',
                'cheap_soon',
                'races',
                'races_join',
                'race_stats',
                'race_matches',
                'race_price',
                'races_over',
                'mission_matches',
                'market',
                'coefficent',
                'burn',
                'tournament',
                'no_adapt',
                'wait',
                'paused',
                'auto_claim',
                'level_ups',
                'level_ups_to_15',
                'tournament_market',
                'fee_monitor',
                'css_minimum',
                'fee_spike',
                'mission_priority_fee',
            ],
        )

        self.update.callback_query = mock.MagicMock(data='toggle __all')
        self.cli.args.wtv_other = 2
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.update.callback_query.edit_message_text.assert_called_once()
        settings = [
            line.split('`')[1] if line and line[0] == '`' else None
            for line in self.update.callback_query.edit_message_text.mock_calls[0][2]['text'].splitlines()
        ]
        self.assertEqual(
            settings,
            [
                'boost_wallet',
                None,
                None,
                'data_dir',
                None,
                None,
                'balance_balance',
                None,
                None,
                'css_fee',
                None,
            ],
        )

    def test_settings(self):
        self.bot.cmd_settings(self.update, self.context)
        expected_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton('🔧 [0] css_minimum', callback_data=f'toggle css_minimum'),
                    InlineKeyboardButton('🔧 🔴 wtv', callback_data=f'toggle wtv'),
                ],
                [
                    InlineKeyboardButton('🔧 [1] choose', callback_data=f'toggle choose'),
                    InlineKeyboardButton('🔧 ❌ wtv_list', callback_data=f'toggle wtv_list'),
                ],
                [
                    InlineKeyboardButton(f'📇 Show all', callback_data='toggle __all'),
                    InlineKeyboardButton(f'❌ Niente', callback_data='toggle'),
                    InlineKeyboardButton(f'❔ Help', callback_data='toggle __help'),
                ],
            ]
        )
        self.update.message.reply_markdown.assert_called_once_with('Toggle settings', reply_markup=mock.ANY)
        self.assertEqual(
            self.update.message.reply_markdown.mock_calls[0][2]['reply_markup'].to_dict(), expected_markup.to_dict()
        )

        self.update.reset_mock()
        self.bot._settings_list = None
        self.bot.cmd_settings(self.update, self.context)
        self.update.message.reply_markdown.assert_called_once_with('No settings available...')

    def test_handle_buttons_toggle_nothing(self):
        self.update.callback_query = mock.MagicMock(data='toggle')
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.update.callback_query.edit_message_text.assert_called_once_with(
            text='Did *nothing*, my favorite action', parse_mode='Markdown'
        )

    def test_handle_buttons_toggle_boolean(self):
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

        self.update.callback_query = mock.MagicMock(data='toggle it wtv')
        self.update.callback_query.message.chat.id = self.user.id
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.update.callback_query.edit_message_text.assert_called_once_with(
            text='Toggled *wtv* to *True*', parse_mode='Markdown'
        )
        self.assertEqual(self.cli.args.wtv, True)

        self.update.callback_query.answer.reset_mock()
        self.update.callback_query.edit_message_text.reset_mock()
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.update.callback_query.edit_message_text.assert_called_once_with(
            text='Toggled *wtv* to *False*', parse_mode='Markdown'
        )
        self.assertEqual(self.cli.args.wtv, False)

    def test_handle_buttons_toggle_append_action(self):
        self.bot.updater.bot.send_message = mock.MagicMock()
        self.update.callback_query = mock.MagicMock(data='toggle wtv_list')
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.update.callback_query.edit_message_text.assert_called_once_with(
            text='`wtv_list`\nWhatever List\n```\n\n```', reply_markup=None, parse_mode='Markdown'
        )
        self.assertEqual(self.cli.args.wtv_list, None)

        self.update.message = mock.MagicMock(
            reply_to_message=mock.MagicMock(text='wtv_list'),
            text='2.0',
        )
        self.update.message.chat.id = self.user.id
        self.update.message.message_id = 123
        self.bot.cmd_message(self.update, self.context)
        self.bot.updater.bot.send_message.assert_called_once_with(
            999999999,
            text="Toggled *wtv_list* to *[2.0]*",
            reply_to_message_id=123,
            reply_markup=mock.ANY,
            parse_mode='Markdown',
        )
        self.assertEqual(self.cli.args.wtv_list, [2])

        self.update.message = mock.MagicMock(
            reply_to_message=mock.MagicMock(text='wtv_list'),
            text='3\n4',
        )
        self.bot.updater.bot.send_message.reset_mock()
        self.update.message.chat.id = self.user.id
        self.update.message.message_id = 123
        self.bot.cmd_message(self.update, self.context)
        self.bot.updater.bot.send_message.assert_called_once_with(
            999999999,
            text="Toggled *wtv_list* to *[3.0, 4.0]*",
            reply_to_message_id=123,
            reply_markup=mock.ANY,
            parse_mode='Markdown',
        )
        self.assertEqual(self.cli.args.wtv_list, [3, 4])

        self.update.message = mock.MagicMock(
            reply_to_message=mock.MagicMock(text='wtv_list'),
            text='empty',
        )
        self.bot.updater.bot.send_message.reset_mock()
        self.update.message.chat.id = self.user.id
        self.update.message.message_id = 123
        self.bot.cmd_message(self.update, self.context)
        self.bot.updater.bot.send_message.assert_called_once_with(
            999999999,
            text='Toggled *wtv_list* to *None*',
            reply_to_message_id=123,
            reply_markup=mock.ANY,
            parse_mode='Markdown',
        )
        self.assertEqual(self.cli.args.wtv_list, None)

        self.update.message = mock.MagicMock(
            reply_to_message=mock.MagicMock(text='wtv_list'),
            text='a',
        )
        self.bot.updater.bot.send_message.reset_mock()
        self.update.message.chat.id = self.user.id
        self.update.message.message_id = 123
        self.bot.cmd_message(self.update, self.context)
        self.bot.updater.bot.send_message.assert_called_once_with(
            999999999,
            text="`argument --wtv-list: invalid float value: 'a'`",
            reply_to_message_id=123,
            reply_markup=mock.ANY,
            parse_mode='Markdown',
        )
        self.assertEqual(self.cli.args.wtv_list, None)

    def test_handle_buttons_toggle_choices(self):
        self.bot.updater.bot.send_message = mock.MagicMock()
        self.update.callback_query = mock.MagicMock(data='toggle choose')
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.update.callback_query.edit_message_text.assert_called_once_with(
            text='`choose`\nWhatever Other\n```\n1\n```', reply_markup=None, parse_mode='Markdown'
        )
        self.assertEqual(self.cli.args.choose, 1)

        self.update.message = mock.MagicMock(
            reply_to_message=mock.MagicMock(text='choose'),
            text='2',
        )
        self.update.message.chat.id = self.user.id
        self.update.message.message_id = 123
        self.bot.cmd_message(self.update, self.context)
        self.bot.updater.bot.send_message.assert_called_once_with(
            999999999,
            text='Toggled *choose* to *2*',
            reply_to_message_id=123,
            reply_markup=mock.ANY,
            parse_mode='Markdown',
        )
        self.assertEqual(self.cli.args.choose, 2)

        self.update.message = mock.MagicMock(
            reply_to_message=mock.MagicMock(text='choose'),
            text='empty',
        )
        self.bot.updater.bot.send_message.reset_mock()
        self.update.message.chat.id = self.user.id
        self.update.message.message_id = 123
        self.bot.cmd_message(self.update, self.context)
        self.bot.updater.bot.send_message.assert_called_once_with(
            999999999,
            text='Toggled *choose* to *1*',
            reply_to_message_id=123,
            reply_markup=mock.ANY,
            parse_mode='Markdown',
        )
        self.assertEqual(self.cli.args.choose, 1)

        self.update.message = mock.MagicMock(
            reply_to_message=mock.MagicMock(text='choose'),
            text='8',
        )
        self.bot.updater.bot.send_message.reset_mock()
        self.update.message.chat.id = self.user.id
        self.update.message.message_id = 123
        self.bot.cmd_message(self.update, self.context)
        self.bot.updater.bot.send_message.assert_called_once_with(
            999999999,
            text='`argument --choose: invalid choice: 8 (choose from 1, 2)`',
            reply_to_message_id=123,
            reply_markup=mock.ANY,
            parse_mode='Markdown',
        )
        self.assertEqual(self.cli.args.choose, 1)

    def test_handle_buttons_toggle_help(self):
        self.update.callback_query = mock.MagicMock(data='toggle __help')
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.update.callback_query.edit_message_text.assert_called_once_with(
            text='''\
`css_minimum` \\[0] css
`wtv` 🔴 Whatever
`choose` \\[1] Whatever Other
`wtv_list` ❌ Whatever List''',
            parse_mode='Markdown',
        )

        self.update.callback_query = mock.MagicMock(data='toggle __all')
        self.cli.args.css_fee = (2, 2)
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.update.callback_query.edit_message_text.assert_called_once_with(
            text='`css_fee` = `(2, 2)`\nWhatever Other\n', parse_mode='Markdown'
        )

    def test_claim(self):
        cli2 = mock.MagicMock(
            owner='0x3fff',
            args=mock.MagicMock(wtv=False),
        )
        cli2.name = '0x3f'
        self.bot.register_cli(cli2)

        self.cli.client.web3.multicall_balances.return_value = {
            self.cli.owner: [1, 1, 1, 1, 1],
            cli2.owner: [1, 1, 1, 1, 3],
        }

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
        self.assertEqual(len(self.update.callback_query.edit_message_text.call_args_list), 2)
        self.assertEqual(
            self.update.callback_query.edit_message_text.call_args_list[-1][0][0],
            'claimed 1e-18 from 0x2f\n*Total claimed*: 1e-18',
        )

        self.update.callback_query.reset_mock()
        self.update.callback_query = mock.MagicMock(data='claim')
        self.update.callback_query.message.text = ''
        self.bot.handle_buttons(self.update, self.context)
        self.update.callback_query.answer.assert_called_once_with()
        self.assertEqual(len(self.update.callback_query.edit_message_text.call_args_list), 3)
        self.assertEqual(
            self.update.callback_query.edit_message_text.call_args_list[0][0][0],
            'claiming from 0x2f...\nclaiming from 0x3f...\nclaimed 1e-18 from 0x2f',
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
        self.cli.client.web3.swap_slime_avax.side_effect = [10000000000000000, {'status': 1}]
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
        self.assertEqual(len(self.update.callback_query.edit_message_text.call_args_list), 7)
        self.assertEqual(
            self.update.callback_query.edit_message_text.call_args_list[0][0][0],
            'claiming from 0x2f...\nclaiming from 0x3f...\nclaimed 1e-18 from 0x2f',
        )
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
        # mock value taken from test_cli::test_balance
        self.cli._balance.return_value = {'SLIME': (1, 1), 'WAVAX': (1, 1), 'AVAX': 1, 'SNAILS': 1}
        self.bot.cmd_balance(self.update, self.context)
        self.update.message.reply_markdown.assert_called_once_with('Loading balances...')
        self.assertEqual(
            self.update.message.reply_markdown.return_value.edit_text.call_args_list,
            [
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
        # mock value taken from test_cli::test_balance
        self.cli._balance.return_value = {'SLIME': (1, 1), 'WAVAX': (1, 1), 'AVAX': 1, 'SNAILS': 1}
        cli2.client.web3.claimable_slime.return_value = 2
        cli2.client.web3.claimable_wavax.return_value = 2
        cli2.client.web3.get_balance.return_value = 2
        cli2._balance.return_value = {'SLIME': (2, 2), 'WAVAX': (2, 2), 'AVAX': 2, 'SNAILS': 2}
        self.bot.cmd_balance(self.update, self.context)
        self.update.message.reply_markdown.assert_called_once_with('Loading balances...')
        reply = self.update.message.reply_markdown.return_value
        self.assertEqual(len(reply.edit_text.call_args_list), 1)
        self.assertEqual(
            reply.edit_text.call_args_list[-1],
            mock.call(
                text='''\
`>> 0x2f`
🧪 1 / 1.000
*WAVAX*: 1 / 1
🔺 1.000 / 🐌 1
`>> 0x3f`
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

    def test_notify(self):
        send_mock = mock.MagicMock()
        self.bot.updater.bot.send_message = send_mock

        self.bot.notify('hello #12345, how are you?')
        send_mock.assert_called_once_with(
            999999999,
            'hello #12345, how are you?',
            parse_mode='Markdown',
            disable_notification=False,
            reply_markup=None,
        )

        send_mock.reset_mock()
        self.bot.notify('hello Snail #12345, how are you?')
        send_mock.assert_called_once_with(
            999999999,
            'hello [Snail #12345](https://www.snailtrail.art/snails/12345/about), how are you?',
            parse_mode='Markdown',
            disable_notification=False,
            reply_markup=None,
        )

        send_mock.reset_mock()
        self.bot.notify('hello John (#12345), how are you?')
        send_mock.assert_called_once_with(
            999999999,
            'hello John [(#12345)](https://www.snailtrail.art/snails/12345/about), how are you?',
            parse_mode='Markdown',
            disable_notification=False,
            reply_markup=None,
        )
