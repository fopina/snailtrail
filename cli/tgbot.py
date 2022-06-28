from telegram import Update, constants
from telegram.utils.helpers import escape_markdown
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
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

    return wrapper_func


class Notifier:
    def __init__(self, token, owner_id, cli_obj):
        self.__token = token
        self.owner_id = owner_id
        self.__cli = cli_obj

        if token:
            self.__updater = Updater(self.__token)
            dispatcher = self.__updater.dispatcher
            dispatcher.add_handler(CommandHandler("start", self.cmd_start))
            dispatcher.add_handler(CommandHandler("help", self.cmd_help))
            dispatcher.add_handler(CommandHandler("stats", self.cmd_stats))
        else:
            self.__updater = None

    @bot_auth
    def cmd_start(self, update: Update, context: CallbackContext) -> None:
        user = update.effective_user
        update.message.reply_markdown_v2(
            fr'Hi {user.mention_markdown_v2()}\!',
        )

    @bot_auth
    def cmd_help(self, update: Update, context: CallbackContext) -> None:
        update.message.reply_text('Help!')

    @bot_auth
    def cmd_stats(self, update: Update, context: CallbackContext) -> None:
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
                    escmv2(f"{snail.family} {snail.gender} {snail.klass} {snail.purity}"),
                    self._breed_status_markdown(snail.breed_status),
                    escmv2(self._queueable_at(snail)),
                )
                for snail in it
            )
        )

    def idle(self):
        if self.__updater:
            self.__updater.idle()

    def start_polling(self):
        if self.__updater:
            self.__updater.start_polling()

    def stop_polling(self):
        if self.__updater:
            self.__updater.stop()

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

    def notify(self, message, format='Markdown', silent=False):
        if self.__updater and self.owner_id:
            self.__updater.bot.send_message(self.owner_id, message, parse_mode=format, disable_notification=silent)
