import os
import logging
import asyncio
from aiohttp import web
from telegram.ext import Application, CommandHandler, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from config import BOT_TOKEN, WEBHOOK_PORT, LOG_LEVEL, LOG_FILE
from database import init_db
from handlers.user import (
    start, help_command, buy, product_callback, enter_nick, confirm_payment,
    history, history_callback, cancel,
    SELECTING_PRODUCT, ENTERING_NICK, CONFIRM_PAYMENT
)
from handlers.admin import admin_command, rcon_command_input, RCON_COMMAND
from webhook import webhook_handler

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

async def main():
    await init_db()
    logger.info("Database initialized")

    application = Application.builder().token(BOT_TOKEN).build()

    # Обработчики пользователя
    conv_buy = ConversationHandler(
        entry_points=[CommandHandler('buy', buy)],
        states={
            SELECTING_PRODUCT: [CallbackQueryHandler(product_callback, pattern='^product_|^cancel$')],
            ENTERING_NICK: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_nick)],
            CONFIRM_PAYMENT: [CallbackQueryHandler(confirm_payment, pattern='^pay_confirm$|^cancel$')],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    conv_admin = ConversationHandler(
        entry_points=[CommandHandler('admin', admin_command)],
        states={
            RCON_COMMAND: [MessageHandler(filters.TEXT & ~filters.COMMAND, rcon_command_input)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(conv_buy)
    application.add_handler(conv_admin)
    application.add_handler(CommandHandler('history', history))
    application.add_handler(CallbackQueryHandler(history_callback, pattern='^history_'))

    # Веб-сервер для вебхуков
    app = web.Application()
    app.router.add_post('/webhook', webhook_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', WEBHOOK_PORT)
    await site.start()
    logger.info(f"Webhook server running on port {WEBHOOK_PORT}")

    # Запуск бота (поллинг)
    logger.info("Starting bot polling...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Stopping...")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await runner.cleanup()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
