import yookassa
from yookassa import Configuration, Payment
from config import SHOP_ID, SECRET_KEY, TEST_MODE
import time
import logging

logger = logging.getLogger(__name__)

Configuration.account_id = SHOP_ID
Configuration.secret_key = SECRET_KEY

async def create_payment(amount, description, order_id, user_id, username, product_name, return_url=None):
    if not return_url:
        return_url = "https://t.me/your_bot"
    payment = Payment.create({
        "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": return_url},
        "capture": True,
        "description": description,
        "metadata": {
            "order_id": str(order_id),
            "user_id": str(user_id),
            "username": username,
            "product": product_name
        },
        "test": TEST_MODE
    }, idempotency_key=f"{order_id}_{user_id}_{int(time.time())}")
    return payment

async def handle_webhook(data, signature):
    try:
        event = yookassa.Webhook.handle(data, signature)
        if event.event_type == 'payment.succeeded':
            return {'payment_id': event.object.id, 'status': 'paid'}
        elif event.event_type == 'payment.canceled':
            return {'payment_id': event.object.id, 'status': 'failed'}
        else:
            return None
    except Exception as e:
        logger.error(f"Webhook signature error: {e}")
        raise
