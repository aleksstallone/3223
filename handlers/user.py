from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
import logging
from database import AsyncSessionLocal, User, Order
from config import PRODUCTS
from services.payment import create_payment
from sqlalchemy import select, func, desc
import time

logger = logging.getLogger(__name__)

SELECTING_PRODUCT, ENTERING_NICK, CONFIRM_PAYMENT = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    async with AsyncSessionLocal() as session:
        async with session.begin():
            existing = await session.execute(select(User).where(User.id == user.id))
            if not existing.scalar_one_or_none():
                session.add(User(id=user.id, username=user.username, first_name=user.first_name))
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n"
        "Я бот для покупки доната на Minecraft сервере.\n\n"
        "/buy — выбрать товар\n"
        "/history — история покупок\n"
        "/help — справка\n"
        "/admin — RCON-команда (для админов)"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/buy — купить донат\n"
        "/history — мои покупки\n"
        "/admin — выполнить RCON-команду (админы)\n"
        "/help — эта справка\n"
        "/cancel — отменить"
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not PRODUCTS:
        await update.message.reply_text("😕 Товары недоступны.")
        return ConversationHandler.END
    keyboard = []
    for p in PRODUCTS:
        keyboard.append([InlineKeyboardButton(f"{p['name']} — {p['price']} руб.", callback_data=f"product_{p['name']}")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    await update.message.reply_text("🛍 Выберите товар:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECTING_PRODUCT

async def product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("❌ Отменено.")
        return ConversationHandler.END
    product_name = query.data.replace("product_", "")
    product = next((p for p in PRODUCTS if p['name'] == product_name), None)
    if not product:
        await query.edit_message_text("❌ Товар не найден.")
        return ConversationHandler.END
    context.user_data['product_name'] = product_name
    context.user_data['product_price'] = product['price']
    context.user_data['product_command'] = product['command']
    await query.edit_message_text(f"✅ Вы выбрали *{product_name}* за *{product['price']}* руб.\nВведите ник игрока:", parse_mode="Markdown")
    return ENTERING_NICK

async def enter_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nick = update.message.text.strip()
    if not nick or len(nick) > 32 or not nick.isalnum():
        await update.message.reply_text("❌ Некорректный ник. Только буквы/цифры до 32 символов.")
        return ENTERING_NICK
    context.user_data['mc_nick'] = nick
    product_name = context.user_data['product_name']
    price = context.user_data['product_price']
    keyboard = [
        [InlineKeyboardButton("✅ Оплатить", callback_data="pay_confirm")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
    ]
    await update.message.reply_text(
        f"📝 Проверьте: {product_name} — {price} руб., ник: {nick}\nНажмите «Оплатить».",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRM_PAYMENT

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("❌ Отменено.")
        return ConversationHandler.END

    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or "Игрок"
    mc_nick = context.user_data['mc_nick']
    product_name = context.user_data['product_name']
    price = context.user_data['product_price']

    payment_id = f"temp_{user_id}_{int(time.time())}"
    async with AsyncSessionLocal() as session:
        async with session.begin():
            order = Order(
                user_id=user_id,
                username=username,
                product_name=product_name,
                amount=price,
                payment_id=payment_id,
                status="pending"
            )
            session.add(order)
            await session.flush()
            order_id = order.id

    try:
        payment = await create_payment(price, f"Покупка {product_name} для {mc_nick}", order_id, user_id, mc_nick, product_name)
        # Обновляем payment_id
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(
                    "UPDATE orders SET payment_id = :pid WHERE id = :oid",
                    {"pid": payment.id, "oid": order_id}
                )
        url = payment.confirmation.confirmation_url
        keyboard = [[InlineKeyboardButton("🔗 Оплатить", url=url)]]
        await query.edit_message_text(
            f"💳 Платёж создан! Сумма: {price} руб.\nПосле оплаты права выдадут автоматически.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Payment error: {e}")
        await query.edit_message_text("❌ Ошибка создания платежа. Попробуйте позже.")
    return ConversationHandler.END

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    page = int(context.args[0]) if context.args and context.args[0].isdigit() else 0
    limit = 5
    offset = page * limit
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(Order)
                .where(Order.user_id == user_id)
                .order_by(desc(Order.created_at))
                .offset(offset)
                .limit(limit)
            )
            orders = result.scalars().all()
            total = await session.execute(select(func.count(Order.id)).where(Order.user_id == user_id))
            total = total.scalar()
    if not orders:
        await update.message.reply_text("📭 У вас пока нет покупок.")
        return
    text = "📜 *Ваши покупки:*\n\n"
    for o in orders:
        emoji = {"pending":"⏳","paid":"✅","failed":"❌"}.get(o.status, "❓")
        text += f"{emoji} *{o.product_name}* — {o.amount} руб.\n"
        text += f"   Статус: {o.status}\n"
        text += f"   {o.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    if total > limit:
        text += f"Страница {page+1} из { (total+limit-1)//limit }\n"
        keyboard = []
        if page > 0:
            keyboard.append(InlineKeyboardButton("◀️ Назад", callback_data=f"history_{page-1}"))
        if (page+1)*limit < total:
            keyboard.append(InlineKeyboardButton("Вперёд ▶️", callback_data=f"history_{page+1}"))
        if keyboard:
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([keyboard]))
        else:
            await update.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

async def history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split("_")[1])
    user_id = update.effective_user.id
    limit = 5
    offset = page * limit
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(Order)
                .where(Order.user_id == user_id)
                .order_by(desc(Order.created_at))
                .offset(offset)
                .limit(limit)
            )
            orders = result.scalars().all()
            total = await session.execute(select(func.count(Order.id)).where(Order.user_id == user_id))
            total = total.scalar()
    text = "📜 *Ваши покупки:*\n\n"
    for o in orders:
        emoji = {"pending":"⏳","paid":"✅","failed":"❌"}.get(o.status, "❓")
        text += f"{emoji} *{o.product_name}* — {o.amount} руб.\n"
        text += f"   Статус: {o.status}\n"
        text += f"   {o.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    if total > limit:
        text += f"Страница {page+1} из { (total+limit-1)//limit }\n"
        keyboard = []
        if page > 0:
            keyboard.append(InlineKeyboardButton("◀️ Назад", callback_data=f"history_{page-1}"))
        if (page+1)*limit < total:
            keyboard.append(InlineKeyboardButton("Вперёд ▶️", callback_data=f"history_{page+1}"))
        if keyboard:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([keyboard]))
        else:
            await query.edit_message_text(text, parse_mode="Markdown")
    else:
        await query.edit_message_text(text, parse_mode="Markdown")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Операция отменена.")
    return ConversationHandler.END
