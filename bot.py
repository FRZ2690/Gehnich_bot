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
    ADMIN_ADD_PRODUCT_CAT, ADMIN_ADD_PRODUCT_NAME,
    ADMIN_ADD_PRODUCT_PRICE, ADMIN_ADD_PRODUCT_UNIT
) = range(11)

# ============ دیتابیس ============
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        default_data = {
            "categories": {
                "چاشنی های گهنیج": {
                    "پودر لیمو عمانی (نمکپاشی)": {"price": 110000, "unit": "نمکپاشی", "available": True},
                    "چاشنی ماست (نمکپاشی)": {"price": 120000, "unit": "نمکپاشی", "available": True},
                    "چاشنی ماست (نیم کیلویی)": {"price": 475000, "unit": "نیم کیلویی", "available": True},
                    "ادویه سوسیس بندری (قوطی مربعی)": {"price": 200000, "unit": "قوطی مربعی", "available": True},
                    "ادویه سوسیس بندری (نیم کیلویی)": {"price": 590000, "unit": "نیم کیلویی", "available": True},
                    "چاشنی زعتر (نمکپاشی)": {"price": 150000, "unit": "نمکپاشی", "available": True},
                    "چاشنی زعتر (نیم کیلویی)": {"price": 490000, "unit": "نیم کیلویی", "available": True},
                    "چاشنی املت (نمکپاشی)": {"price": 120000, "unit": "نمکپاشی", "available": True},
                    "چاشنی املت (نیم کیلویی)": {"price": 300000, "unit": "نیم کیلویی", "available": True},
                    "چاشنی سیب زمینی (نمکپاشی)": {"price": 150000, "unit": "نمکپاشی", "available": True},
                    "چاشنی سیب زمینی (نیم کیلویی)": {"price": 460000, "unit": "نیم کیلویی", "available": True},
                    "ایتالیایی (نمکپاشی)": {"price": 150000, "unit": "نمکپاشی", "available": True},
                    "ایتالیایی (نیم کیلویی)": {"price": 555000, "unit": "نیم کیلویی", "available": True},
                    "ادویه ماکارونی (نمکپاشی)": {"price": 150000, "unit": "نمکپاشی", "available": True},
                    "ادویه ماکارونی (نیم کیلویی)": {"price": 490000, "unit": "نیم کیلویی", "available": True},
                    "فلفل سیاه (نمکپاشی)": {"price": 220000, "unit": "نمکپاشی", "available": True},
                    "فلفل سیاه (نیم کیلویی)": {"price": 950000, "unit": "نیم کیلویی", "available": True},
                    "فلفل سیاه (نکوبیده قوطی 150گ)": {"price": 300000, "unit": "قوطی 150 گرم", "available": True},
                    "دارچین (نمکپاشی)": {"price": 100000, "unit": "نمکپاشی", "available": True},
                    "دارچین (نیم کیلویی)": {"price": 395000, "unit": "نیم کیلویی", "available": True},
                    "دارچین (سالم 150 گ)": {"price": 150000, "unit": "قوطی 150 گرم سالم", "available": True},
                    "پودر فلفل قرمز تند چیلی (نمکپاشی)": {"price": 150000, "unit": "نمکپاشی", "available": True},
                    "پودر فلفل قرمز تند چیلی (نیم کیلویی)": {"price": 640000, "unit": "نیم کیلویی", "available": True},
                },
                "ادویه جات ترکیبی گهنیج": {
                    "ادویه مامان بلوچی (قوطی مربعی 130گ)": {"price": 200000, "unit": "قوطی مربعی 130 گرم", "available": True},
                    "ادویه مامان بلوچی (پاکت نیم کیلویی)": {"price": 600000, "unit": "پاکت نیم کیلویی", "available": True},
                    "ادویه بریانی بلوچی (قوطی مربعی 130گ)": {"price": 170000, "unit": "قوطی مربعی 130 گرم", "available": True},
                    "ادویه بریانی بلوچی (پاکت نیم کیلویی)": {"price": 435000, "unit": "پاکت نیم کیلویی", "available": True},
                    "ادویه عربی مخصوص (قوطی مربعی 130گ)": {"price": 370000, "unit": "قوطی مربعی 130 گرم", "available": True},
                    "ادویه عربی مخصوص (پاکت نیم کیلویی)": {"price": 1245000, "unit": "پاکت نیم کیلویی", "available": True},
                    "ادویه کاری مخصوص (قوطی مربعی 130گ)": {"price": 180000, "unit": "قوطی مربعی 130 گرم", "available": True},
                    "ادویه کاری مخصوص (پاکت نیم کیلویی)": {"price": 480000, "unit": "پاکت نیم کیلویی", "available": True},
                    "ادویه ماهی و میگو (قوطی مربعی 130گ)": {"price": 200000, "unit": "قوطی مربعی 130 گرم", "available": True},
                    "ادویه ماهی و میگو (پاکت نیم کیلویی)": {"price": 570000, "unit": "پاکت نیم کیلویی", "available": True},
                    "ادویه کباب (قوطی مربعی 130گ)": {"price": 170000, "unit": "قوطی مربعی 130 گرم", "available": True},
                    "ادویه کباب (پاکت نیم کیلویی)": {"price": 470000, "unit": "پاکت نیم کیلویی", "available": True},
                    "ادویه کرایی بلوچی (قوطی مربعی 130گ)": {"price": 200000, "unit": "قوطی مربعی 130 گرم", "available": True},
                    "ادویه کرایی بلوچی (پاکت نیم کیلویی)": {"price": 610000, "unit": "پاکت نیم کیلویی", "available": True},
                    "ادویه کاچی (قوطی مربعی 130گ)": {"price": 170000, "unit": "قوطی مربعی 130 گرم", "available": True},
                    "ادویه کاچی (پاکت نیم کیلویی)": {"price": 500000, "unit": "پاکت نیم کیلویی", "available": True},
                    "ادویه کاجون (قوطی مربعی 130گ)": {"price": 170000, "unit": "قوطی مربعی 130 گرم", "available": True},
                    "ادویه کاجون (پاکت نیم کیلویی)": {"price": 480000, "unit": "پاکت نیم کیلویی", "available": True},
                    "ادویه مرغ (قوطی مربعی 130گ)": {"price": 180000, "unit": "قوطی مربعی 130 گرم", "available": True},
                    "ادویه مرغ (نیم کیلویی پاکت)": {"price": 500000, "unit": "پاکت نیم کیلویی", "available": True},
                    "ادویه سمبوسه (قوطی مربعی 130گ)": {"price": 220000, "unit": "قوطی مربعی 130 گرم", "available": True},
                    "ادویه سمبوسه (پاکت نیم کیلویی)": {"price": 660000, "unit": "پاکت نیم کیلویی", "available": True},
                    "ادویه گراماسالا (قوطی مربعی 130گ)": {"price": 320000, "unit": "قوطی مربعی 130 گرم", "available": True},
                    "ادویه گراماسالا (پاکت نیم کیلویی)": {"price": 1035000, "unit": "پاکت نیم کیلویی", "available": True},
                    "ادویه فلافل (قوطی مربعی 130گ)": {"price": 180000, "unit": "قوطی مربعی 130 گرم", "available": True},
                    "ادویه پکوره (قوطی مربعی 130گ)": {"price": 120000, "unit": "قوطی مربعی 130 گرم", "available": True},
                },
                "ادویه جات اصلی": {
                    "پودر پاپریکا (قوطی مربعی)": {"price": 150000, "unit": "قوطی مربعی", "available": True},
                    "پودر پاپریکا (پاکت نیم کیلویی)": {"price": 360000, "unit": "پاکت نیم کیلویی", "available": True},
                    "پودر سیر خالص (قوطی 180 گ)": {"price": 220000, "unit": "قوطی 180 گرم", "available": True},
                    "پودر سیر خالص (پاکت نیم کیلویی)": {"price": 500000, "unit": "پاکت نیم کیلویی", "available": True},
                    "زیره سبز (قوطی مربعی)": {"price": 130000, "unit": "قوطی مربعی", "available": True},
                    "زیره سبز (پاکت نیم کیلویی)": {"price": 360000, "unit": "پاکت نیم کیلویی", "available": True},
                    "زیره سیاه (قوطی مربعی)": {"price": 410000, "unit": "قوطی مربعی", "available": True},
                    "زیره سیاه (پاکت نیم کیلویی)": {"price": 1330000, "unit": "پاکت نیم کیلویی", "available": True},
                    "زنجبیل (قوطی مربعی)": {"price": 140000, "unit": "قوطی مربعی", "available": True},
                    "زنجبیل (پاکت نیم کیلویی)": {"price": 480000, "unit": "پاکت نیم کیلویی", "available": True},
                    "پودر گشنیز (قوطی مربعی)": {"price": 100000, "unit": "قوطی مربعی", "available": True},
                    "پودر گشنیز (پاکت نیم کیلویی)": {"price": 280000, "unit": "پاکت نیم کیلویی", "available": True},
                    "تخم گشنیز (قوطی مربعی)": {"price": 80000, "unit": "قوطی مربعی", "available": True},
                    "تخم گشنیز (پاکت نیم کیلویی)": {"price": 280000, "unit": "پاکت نیم کیلویی", "available": True},
                },
                "دانه ها و تخم ها": {
                    "دانه چیا (200 گرمی)": {"price": 190000, "unit": "قوطی 200 گرم", "available": True},
                    "خاکشیر (200 گرمی)": {"price": 120000, "unit": "قوطی 200 گرم", "available": True},
                    "تخم شربتی ریز": {"price": 180000, "unit": "قوطی", "available": True},
                    "تخم شربتی درشت": {"price": 140000, "unit": "قوطی", "available": True},
                    "سیاهدانه": {"price": 200000, "unit": "قوطی", "available": True},
                    "بارهنگ": {"price": 160000, "unit": "قوطی", "available": True},
                    "پاپ کورن بزرگ (800 گ)": {"price": 330000, "unit": "قوطی 800 گرم", "available": True},
                    "اسپند": {"price": 80000, "unit": "قوطی", "available": True},
                    "تخم زنیان": {"price": 120000, "unit": "قوطی", "available": True},
                },
                "طعم دهنده ها": {
                    "آروماتز": {"price": 170000, "unit": "قوطی", "available": True},
                    "سیر و کره": {"price": 150000, "unit": "قوطی", "available": True},
                    "دود": {"price": 120000, "unit": "قوطی", "available": True},
                    "قارچ و خامه": {"price": 180000, "unit": "قوطی", "available": True},
                    "کره": {"price": 100000, "unit": "قوطی", "available": True},
                    "لیمو فلفلی زرد": {"price": 150000, "unit": "قوطی", "available": True},
                    "لیمو فلفلی چاشنی": {"price": 190000, "unit": "قوطی", "available": True},
                    "پنیر چدار": {"price": 120000, "unit": "قوطی", "available": True},
                    "پیاز جعفری": {"price": 150000, "unit": "قوطی", "available": True},
                    "کچاپ": {"price": 150000, "unit": "قوطی", "available": True},
                    "سماق": {"price": 200000, "unit": "قوطی", "available": True},
                    "ادویه انبه": {"price": 150000, "unit": "قوطی", "available": True},
                    "پودر آویشن": {"price": 200000, "unit": "قوطی", "available": True},
                    "ادویه برگر": {"price": 150000, "unit": "قوطی", "available": True},
                    "پودر لیمو": {"price": 110000, "unit": "قوطی", "available": True},
                    "پودر لبو": {"price": 120000, "unit": "قوطی", "available": True},
                    "عصاره مرغ": {"price": 120000, "unit": "قوطی", "available": True},
                },
                "سبزی خشک و متفرقه": {
                    "فلفل لاهوری (کناری)": {"price": 200000, "unit": "بسته", "available": True},
                    "نعناع خشک بزرگ": {"price": 220000, "unit": "بسته بزرگ", "available": True},
                    "نعناع خشک متوسط": {"price": 160000, "unit": "بسته متوسط", "available": True},
                    "شوید خشک بزرگ": {"price": 220000, "unit": "بسته بزرگ", "available": True},
                    "شنبلیله خشک": {"price": 230000, "unit": "بسته", "available": True},
                    "ترخون خشک": {"price": 260000, "unit": "بسته", "available": True},
                    "رزماری خشک قوطی": {"price": 70000, "unit": "قوطی", "available": True},
                    "برگ بو (40 گرم)": {"price": 100000, "unit": "بسته 40 گرم", "available": True},
                    "هل اکبر بنفش (20 گرمی)": {"price": 270000, "unit": "بسته 20 گرم", "available": True},
                    "نمک صورتی یک کیلو": {"price": 150000, "unit": "یک کیلو", "available": True},
                    "پرک لیمو کوچک": {"price": 200000, "unit": "بسته کوچک", "available": True},
                    "پرک لیمو بزرگ": {"price": 500000, "unit": "بسته بزرگ", "available": True},
                    "رب انار ترش": {"price": 450000, "unit": "بسته", "available": True},
                    "رب انار ترش متوسط": {"price": 420000, "unit": "بسته متوسط", "available": True},
                    "آبغوره خالص": {"price": 250000, "unit": "بسته", "available": True},
                    "غنچه گل محمدی": {"price": 300000, "unit": "بسته", "available": True},
                    "گلرنگ (زردی) بسته 80 گ": {"price": 250000, "unit": "بسته 80 گرم", "available": True},
                    "رب گوجه خالص خونگی 1100 گرم": {"price": 420000, "unit": "بسته 1100 گرم", "available": True},
                },
                "عرقیجات خالص": {
                    "گلاب ویژه": {"price": 290000, "unit": "بطری", "available": True},
                    "عرق نسترن": {"price": 190000, "unit": "بطری", "available": True},
                    "عرق بهار نارنج": {"price": 220000, "unit": "بطری", "available": True},
                    "عرق چهل گیاه": {"price": 200000, "unit": "بطری", "available": True},
                    "عرق زنیان": {"price": 150000, "unit": "بطری", "available": True},
                    "عرق بید مشک": {"price": 190000, "unit": "بطری", "available": True},
                    "عرق آویشن": {"price": 150000, "unit": "بطری", "available": True},
                    "عرق شاتره": {"price": 150000, "unit": "بطری", "available": True},
                    "عرق رازیانه": {"price": 150000, "unit": "بطری", "available": True},
                    "عرق شوید": {"price": 150000, "unit": "بطری", "available": True},
                    "عرق خار مریم": {"price": 150000, "unit": "بطری", "available": True},
                    "عرق خار شتر": {"price": 150000, "unit": "بطری", "available": True},
                    "عرق زیره": {"price": 150000, "unit": "بطری", "available": True},
                    "عرق کاسنی": {"price": 150000, "unit": "بطری", "available": True},
                    "عرق طارونه": {"price": 150000, "unit": "بطری", "available": True},
                    "معجون آرامش بخش": {"price": 270000, "unit": "بطری", "available": True},
                    "معجون معده": {"price": 270000, "unit": "بطری", "available": True},
                    "عرق نعناع": {"price": 220000, "unit": "بطری", "available": True},
                },
                "زردچوبه چارمنار": {
                    "زردچوبه چارمنار (نیم کیلو)": {"price": 470000, "unit": "نیم کیلو", "available": True},
                    "زردچوبه چارمنار (150 گرمی)": {"price": 180000, "unit": "150 گرمی", "available": True},
                },
            },
            "orders": [],
            "shipping_options": {
                "پست پیشتاز": 45000,
                "پست سفارشی": 30000,
                "تیپاکس": 65000,
                "پیک ": 100000
            },
            "card_number": "6219861941858903",
            "card_holder": "فهیمه امینی"
        }
        save_data(default_data)
        return default_data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def format_price(price):
    return f"{price:,} تومان"

def get_all_products(data):
    """همه محصولات رو از همه دسته ها برمیگردونه"""
    all_products = {}
    for cat_name, products in data.get("categories", {}).items():
        for prod_name, prod_info in products.items():
            all_products[prod_name] = {**prod_info, "category": cat_name}
    return all_products

def find_product(data, product_name):
    """یه محصول رو در دسته ها پیدا میکنه"""
    for cat_name, products in data.get("categories", {}).items():
        if product_name in products:
            return products[product_name], cat_name
    return None, None

# ============ شروع ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if "cart" not in context.user_data:
        context.user_data["cart"] = {}

    welcome_text = (
        f"🌿 سلام {user.first_name} عزیز!\n\n"
        f"به فروشگاه ادویه جات گهنیج خوش آمدید 🌶\n\n"
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

# ============ نمایش دسته بندی ها ============
async def browse_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    categories = data.get("categories", {})

    text = "🌿 دسته بندی محصولات:\n\nلطفا یک دسته را انتخاب کنید:"
    keyboard = []

    for cat_name in categories.keys():
        product_count = len(categories[cat_name])
        keyboard.append([
            InlineKeyboardButton(
                f"📂 {cat_name} ({product_count} محصول)",
                callback_data=f"cat_{cat_name}"
            )
        ])

    keyboard.append([InlineKeyboardButton("🛍 سبد خرید", callback_data="cart")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

# ============ نمایش محصولات یک دسته ============
async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_name = query.data.replace("cat_", "")
    data = load_data()
    products = data.get("categories", {}).get(cat_name, {})

    text = f"📂 {cat_name}\n\n"
    keyboard = []

    for name, info in products.items():
        if info["available"]:
            text += f"▫️ {name} - {format_price(info['price'])}\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"🌶 {name}",
                    callback_data=f"product_{name}"
                )
            ])

    keyboard.append([InlineKeyboardButton("🛍 سبد خرید", callback_data="cart")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به دسته ها", callback_data="browse")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # چون متن ممکنه طولانی باشه
    if len(text) > 4000:
        text = text[:3900] + "\n...\n(محصولات زیاد است، از دکمه ها انتخاب کنید)"

    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

# ============ جزئیات محصول ============
async def view_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_name = query.data.replace("product_", "")
    data = load_data()
    product, cat_name = find_product(data, product_name)

    if not product:
        await query.edit_message_text("❌ محصول پیدا نشد!")
        return MAIN_MENU

    context.user_data["selected_product"] = product_name

    text = (
        f"🌿 {product_name}\n\n"
        f"📂 دسته: {cat_name}\n"
        f"💰 قیمت: {format_price(product['price'])}\n"
        f"📦 نوع بسته: {product['unit']}\n"
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
            InlineKeyboardButton("4️⃣", callback_data="qty_4"),
            InlineKeyboardButton("5️⃣", callback_data="qty_5"),
            InlineKeyboardButton("🔟", callback_data="qty_10"),
        ],
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"cat_{cat_name}")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

# ============ اضافه به سبد ============
async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    qty_str = query.data.replace("qty_", "")
    qty = int(qty_str)
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
    product, _ = find_product(data, product_name)
    item_total = int(product["price"] * qty)

    text = (
        f"✅ به سبد خرید اضافه شد!\n\n"
        f"🌶 {product_name}\n"
        f"📦 تعداد: {qty}\n"
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

# ============ سبد خرید ============
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
        product, _ = find_product(data, product_name)
        if product:
            price = product["price"]
            item_total = int(price * qty)
            total += item_total
            text += f"▫️ {product_name}\n   {qty} عدد × {format_price(price)} = {format_price(item_total)}\n\n"

    text += f"\n💰 جمع کل: {format_price(total)}"

    keyboard = [
        [InlineKeyboardButton("✅ تکمیل سفارش", callback_data="checkout")],
        [InlineKeyboardButton("🗑 خالی کردن سبد", callback_data="clear_cart")],
        [InlineKeyboardButton("🛒 ادامه خرید", callback_data="browse")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_main")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if len(text) > 4000:
        text = text[:3900] + "\n...(سبد بزرگ است)"

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
        product, _ = find_product(data, product_name)
        if product:
            price = product["price"]
            item_total = int(price * qty)
            products_total += item_total
            order_details += f"  ▫️ {product_name}: {qty} عدد = {format_price(item_total)}\n"

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

    if len(text) > 4000:
        text = text[:3900] + "\n...(خلاصه)"

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
        product, _ = find_product(data, product_name)
        if product:
            price = product["price"]
            order_text += f"  ▫️ {product_name}: {qty} عدد = {format_price(int(price * qty))}\n"

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
        # اگه متن طولانی باشه، تیکه تیکه بفرست
        if len(admin_text) > 4000:
            chunks = [admin_text[i:i+4000] for i in range(0, len(admin_text), 4000)]
            for chunk in chunks:
                await context.bot.send_message(chat_id=ADMIN_ID, text=chunk)
        else:
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
        "📱 تلفن: 09158483757\n"
        "🏪  آدرس: ایرانشهر بلوار شهید بهشتی\n"
        "⏰ ساعت کاری: 10 الی 14 و 15:30 الی 21 \n\n"
        "🌿 فروشگاه ادویه گهنیج"
    )

    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔍 نام محصول مورد نظر خود را تایپ کنید:\n(مثلاً: زردچوبه یا زعتر)")
    context.user_data["searching"] = True
    return MAIN_MENU

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("searching"):
        context.user_data["searching"] = False
        search_term = update.message.text.strip()
        data = load_data()
        
        all_products = get_all_products(data)
        results = {}
        for name, info in all_products.items():
            if search_term in name and info["available"]:
                results[name] = info

        if not results:
            text = f"❌ محصولی با نام «{search_term}» پیدا نشد."
            keyboard = [
                [InlineKeyboardButton("🛒 همه محصولات", callback_data="browse")],
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_main")],
            ]
        else:
            text = f"🔍 نتایج جستجو برای «{search_term}»:\n\n"
            keyboard = []
            count = 0
            for name, info in results.items():
                if count >= 30:  # حداکثر 30 نتیجه
                    text += f"\n(و {len(results) - 30} مورد دیگر...)"
                    break
                text += f"▫️ {name} - {format_price(info['price'])}\n"
                keyboard.append([
                    InlineKeyboardButton(f"🌶 {name}", callback_data=f"product_{name}")
                ])
                count += 1
            keyboard.append([InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_main")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if len(text) > 4000:
            text = text[:3900] + "\n...(نتایج زیاد است)"
            
        await update.message.reply_text(text, reply_markup=reply_markup)
        return MAIN_MENU

# ============ پنل مدیریت ============
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text("❌ شما دسترسی ندارید!")
        return MAIN_MENU

    text = "⚙️ پنل مدیریت فروشگاه گهنیج\n\nیکی از گزینه ها را انتخاب کنید:"

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
    text = "💰 ویرایش قیمت ها\n\nابتدا دسته را انتخاب کنید:"
    keyboard = []

    for cat_name in data.get("categories", {}).keys():
        keyboard.append([
            InlineKeyboardButton(
                f"📂 {cat_name}",
                callback_data=f"adminprice_cat_{cat_name}"
            )
        ])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def admin_price_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_name = query.data.replace("adminprice_cat_", "")
    data = load_data()
    products = data.get("categories", {}).get(cat_name, {})

    text = f"💰 ویرایش قیمت - {cat_name}\n\nمحصول را انتخاب کنید:\n\n"
    keyboard = []

    for name, info in products.items():
        text += f"▫️ {name}: {format_price(info['price'])}\n"
        keyboard.append([
            InlineKeyboardButton(
                f"✏️ {name}",
                callback_data=f"editprice_{name}"
            )
        ])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_prices")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if len(text) > 4000:
        text = text[:3900] + "\n...(از دکمه ها استفاده کنید)"

    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def admin_select_for_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_name = query.data.replace("editprice_", "")
    context.user_data["editing_product"] = product_name

    data = load_data()
    product, _ = find_product(data, product_name)

    if not product:
        await query.edit_message_text("❌ محصول پیدا نشد!")
        return MAIN_MENU

    await query.edit_message_text(
        f"✏️ ویرایش قیمت\n\n"
        f"🌶 {product_name}\n"
        f"💰 قیمت فعلی: {format_price(product['price'])}\n\n"
        f"لطفا قیمت جدید را به تومان وارد کنید:\n(فقط عدد، مثلا: 150000)"
    )
    return ADMIN_NEW_PRICE

async def save_new_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_price = int(update.message.text.replace(",", "").replace("،", "").strip())
    except ValueError:
        await update.message.reply_text("❌ لطفا فقط عدد وارد کنید!")
        return ADMIN_NEW_PRICE

    product_name = context.user_data.get("editing_product")
    data = load_data()
    
    # پیدا کردن و آپدیت
    updated = False
    for cat_name, products in data.get("categories", {}).items():
        if product_name in products:
            old_price = products[product_name]["price"]
            products[product_name]["price"] = new_price
            save_data(data)
            
            await update.message.reply_text(
                f"✅ قیمت با موفقیت تغییر کرد!\n\n"
                f"🌶 {product_name}\n"
                f"💰 قبلی: {format_price(old_price)}\n"
                f"💰 جدید: {format_price(new_price)}"
            )
            updated = True
            break
    
    if not updated:
        await update.message.reply_text("❌ محصول پیدا نشد!")

    keyboard = [
        [InlineKeyboardButton("💰 ویرایش قیمت دیگر", callback_data="admin_prices")],
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("چه کاری انجام بدم؟", reply_markup=reply_markup)
    return MAIN_MENU

# ============ افزودن محصول ============
async def admin_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    text = "➕ افزودن محصول جدید\n\nابتدا دسته را انتخاب کنید:"
    keyboard = []

    for cat_name in data.get("categories", {}).keys():
        keyboard.append([
            InlineKeyboardButton(f"📂 {cat_name}", callback_data=f"addcat_{cat_name}")
        ])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def admin_select_cat_for_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_name = query.data.replace("addcat_", "")
    context.user_data["adding_category"] = cat_name

    await query.edit_message_text(
        f"➕ افزودن محصول به دسته:\n📂 {cat_name}\n\n"
        f"نام محصول را وارد کنید:"
    )
    return ADMIN_ADD_PRODUCT_NAME

async def get_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_product_name"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ نام: {update.message.text}\n\nقیمت را به تومان وارد کنید:"
    )
    return ADMIN_ADD_PRODUCT_PRICE

async def get_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = int(update.message.text.replace(",", "").replace("،", "").strip())
        context.user_data["new_product_price"] = price
    except ValueError:
        await update.message.reply_text("❌ فقط عدد وارد کنید!")
        return ADMIN_ADD_PRODUCT_PRICE

    await update.message.reply_text(
        f"✅ قیمت: {format_price(price)}\n\n"
        f"نوع بسته را وارد کنید:\n(مثلا: نمکپاشی، نیم کیلویی، قوطی مربعی)"
    )
    return ADMIN_ADD_PRODUCT_UNIT

async def get_product_unit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    unit = update.message.text.strip()
    name = context.user_data["new_product_name"]
    price = context.user_data["new_product_price"]
    cat_name = context.user_data.get("adding_category")

    data = load_data()
    if cat_name not in data.get("categories", {}):
        data["categories"][cat_name] = {}
    
    data["categories"][cat_name][name] = {"price": price, "unit": unit, "available": True}
    save_data(data)

    await update.message.reply_text(
        f"✅ محصول اضافه شد!\n\n"
        f"📂 دسته: {cat_name}\n"
        f"🌶 نام: {name}\n"
        f"💰 قیمت: {format_price(price)}\n"
        f"📦 بسته: {unit}"
    )

    keyboard = [
        [InlineKeyboardButton("➕ افزودن دیگر", callback_data="admin_add")],
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("چه کاری انجام بدم؟", reply_markup=reply_markup)
    return MAIN_MENU

# ============ حذف محصول ============
async def admin_remove_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    text = "➖ حذف محصول\n\nابتدا دسته را انتخاب کنید:"
    keyboard = []

    for cat_name in data.get("categories", {}).keys():
        keyboard.append([
            InlineKeyboardButton(f"📂 {cat_name}", callback_data=f"rmcat_{cat_name}")
        ])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def admin_remove_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_name = query.data.replace("rmcat_", "")
    data = load_data()
    products = data.get("categories", {}).get(cat_name, {})

    text = f"➖ حذف از {cat_name}\n\nمحصول را انتخاب کنید:"
    keyboard = []

    for name in products:
        keyboard.append([InlineKeyboardButton(f"🗑 {name}", callback_data=f"remove_{name}")])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_remove")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def confirm_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_name = query.data.replace("remove_", "")
    data = load_data()
    
    removed = False
    for cat_name, products in data.get("categories", {}).items():
        if product_name in products:
            del data["categories"][cat_name][product_name]
            save_data(data)
            removed = True
            break

    if removed:
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
        text = "📋 آخرین سفارشات:\n\n"
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
                f"💵 {format_price(order['grand_total'])}\n\n"
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
    
    total_products = sum(len(prods) for prods in data.get("categories", {}).values())
    total_categories = len(data.get("categories", {}))

    text = (
        f"📊 آمار فروشگاه گهنیج:\n\n"
        f"📦 تعداد سفارشات: {len(orders)}\n"
        f"💰 مجموع فروش: {format_price(sum(o.get('grand_total', 0) for o in orders))}\n"
        f"📂 تعداد دسته ها: {total_categories}\n"
        f"🌶 تعداد کل محصولات: {total_products}"
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
                CallbackQueryHandler(show_category, pattern="^cat_"),
                CallbackQueryHandler(view_product, pattern="^product_"),
                CallbackQueryHandler(add_to_cart, pattern="^qty_"),
                CallbackQueryHandler(show_cart, pattern="^cart$"),
                CallbackQueryHandler(clear_cart, pattern="^clear_cart$"),
                CallbackQueryHandler(checkout_start, pattern="^checkout$"),
                CallbackQueryHandler(contact_us, pattern="^contact$"),
                CallbackQueryHandler(search_start, pattern="^search$"),
                CallbackQueryHandler(admin_panel, pattern="^admin$"),
                CallbackQueryHandler(admin_prices, pattern="^admin_prices$"),
                CallbackQueryHandler(admin_price_category, pattern="^adminprice_cat_"),
                CallbackQueryHandler(admin_select_for_price, pattern="^editprice_"),
                CallbackQueryHandler(admin_add_product, pattern="^admin_add$"),
                CallbackQueryHandler(admin_select_cat_for_add, pattern="^addcat_"),
                CallbackQueryHandler(admin_remove_product, pattern="^admin_remove$"),
                CallbackQueryHandler(admin_remove_cat, pattern="^rmcat_"),
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
