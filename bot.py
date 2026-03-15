from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters, Job
)
from datetime import time

# ====== إعدادات عامة ======
orders = {}
ADMIN_ID = 708528064  # 🔴 حط رقم الـ Telegram ID تبعك هنا
DAILY_CLEAR_TIME = time(hour=8, minute=30)  # مسح يومي للطلبات

announce_message_id = None
announce_chat_id = None
announce_job: Job = None  # لتحديث العداد
ANNOUNCE_DURATION = 15 * 60  # 15 دقيقة بالثواني

# ====== الكيبورد ======
def get_keyboard():
    keyboard = [
        [InlineKeyboardButton("اطلب", callback_data="order")],
        [InlineKeyboardButton("حذف طلباتي", callback_data="delete")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ====== Start ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🍔 أهلاً بالجوعان! استخدم الأزرار للطلب:",
        reply_markup=get_keyboard()
    )

# ====== Announce مع العداد ======
async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global announce_message_id, announce_chat_id, announce_job
    if update.effective_user.id != ADMIN_ID:
        return

    orders.clear()

    announce_chat_id = update.effective_chat.id
    remaining = ANNOUNCE_DURATION // 60  # دقائق متبقية

    # إرسال الرسالة بالغروب
    msg = await update.message.reply_text(
        f"📢 تم فتح الطلبية لليوم! اضغط على زر اطلب خلال {remaining} دقيقة 👇",
        reply_markup=get_keyboard()
    )
    announce_message_id = msg.message_id

    # جدولة تحديث العداد كل دقيقة
    announce_job = context.job_queue.run_repeating(
        update_announce_timer, 60,  # كل دقيقة
        data={"chat_id": announce_chat_id, "message_id": announce_message_id, "remaining": ANNOUNCE_DURATION}
    )

# ====== تحديث العداد ======
async def update_announce_timer(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    remaining = job_data["remaining"]
    chat_id = job_data["chat_id"]
    message_id = job_data["message_id"]

    remaining -= 60
    job_data["remaining"] = remaining

    if remaining <= 0:
        # الوقت انتهى → حذف الرسالة
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except:
            pass
        context.job.schedule_removal()
        return

    # تحديث الرسالة مع الوقت المتبقي
    minutes = remaining // 60
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=f"📢 تم فتح الطلبية لليوم! اضغط على زر اطلب خلال {minutes} دقيقة 👇",
        reply_markup=get_keyboard()
    )

# ====== عرض الطلبات ======
async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not orders:
        await update.message.reply_text("ما في طلبات حالياً.")
        return

    text = "📋 الطلبات الحالية:\n\n"
    for user, order in orders.items():
        text += f"• {user}: {order}\n"
    await update.message.reply_text(text)

# ====== ضغط الأزرار ======
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_name = query.from_user.first_name

    if query.data == "order":
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🍔 {user_name}، اكتب طلبك هنا:",
            reply_markup=get_keyboard()
        )
        context.user_data["await_order"] = True

    elif query.data == "delete":
        if user_name in orders:
            del orders[user_name]
        await context.bot.send_message(chat_id=user_id, text="🗑 تم حذف جميع طلباتك")

# ====== تسجيل الطلب بالخاص فقط ======
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    user_name = update.message.from_user.first_name

    if context.user_data.get("await_order"):
        text = update.message.text
        orders[user_name] = text
        await update.message.reply_text("✅ تم تسجيل طلبك\nدقائق الانتظار اكسبها بالاستغفار")
        context.user_data["await_order"] = False

# ====== مسح الطلبات يومياً ======
async def auto_clear(context: ContextTypes.DEFAULT_TYPE):
    orders.clear()
    print("✅ تم مسح الطلبات القديمة تلقائياً")

# ====== مسح الطلبات يدوي ======
async def clear_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    orders.clear()
    await update.message.reply_text("🗑 تم مسح جميع الطلبات يدوياً")

# ====== Main ======
def main():
    TOKEN = "7796058802:AAHfuch3IxkI5wx4rOy7Yaj1IZLqWU4lno8"  # ضع توكنك هنا
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("announce", announce))
    app.add_handler(CommandHandler("orders", show_orders))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(CommandHandler("clear", clear_orders))

    app.job_queue.run_daily(auto_clear, DAILY_CLEAR_TIME)

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()

