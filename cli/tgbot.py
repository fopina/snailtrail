from typing import List, Tuple
from telegram import Update, constants, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.utils.helpers import escape_markdown
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler
import logging

logger = logging.getLogger(__name__)


def escmv2(*a, **b):
    return escape_markdown(*a, version=2, **b)


def bot_auth(func):
    def wrapper_func(notifier, update: Update, context: CallbackContext):
        if not notifier.owner_id or update.effective_user['id'] != notifier.owner_id:
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
        except Exception:
            logger.exception('error caught')
            update.message.reply_text('error occurred, check logs')

    wrapper_func.__doc__ = func.__doc__
    return wrapper_func


class Notifier:
    def __init__(self, token, owner_id, cli_obj, settings_list=None):
        self.__token = token
        self.owner_id = owner_id
        self.__cli = cli_obj
        self._settings_list = settings_list

        if token:
            self.updater = Updater(self.__token)
            dispatcher = self.updater.dispatcher
            dispatcher.add_handler(CommandHandler("start", self.cmd_start))
            dispatcher.add_handler(CallbackQueryHandler(self.handle_buttons))
            dispatcher.add_handler(CommandHandler("stats", self.cmd_stats))
            dispatcher.add_handler(CommandHandler("nextmission", self.cmd_nextmission))
            dispatcher.add_handler(CommandHandler("balance", self.cmd_balance))
            dispatcher.add_handler(CommandHandler("incubate", self.cmd_incubate))
            dispatcher.add_handler(CommandHandler("market", self.cmd_marketplace_stats))
            dispatcher.add_handler(CommandHandler("settings", self.cmd_settings))
        else:
            self.updater = None

    def handle_buttons(self, update: Update, context: CallbackContext) -> None:
        """Parses the CallbackQuery and updates the message text."""
        query = update.callback_query
        query.answer()
        cmd, *opts = query.data.split(' ', 1)
        if cmd == 'toggle':
            return self.handle_buttons_toggle(opts, update, context)
        elif cmd == 'joinrace':
            return self.handle_buttons_joinrace(opts, update, context)
        query.edit_message_text(text=f"Unknown option: {query.data}")

    def handle_buttons_toggle(self, opts: str, update: Update, context: CallbackContext) -> None:
        """Process settings toggle"""
        query = update.callback_query
        if not opts:
            query.edit_message_text(text="Did *nothing*, my favorite action", parse_mode='Markdown')
            return
        opts = opts[0]

        if not hasattr(self.__cli.args, opts):
            query.edit_message_text(text=f"Unknown setting: {opts}")
            return

        ov = getattr(self.__cli.args, opts)
        setattr(self.__cli.args, opts, not ov)
        query.edit_message_text(text=f"Toggled *{opts}* to *{not ov}*", parse_mode='Markdown')

    def handle_buttons_joinrace(self, opts: str, update: Update, context: CallbackContext) -> None:
        """Process join race buttons"""
        query = update.callback_query
        if not opts:
            query.edit_message_reply_markup()
            return
        race_id, snail_id = map(int, opts[0].split(' '))
        try:
            r, _ = self.__cli.client.join_competitive_races(snail_id, race_id, self.__cli.owner)
            query.edit_message_text(query.message.text + ' ✅')
            query.message.reply_markdown(text=f'✅ Race joined: {r["message"]}')
        except Exception:
            logger.exception('unexpected joinRace error')
            query.edit_message_text(query.message.text + ' ❌')
            query.message.reply_markdown(text='❌ Race FAILED to join')

    @bot_auth
    def cmd_start(self, update: Update, context: CallbackContext) -> None:
        """
        Start
        """
        user = update.effective_user
        update.message.reply_markdown_v2(
            fr'Hi {user.mention_markdown_v2()}\!',
        )

    @bot_auth
    def cmd_help(self, update: Update, context: CallbackContext) -> None:
        """
        Help
        """
        update.message.reply_text('Help!')

    @bot_auth
    def cmd_stats(self, update: Update, context: CallbackContext) -> None:
        """
        My snails stats
        """
        update.message.reply_chat_action(constants.CHATACTION_TYPING)
        it = self.__cli.client.iterate_all_snails(filters={'owner': self.__cli.owner})
        it = list(it)
        it.sort(key=lambda x: x.breed_status)
        # queuable times
        queues = {s.id: s for s in self.__cli.client.iterate_my_snails_for_missions(self.__cli.owner)}
        for s in it:
            s['queueable_at'] = queues.get(s.id).get('queueable_at')
        update.message.reply_markdown_v2(
            '\n'.join(
                '🐌  %s %s 🍆  *%s* 🏁 %s'
                % (
                    f'[{escmv2(snail.name)}](https://www.snailtrail.art/snails/{snail.id}/about)',
                    escmv2(f"lv {snail.level} - {snail.family} {snail.gender} {snail.klass} {snail.purity}"),
                    self._breed_status_markdown(snail.breed_status),
                    escmv2(self._queueable_at(snail)),
                )
                for snail in it
            )
        )

    @bot_auth
    def cmd_balance(self, update: Update, context: CallbackContext) -> None:
        """
        Current balance (snail count, avax, slime)
        """
        update.message.reply_chat_action(constants.CHATACTION_TYPING)
        update.message.reply_text(self.__cli._balance())

    @bot_auth
    def cmd_nextmission(self, update: Update, context: CallbackContext) -> None:
        """
        Show time to next daily mission
        """
        if self.__cli._next_mission is None:
            update.message.reply_markdown('next mission is *unknown*')
        else:
            update.message.reply_markdown(
                f'next mission in `{str(self.__cli._next_mission - self.__cli._now()).split(".")[0]}`'
            )

    @bot_auth
    def cmd_incubate(self, update: Update, context: CallbackContext) -> None:
        """
        Show current incubation coefficent
        """
        update.message.reply_markdown(f'current coefficient is `{self.__cli.client.web3.get_current_coefficent()}`')

    @bot_auth
    def cmd_marketplace_stats(self, update: Update, context: CallbackContext) -> None:
        """
        Show marketplace stats - volume, floors and highs
        """
        d = self.__cli.client.marketplace_stats()
        txt = [f"*Volume*: {d['volume']}"]
        for k, v in d['prices'].items():
            txt.append(f"*{k}*: {' / '.join(map(str, v))}")
        update.message.reply_markdown('\n'.join(txt))

    @bot_auth
    def cmd_settings(self, update: Update, context: CallbackContext) -> None:
        """
        Toggle bot settings
        """
        keyboard = []
        for i in range(0, len(self._settings_list), 2):
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f'{setting.dest}: {getattr(self.__cli.args, setting.dest)}', callback_data=f'toggle {setting.dest}'
                    )
                    for setting in self._settings_list[i : i + 2]
                ]
            )
        keyboard.append([InlineKeyboardButton(f'Niente', callback_data='toggle')])
        update.message.reply_markdown('Toggle settings', reply_markup=InlineKeyboardMarkup(keyboard))

    def idle(self):
        if self.updater:
            self.updater.idle()

    def start_polling(self):
        if self.updater:
            commands = [
                (v1.command[0], v1.callback.__doc__.strip())
                for v in self.updater.dispatcher.handlers.values()
                for v1 in v
                if isinstance(v1, CommandHandler) and v1.command[0] != 'start'
            ]
            self.updater.bot.set_my_commands(commands)
            self.updater.start_polling()

    def stop_polling(self):
        if self.updater:
            self.updater.stop()
            self.updater.bot.edit_message_text

    def _breed_status_markdown(self, status):
        if status >= 0:
            return escmv2(f"⏲️ {status:.2f}d")
        elif status == -1:
            return f"✅ BREEDER"
        elif status == -2:
            return f"✅ NEW BREEDER"
        else:
            return f"🔥 NO BREED?"

    def _queueable_at(self, snail):
        tleft = snail.queueable_at - self.__cli._now()
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
        if self.updater and self.owner_id:
            if edit is None:
                if actions:
                    keyboard = [
                        [InlineKeyboardButton(x[0], callback_data=x[1])]
                        for x in actions
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                else:
                    reply_markup = None
                return self.updater.bot.send_message(
                    self.owner_id, message, parse_mode=format, disable_notification=silent, reply_markup=reply_markup
                )
            else:
                return self.updater.bot.edit_message_text(
                    message, edit['chat']['id'], edit['message_id'], parse_mode=format
                )
