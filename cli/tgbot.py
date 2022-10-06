from typing import Dict, List, Optional, Tuple
from xmlrpc.client import Boolean
from telegram import Update, constants, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.utils.helpers import escape_markdown
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler
import logging

from .cli import CLI, client

logger = logging.getLogger(__name__)


def escmv2(*a, **b):
    return escape_markdown(*a, version=2, **b)


def bot_auth(func):
    def wrapper_func(notifier, update: Update, context: CallbackContext):
        if not notifier.chat_id or update.effective_user['id'] != notifier.chat_id:
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
    clis: Dict[str, CLI]

    def __init__(self, token, chat_id, settings_list=None):
        self.__token = token
        self.chat_id = chat_id
        self.clis = {}
        self._settings_list = settings_list

        if token:
            self.updater = Updater(self.__token)
            dispatcher = self.updater.dispatcher
            dispatcher.add_handler(CommandHandler("start", self.cmd_start))
            dispatcher.add_handler(CallbackQueryHandler(self.handle_buttons))
            dispatcher.add_handler(CommandHandler("stats", self.cmd_stats))
            dispatcher.add_handler(CommandHandler("nextmission", self.cmd_nextmission))
            dispatcher.add_handler(CommandHandler("balance", self.cmd_balance))
            dispatcher.add_handler(CommandHandler("claim", self.cmd_claim))
            dispatcher.add_handler(CommandHandler("swapsend", self.cmd_swapsend))
            dispatcher.add_handler(CommandHandler("incubate", self.cmd_incubate))
            dispatcher.add_handler(CommandHandler("market", self.cmd_marketplace_stats))
            dispatcher.add_handler(CommandHandler("reloadsnails", self.cmd_reload_snails))
            dispatcher.add_handler(CommandHandler("settings", self.cmd_settings))
            dispatcher.add_handler(CommandHandler("help", self.cmd_help))
        else:
            self.updater = None

    @property
    def any_cli(self) -> CLI:
        return list(self.clis.values())[0]

    @property
    def multi_cli(self) -> Boolean:
        return len(self.clis) > 1

    def tag_with_wallet(self, cli: CLI, output: Optional[list] = None):
        if not self.multi_cli:
            return ''
        m = f'`{cli.masked_wallet}`'
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
        cli = self.clis[owner]
        try:
            r, _ = cli.client.join_competitive_races(int(snail_id), int(race_id), cli.owner)
            query.edit_message_text(query.message.text + '\n✅  Race joined')
        except Exception as e:
            logger.exception('unexpected joinRace error')
            query.edit_message_text(query.message.text + f'\n❌ Race FAILED to join: {e}')

    def handle_buttons_claim(self, opts: str, update: Update, context: CallbackContext) -> None:
        """Process claim buttons"""
        query = update.callback_query
        extra_text = []

        def _claim(cli):
            try:
                r = cli.client.web3.claim_rewards()
                if r.get('status') == 1:
                    bal = int(r['logs'][1]['data'], 16) / 1000000000000000000
                    extra_text.append(f'claimed {bal} from {cli.masked_wallet}')
                else:
                    extra_text.append(f'claim failed for {cli.masked_wallet}')
                    logger.error('error claiming: %s', r)
            except client.web3client.exceptions.ContractLogicError as e:
                extra_text.append(f'claim failed for {cli.masked_wallet}: {e}')
                logger.exception('error claiming')
            query.edit_message_text(query.message.text + '\n' + '\n'.join(extra_text))

        if not opts:
            # claim every account
            for c in self.clis.values():
                _claim(c)
        else:
            _claim(self.clis[opts[0]])

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

        extra_text = []
        for c in self.clis.values():
            if cli.owner == c.owner:
                continue
            bal = c.client.web3.balance_of_slime(raw=True)
            if not bal:
                extra_text.append(f'{c.masked_wallet}: Nothing to send')
            else:
                extra_text.append(f'{c.masked_wallet}: sending {bal / 1000000000000000000}')
                query.edit_message_text(query.message.text + '\n' + '\n'.join(extra_text))
                r = c.client.web3.transfer_slime(cli.owner, bal)
                sent = int(r['logs'][0]['data'], 16) / 1000000000000000000
                extra_text.append(f'{c.masked_wallet}: sent {sent} SLIME')
            query.edit_message_text(query.message.text + '\n' + '\n'.join(extra_text))

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

        update.message.reply_markdown_v2(
            '\n'.join(
                '🐌  %s\n%s\n🍆  *%s* 🏁 %s 🎫 %s'
                % (
                    f'[{escmv2(snail.name)}](https://www.snailtrail.art/snails/{snail.id}/about)',
                    escmv2(f"lv {snail.level} - {snail.family} {snail.gender.emoji()} {snail.klass} {snail.purity}"),
                    self._breed_status_markdown(snail.breed_status),
                    escmv2(self._queueable_at(snail)),
                    escmv2(str(snail.stats['mission_tickets'])),
                )
                for snail in all_snails
            )
        )

    @bot_auth
    def cmd_balance(self, update: Update, context: CallbackContext) -> None:
        """
        Current balance (snail count, avax, slime)
        """
        update.message.reply_chat_action(constants.CHATACTION_TYPING)
        msg = []
        for c in self.clis.values():
            self.tag_with_wallet(c, msg)
            msg.append(c._balance())
        update.message.reply_markdown('\n'.join(msg))

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
                        f'💰 {c.masked_wallet}: {c.client.web3.claimable_rewards()}',
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
                        f'💰 {c.masked_wallet}: {c.client.web3.balance_of_slime():0.2f} / {c.client.web3.get_balance():0.2f}',
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
            if c._next_mission is None:
                msgs.append('next mission is *unknown*')
            else:
                msgs.append(f'next mission in `{str(c._next_mission - c._now()).split(".")[0]}`')
        update.message.reply_markdown('\n'.join(msgs))

    @bot_auth
    def cmd_incubate(self, update: Update, context: CallbackContext) -> None:
        """
        Show current incubation coefficent
        """
        update.message.reply_markdown(f'current coefficient is `{self.any_cli.client.web3.get_current_coefficent()}`')

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
                        f'🔧 {setting.dest}: {getattr(self.any_cli.args, setting.dest)}',
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
        if self.updater and self.chat_id:
            if edit is None:
                if actions:
                    keyboard = [[InlineKeyboardButton(x[0], callback_data=x[1])] for x in actions]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                else:
                    reply_markup = None
                return self.updater.bot.send_message(
                    self.chat_id, message, parse_mode=format, disable_notification=silent, reply_markup=reply_markup
                )
            else:
                return self.updater.bot.edit_message_text(
                    message, edit['chat']['id'], edit['message_id'], parse_mode=format
                )
