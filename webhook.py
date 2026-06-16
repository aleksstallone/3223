import json
import logging
from aiohttp import web
from services.payment import handle_webhook
from database import AsyncSessionLocal, Order
from config import PRODUCTS
from services.rcon import send_rcon_command
from telegram import Bot
from config import BOT_TOKEN

logger = logging.getLogger(__name__)
bot = Bot(token=BOT_TOKEN)

async def webhook_handler(request):
    try:
        data = await request.json()
        signature = request.headers.get('X-Yoo-Signature')
        if not signature:
            return web.Response(status=400, text="Missing signature")
        result = await handle_webhook(data, signature)
        if not result:
            return web.Response(status=200, text="Ignored event")
        payment_id = result['payment_id']
        status = result['status']
        if status == 'paid':
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    order = await session.execute(
                        "SELECT * FROM orders WHERE payment_id = :pid", {"pid": payment_id}
                    )
                    order = order.fetchone()
                    if not order:
                        return web.Response(status=404, text="Order not found")
                    if order.status == 'paid':
                        return web.Response(status=200, text="Already processed")
                    product_name = order.product_name
                    product = next((p for p in PRODUCTS if p['name'] == product_name), None)
                    if not product:
                        await session.execute(
                            "UPDATE orders SET status = 'failed', rcon_response = 'Product not found' WHERE payment_id = :pid",
                            {"pid": payment_id}
                        )
                        return web.Response(status=500, text="Product missing")
                    command = product['command'].format(nick=order.username)
                    try:
                        response = await send_rcon_command(command)
                        await session.execute(
                            "UPDATE orders SET status = 'paid', rcon_response = :resp WHERE payment_id = :pid",
                            {"resp": response, "pid": payment_id}
                        )
                        # Уведомляем пользователя
                        try:
                            await bot.send_message(
                                chat_id=order.user_id,
                                text=f"✅ Платёж подтверждён! Права на *{product_name}* выданы.",
                                parse_mode="Markdown"
                            )
                        except Exception as e:
                            logger.error(f"Notify error: {e}")
                        return web.Response(status=200, text="OK")
                    except Exception as e:
                        logger.error(f"RCON error: {e}")
                        await session.execute(
                            "UPDATE orders SET status = 'failed', rcon_response = :err WHERE payment_id = :pid",
                            {"err": str(e), "pid": payment_id}
                        )
                        return web.Response(status=500, text="RCON failed")
        elif status == 'failed':
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await session.execute(
                        "UPDATE orders SET status = 'failed' WHERE payment_id = :pid",
                        {"pid": payment_id}
                    )
            return web.Response(status=200, text="OK")
        else:
            return web.Response(status=200, text="OK")
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return web.Response(status=500, text=str(e))
