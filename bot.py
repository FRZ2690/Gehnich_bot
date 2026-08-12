import logging
import json
import os
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters, ContextTypes
)
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# ============ تنظیمات ============
BOT_TOKEN = os.environ.get("BOT_TOKEN", "TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
DATA_FILE = "data.json"
PORT = int(os.environ.get("PORT", 10000))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ وب سرور ============
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("ربات فعال است".encode("utf-8"))
    def log_message(self, format, *args):
        pass

def run_health_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()

# ============ مراحل ============
(
    MAIN_MENU, CHECKOUT_NAME, CHECKOUT_PHONE, CHECKOUT_ADDRESS,
    CHECKOUT_SHIPPING, UPLOAD_RECEIPT, ADMIN_NEW_PRICE,
    ADMIN_ADD_PRODUCT_NAME, ADMIN_ADD_PRODUCT_PRICE, ADMIN_ADD_PRODUCT_UNIT
) = range(10)

# ============ دیتابیس ============
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        default_data = {
            "products": {
                "زردچوبه": {"price": 150000, "unit": "کیلویی", "available": True},
                "دارچین": {"price": 200000, "unit": "کیلویی", "available": True},
                "زعفران": {"price": 850000, "unit": "مثقالی", "available": True},
                "فلفل سیاه": {"price": 180000, "unit": "کیلویی", "available": True},
                "زنجبیل": {"price": 120000, "unit": "کیلویی", "available": True},
                "هل سبز": {"price": 950000, "unit": "کیلویی", "available": True},
                "پودر کاری": {"price": 160000, "unit": "کیلویی", "available": True},
                "سماق": {"price": 130000, "unit": "کیلویی", "available": True},
                "آویشن": {"price": 110000, "unit": "کیلویی", "available": True},
                "رازیانه": {"price": 95000, "unit": "کیلویی", "available": True},
                "میخک": {"price": 380000, "unit": "کیلویی", "available": True},
                "جوز هندی": {"price": 420000, "unit": "کیلویی", "available": True},
            },
            "orders": [],
            "shipping_options": {
                "پست پیشتاز": 45000,
                "پست سفارشی": 30000,
                "تیپاکس": 65000,
                "پیک (تهران)": 50000
            },
            "card_number": "6037-XXXX-XXXX-XXXX",
            "card_holder": "نام صاحب فروشگاه"
        }
        save_data(default_data)
        return default_data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def format_price(price):
    return f"{price:,} تومان"

# ============ شروع ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if "cart" not in context.user_data:
        context.user_data["cart"] = {}

    welcome_text = (
        f"🌿 سلام {user.first_name} عزیز!\n\n"
        f"به فروشگاه ادویه جات خوش آمدید\n\n"
        f"از منوی زیر انتخاب کنید:"
    )

    keyboard = [
        [InlineKeyboardButton("🛒 مشاهده محصولات", callback_data="browse")],
        [InlineKeyboardButton("🔍 جستجوی محصول", callback_data="search")],
        [InlineKeyboardButton("🛍 سبد خرید", callback_data="cart")],
        [InlineKeyboardButton("📞 تماس با ما", callback_data="contact")],
    ]

    if user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    return MAIN_MENU

# ============ محصولات ============
async def browse_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    products = data["products"]

    text = "🌿 لیست محصولات موجود:\n\n"
    keyboard = []

    for name, info in products.items():
        if info["available"]:
            text += f"▫️ {name} - {format_price(info['price'])} ({info['unit']})\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"🌶 {name} | {format_price(info['price'])}",
                    callback_data=f"product_{name}"
                )
            ])

    keyboard.append([InlineKeyboardButton("🛍 سبد خرید", callback_data="cart")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def view_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_name = query.data.replace("product_", "")
    data = load_data()

    if product_name not in data["products"]:
        await query.edit_message_text("❌ محصول پیدا نشد!")
        return MAIN_MENU

    product = data["products"][product_name]
    context.user_data["selected_product"] = product_name

    text = (
        f"🌿 {product_name}\n\n"
        f"💰 قیمت: {format_price(product['price'])}\n"
        f"📦 واحد: {product['unit']}\n"
        f"✅ موجود\n\n"
        f"تعداد مورد نظر را انتخاب کنید:"
    )

    keyboard = [
        [
            InlineKeyboardButton("1️⃣", callback_data="qty_1"),
            InlineKeyboardButton("2️⃣", callback_data="qty_2"),
            InlineKeyboardButton("3️⃣", callback_data="qty_3"),
        ],
        [
            InlineKeyboardButton("۰.۵", callback_data="qty_0.5"),
            InlineKeyboardButton("۱.۵", callback_data="qty_1.5"),
            InlineKeyboardButton("5️⃣", callback_data="qty_5"),
        ],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="browse")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    qty_str = query.data.replace("qty_", "")
    qty = float(qty_str)
    product_name = context.user_data.get("selected_product")

    if not product_name:
        await query.edit_message_text("❌ خطا! دوباره محصول را انتخاب کنید.")
        return MAIN_MENU

    if "cart" not in context.user_data:
        context.user_data["cart"] = {}

    if product_name in context.user_data["cart"]:
        context.user_data["cart"][product_name] += qty
    else:
        context.user_data["cart"][product_name] = qty

    data = load_data()
    product = data["products"][product_name]
    item_total = int(product["price"] * qty)

    text = (
        f"✅ {product_name} به سبد خرید اضافه شد!\n\n"
        f"📦 مقدار: {qty} {product['unit']}\n"
        f"💰 قیمت: {format_price(item_total)}\n"
    )

    keyboard = [
        [InlineKeyboardButton("🛒 ادامه خرید", callback_data="browse")],
        [InlineKeyboardButton("🛍 مشاهده سبد خرید", callback_data="cart")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_main")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cart = context.user_data.get("cart", {})

    if not cart:
        keyboard = [
            [InlineKeyboardButton("🛒 مشاهده محصولات", callback_data="browse")],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🛍 سبد خرید شما خالی است!", reply_markup=reply_markup)
        return MAIN_MENU

    data = load_data()
    text = "🛍 سبد خرید شما:\n\n"
    total = 0

    for product_name, qty in cart.items():
        if product_name in data["products"]:
            price = data["products"][product_name]["price"]
            unit = data["products"][product_name]["unit"]
            item_total = int(price * qty)
            total += item_total
            text += f"▫️ {product_name}: {qty} {unit} = {format_price(item_total)}\n"

    text += f"\n💰 جمع کل: {format_price(total)}"

    keyboard = [
        [InlineKeyboardButton("✅ تکمیل سفارش", callback_data="checkout")],
        [InlineKeyboardButton("🗑 خالی کردن سبد", callback_data="clear_cart")],
        [InlineKeyboardButton("🛒 ادامه خرید", callback_data="browse")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_main")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["cart"] = {}

    keyboard = [
        [InlineKeyboardButton("🛒 مشاهده محصولات", callback_data="browse")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("🗑 سبد خرید خالی شد!", reply_markup=reply_markup)
    return MAIN_MENU

# ============ تکمیل سفارش ============
async def checkout_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cart = context.user_data.get("cart", {})
    if not cart:
        await query.edit_message_text("❌ سبد خرید خالی است!")
        return MAIN_MENU

    await query.edit_message_text(
        "📝 تکمیل سفارش - مرحله ۱ از ۴\n\nلطفا نام و نام خانوادگی خود را وارد کنید:"
    )
    return CHECKOUT_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["customer_name"] = update.message.text
    await update.message.reply_text("📝 مرحله ۲ از ۴\n\nلطفا شماره تلفن خود را وارد کنید:")
    return CHECKOUT_PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["customer_phone"] = update.message.text
    await update.message.reply_text(
        "📝 مرحله ۳ از ۴\n\nلطفا آدرس کامل خود را وارد کنید:\n(استان، شهر، خیابان، پلاک، کدپستی)"
    )
    return CHECKOUT_ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["customer_address"] = update.message.text

    data = load_data()
    shipping = data["shipping_options"]

    text = "📝 مرحله ۴ از ۴\n\n🚚 روش ارسال را انتخاب کنید:\n\n"
    keyboard = []

    for method, cost in shipping.items():
        text += f"▫️ {method}: {format_price(cost)}\n"
        keyboard.append([
            InlineKeyboardButton(
                f"🚚 {method} | {format_price(cost)}",
                callback_data=f"ship_{method}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)
    return CHECKOUT_SHIPPING

async def select_shipping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    shipping_method = query.data.replace("ship_", "")
    context.user_data["shipping_method"] = shipping_method

    data = load_data()
    shipping_cost = data["shipping_options"].get(shipping_method, 0)
    context.user_data["shipping_cost"] = shipping_cost

    cart = context.user_data.get("cart", {})
    products_total = 0
    order_details = ""

    for product_name, qty in cart.items():
        if product_name in data["products"]:
            price = data["products"][product_name]["price"]
            unit = data["products"][product_name]["unit"]
            item_total = int(price * qty)
            products_total += item_total
            order_details += f"  ▫️ {product_name}: {qty} {unit} = {format_price(item_total)}\n"

    grand_total = products_total + shipping_cost
    context.user_data["grand_total"] = grand_total

    text = (
        f"🧾 خلاصه سفارش:\n\n"
        f"👤 نام: {context.user_data['customer_name']}\n"
        f"📱 تلفن: {context.user_data['customer_phone']}\n"
        f"📍 آدرس: {context.user_data['customer_address']}\n"
        f"🚚 ارسال: {shipping_method}\n\n"
        f"📦 محصولات:\n{order_details}\n"
        f"💰 جمع محصولات: {format_price(products_total)}\n"
        f"🚚 هزینه ارسال: {format_price(shipping_cost)}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💵 مبلغ قابل پرداخت: {format_price(grand_total)}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💳 شماره کارت:\n"
        f"{data['card_number']}\n"
        f"به نام: {data['card_holder']}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"لطفا مبلغ را واریز کنید و عکس رسید را ارسال کنید:"
    )

    keyboard = [[InlineKeyboardButton("❌ انصراف", callback_data="back_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return UPLOAD_RECEIPT

async def receive_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ لطفا عکس رسید پرداخت را ارسال کنید.")
        return UPLOAD_RECEIPT

    data = load_data()
    cart = context.user_data.get("cart", {})
    user = update.effective_user

    order = {
        "order_id": len(data["orders"]) + 1,
        "user_id": user.id,
        "username": user.username or "ندارد",
        "customer_name": context.user_data["customer_name"],
        "customer_phone": context.user_data["customer_phone"],
        "customer_address": context.user_data["customer_address"],
        "shipping_method": context.user_data["shipping_method"],
        "shipping_cost": context.user_data["shipping_cost"],
        "items": dict(cart),
        "grand_total": context.user_data["grand_total"],
        "status": "در انتظار تایید"
    }

    data["orders"].append(order)
    save_data(data)

    await update.message.reply_text(
        f"✅ سفارش شما ثبت شد!\n\n"
        f"🔢 شماره سفارش: #{order['order_id']}\n"
        f"💵 مبلغ: {format_price(order['grand_total'])}\n\n"
        f"وضعیت: در انتظار تایید پرداخت\n"
        f"🙏 از خرید شما متشکریم!"
    )

    order_text = ""
    for product_name, qty in cart.items():
        if product_name in data["products"]:
            price = data["products"][product_name]["price"]
            unit = data["products"][product_name]["unit"]
            order_text += f"  ▫️ {product_name}: {qty} {unit} = {format_price(int(price * qty))}\n"

    admin_text = (
        f"🔔 سفارش جدید #{order['order_id']}\n\n"
        f"👤 نام: {order['customer_name']}\n"
        f"📱 تلفن: {order['customer_phone']}\n"
        f"📍 آدرس: {order['customer_address']}\n"
        f"🚚 ارسال: {order['shipping_method']} ({format_price(order['shipping_cost'])})\n\n"
        f"📦 محصولات:\n{order_text}\n"
        f"💵 مبلغ کل: {format_price(order['grand_total'])}\n\n"
        f"🆔 یوزرنیم: @{order['username']}\n"
        f"🔑 آیدی: {order['user_id']}"
    )

    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text)
        photo = update.message.photo[-1]
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo.file_id,
            caption=f"🧾 رسید پرداخت سفارش #{order['order_id']}"
        )
    except Exception as e:
        logger.error(f"Error sending to admin: {e}")

    context.user_data["cart"] = {}
    return ConversationHandler.END

async def contact_us(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = (
        "📞 تماس با ما:\n\n"
        "📱 تلفن: 09XXXXXXXXX\n"
        "🏪 آدرس: تهران\n"
        "⏰ ساعت کاری: ۹ صبح تا ۹ شب"
    )

    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔍 نام محصول مورد نظر خود را تایپ کنید:")
    context.user_data["searching"] = True
    return MAIN_MENU

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("searching"):
        context.user_data["searching"] = False
        search_term = update.message.text
        data = load_data()
        results = {}
        for name, info in data["products"].items():
            if search_term in name and info["available"]:
                results[name] = info

        if not results:
            text = f"❌ محصولی با نام «{search_term}» پیدا نشد."
            keyboard = [
                [InlineKeyboardButton("🛒 همه محصولات", callback_data="browse")],
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_main")],
            ]
        else:
            text = f"🔍 نتایج جستجو:\n\n"
            keyboard = []
            for name, info in results.items():
                text += f"▫️ {name} - {format_price(info['price'])}\n"
                keyboard.append([
                    InlineKeyboardButton(f"🌶 {name}", callback_data=f"product_{name}")
                ])
            keyboard.append([InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_main")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup)
        return MAIN_MENU

# ============ پنل مدیریت ============
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text("❌ شما دسترسی ندارید!")
        return MAIN_MENU

    text = "⚙️ پنل مدیریت فروشگاه\n\nیکی از گزینه ها را انتخاب کنید:"

    keyboard = [
        [InlineKeyboardButton("💰 ویرایش قیمت ها", callback_data="admin_prices")],
        [InlineKeyboardButton("➕ افزودن محصول", callback_data="admin_add")],
        [InlineKeyboardButton("➖ حذف محصول", callback_data="admin_remove")],
        [InlineKeyboardButton("📋 لیست سفارشات", callback_data="admin_orders")],
        [InlineKeyboardButton("📊 آمار فروش", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def admin_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    text = "💰 ویرایش قیمت ها\n\nمحصول را انتخاب کنید:\n\n"
    keyboard = []

    for name, info in data["products"].items():
        text += f"▫️ {name}: {format_price(info['price'])}\n"
        keyboard.append([
            InlineKeyboardButton(
                f"✏️ {name} | {format_price(info['price'])}",
                callback_data=f"editprice_{name}"
            )
        ])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def admin_select_for_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_name = query.data.replace("editprice_", "")
    context.user_data["editing_product"] = product_name

    data = load_data()
    current_price = data["products"][product_name]["price"]

    await query.edit_message_text(
        f"✏️ ویرایش قیمت {product_name}\n\n"
        f"💰 قیمت فعلی: {format_price(current_price)}\n\n"
        f"لطفا قیمت جدید را به تومان وارد کنید:\n(فقط عدد، مثلا: 150000)"
    )
    return ADMIN_NEW_PRICE

async def save_new_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_price = int(update.message.text.replace(",", "").replace("،", ""))
    except ValueError:
        await update.message.reply_text("❌ لطفا فقط عدد وارد کنید!")
        return ADMIN_NEW_PRICE

    product_name = context.user_data.get("editing_product")
    data = load_data()

    if product_name in data["products"]:
        old_price = data["products"][product_name]["price"]
        data["products"][product_name]["price"] = new_price
        save_data(data)

        await update.message.reply_text(
            f"✅ قیمت {product_name} تغییر کرد!\n\n"
            f"💰 قبلی: {format_price(old_price)}\n"
            f"💰 جدید: {format_price(new_price)}"
        )

    keyboard = [
        [InlineKeyboardButton("💰 ویرایش قیمت دیگر", callback_data="admin_prices")],
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("چه کاری انجام بدم؟", reply_markup=reply_markup)
    return MAIN_MENU

async def admin_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("➕ افزودن محصول جدید\n\nنام محصول را وارد کنید:")
    return ADMIN_ADD_PRODUCT_NAME

async def get_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_product_name"] = update.message.text
    await update.message.reply_text(f"✅ نام: {update.message.text}\n\nقیمت را به تومان وارد کنید:")
    return ADMIN_ADD_PRODUCT_PRICE

async def get_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = int(update.message.text.replace(",", "").replace("،", ""))
        context.user_data["new_product_price"] = price
    except ValueError:
        await update.message.reply_text("❌ فقط عدد وارد کنید!")
        return ADMIN_ADD_PRODUCT_PRICE

    await update.message.reply_text(
        f"✅ قیمت: {format_price(price)}\n\n"
        f"واحد فروش را وارد کنید:\n(مثلا: کیلویی، مثقالی، بسته ای)"
    )
    return ADMIN_ADD_PRODUCT_UNIT

async def get_product_unit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    unit = update.message.text
    name = context.user_data["new_product_name"]
    price = context.user_data["new_product_price"]

    data = load_data()
    data["products"][name] = {"price": price, "unit": unit, "available": True}
    save_data(data)

    await update.message.reply_text(
        f"✅ محصول اضافه شد!\n\n🌶 {name}\n💰 {format_price(price)}\n📦 {unit}"
    )

    keyboard = [
        [InlineKeyboardButton("➕ محصول دیگر", callback_data="admin_add")],
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("چه کاری انجام بدم؟", reply_markup=reply_markup)
    return MAIN_MENU

async def admin_remove_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    keyboard = []
    for name in data["products"]:
        keyboard.append([InlineKeyboardButton(f"🗑 {name}", callback_data=f"remove_{name}")])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("➖ حذف محصول\n\nکدام محصول حذف شود؟", reply_markup=reply_markup)
    return MAIN_MENU

async def confirm_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_name = query.data.replace("remove_", "")
    data = load_data()

    if product_name in data["products"]:
        del data["products"][product_name]
        save_data(data)
        text = f"✅ {product_name} حذف شد!"
    else:
        text = "❌ محصول پیدا نشد!"

    keyboard = [
        [InlineKeyboardButton("➖ حذف دیگر", callback_data="admin_remove")],
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    orders = data.get("orders", [])

    if not orders:
        text = "📋 هیچ سفارشی ثبت نشده."
    else:
        text = "📋 سفارشات:\n\n"
        for order in orders[-10:]:
            items_text = ""
            for item, qty in order["items"].items():
                items_text += f"  • {item}: {qty}\n"
            text += (
                f"━━━━━━━━━━━━\n"
                f"# {order['order_id']}\n"
                f"👤 {order['customer_name']}\n"
                f"📱 {order['customer_phone']}\n"
                f"📍 {order['customer_address']}\n"
                f"🚚 {order['shipping_method']}\n"
                f"📦:\n{items_text}"
                f"💵 {format_price(order['grand_total'])}\n"
                f"📋 {order['status']}\n\n"
            )

    keyboard = [
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if len(text) > 4000:
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for i, chunk in enumerate(chunks):
            if i == len(chunks) - 1:
                await context.bot.send_message(
                    chat_id=query.message.chat_id, text=chunk, reply_markup=reply_markup
                )
            else:
                await context.bot.send_message(chat_id=query.message.chat_id, text=chunk)
    else:
        await query.edit_message_text(text, reply_markup=reply_markup)

    return MAIN_MENU

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    orders = data.get("orders", [])

    text = (
        f"📊 آمار فروشگاه:\n\n"
        f"📦 تعداد سفارشات: {len(orders)}\n"
        f"💰 مجموع فروش: {format_price(sum(o.get('grand_total', 0) for o in orders))}\n"
        f"🌶 تعداد محصولات: {len(data['products'])}"
    )

    keyboard = [
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await start(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ لغو شد. برای شروع /start بزنید.")
    return ConversationHandler.END

def main():
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    logger.info(f"Health server on port {PORT}")

    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(browse_products, pattern="^browse$"),
                CallbackQueryHandler(view_product, pattern="^product_"),
                CallbackQueryHandler(add_to_cart, pattern="^qty_"),
                CallbackQueryHandler(show_cart, pattern="^cart$"),
                CallbackQueryHandler(clear_cart, pattern="^clear_cart$"),
                CallbackQueryHandler(checkout_start, pattern="^checkout$"),
                CallbackQueryHandler(contact_us, pattern="^contact$"),
                CallbackQueryHandler(search_start, pattern="^search$"),
                CallbackQueryHandler(admin_panel, pattern="^admin$"),
                CallbackQueryHandler(admin_prices, pattern="^admin_prices$"),
                CallbackQueryHandler(admin_select_for_price, pattern="^editprice_"),
                CallbackQueryHandler(admin_add_product, pattern="^admin_add$"),
                CallbackQueryHandler(admin_remove_product, pattern="^admin_remove$"),
                CallbackQueryHandler(confirm_remove, pattern="^remove_"),
                CallbackQueryHandler(admin_orders, pattern="^admin_orders$"),
                CallbackQueryHandler(admin_stats, pattern="^admin_stats$"),
                CallbackQueryHandler(back_to_main, pattern="^back_main$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message),
            ],
            CHECKOUT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            CHECKOUT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            CHECKOUT_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            CHECKOUT_SHIPPING: [
                CallbackQueryHandler(select_shipping, pattern="^ship_"),
                CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            ],
            UPLOAD_RECEIPT: [
                MessageHandler(filters.PHOTO, receive_receipt),
                CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            ],
            ADMIN_NEW_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_price)],
            ADMIN_ADD_PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_product_name)],
            ADMIN_ADD_PRODUCT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_product_price)],
            ADMIN_ADD_PRODUCT_UNIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_product_unit)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    logger.info("Bot started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
