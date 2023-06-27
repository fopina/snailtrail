from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from telegram import Update, constants, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.utils.helpers import escape_markdown
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler
import logging

from . import cli
from .cli import DECIMALS

logger = logging.getLogger(__name__)


def escmv2(*a, **b):
    return escape_markdown(*a, version=2, **b)


def bot_auth(func):
    def wrapper_func(notifier, update: Update, context: CallbackContext):
        if not notifier.owner_chat_id or update.effective_user['id'] != notifier.owner_chat_id:
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

    def __init__(self, token, chat_id, owner_chat_id=None, settings_list=None):
        self.__token = token
        self.chat_id = chat_id
        self.clis = {}
        self._settings_list = settings_list
        if owner_chat_id is None:
            self.owner_chat_id = self.chat_id
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
            dispatcher.add_handler(CommandHandler("claim", self.cmd_claim))
            dispatcher.add_handler(CommandHandler("swapsend", self.cmd_swapsend))
            dispatcher.add_handler(CommandHandler("incubate", self.cmd_incubate))
            dispatcher.add_handler(CommandHandler("burn", self.cmd_burn))
            dispatcher.add_handler(CommandHandler("market", self.cmd_marketplace_stats))
            dispatcher.add_handler(CommandHandler("racereview", self.cmd_race_review))
            dispatcher.add_handler(CommandHandler("racepending", self.cmd_race_pending))
            dispatcher.add_handler(CommandHandler("inventory", self.cmd_inventory))
            dispatcher.add_handler(CommandHandler("stats", self.cmd_stats))
            dispatcher.add_handler(CommandHandler("reloadsnails", self.cmd_reload_snails))
            dispatcher.add_handler(CommandHandler("settings", self.cmd_settings))
            dispatcher.add_handler(CommandHandler("usethisformissions", self.cmd_usethisformissions))
            dispatcher.add_handler(CommandHandler("help", self.cmd_help))
        else:
            self.updater = None

    @property
    def any_cli(self) -> 'cli.CLI':
        return list(self.clis.values())[0]

    @property
    def multi_cli(self) -> bool:
        return len(self.clis) > 1

    @property
    def main_cli(self) -> 'cli.CLI':
        if self.multi_cli:
            for c in self.clis.values():
                if c.report_as_main:
                    return c
        return self.any_cli

    def tag_with_wallet(self, cli: 'cli.CLI', output: Optional[list] = None):
        if not self.multi_cli:
            return ''
        m = f'`{cli.name}`'
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
        elif cmd == 'swapsend':
            return self.handle_buttons_swapsend(opts, update, context)
        query.edit_message_text(text=f"Unknown option: {query.data}")

    def handle_buttons_toggle(self, opts: str, update: Update, context: CallbackContext) -> None:
        """Process settings toggle"""
        query = update.callback_query
        if not opts:
            query.edit_message_text(text="Did *nothing*, my favorite action", parse_mode='Markdown')
            return
        opts = opts[0]

        _cli = self.any_cli

        if opts == '__help':
            m = [f'`{setting.dest}` {escape_markdown(setting.help)}' for setting in self._settings_list]
            query.edit_message_text(text='\n'.join(m), parse_mode='Markdown')
            return

        if not hasattr(_cli.args, opts):
            query.edit_message_text(text=f"Unknown setting: {opts}")
            return

        ov = getattr(_cli.args, opts)
        setattr(_cli.args, opts, not ov)
        query.edit_message_text(text=f"Toggled *{opts}* to *{not ov}*", parse_mode='Markdown')
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

    def handle_buttons_claim(self, opts: str, update: Update, context: CallbackContext) -> None:
        """Process claim buttons"""
        query = update.callback_query
        extra_text = []
        hash_queue = []
        final_status = {}

        def _claim(_cli: 'cli.CLI'):
            extra_text.append(f'claiming from {_cli.name}...')
            query.edit_message_text('\n'.join(extra_text))
            try:
                h = _cli.client.web3.claim_rewards(wait_for_transaction_receipt=False)
                final_status[_cli.name] = None
                hash_queue.append((_cli, h))
            except cli.client.web3client.exceptions.ContractLogicError as e:
                extra_text[-1] = f'claim FAILED for {_cli.name}: {e}'
                query.edit_message_text('\n'.join(extra_text))
                final_status[_cli.name] = extra_text[-1]
                logger.exception('error claiming')

        if not opts:
            # claim every account
            for c in self.clis.values():
                _claim(c)
        else:
            _claim(self.clis[opts[0]])

        total_claimed = 0
        # check every receipt
        for _cli, hash in hash_queue:
            try:
                r = _cli.client.web3.web3.eth.wait_for_transaction_receipt(hash, timeout=120)
                if r.get('status') == 1:
                    bal = int(r['logs'][1]['data'], 16) / DECIMALS
                    total_claimed += bal
                    extra_text.append(f'claimed {bal} from {_cli.name}')
                else:
                    extra_text.append(f'claim FAILED for {_cli.name}')
                    logger.error('error claiming: %s', r)
            except cli.client.web3client.exceptions.ContractLogicError as e:
                extra_text.append(f'claim FAILED for {_cli.name}: {e}')
                logger.exception('error claiming')
            final_status[_cli.name] = extra_text[-1]
            query.edit_message_text('\n'.join(extra_text))

        # clean up message
        query.edit_message_text(
            '\n'.join(list(final_status.values()) + [f'*Total claimed*: {total_claimed}']),
            parse_mode='Markdown',
        )

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

        hash_queue = []
        final_status = {}

        extra_text = [f'*Sending to {cli.name}*']
        final_status['_'] = extra_text[-1]
        query.edit_message_text('\n'.join(extra_text), parse_mode='Markdown')

        # submit transactions
        for c in self.clis.values():
            if cli.owner == c.owner:
                continue
            bal = c.client.web3.balance_of_slime(raw=True)
            if not bal:
                extra_text.append(f'{c.name}: Nothing to send')
            else:
                extra_text.append(f'{c.name}: sending {bal / DECIMALS}')
                query.edit_message_text('\n'.join(extra_text), parse_mode='Markdown')
                h = c.client.web3.transfer_slime(cli.owner, bal, wait_for_transaction_receipt=False)
                final_status[c.name] = None
                hash_queue.append((c, h))

        total_sent = 0
        # wait for receipts
        for c, hash in hash_queue:
            r = c.client.web3.web3.eth.wait_for_transaction_receipt(hash, timeout=120)
            sent = int(r['logs'][0]['data'], 16) / DECIMALS
            total_sent += sent
            extra_text.append(f'{c.name}: sent {sent} SLIME')
            query.edit_message_text('\n'.join(extra_text), parse_mode='Markdown')
            final_status[c.name] = extra_text[-1]

        # clean up message
        query.edit_message_text(
            '\n'.join(list(final_status.values()) + [f'*Total sent*: {total_sent}']),
            parse_mode='Markdown',
        )

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
            m.edit_text(text='\n'.join(msg), parse_mode='Markdown')
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

        if self.multi_cli:
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
            m.edit_text(text='\n'.join(msg), parse_mode='Markdown')
            msg.pop()
            for _, v in c.cmd_inventory(verbose=False).items():
                msg.append(f'_{v[0].name}_: {len(v)}')
                totals[v[0].name] += len(v)
            m.edit_text(text='\n'.join(msg), parse_mode='Markdown')

        if self.multi_cli:
            msg.append('`Total`')
            for k, v in totals.items():
                msg.append(f'_{k}_: {v}')
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
                msg.append(f"🎁 {data['next_rewards']}")
            msg.append(f'👥 {data["member_count"]} 🐌 {data["snail_count"]}')
            for _m in data['members']:
                if _m[1]:
                    msg.append(f'*{_m[0]}* 🎁 {_m[1]}')
            msg.append('')

        m.edit_text(text='\n'.join(msg), parse_mode='Markdown')

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
        if self.main_cli._notify_burn_coefficent is None:
            update.message.reply_markdown(f'burn coefficient monitor is disabled')
        else:
            update.message.reply_markdown(f'current burn coefficient is `{self.main_cli._notify_burn_coefficent[0]}`')

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
        Reset snails cache
        """
        for c in self.clis.values():
            c.reset_cache_my_snails()
        update.message.reply_text('✅')

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
                        f'🔧 {"🟢" if getattr(self.any_cli.args, setting.dest) else "🔴"} {setting.dest}',
                        callback_data=f'toggle {setting.dest}',
                    )
                    for setting in self._settings_list[i : i + 2]
                ]
            )
        keyboard.append(
            [
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

        Returns:
            :class:`telegram.Message`: On success, the sent message is returned.

        Raises:
            :class:`telegram.error.TelegramError`

        """
        if chat_id is None:
            chat_id = self.chat_id
        if self.updater and chat_id:
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
