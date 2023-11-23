import logging
import re
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

import configargparse
from telegram import ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Update, constants
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler, MessageHandler, Updater
from telegram.utils.helpers import escape_markdown

from . import cli, utils
from .cli import DECIMALS

if TYPE_CHECKING:
    from . import multicli

logger = logging.getLogger(__name__)


def escmv2(*a, **b):
    return escape_markdown(*a, version=2, **b)


def bot_auth(func):
    def wrapper_func(notifier, update: Update, context: CallbackContext):
        if not notifier.owner_chat_id or update.effective_user['id'] not in notifier.owner_chat_id:
            logger.error(
                '%s %s (%s / %d) not in allow list',
                update.effective_user['first_name'],
                update.effective_user['last_name'],
                update.effective_user['username'],
                update.effective_user['id'],
            )
            return
        try:
            return func(notifier, update, context)
        except Exception as e:
            logger.exception('error caught')
            update.message.reply_markdown(
                f'''error occurred, check logs
```
{escape_markdown(str(e))}
```
'''
            )

    wrapper_func.__doc__ = func.__doc__
    return wrapper_func


class Notifier:
    clis: Dict[str, 'cli.CLI']
    _owner_chat_id = None

    SNAIL_ID1_RE = re.compile(r'(Snail \#(\d+))')
    SNAIL_ID2_RE = re.compile(r'(\(#(\d+)\))')

    def __init__(self, token, chat_id, owner_chat_id=None):
        self.__token = token
        self.chat_id = chat_id
        self.clis = {}
        self._sent_messages = set()
        self._settings_list = []
        self._read_only_settings = None
        if owner_chat_id is None:
            self.owner_chat_id = {self.chat_id} if self.chat_id else None
        else:
            self.owner_chat_id = owner_chat_id

        if token:
            self.updater = Updater(self.__token)
            dispatcher = self.updater.dispatcher
            dispatcher.add_handler(CommandHandler("start", self.cmd_start))
            dispatcher.add_handler(CallbackQueryHandler(self.handle_buttons))
            dispatcher.add_handler(CommandHandler("nextmission", self.cmd_nextmission))
            dispatcher.add_handler(CommandHandler("balance", self.cmd_balance))
            dispatcher.add_handler(CommandHandler("guild", self.cmd_guild))
            dispatcher.add_handler(CommandHandler("css", self.cmd_css))
            dispatcher.add_handler(CommandHandler("claim", self.cmd_claim))
            dispatcher.add_handler(CommandHandler("swapsend", self.cmd_swapsend))
            dispatcher.add_handler(CommandHandler("incubate", self.cmd_incubate))
            dispatcher.add_handler(CommandHandler("burn", self.cmd_burn))
            dispatcher.add_handler(CommandHandler("market", self.cmd_marketplace_stats))
            dispatcher.add_handler(CommandHandler("racereview", self.cmd_race_review))
            dispatcher.add_handler(CommandHandler("racepending", self.cmd_race_pending))
            dispatcher.add_handler(CommandHandler("inventory", self.cmd_inventory))
            dispatcher.add_handler(CommandHandler("boosted", self.cmd_boosted))
            dispatcher.add_handler(CommandHandler("stats", self.cmd_stats))
            dispatcher.add_handler(CommandHandler("fee", self.cmd_fee))
            dispatcher.add_handler(CommandHandler("balancebalance", self.cmd_balance_balance))
            dispatcher.add_handler(CommandHandler("reloadsnails", self.cmd_reload_snails))
            dispatcher.add_handler(CommandHandler("settings", self.cmd_settings))
            dispatcher.add_handler(CommandHandler("usethisformissions", self.cmd_usethisformissions))
            dispatcher.add_handler(CommandHandler("help", self.cmd_help))
            dispatcher.add_handler(MessageHandler(None, self.cmd_message))
        else:
            self.updater = None

    @property
    def settings(self):
        return self._settings_list

    @settings.setter
    def settings(self, value):
        rw, ro = value
        self._settings_list = rw
        self._read_only_settings = ro

    @property
    def owner_chat_id(self):
        return self._owner_chat_id

    @owner_chat_id.setter
    def owner_chat_id(self, value):
        if value is None:
            self._owner_chat_id = None
        elif isinstance(value, int):
            self._owner_chat_id = {value}
        elif isinstance(value, (list, tuple, set)):
            self._owner_chat_id = set(value)
        else:
            raise ValueError('invalid owner_chat_id type')

    @property
    def any_cli(self) -> 'cli.CLI':
        return list(self.clis.values())[0]

    @property
    def is_multi_cli(self) -> bool:
        return len(self.clis) > 1

    @property
    def main_cli(self) -> 'cli.CLI':
        if self.is_multi_cli:
            for c in self.clis.values():
                if c.report_as_main:
                    return c
        return self.any_cli

    @property
    def multicli(self) -> 'multicli.CLI':
        return self.any_cli.multicli

    def tag_with_wallet(self, cli: 'cli.CLI', output: Optional[list] = None):
        if not self.is_multi_cli:
            return ''
        m = f'`>> {cli.name}`'
        if output is not None:
            output.append(m)
        return m

    def _slow_query(self, query):
        return query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🚧 Loading...', callback_data='ignore')]])
        )

    def register_cli(self, cli):
        self.clis[cli.owner] = cli

    def handle_buttons(self, update: Update, context: CallbackContext) -> None:
        """Parses the CallbackQuery and updates the message text."""
        query = update.callback_query
        query.answer()
        cmd, *opts = query.data.split(' ', 1)
        if cmd == 'ignore':
            return
        if cmd == 'toggle':
            return self.handle_buttons_toggle(opts, update, context)
        elif cmd == 'joinrace':
            return self.handle_buttons_joinrace(opts, update, context)
        elif cmd == 'claim':
            return self.handle_buttons_claim(opts, update, context)
        elif cmd == 'css':
            return self.handle_buttons_css(opts, update, context)
        elif cmd == 'swapsend':
            return self.handle_buttons_swapsend(opts, update, context)
        elif cmd == 'balance_balance':
            return self.handle_buttons_balance_balance(opts, update, context)
        query.edit_message_text(text=f"Unknown option: {query.data}")

    def handle_buttons_toggle(self, opts: str, update: Update, context: CallbackContext) -> None:
        """Process settings toggle"""
        query = update.callback_query
        if not opts:
            query.edit_message_text(text="Did *nothing*, my favorite action", parse_mode='Markdown')
            return

        preview = True
        opts = opts[0]
        if opts[:3] == 'it ':
            opts = opts[3:]
            preview = False

        _cli = self.any_cli

        if opts == '__help':
            m = [
                f'`{setting.dest}` {escape_markdown(self.__setting_value(setting))} {escape_markdown(setting.help)}'
                for setting in self._settings_list
            ]
            query.edit_message_text(text='\n'.join(m), parse_mode='Markdown')
            return

        if opts == '__all':
            if self._read_only_settings is None:
                m = ['No settings available...']
            else:
                m = [
                    f'`{setting.dest}` = `{getattr(_cli.args, setting.dest, None)}`\n{escape_markdown(setting.help)}\n'
                    for setting in self._read_only_settings
                ]
            query.edit_message_text(text='\n'.join(m), parse_mode='Markdown')
            return

        if not hasattr(_cli.args, opts):
            query.edit_message_text(text=f"Unknown setting: {opts}")
            return

        if preview:
            for setting in self._settings_list:
                if setting.dest == opts:
                    break
            else:
                raise Exception('invalid setting', opts)

            ov = getattr(_cli.args, opts)
            if setting.type in (int, float):
                if isinstance(setting, (configargparse.argparse._AppendAction)):
                    ov = '\n'.join(map(str, ov)) if ov else ''
                query.edit_message_text(
                    text=f'`{opts}`\n{escape_markdown(setting.help)}\n```\n{ov}\n```',
                    reply_markup=None,
                    parse_mode='Markdown',
                )
                query.message.reply_markdown(
                    text=f'New value for `{opts}`.\nUse `cancel` to ignore, `empty` to set it to None and multiple lines if it is a multiple argument option.',
                    reply_markup=ForceReply(force_reply=True, input_field_placeholder=ov),
                    reply_to_message_id=query.message.message_id,
                )
            else:
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "🔴 Disable" if ov else "🟢 Enable",
                            callback_data=f'toggle it {setting.dest}',
                        )
                    ],
                    [InlineKeyboardButton(f'❌ Niente', callback_data='toggle')],
                ]
                query.edit_message_text(
                    text=f'`{opts}` {"🟢" if ov else "🔴"}\n{escape_markdown(setting.help)}',
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown',
                )
        else:
            ov = getattr(_cli.args, opts)
            setattr(_cli.args, opts, not ov)
            msg = f"Toggled *{opts}* to *{not ov}*"
            query.edit_message_text(text=msg, parse_mode='Markdown')
            if query.message.chat.id != self.chat_id:
                # also notify main chat
                self.notify(msg)
            _cli.save_bot_settings()

    def handle_buttons_joinrace(self, opts: str, update: Update, context: CallbackContext) -> None:
        """Process join race buttons"""
        query = update.callback_query
        self._slow_query(query)
        if not opts:
            query.edit_message_reply_markup()
            return
        owner, snail_id, race_id = opts[0].split(' ')
        try:
            cli = self.clis[owner]
            r, _ = cli.client.join_competitive_races(int(snail_id), int(race_id), cli.owner)
            query.edit_message_text(query.message.text + '\n✅  Race joined')
        except Exception as e:
            logger.exception('unexpected joinRace error')
            query.edit_message_text(
                query.message.text + f'\n❌ Race FAILED to join: {e}', reply_markup=query.message.reply_markup
            )

    @staticmethod
    def _async_claim(
        clis: 'List[cli.CLI]', cb: Callable[['cli.CLI', int, str, Optional[List[Any]]], None], minimum=None
    ):
        hash_queue = []

        for _cli in clis:
            if minimum:
                _b = _cli.client.web3.claimable_slime()
                if _b > minimum:
                    cb(_cli, 0, f'claiming {_b} from {_cli.name}...')
                else:
                    cb(_cli, 1, f'skipping {_cli.name}, only {_b}...', [0])
                    continue
            else:
                cb(_cli, 0, f'claiming from {_cli.name}...')
            try:
                h = _cli.client.web3.claim_rewards(wait_for_transaction_receipt=False)
                hash_queue.append((_cli, h))
            except cli.client.web3client.exceptions.ContractLogicError as e:
                if 'Nothing to claim' in str(e):
                    cb(_cli, 1, f'nothing claimed from {_cli.name}', [0])
                else:
                    cb(_cli, 2, f'claim FAILED for {_cli.name}: {e}')
                    logger.exception('error claiming')

        # check every receipt
        for _cli, hash in hash_queue:
            try:
                r = _cli.client.web3.web3.eth.wait_for_transaction_receipt(hash, timeout=120)
                if r.get('status') == 1:
                    if len(r['logs']) not in (1, 3):
                        logger.error('weird tx data: %s', r)
                        bal = 0
                    else:
                        ind = 0 if len(r['logs']) == 1 else 1
                        bal = int(r['logs'][ind]['data'], 16) / DECIMALS
                    cb(_cli, 1, f'claimed {bal} from {_cli.name}', [bal])
                else:
                    cb(_cli, 2, f'claim FAILED for {_cli.name}')
                    logger.error('error claiming: %s', r)
            except cli.client.web3client.exceptions.ContractLogicError as e:
                cb(_cli, 2, f'claim FAILED for {_cli.name}')
                logger.exception('error claiming')

    def handle_buttons_claim(self, opts: str, update: Update, context: CallbackContext) -> None:
        """Process claim buttons"""
        query = update.callback_query
        extra_text = []
        final_status = {}
        total_claimed = [0]

        if not opts:
            # claim every account
            clis = list(self.clis.values())
        else:
            cli = self.clis.get(opts[0])
            if cli is None:
                query.edit_message_reply_markup()
                return
            clis = [cli]

        def _cb(_cli: 'cli.CLI', st: int, msg: str, args=None):
            extra_text.append(msg)
            trivial_edit_message_text(query, '\n'.join(extra_text))
            if st == 0:
                final_status[_cli.name] = None
            elif st == 1:
                final_status[_cli.name] = extra_text[-1]
                total_claimed[0] += args[0]
            elif st == 2:
                final_status[_cli.name] = extra_text[-1]

        self._async_claim(clis, _cb)

        # clean up message
        query.edit_message_text(
            '\n'.join(list(final_status.values()) + [f'*Total claimed*: {total_claimed[0]}']),
            parse_mode='Markdown',
        )

    @staticmethod
    def _async_swapsend(
        _from: 'cli.CLI', clis: 'List[cli.CLI]', cb: Callable[['cli.CLI', int, str, Optional[List[Any]]], None]
    ):
        hash_queue = []

        # submit transactions
        for _cli in clis:
            if _from.owner == _cli.owner:
                continue
            bal = _cli.client.web3.balance_of_slime(raw=True)
            if not bal:
                cb(_cli, 2, f'{_cli.name}: Nothing to send')
            else:
                cb(_cli, 0, f'{_cli.name}: sending {bal / DECIMALS}')
                h = _cli.client.web3.transfer_slime(_from.owner, bal, wait_for_transaction_receipt=False)
                hash_queue.append((_cli, h))

        # wait for receipts
        for _cli, hash in hash_queue:
            r = _cli.client.web3.web3.eth.wait_for_transaction_receipt(hash, timeout=120)
            sent = int(r['logs'][0]['data'], 16) / DECIMALS
            cb(_cli, 1, f'{_cli.name}: sent {sent} SLIME', [sent])

    def handle_buttons_swapsend(self, opts: str, update: Update, context: CallbackContext) -> None:
        """Process swapsend buttons"""
        query = update.callback_query
        if not opts:
            query.edit_message_reply_markup()
            return
        cli = self.clis.get(opts[0])
        if cli is None:
            query.edit_message_reply_markup()
            return

        final_status = {}
        total_sent = [0]

        extra_text = [f'*Sending to {cli.name}*']
        final_status['_'] = extra_text[-1]
        trivial_edit_message_text(query, '\n'.join(extra_text), parse_mode='Markdown')

        def _cb(_cli: 'cli.CLI', st: int, msg: str, args=None):
            extra_text.append(msg)
            trivial_edit_message_text(query, '\n'.join(extra_text), parse_mode='Markdown')
            if st == 0:
                final_status[_cli.name] = None
            elif st == 1:
                final_status[_cli.name] = extra_text[-1]
                total_sent[0] += args[0]
            elif st == 2:
                final_status[_cli.name] = extra_text[-1]

        self._async_swapsend(cli, list(self.clis.values()), _cb)

        # clean up message
        query.edit_message_text(
            '\n'.join(list(final_status.values()) + [f'*Total sent*: {total_sent[0]}']),
            parse_mode='Markdown',
        )

    def handle_buttons_balance_balance(self, opts: str, update: Update, context: CallbackContext) -> None:
        """Process /balancebalance confirmation"""
        query = update.callback_query
        query.message.reply_chat_action(constants.CHATACTION_TYPING)

        msg = [query.message.text, '', '**for real**']

        def _cb(_m):
            msg.append(escape_markdown(_m))
            query.message.edit_text(text='\n'.join(msg), parse_mode='Markdown')

        stop, limit = self.main_cli.args.balance_balance
        utils.balance_balance(self.clis.values(), limit, stop, _cb, force=True)

    def handle_buttons_css(self, opts: str, update: Update, context: CallbackContext) -> None:
        """Process /css buttons"""
        query = update.callback_query
        if not opts:
            query.edit_message_reply_markup()
            return
        cli = self.clis.get(opts[0])
        if cli is None:
            query.edit_message_reply_markup()
            return

        extra_text = []
        final_status = {}
        total_claimed = [0]

        def _cb(_cli: 'cli.CLI', st: int, msg: str, args=None):
            extra_text.append(msg)
            trivial_edit_message_text(query, '\n'.join(extra_text), parse_mode='Markdown')
            if st == 0:
                final_status[_cli.name] = None
            elif st == 1:
                final_status[_cli.name] = extra_text[-1]
                total_claimed[0] += args[0]
            elif st == 2:
                final_status[_cli.name] = extra_text[-1]

        self._async_claim(list(self.clis.values()), _cb, minimum=self.main_cli.args.css_minimum)

        slime_claimed = total_claimed[0]
        extra_text = list(final_status.values()) + [f'*Total claimed*: {slime_claimed}', '']
        trivial_edit_message_text(query, '\n'.join(extra_text), parse_mode='Markdown')

        final_status = {}
        total_claimed[0] = 0
        sti = len(extra_text)
        self._async_swapsend(cli, list(self.clis.values()), _cb)

        extra_text = extra_text[:sti] + list(final_status.values()) + [f'*Total sent*: {total_claimed[0]}', '']
        trivial_edit_message_text(query, '\n'.join(extra_text), parse_mode='Markdown')

        if self.main_cli.args.css_fee and slime_claimed:
            creditor, rate = self.main_cli.args.css_fee
            fee = int(slime_claimed * float(rate) * DECIMALS)
            r = cli.client.web3.transfer_slime(creditor, fee)
            sent = int(r['logs'][0]['data'], 16) / DECIMALS
            extra_text.append(f'*Paid fee of {sent}*')
            trivial_edit_message_text(query, '\n'.join(extra_text), parse_mode='Markdown')

        balance = cli.client.web3.balance_of_slime(raw=True)
        out_min = cli.client.web3.swap_slime_avax(amount_in=balance, preview=True)

        _msg = f'{balance / DECIMALS:0.2f} SLIME for {out_min / DECIMALS:0.2f} AVAX'
        extra_text.append(f'Swapping {_msg}')
        trivial_edit_message_text(query, '\n'.join(extra_text), parse_mode='Markdown')

        cli.client.web3.swap_slime_avax(amount_in=balance, amount_out=out_min)
        extra_text[-1] = f'Swapped {_msg} ✅'
        query.edit_message_text('\n'.join(extra_text), parse_mode='Markdown')

    @bot_auth
    def cmd_start(self, update: Update, context: CallbackContext) -> None:
        """
        Start
        """
        update.message.reply_markdown_v2(
            fr'Hi {update.effective_user.mention_markdown_v2()}\!',
        )

    @bot_auth
    def cmd_help(self, update: Update, context: CallbackContext) -> None:
        """
        Help
        """
        m = [f'/{v[0]} - {v[1]}' for v in self._listed_commands() if v[0] != 'help']
        update.message.reply_text('\n'.join(m))

    def cmd_message(self, update: Update, context: CallbackContext) -> None:
        """
        Help
        """
        if update.message.reply_to_message:
            return self._cmd_replies(update, context)
        return self._cmd_invalid(update, context)

    def _cmd_replies(self, update: Update, context: CallbackContext) -> None:
        # only non-boolean settings handled here, for now
        keyword = update.message.reply_to_message.text.splitlines()[0].split()[-1].rstrip('.')
        for setting in self._settings_list:
            if setting.dest == keyword:
                break
        else:
            return self._cmd_invalid(update, context)

        if update.message.text.lower() == 'cancel':
            return

        args = self.any_cli.args
        try:
            if update.message.text.lower() == 'empty':
                nv = None
            elif isinstance(setting, (configargparse.argparse._AppendAction)):
                nv = update.message.text.split('\n')
                nv = list(map(setting.type, nv))
            else:
                nv = setting.type(update.message.text)
            setattr(args, keyword, nv)
            msg = f"Toggled *{keyword}* to *{nv}*"
        except ValueError:
            msg = f'`{update.message.text}` is not valid value for `{keyword}`'

        self.updater.bot.send_message(
            update.message.chat.id,
            text=msg,
            reply_to_message_id=update.message.message_id,
            parse_mode='Markdown',
        )
        if update.message.chat.id != self.chat_id:
            # also notify main chat
            self.notify(msg)
        self.any_cli.save_bot_settings()

    def _cmd_invalid(self, update: Update, context: CallbackContext) -> None:
        update.effective_user['first_name'],
        update.effective_user['last_name'],
        update.effective_user['username'],
        update.effective_user['id'],
        logger.warning(
            'New message: %s %s (%s / %d) said %s',
            update.effective_user['first_name'],
            update.effective_user['last_name'],
            update.effective_user['username'],
            update.effective_user['id'],
            update.message.text,
        )

    @bot_auth
    def cmd_stats(self, update: Update, context: CallbackContext) -> None:
        """
        My snails stats
        """
        update.message.reply_chat_action(constants.CHATACTION_TYPING)
        all_snails = []

        for c in self.clis.values():
            it = list(c.my_snails.values())
            it.sort(key=lambda x: x.breed_status)
            # queuable times
            queues = {s.id: s for s in c.client.iterate_my_snails_for_missions(c.owner)}
            for s in it:
                s['queueable_at'] = queues.get(s.id).get('queueable_at')
            all_snails.extend(it)

        # split into blocks of 50 snails due to message size limit of 4k (100 snails already error)
        for partly in range(0, len(all_snails), 50):
            update.message.reply_markdown_v2(
                '\n'.join(
                    '🐌  %s\n%s\n🍆  *%s* 🏁 %s 🎫 %s'
                    % (
                        f'[{escmv2(snail.name)}](https://www.snailtrail.art/snails/{snail.id}/about)',
                        escmv2(
                            f"{snail.level_str} {snail.family.gene} {snail.gender.emoji()} {snail.klass} {snail.purity_str}"
                        ),
                        self._breed_status_markdown(snail.breed_status),
                        escmv2(self._queueable_at(snail)),
                        escmv2(str(snail.stats['mission_tickets'])),
                    )
                    for snail in all_snails[partly : partly + 50]
                )
            )

    @bot_auth
    def cmd_balance(self, update: Update, context: CallbackContext) -> None:
        """
        Current balance (snail count, avax, slime)
        """
        update.message.reply_chat_action(constants.CHATACTION_TYPING)
        msg = []
        totals = [0, 0, 0]
        m = update.message.reply_markdown('Loading balances...')

        cache = self.main_cli.client.web3.multicall_balances([c.owner for c in self.clis.values()])
        for c in self.clis.values():
            self.tag_with_wallet(c, msg)
            msg.append('...Loading...')
            trivial_edit_text(m, text='\n'.join(msg), parse_mode='Markdown')
            data = c._balance(data=cache[c.owner])
            totals[0] += sum(data['SLIME'])
            totals[1] += sum(data['WAVAX']) + data['AVAX']
            totals[2] += data['SNAILS']
            wstr = f"*WAVAX*: {data['WAVAX'][0]} / {data['WAVAX'][1]}\n" if sum(data['WAVAX']) else ''
            msg[
                -1
            ] = f'''🧪 {data['SLIME'][0]} / {data['SLIME'][1]:.3f}
{wstr}🔺 {data['AVAX']:.3f} / 🐌 {data['SNAILS']}'''
            m.edit_text(text='\n'.join(msg), parse_mode='Markdown')

        if self.is_multi_cli:
            msg.append(
                f'''`Total`
🧪 {totals[0]:.3f}
🔺 {totals[1]:.3f}
🐌 {totals[2]}'''
            )
            m.edit_text(text='\n'.join(msg), parse_mode='Markdown')

    @bot_auth
    def cmd_inventory(self, update: Update, context: CallbackContext) -> None:
        """
        Inventory items
        """
        update.message.reply_chat_action(constants.CHATACTION_TYPING)
        msg = []
        totals = defaultdict(lambda: 0)
        m = update.message.reply_markdown('Loading items...')
        for c in self.clis.values():
            self.tag_with_wallet(c, msg)
            msg.append('...Loading...')
            trivial_edit_text(m, text='\n'.join(msg), parse_mode='Markdown')
            msg.pop()
            for _, v in c.cmd_inventory(verbose=False).items():
                msg.append(f'_{v[0].name}_: {len(v)}')
                totals[v[0].name] += len(v)
            trivial_edit_text(m, text='\n'.join(msg), parse_mode='Markdown')

        if self.is_multi_cli:
            msg.append('`Total`')
            for k, v in totals.items():
                msg.append(f'_{k}_: {v}')
            m.edit_text(text='\n'.join(msg), parse_mode='Markdown')

    @bot_auth
    def cmd_fee(self, update: Update, context: CallbackContext) -> None:
        """
        Display current avalanche fees
        """
        update.message.reply_chat_action(constants.CHATACTION_TYPING)
        median = self.main_cli.client.gas_price()
        mission_fee = self.main_cli.client.max_mission_fee
        pct = median * 100 / mission_fee
        update.message.reply_markdown(
            f'''\
Configured max (mission) fee: {mission_fee}
Current median fee: {median}
Median is {pct:.2f}% of your base fee
'''
        )

    @bot_auth
    def cmd_boosted(self, update: Update, context: CallbackContext) -> None:
        """
        List currently boosted snails
        """
        update.message.reply_chat_action(constants.CHATACTION_TYPING)
        args = self.main_cli.args
        if not args.boost and not args.boost_wallet and not args.boost_pure:
            update.message.reply_markdown('No boosts')
            return
        msg = []
        m = update.message.reply_markdown('Loading snails...')
        boosted = set(args.boost or [])
        boosted_wallets = set(w.address for w in (args.boost_wallet or []))
        total = 0
        for c in self.clis.values():
            self.tag_with_wallet(c, msg)
            msg.append('...Loading...')
            trivial_edit_text(m, text='\n'.join(msg), parse_mode='Markdown')
            msg.pop()
            ltotal = 0
            for snail in c.my_snails.values():
                if (
                    (snail.id in boosted)
                    or (c.owner in boosted_wallets)
                    or (args.boost_pure and snail.purity >= args.boost_pure)
                ):
                    if args.boost_to and snail.level >= args.boost_to:
                        continue
                    ltotal += 1
                    msg.append(str(snail))
            if ltotal:
                msg.append(f'🐌 {ltotal}')
            total += ltotal
            trivial_edit_text(m, text='\n'.join(msg), parse_mode='Markdown')
        msg.append(f'🐌🐌 {total}')
        m.edit_text(text='\n'.join(msg), parse_mode='Markdown')

    @bot_auth
    def cmd_guild(self, update: Update, context: CallbackContext) -> None:
        """
        Guild stats and balance
        """
        update.message.reply_chat_action(constants.CHATACTION_TYPING)
        m = update.message.reply_markdown('Loading details...')

        msg = []
        guilds = {}

        for c in self.clis.values():
            data = c._cmd_guild_data()
            if data:
                if c.profile_guild not in guilds:
                    guilds[c.profile_guild] = data
                    guilds[c.profile_guild]['members'] = []
                if not guilds[c.profile_guild]['next_rewards'] and data['next_rewards']:
                    # in case first member did not have next_rewards but the others do :shrug:
                    guilds[c.profile_guild]['next_rewards'] = data['next_rewards']
                guilds[c.profile_guild]['members'].append((c.name, data['rewards']))

        for k, data in guilds.items():
            msg.append(f'`Guild: {k}`')
            msg.append(f'💪 {data["level"]}')
            _ph = data["tomato_ph"]
            _m = f'🍅 {data["tomato"]}'
            if _ph:
                _m += f' ⏲️ {_ph}'
            msg.append(_m)
            msg.append(f'🥬 {data["lettuce"]}')
            if data['next_rewards']:
                for k, v in data['next_rewards']:
                    msg.append(f"🎁 `{k}`: {v}")
            msg.append(f'👥 {data["member_count"]} 🐌 {data["snail_count"]}')
            for _m in data['members']:
                if _m[1]:
                    _m2 = ', '.join([f'`{k}`: {v}' for k, v in _m[1]])
                    msg.append(f'*{_m[0]}* 🎁 {_m2}')
            msg.append('')

        m.edit_text(text='\n'.join(msg), parse_mode='Markdown')

    @bot_auth
    def cmd_balance_balance(self, update: Update, context: CallbackContext) -> None:
        """
        Distribute AVAX balance from richest wallet to the others
        """
        update.message.reply_chat_action(constants.CHATACTION_TYPING)
        msg = []
        m = update.message.reply_markdown('Checking balances...')
        stop, limit = self.main_cli.args.balance_balance

        def _cb(_m):
            msg.append(_m)
            m.edit_text(text='\n'.join(msg), parse_mode='Markdown')

        r = utils.balance_balance(self.clis.values(), limit, stop, _cb)

        if r:
            keyboard = [
                [
                    InlineKeyboardButton(
                        'Confirm',
                        callback_data=f'balance_balance',
                    )
                ],
                [InlineKeyboardButton(f'❌ Niente', callback_data='toggle')],
            ]
            m.edit_text(text='\n'.join(msg), parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    @bot_auth
    def cmd_css(self, update: Update, context: CallbackContext) -> None:
        """
        Claim, send and swap all slime
        """
        update.message.reply_chat_action(constants.CHATACTION_TYPING)
        keyboard = []
        for c in self.clis.values():
            keyboard.append(
                [
                    InlineKeyboardButton(
                        c.name,
                        callback_data=f'css {c.owner}',
                    )
                ]
            )
        keyboard.append([InlineKeyboardButton(f'❌ Niente', callback_data='toggle')])
        update.message.reply_markdown('Choose an option', reply_markup=InlineKeyboardMarkup(keyboard))

    @bot_auth
    def cmd_claim(self, update: Update, context: CallbackContext) -> None:
        """
        Claim rewards
        """
        update.message.reply_chat_action(constants.CHATACTION_TYPING)
        keyboard = []
        for c in self.clis.values():
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f'💰 {c.name}: {c.client.web3.claimable_slime()}',
                        callback_data=f'claim {c.owner}',
                    )
                ]
            )
        keyboard.append([InlineKeyboardButton(f'All', callback_data='claim')])
        keyboard.append([InlineKeyboardButton(f'❌ Niente', callback_data='toggle')])
        update.message.reply_markdown('Choose an option', reply_markup=InlineKeyboardMarkup(keyboard))

    @bot_auth
    def cmd_swapsend(self, update: Update, context: CallbackContext) -> None:
        """
        Send all slime to one account (for single swaps)
        """
        update.message.reply_chat_action(constants.CHATACTION_TYPING)

        keyboard = []
        for c in self.clis.values():
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f'💰 {c.name}: {c.client.web3.balance_of_slime():0.2f} / {c.client.web3.get_balance():0.2f}',
                        callback_data=f'swapsend {c.owner}',
                    )
                ]
            )
        keyboard.append([InlineKeyboardButton(f'❌ Niente', callback_data='toggle')])
        update.message.reply_markdown('Choose a wallet', reply_markup=InlineKeyboardMarkup(keyboard))

    @bot_auth
    def cmd_nextmission(self, update: Update, context: CallbackContext) -> None:
        """
        Show time to next daily mission
        """
        msgs = []
        for c in self.clis.values():
            self.tag_with_wallet(c, msgs)
            if not c._next_mission[0]:
                msgs.append(f'🫥 {c._next_mission[1]}')
            elif not c._next_mission[1]:
                msgs.append('⁉️')
            else:
                msgs.append(f'⏲️ `{str(c._next_mission[1] - c._now()).split(".")[0]}`')
        update.message.reply_markdown('\n'.join(msgs))

    @bot_auth
    def cmd_incubate(self, update: Update, context: CallbackContext) -> None:
        """
        Show current incubation coefficent
        """
        update.message.reply_markdown(
            f'current breed coefficient is `{self.any_cli.client.web3.get_current_coefficent()}`'
        )

    @bot_auth
    def cmd_burn(self, update: Update, context: CallbackContext) -> None:
        """
        Show current burn coefficent
        """
        r = self.any_cli._burn_coef()
        if r is None:
            update.message.reply_markdown('No snail available for burn coefficient')
        else:
            coef = r['payload']['coef']
            update.message.reply_markdown(f'current burn coefficient is `{coef}`')

    @bot_auth
    def cmd_marketplace_stats(self, update: Update, context: CallbackContext) -> None:
        """
        Show marketplace stats - volume, floors and highs
        """
        d = self.any_cli.client.marketplace_stats()
        txt = [f"*Volume*: {d['volume']}"]
        for k, v in d['prices'].items():
            txt.append(f"*{k}*: {' / '.join(map(str, v))}")
        update.message.reply_markdown('\n'.join(txt))

    @bot_auth
    def cmd_reload_snails(self, update: Update, context: CallbackContext) -> None:
        """
        Reset snails cache (and reload wallet guilds)
        """
        for c in self.clis.values():
            c.reset_cache_my_snails()
        self.multicli.load_profiles()
        update.message.reply_text('✅')

    def __setting_value(self, setting, short=False):
        v = getattr(self.any_cli.args, setting.dest)
        if setting.type in (int, float):
            if v is None:
                return '❌'
            if isinstance(setting, (configargparse.argparse._AppendAction)):
                if not v:
                    return '❌'
                if short:
                    return '[...]'
            return f'[{v}]'
        # otherwise it's a bool setting
        return "🟢" if v else "🔴"

    @bot_auth
    def cmd_settings(self, update: Update, context: CallbackContext) -> None:
        """
        Toggle bot settings
        """
        if not self._settings_list:
            update.message.reply_markdown('No settings available...')
            return
        keyboard = []
        for i in range(0, len(self._settings_list), 2):
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f'🔧 {self.__setting_value(setting, short=True)} {setting.dest}',
                        callback_data=f'toggle {setting.dest}',
                    )
                    for setting in self._settings_list[i : i + 2]
                ]
            )
        keyboard.append(
            [
                InlineKeyboardButton(f'📇 Show all', callback_data='toggle __all'),
                InlineKeyboardButton(f'❌ Niente', callback_data='toggle'),
                InlineKeyboardButton(f'❔ Help', callback_data='toggle __help'),
            ]
        )
        update.message.reply_markdown('Toggle settings', reply_markup=InlineKeyboardMarkup(keyboard))

    @bot_auth
    def cmd_usethisformissions(self, update: Update, context: CallbackContext) -> None:
        """
        Use this chat for mission join notifications
        """
        _cli = self.any_cli
        oid = _cli.args.mission_chat_id or '-'
        _cli.args.mission_chat_id = update.message.chat.id
        msg = f'Changed `mission-chat-id` from `{oid}` to `{update.message.chat.id}`'
        update.message.reply_markdown(f'{msg} (this one)')
        if update.message.chat.id != self.chat_id:
            # also notify main chat
            self.notify(msg)
        _cli.save_bot_settings()

    @bot_auth
    def cmd_race_review(self, update: Update, context: CallbackContext) -> None:
        """
        Review all races to join (that were already notified)
        """
        update.message.reply_chat_action(constants.CHATACTION_TYPING)

        for c in self.clis.values():
            c.find_races(check_notified=False)

    @bot_auth
    def cmd_race_pending(self, update: Update, context: CallbackContext) -> None:
        """
        View pending races (that you joined)
        """
        update.message.reply_chat_action(constants.CHATACTION_TYPING)

        m = update.message.reply_markdown('Loading...')
        msg = []
        for c in self.clis.values():
            self.tag_with_wallet(c, msg)
            msg.append('...Loading...')
            m.edit_text(text='\n'.join(msg), parse_mode='Markdown')
            no_races = True
            for r in c.client.iterate_onboarding_races(own=True, filters={'owner': c.owner}):
                msg.insert(-1, f'{r.track} (#{r.id}): {len(r.athletes)} athletes scheduled for {r.schedules_at}')
                no_races = False
            if no_races:
                msg = msg[:-2]
            else:
                msg = msg[:-1]
            if msg:
                m.edit_text(text='\n'.join(msg), parse_mode='Markdown')
        if not msg:
            m.edit_text(text='None pending', parse_mode='Markdown')

    def idle(self):
        if self.updater:
            self.updater.idle()

    def _listed_commands(self):
        return [
            (v1.command[0], v1.callback.__doc__.strip())
            for v in self.updater.dispatcher.handlers.values()
            for v1 in v
            if isinstance(v1, CommandHandler) and v1.command[0] != 'start'
        ]

    def start_polling(self):
        if self.updater:
            self.updater.bot.set_my_commands(self._listed_commands())
            self.updater.start_polling()

    def stop_polling(self):
        if self.updater:
            self.updater.stop()
            self.updater.bot.edit_message_text

    def _breed_status_markdown(self, status):
        if status >= 0:
            return escmv2(f"⏲️ {status:.2f}d")
        elif status == -1:
            return f"✅"
        elif status == -2:
            return f"🥒"
        else:
            return f"🔥"

    def _queueable_at(self, snail):
        tleft = snail.queueable_at - self.any_cli._now()
        if tleft.total_seconds() <= 0:
            return '✅'
        return f'⏲️  {str(tleft).rsplit(":", 1)[0]}'

    def notify(
        self,
        message: str,
        format: str = 'Markdown',
        silent: bool = False,
        edit: dict[str] = None,
        actions: List[Tuple[str]] = None,
        chat_id: int = None,
        only_once: bool = False,
        from_wallet: Optional[str] = None,
    ):
        """Use this method to send text messages

        Args:
            message (:obj:`str`): Text of the message to be sent. Max 4096 characters after entities
                parsing.
            format (:obj:`str`): Send Markdown or HTML, if you want Telegram apps to show bold,
                italic, fixed-width text or inline URLs in your bot's message.
            silent (:obj:`bool`, optional): Sends the message silently. Users will
                receive a notification with no sound.
            edit (:obj:`dict[str]`, optional): If not None, it should be the old `telegram.Message`
                which will then be edited.
            actions (:obj:`List[Tuple[str]]`, optional): If not None, used as inline keyboard buttons
            chat_id (:obj:`int`, optional): If not None, target chat_id of the message (instead of default one)
            only_once (:obj:`bool`, optional): If true, message with same text is not sent if it has already been processed
            from_wallet (:obj:`str`, optional): If multi cli, prepend this wallet name to the message text

        Returns:
            :class:`telegram.Message`: On success, the sent message is returned.

        Raises:
            :class:`telegram.error.TelegramError`

        """

        if only_once:
            _h = hash(message)
            if _h in self._sent_messages:
                return
            self._sent_messages.add(_h)

        if format == 'Markdown':
            message = self._link_snails(message)

        if chat_id is None:
            chat_id = self.chat_id
        if self.updater and chat_id:
            if len(self.clis) > 1 and from_wallet:
                if format == 'Markdown':
                    from_wallet = f'`{from_wallet}`'
                message = f'{from_wallet}\n{message}'
            if edit is None:
                if actions:
                    keyboard = [[InlineKeyboardButton(x[0], callback_data=x[1])] for x in actions]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                else:
                    reply_markup = None
                return self.updater.bot.send_message(
                    chat_id, message, parse_mode=format, disable_notification=silent, reply_markup=reply_markup
                )
            else:
                return self.updater.bot.edit_message_text(
                    message, edit['chat']['id'], edit['message_id'], parse_mode=format
                )

    def _link_snails(self, message):
        _r = r'[\1](https://www.snailtrail.art/snails/\2/about)'
        m = self.SNAIL_ID1_RE.sub(_r, message)
        return self.SNAIL_ID2_RE.sub(_r, m)


def trivial_edit_message_text(query, *args, **kwargs):
    try:
        return query.edit_message_text(*args, **kwargs)
    except Exception:
        logger.exception('telegram timeout')


def trivial_edit_text(query, *args, **kwargs):
    try:
        return query.edit_text(*args, **kwargs)
    except Exception:
        logger.exception('telegram timeout')
