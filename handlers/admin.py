from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
import logging
from config import ADMIN_IDS
from services.rcon import send_rcon_command

logger = logging.getLogger(__name__)
RCON_COMMAND = 10

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет прав администратора.")
        return ConversationHandler.END
    await update.message.reply_text("Введите команду для RCON (без слеша, например, `list`):", parse_mode="Markdown")
    return RCON_COMMAND

async def rcon_command_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command = update.message.text.strip()
    if not command:
        await update.message.reply_text("Команда не может быть пустой. Попробуйте снова.")
        return RCON_COMMAND
    await update.message.reply_text(f"⏳ Выполняю `{command}`...", parse_mode="Markdown")
    try:
        response = await send_rcon_command(command)
        if len(response) > 4000:
            response = response[:4000] + "... (обрезано)"
        await update.message.reply_text(f"✅ Результат:\n```\n{response}\n```", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"RCON admin error: {e}")
        await update.message.reply_text(f"❌ Ошибка RCON: {str(e)}")
    return ConversationHandler.END
