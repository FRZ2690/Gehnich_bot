import logging
import json
import os
import hashlib
from collections import OrderedDict
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

ADMIN_ID_RAW = os.environ.get("ADMIN_ID", "0")
try:
    if "," in ADMIN_ID_RAW:
        DEFAULT_ADMIN_IDS = [int(x.strip()) for x in ADMIN_ID_RAW.split(",") if x.strip()]
    else:
        DEFAULT_ADMIN_IDS = [int(ADMIN_ID_RAW)]
except ValueError:
    DEFAULT_ADMIN_IDS = [0]

SUPER_ADMIN_ID = DEFAULT_ADMIN_IDS[0] if DEFAULT_ADMIN_IDS else 0

DATA_FILE = "data.json"
PORT = int(os.environ.get("PORT", 10000))

# استیکرهای پیشفرض دسته ها
DEFAULT_CAT_ICONS = {
    "ادویه جات ترکیبی گهنیج": "🔬",
    "چاشنی های گهنیج": "🧂",
    "ادویه جات اصلی": "🌿",
    "دانه ها و تخم ها": "🌰",
    "طعم دهنده ها": "🍋",
    "سبزی خشک و متفرقه": "🥬",
    "عرقیجات خالص": "🌸",
    "زردچوبه چارمنار": "💛",
}

# ترتیب پیشفرض دسته ها
DEFAULT_CAT_ORDER = [
    "ادویه جات ترکیبی گهنیج",
    "چاشنی های گهنیج",
    "ادویه جات اصلی",
    "دانه ها و تخم ها",
    "طعم دهنده ها",
    "سبزی خشک و متفرقه",
    "عرقیجات خالص",
    "زردچوبه چارمنار",
]

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
    ADMIN_ADD_PRODUCT_NAME, ADMIN_ADD_PRODUCT_PRICE, ADMIN_ADD_PRODUCT_UNIT,
    ADMIN_NEW_SHIPPING_PRICE, ADMIN_ADD_SHIPPING_NAME, ADMIN_ADD_SHIPPING_PRICE,
    ADMIN_NEW_CARD_NUMBER, ADMIN_NEW_CARD_HOLDER,
    ADMIN_NEW_PHONE, ADMIN_NEW_ADDRESS, ADMIN_NEW_HOURS,
    ADMIN_ADD_NEW_ADMIN_ID,
    ADMIN_ADD_CAT_NAME, ADMIN_ADD_CAT_ICON,
    ADMIN_EDIT_CAT_NAME, ADMIN_EDIT_CAT_ICON
) = range(23)

# ============ کش ============
_id_to_name_cache = {}
_name_to_id_cache = {}
_id_to_cat_cache = {}
_cat_to_id_cache = {}

def get_short_id(name, prefix=""):
    h = hashlib.md5((prefix + name).encode('utf-8')).hexdigest()[:10]
    return h

def build_cache():
    global _id_to_name_cache, _name_to_id_cache, _id_to_cat_cache, _cat_to_id_cache
    _id_to_name_cache = {}
    _name_to_id_cache = {}
    _id_to_cat_cache = {}
    _cat_to_id_cache = {}
    
    data = load_data_raw()
    for cat_name in data.get("categories", {}).keys():
        cat_id = get_short_id(cat_name, "cat_")
        _id_to_cat_cache[cat_id] = cat_name
        _cat_to_id_cache[cat_name] = cat_id
        
        for prod_name in data["categories"][cat_name].keys():
            prod_id = get_short_id(prod_name, "prod_")
            _id_to_name_cache[prod_id] = prod_name
            _name_to_id_cache[prod_name] = prod_id

def get_cat_id(cat_name):
    if cat_name not in _cat_to_id_cache:
        build_cache()
    return _cat_to_id_cache.get(cat_name, "")

def get_cat_name(cat_id):
    if cat_id not in _id_to_cat_cache:
        build_cache()
    return _id_to_cat_cache.get(cat_id, "")

def get_prod_id(prod_name):
    if prod_name not in _name_to_id_cache:
        build_cache()
    return _name_to_id_cache.get(prod_name, "")

def get_prod_name(prod_id):
    if prod_id not in _id_to_name_cache:
        build_cache()
    return _id_to_name_cache.get(prod_id, "")

def get_cat_icon(data, cat_name):
    icons = data.get("cat_icons", DEFAULT_CAT_ICONS)
    return icons.get(cat_name, "📂")

def get_ordered_categories(data):
    cat_order = data.get("cat_order", DEFAULT_CAT_ORDER)
    categories = data.get("categories", {})
    ordered = []
    for cat_name in cat_order:
        if cat_name in categories:
            ordered.append(cat_name)
    for cat_name in categories:
        if cat_name not in ordered:
            ordered.append(cat_name)
    return ordered

# ============ دیتابیس ============
def load_data_raw():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return get_default_data()

def get_default_data():
    return {
        "categories": {
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
            "پیک (ایرانشهر)": 120000
        },
        "card_number": "6037-XXXX-XXXX-XXXX",
        "card_holder": "نام صاحب فروشگاه",
        "contact_info": {
            "phone": "09158483757",
            "address": "ایرانشهر بلوار شهید بهشتی",
            "hours": "10-14 & 15:30-21"
        },
        "admins": list(DEFAULT_ADMIN_IDS),
        "cat_icons": dict(DEFAULT_CAT_ICONS),
        "cat_order": list(DEFAULT_CAT_ORDER)
    }
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "contact_info" not in data:
                data["contact_info"] = {
                    "phone": "09158483757",
                    "address": "ایرانشهر بلوار شهید بهشتی ",
                    "hours": "10-14 & 15:30-21"
                }
            if "admins" not in data:
                data["admins"] = list(DEFAULT_ADMIN_IDS)
            if SUPER_ADMIN_ID not in data["admins"]:
                data["admins"].append(SUPER_ADMIN_ID)
            if "cat_icons" not in data:
                data["cat_icons"] = dict(DEFAULT_CAT_ICONS)
            if "cat_order" not in data:
                data["cat_order"] = list(DEFAULT_CAT_ORDER)
            save_data(data)
            return data
    else:
        default_data = get_default_data()
        save_data(default_data)
        return default_data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    build_cache()

def format_price(price):
    return f"{price:,} تومان"

def get_all_products(data):
    all_products = {}
    for cat_name, products in data.get("categories", {}).items():
        for prod_name, prod_info in products.items():
            all_products[prod_name] = {**prod_info, "category": cat_name}
    return all_products

def find_product(data, product_name):
    for cat_name, products in data.get("categories", {}).items():
        if product_name in products:
            return products[product_name], cat_name
    return None, None

def is_admin(user_id):
    data = load_data()
    admins = data.get("admins", list(DEFAULT_ADMIN_IDS))
    return user_id in admins

def is_super_admin(user_id):
    return user_id == SUPER_ADMIN_ID

# ============ شروع ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if "cart" not in context.user_data:
        context.user_data["cart"] = {}

    welcome_text = (
        f"🌿 سلام {user.first_name} عزیز!\n\n"
        f"به فروشگاه ادویه جات گهنیج خوش آمدید 🌿\n\n"
        f"از منوی زیر انتخاب کنید:"
    )

    keyboard = [
        [InlineKeyboardButton("🛒 مشاهده محصولات", callback_data="browse")],
        [InlineKeyboardButton("🔍 جستجوی محصول", callback_data="search")],
        [InlineKeyboardButton("🛍 سبد خرید", callback_data="cart")],
        [InlineKeyboardButton("📞 تماس با ما", callback_data="contact")],
    ]

    if is_admin(user.id):
        keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    return MAIN_MENU

# ============ نمایش دسته بندی ها (دو ستونه با کادر سبز) ============
async def browse_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    build_cache()

    text = (
        "🌿 فروشگاه ادویه گهنیج\n\n"
        "📂 دسته بندی محصولات:\n\n"
        "لطفا یک دسته را انتخاب کنید:"
    )
    
    keyboard = []
    ordered_cats = get_ordered_categories(data)
    
    # دو ستونه
    row = []
    for i, cat_name in enumerate(ordered_cats):
        product_count = len(data["categories"][cat_name])
        cat_id = get_cat_id(cat_name)
        icon = get_cat_icon(data, cat_name)
        
        button_text = f"{icon} {cat_name}"
        row.append(InlineKeyboardButton(button_text, callback_data=f"cat_{cat_id}"))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)

    # سبد خرید در وسط و پایین
    keyboard.append([InlineKeyboardButton("       🛍 سبد خرید       ", callback_data="cart")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_id = query.data.replace("cat_", "")
    cat_name = get_cat_name(cat_id)
    
    if not cat_name:
        await query.edit_message_text("❌ دسته پیدا نشد!")
        return MAIN_MENU
    
    data = load_data()
    products = data.get("categories", {}).get(cat_name, {})
    icon = get_cat_icon(data, cat_name)

    text = f"{icon} {cat_name}\n\nلطفا محصول مورد نظر خود را انتخاب کنید:"
    keyboard = []

    for name, info in products.items():
        if info["available"]:
            prod_id = get_prod_id(name)
            keyboard.append([
                InlineKeyboardButton(
                    f"{icon} {name} - {format_price(info['price'])}",
                    callback_data=f"product_{prod_id}"
                )
            ])

    keyboard.append([InlineKeyboardButton("🛍 سبد خرید", callback_data="cart")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به دسته ها", callback_data="browse")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def view_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    prod_id = query.data.replace("product_", "")
    product_name = get_prod_name(prod_id)
    
    if not product_name:
        await query.edit_message_text("❌ محصول پیدا نشد!")
        return MAIN_MENU
    
    data = load_data()
    product, cat_name = find_product(data, product_name)

    if not product:
        await query.edit_message_text("❌ محصول پیدا نشد!")
        return MAIN_MENU

    context.user_data["selected_product"] = product_name

    text = (
        f"{icon} {product_name}\n\n"
        f"📂 دسته: {cat_name}\n"
        f"💰 قیمت: {format_price(product['price'])}\n"
        f"📦 نوع بسته: {product['unit']}\n"
        f"✅ موجود\n\n"
        f"تعداد مورد نظر را انتخاب کنید:"
    )

    cat_id = get_cat_id(cat_name)
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
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"cat_{cat_id}")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

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
        f"{icon} {product_name}\n"
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

    for idx, (method, cost) in enumerate(shipping.items()):
        text += f"▫️ {method}: {format_price(cost)}\n"
        keyboard.append([
            InlineKeyboardButton(
                f"🚚 {method} | {format_price(cost)}",
                callback_data=f"ship_{idx}"
            )
        ])
    
    context.user_data["shipping_list"] = list(shipping.keys())

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)
    return CHECKOUT_SHIPPING

async def select_shipping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("ship_", ""))
    shipping_list = context.user_data.get("shipping_list", [])
    
    if idx >= len(shipping_list):
        await query.edit_message_text("❌ روش ارسال معتبر نیست!")
        return MAIN_MENU
    
    shipping_method = shipping_list[idx]
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

    admins = data.get("admins", list(DEFAULT_ADMIN_IDS))
    photo = update.message.photo[-1]
    
    for admin_id in admins:
        try:
            if len(admin_text) > 4000:
                chunks = [admin_text[i:i+4000] for i in range(0, len(admin_text), 4000)]
                for chunk in chunks:
                    await context.bot.send_message(chat_id=admin_id, text=chunk)
            else:
                await context.bot.send_message(chat_id=admin_id, text=admin_text)
            
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=photo.file_id,
                caption=f"🧾 رسید پرداخت سفارش #{order['order_id']}"
            )
        except Exception as e:
            logger.error(f"Error sending to admin {admin_id}: {e}")

    context.user_data["cart"] = {}
    return ConversationHandler.END

async def contact_us(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    contact = data.get("contact_info", {})

    text = (
        "📞 تماس با ما:\n\n"
        f"📱 تلفن: {contact.get('phone', '09158483757')}\n"
        f"🏪 آدرس: {contact.get('address', 'ایرانشهر بلوار شهید بهشتی')}\n"
        f"⏰ ساعت کاری: {contact.get('hours', '10-14 & 15:30-21')}\n\n"
        "🌿 فروشگاه ادویه جات گهنیج"
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
        build_cache()
        
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
                if count >= 30:
                    text += f"\n(و {len(results) - 30} مورد دیگر...)"
                    break
                text += f"▫️ {name} - {format_price(info['price'])}\n"
                prod_id = get_prod_id(name)
                keyboard.append([
                    InlineKeyboardButton(f"🌿 {name}", callback_data=f"product_{prod_id}")
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

    if not is_admin(update.effective_user.id):
        await query.edit_message_text("❌ شما دسترسی ندارید!")
        return MAIN_MENU

    text = "⚙️ پنل مدیریت فروشگاه گهنیج\n\nیکی از گزینه ها را انتخاب کنید:"

    keyboard = [
        [InlineKeyboardButton("💰 ویرایش قیمت محصولات", callback_data="admin_prices")],
        [InlineKeyboardButton("➕ افزودن محصول", callback_data="admin_add")],
        [InlineKeyboardButton("➖ حذف محصول", callback_data="admin_remove")],
        [InlineKeyboardButton("📂 مدیریت دسته بندی ها", callback_data="admin_cats")],
        [InlineKeyboardButton("📦 مدیریت هزینه ارسال", callback_data="admin_shipping")],
        [InlineKeyboardButton("💳 مدیریت اطلاعات پرداخت", callback_data="admin_payment")],
        [InlineKeyboardButton("📞 مدیریت اطلاعات تماس", callback_data="admin_contact")],
        [InlineKeyboardButton("📋 لیست سفارشات", callback_data="admin_orders")],
        [InlineKeyboardButton("📊 آمار فروش", callback_data="admin_stats")],
    ]
    
    if is_super_admin(update.effective_user.id):
        keyboard.append([InlineKeyboardButton("👥 مدیریت مدیران", callback_data="admin_admins")])
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

# ============ مدیریت دسته بندی ها ============
async def admin_cats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    build_cache()
    ordered_cats = get_ordered_categories(data)

    text = "📂 مدیریت دسته بندی ها\n\nدسته های فعلی:\n\n"
    keyboard = []

    for i, cat_name in enumerate(ordered_cats):
        icon = get_cat_icon(data, cat_name)
        product_count = len(data["categories"][cat_name])
        text += f"{i+1}. {icon} {cat_name} ({product_count} محصول)\n"
        cat_id = get_cat_id(cat_name)
        
        # ردیف اول: نام دسته
        keyboard.append([
            InlineKeyboardButton(f"{icon} {cat_name}", callback_data=f"catmnu_{cat_id}")
        ])

    keyboard.append([InlineKeyboardButton("➕ افزودن دسته جدید", callback_data="addcat_new")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def admin_cat_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_id = query.data.replace("catmnu_", "")
    cat_name = get_cat_name(cat_id)
    
    if not cat_name:
        await query.edit_message_text("❌ دسته پیدا نشد!")
        return MAIN_MENU
    
    data = load_data()
    icon = get_cat_icon(data, cat_name)
    ordered_cats = get_ordered_categories(data)
    idx = ordered_cats.index(cat_name) if cat_name in ordered_cats else -1
    
    context.user_data["managing_cat"] = cat_name

    text = (
        f"📂 مدیریت دسته:\n\n"
        f"{icon} {cat_name}\n"
        f"موقعیت فعلی: {idx + 1} از {len(ordered_cats)}\n\n"
        f"چه کاری می خواهید انجام دهید؟"
    )
    
    keyboard = [
        [InlineKeyboardButton("✏️ ویرایش نام دسته", callback_data=f"ecn_{cat_id}")],
        [InlineKeyboardButton("🎨 ویرایش استیکر", callback_data=f"eci_{cat_id}")],
    ]
    
    # دکمه های جابجایی ترتیب
    move_row = []
    if idx > 0:
        move_row.append(InlineKeyboardButton("⬆️ بالا", callback_data=f"cmup_{cat_id}"))
    if idx < len(ordered_cats) - 1:
        move_row.append(InlineKeyboardButton("⬇️ پایین", callback_data=f"cmdn_{cat_id}"))
    if move_row:
        keyboard.append(move_row)
    
    keyboard.append([InlineKeyboardButton("🗑 حذف دسته", callback_data=f"dcat_{cat_id}")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_cats")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

# جابجایی به بالا
async def admin_cat_move_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_id = query.data.replace("cmup_", "")
    cat_name = get_cat_name(cat_id)
    
    if not cat_name:
        await query.edit_message_text("❌ دسته پیدا نشد!")
        return MAIN_MENU
    
    data = load_data()
    ordered_cats = get_ordered_categories(data)
    
    if cat_name in ordered_cats:
        idx = ordered_cats.index(cat_name)
        if idx > 0:
            ordered_cats[idx], ordered_cats[idx-1] = ordered_cats[idx-1], ordered_cats[idx]
            data["cat_order"] = ordered_cats
            save_data(data)
    
    # برگشت به منوی دسته
    return await admin_cat_menu(update, context)

# جابجایی به پایین
async def admin_cat_move_down(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_id = query.data.replace("cmdn_", "")
    cat_name = get_cat_name(cat_id)
    
    if not cat_name:
        await query.edit_message_text("❌ دسته پیدا نشد!")
        return MAIN_MENU
    
    data = load_data()
    ordered_cats = get_ordered_categories(data)
    
    if cat_name in ordered_cats:
        idx = ordered_cats.index(cat_name)
        if idx < len(ordered_cats) - 1:
            ordered_cats[idx], ordered_cats[idx+1] = ordered_cats[idx+1], ordered_cats[idx]
            data["cat_order"] = ordered_cats
            save_data(data)
    
    return await admin_cat_menu(update, context)

# ویرایش نام دسته
async def admin_edit_cat_name_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_id = query.data.replace("ecn_", "")
    cat_name = get_cat_name(cat_id)
    
    if not cat_name:
        await query.edit_message_text("❌ دسته پیدا نشد!")
        return MAIN_MENU
    
    context.user_data["editing_cat_name"] = cat_name
    
    await query.edit_message_text(
        f"✏️ ویرایش نام دسته\n\n"
        f"نام فعلی: {cat_name}\n\n"
        f"لطفا نام جدید دسته را وارد کنید:"
    )
    return ADMIN_EDIT_CAT_NAME

async def save_edited_cat_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_name = update.message.text.strip()
    old_name = context.user_data.get("editing_cat_name")
    
    if not old_name:
        await update.message.reply_text("❌ خطا!")
        return MAIN_MENU
    
    data = load_data()
    
    if new_name in data.get("categories", {}) and new_name != old_name:
        await update.message.reply_text(f"⚠️ دسته ای با نام «{new_name}» از قبل وجود دارد!")
        return MAIN_MENU
    
    if old_name in data.get("categories", {}):
        # جابجایی محصولات به نام جدید
        products = data["categories"][old_name]
        # حفظ ترتیب
        new_categories = OrderedDict()
        for k, v in data["categories"].items():
            if k == old_name:
                new_categories[new_name] = products
            else:
                new_categories[k] = v
        data["categories"] = dict(new_categories)
        
        # آپدیت آیکون
        if "cat_icons" in data and old_name in data["cat_icons"]:
            icon = data["cat_icons"][old_name]
            del data["cat_icons"][old_name]
            data["cat_icons"][new_name] = icon
        
        # آپدیت ترتیب
        if "cat_order" in data:
            data["cat_order"] = [new_name if x == old_name else x for x in data["cat_order"]]
        
        save_data(data)
        
        await update.message.reply_text(
            f"✅ نام دسته تغییر کرد!\n\n"
            f"از: {old_name}\n"
            f"به: {new_name}"
        )
    
    keyboard = [
        [InlineKeyboardButton("📂 مدیریت دسته ها", callback_data="admin_cats")],
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("چه کاری انجام بدم؟", reply_markup=reply_markup)
    return MAIN_MENU

# ویرایش استیکر دسته
async def admin_edit_cat_icon_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_id = query.data.replace("eci_", "")
    cat_name = get_cat_name(cat_id)
    
    if not cat_name:
        await query.edit_message_text("❌ دسته پیدا نشد!")
        return MAIN_MENU
    
    data = load_data()
    current_icon = get_cat_icon(data, cat_name)
    context.user_data["editing_cat_icon"] = cat_name
    
    await query.edit_message_text(
        f"🎨 ویرایش استیکر دسته\n\n"
        f"دسته: {cat_name}\n"
        f"استیکر فعلی: {current_icon}\n\n"
        f"لطفا استیکر (ایموجی) جدید را ارسال کنید:\n"
        f"مثال: 🧂 🔬 🌿 🌰 🍋 🥬 🌸 💛 🌶 🍃 🌱"
    )
    return ADMIN_EDIT_CAT_ICON

async def save_edited_cat_icon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_icon = update.message.text.strip()
    cat_name = context.user_data.get("editing_cat_icon")
    
    if not cat_name:
        await update.message.reply_text("❌ خطا!")
        return MAIN_MENU
    
    data = load_data()
    if "cat_icons" not in data:
        data["cat_icons"] = {}
    
    old_icon = data["cat_icons"].get(cat_name, "📂")
    data["cat_icons"][cat_name] = new_icon
    save_data(data)
    
    await update.message.reply_text(
        f"✅ استیکر تغییر کرد!\n\n"
        f"دسته: {cat_name}\n"
        f"از: {old_icon}\n"
        f"به: {new_icon}"
    )
    
    keyboard = [
        [InlineKeyboardButton("📂 مدیریت دسته ها", callback_data="admin_cats")],
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("چه کاری انجام بدم؟", reply_markup=reply_markup)
    return MAIN_MENU

# افزودن دسته جدید
async def admin_add_cat_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "➕ افزودن دسته جدید\n\n"
        "لطفا نام دسته جدید را وارد کنید:"
    )
    return ADMIN_ADD_CAT_NAME

async def get_new_cat_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cat_name = update.message.text.strip()
    data = load_data()
    
    if cat_name in data.get("categories", {}):
        await update.message.reply_text(f"⚠️ دسته «{cat_name}» از قبل وجود دارد!")
        return ADMIN_ADD_CAT_NAME
    
    context.user_data["new_cat_name"] = cat_name
    
    await update.message.reply_text(
        f"✅ نام: {cat_name}\n\n"
        f"لطفا یک استیکر (ایموجی) برای این دسته وارد کنید:\n"
        f"مثال: 🧂 🔬 🌿 🌰 🍋 🥬 🌸 💛"
    )
    return ADMIN_ADD_CAT_ICON

async def save_new_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    icon = update.message.text.strip()
    cat_name = context.user_data.get("new_cat_name")
    
    if not cat_name:
        await update.message.reply_text("❌ خطا!")
        return MAIN_MENU
    
    data = load_data()
    if "categories" not in data:
        data["categories"] = {}
    if "cat_icons" not in data:
        data["cat_icons"] = {}
    if "cat_order" not in data:
        data["cat_order"] = []
    
    data["categories"][cat_name] = {}
    data["cat_icons"][cat_name] = icon
    if cat_name not in data["cat_order"]:
        data["cat_order"].append(cat_name)
    
    save_data(data)
    
    await update.message.reply_text(
        f"✅ دسته جدید اضافه شد!\n\n"
        f"{icon} {cat_name}\n\n"
        f"حالا می توانید به این دسته محصول اضافه کنید."
    )
    
    keyboard = [
        [InlineKeyboardButton("📂 مدیریت دسته ها", callback_data="admin_cats")],
        [InlineKeyboardButton("➕ افزودن محصول به این دسته", callback_data="admin_add")],
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("چه کاری انجام بدم؟", reply_markup=reply_markup)
    return MAIN_MENU

# حذف دسته
async def admin_delete_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_id = query.data.replace("dcat_", "")
    cat_name = get_cat_name(cat_id)
    
    if not cat_name:
        await query.edit_message_text("❌ دسته پیدا نشد!")
        return MAIN_MENU
    
    data = load_data()
    product_count = len(data["categories"].get(cat_name, {}))
    
    if product_count > 0:
        text = (
            f"⚠️ هشدار!\n\n"
            f"دسته «{cat_name}» شامل {product_count} محصول است.\n"
            f"با حذف دسته، تمام محصولات هم حذف می شوند!\n\n"
            f"آیا مطمئن هستید؟"
        )
        keyboard = [
            [InlineKeyboardButton("✅ بله، حذف کن", callback_data=f"cdel_{cat_id}")],
            [InlineKeyboardButton("❌ خیر، انصراف", callback_data="admin_cats")],
        ]
    else:
        # اگر دسته خالی است، مستقیم حذف کن
        return await admin_confirm_delete_cat(update, context)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def admin_confirm_delete_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_id = query.data.replace("cdel_", "").replace("dcat_", "")
    cat_name = get_cat_name(cat_id)
    
    if not cat_name:
        await query.edit_message_text("❌ دسته پیدا نشد!")
        return MAIN_MENU
    
    data = load_data()
    
    if cat_name in data.get("categories", {}):
        del data["categories"][cat_name]
        if "cat_icons" in data and cat_name in data["cat_icons"]:
            del data["cat_icons"][cat_name]
        if "cat_order" in data and cat_name in data["cat_order"]:
            data["cat_order"].remove(cat_name)
        save_data(data)
        text = f"✅ دسته «{cat_name}» و تمام محصولاتش حذف شد!"
    else:
        text = "❌ دسته پیدا نشد!"
    
    keyboard = [
        [InlineKeyboardButton("📂 مدیریت دسته ها", callback_data="admin_cats")],
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

# ============ مدیریت مدیران ============
async def admin_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_super_admin(update.effective_user.id):
        await query.edit_message_text("❌ فقط مدیر ارشد دسترسی دارد!")
        return MAIN_MENU

    data = load_data()
    admins = data.get("admins", list(DEFAULT_ADMIN_IDS))

    text = "👥 مدیریت مدیران\n\nمدیران فعلی:\n\n"
    keyboard = []

    for admin_id in admins:
        if admin_id == SUPER_ADMIN_ID:
            text += f"👑 {admin_id} (مدیر ارشد)\n"
        else:
            text += f"👤 {admin_id}\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"🗑 حذف {admin_id}",
                    callback_data=f"rmadmin_{admin_id}"
                )
            ])

    keyboard.append([InlineKeyboardButton("➕ افزودن مدیر جدید", callback_data="addadmin_new")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def admin_add_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_super_admin(update.effective_user.id):
        await query.edit_message_text("❌ فقط مدیر ارشد دسترسی دارد!")
        return MAIN_MENU

    await query.edit_message_text(
        "➕ افزودن مدیر جدید\n\n"
        "لطفا آیدی عددی کاربر جدید را وارد کنید:\n\n"
        "💡 راهنما:\n"
        "کاربر باید به ربات @userinfobot در تلگرام رفته و /start بزند.\n"
        "عدد Id که نشان داده می شود را کپی کند و به شما بدهد.\n\n"
        "(مثلا: 123456789)"
    )
    return ADMIN_ADD_NEW_ADMIN_ID

async def save_new_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_admin_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ لطفا فقط عدد وارد کنید!")
        return ADMIN_ADD_NEW_ADMIN_ID

    data = load_data()
    admins = data.get("admins", list(DEFAULT_ADMIN_IDS))

    if new_admin_id in admins:
        await update.message.reply_text(f"⚠️ کاربر {new_admin_id} از قبل مدیر است!")
    else:
        admins.append(new_admin_id)
        data["admins"] = admins
        save_data(data)
        
        await update.message.reply_text(
            f"✅ مدیر جدید اضافه شد!\n\n"
            f"🆔 آیدی: {new_admin_id}\n\n"
            f"💡 حالا این کاربر می تواند به ربات پیام /start بدهد و دکمه ⚙️ پنل مدیریت را ببیند."
        )
        
        try:
            await context.bot.send_message(
                chat_id=new_admin_id,
                text=(
                    "🎉 تبریک! شما به عنوان مدیر فروشگاه ادویه جات گهنیج انتخاب شدید.\n\n"
                    "برای شروع، دستور /start را بزنید و دکمه ⚙️ پنل مدیریت را انتخاب کنید."
                )
            )
        except Exception as e:
            logger.warning(f"Could not notify new admin {new_admin_id}: {e}")

    keyboard = [
        [InlineKeyboardButton("👥 مدیریت مدیران", callback_data="admin_admins")],
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("چه کاری انجام بدم؟", reply_markup=reply_markup)
    return MAIN_MENU

async def admin_remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_super_admin(update.effective_user.id):
        await query.edit_message_text("❌ فقط مدیر ارشد دسترسی دارد!")
        return MAIN_MENU

    admin_id_to_remove = int(query.data.replace("rmadmin_", ""))
    
    if admin_id_to_remove == SUPER_ADMIN_ID:
        await query.edit_message_text("❌ نمی توانید مدیر ارشد را حذف کنید!")
        return MAIN_MENU

    data = load_data()
    admins = data.get("admins", list(DEFAULT_ADMIN_IDS))

    if admin_id_to_remove in admins:
        admins.remove(admin_id_to_remove)
        data["admins"] = admins
        save_data(data)
        text = f"✅ مدیر {admin_id_to_remove} حذف شد!"
        
        try:
            await context.bot.send_message(
                chat_id=admin_id_to_remove,
                text="ℹ️ دسترسی مدیریت شما در فروشگاه ادویه جات گهنیج لغو شد."
            )
        except Exception as e:
            logger.warning(f"Could not notify removed admin: {e}")
    else:
        text = "❌ مدیر پیدا نشد!"

    keyboard = [
        [InlineKeyboardButton("👥 مدیریت مدیران", callback_data="admin_admins")],
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

# ============ ویرایش قیمت محصولات ============
async def admin_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    build_cache()
    text = "💰 ویرایش قیمت ها\n\nابتدا دسته را انتخاب کنید:"
    keyboard = []

    for cat_name in get_ordered_categories(data):
        cat_id = get_cat_id(cat_name)
        icon = get_cat_icon(data, cat_name)
        keyboard.append([
            InlineKeyboardButton(
                f"{icon} {cat_name}",
                callback_data=f"apc_{cat_id}"
            )
        ])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def admin_price_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_id = query.data.replace("apc_", "")
    cat_name = get_cat_name(cat_id)
    
    if not cat_name:
        await query.edit_message_text("❌ دسته پیدا نشد!")
        return MAIN_MENU
    
    data = load_data()
    products = data.get("categories", {}).get(cat_name, {})

    text = f"💰 ویرایش قیمت - {cat_name}\n\nمحصول را انتخاب کنید:\n\n"
    keyboard = []

    for name, info in products.items():
        text += f"▫️ {name}: {format_price(info['price'])}\n"
        prod_id = get_prod_id(name)
        keyboard.append([
            InlineKeyboardButton(
                f"✏️ {name}",
                callback_data=f"ep_{prod_id}"
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

    prod_id = query.data.replace("ep_", "")
    product_name = get_prod_name(prod_id)
    
    if not product_name:
        await query.edit_message_text("❌ محصول پیدا نشد!")
        return MAIN_MENU
    
    context.user_data["editing_product"] = product_name

    data = load_data()
    product, _ = find_product(data, product_name)

    if not product:
        await query.edit_message_text("❌ محصول پیدا نشد!")
        return MAIN_MENU

    await query.edit_message_text(
        f"✏️ ویرایش قیمت\n\n"
        f"{icon} {product_name}\n"
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
    
    updated = False
    for cat_name, products in data.get("categories", {}).items():
        if product_name in products:
            old_price = products[product_name]["price"]
            products[product_name]["price"] = new_price
            save_data(data)
            
            await update.message.reply_text(
                f"✅ قیمت با موفقیت تغییر کرد!\n\n"
                f"{icon} {product_name}\n"
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
    build_cache()
    text = "➕ افزودن محصول جدید\n\nابتدا دسته را انتخاب کنید:"
    keyboard = []

    for cat_name in get_ordered_categories(data):
        cat_id = get_cat_id(cat_name)
        icon = get_cat_icon(data, cat_name)
        keyboard.append([
            InlineKeyboardButton(f"{icon} {cat_name}", callback_data=f"ac_{cat_id}")
        ])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def admin_select_cat_for_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_id = query.data.replace("ac_", "")
    cat_name = get_cat_name(cat_id)
    
    if not cat_name:
        await query.edit_message_text("❌ دسته پیدا نشد!")
        return MAIN_MENU
    
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
        f"🌿 نام: {name}\n"
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
    build_cache()
    text = "➖ حذف محصول\n\nابتدا دسته را انتخاب کنید:"
    keyboard = []

    for cat_name in get_ordered_categories(data):
        cat_id = get_cat_id(cat_name)
        icon = get_cat_icon(data, cat_name)
        keyboard.append([
            InlineKeyboardButton(f"{icon} {cat_name}", callback_data=f"rc_{cat_id}")
        ])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def admin_remove_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_id = query.data.replace("rc_", "")
    cat_name = get_cat_name(cat_id)
    
    if not cat_name:
        await query.edit_message_text("❌ دسته پیدا نشد!")
        return MAIN_MENU
    
    data = load_data()
    products = data.get("categories", {}).get(cat_name, {})

    text = f"➖ حذف از {cat_name}\n\nمحصول را انتخاب کنید:"
    keyboard = []

    for name in products:
        prod_id = get_prod_id(name)
        keyboard.append([InlineKeyboardButton(f"🗑 {name}", callback_data=f"rp_{prod_id}")])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_remove")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def confirm_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    prod_id = query.data.replace("rp_", "")
    product_name = get_prod_name(prod_id)
    
    if not product_name:
        await query.edit_message_text("❌ محصول پیدا نشد!")
        return MAIN_MENU
    
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

# ============ مدیریت هزینه ارسال ============
async def admin_shipping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    shipping = data.get("shipping_options", {})

    text = "📦 مدیریت هزینه ارسال\n\nروش های ارسال فعلی:\n\n"
    keyboard = []

    shipping_list = list(shipping.keys())
    context.user_data["admin_shipping_list"] = shipping_list

    for idx, method in enumerate(shipping_list):
        cost = shipping[method]
        text += f"▫️ {method}: {format_price(cost)}\n"
        keyboard.append([
            InlineKeyboardButton(
                f"✏️ ویرایش {method}",
                callback_data=f"es_{idx}"
            ),
            InlineKeyboardButton(
                f"🗑 حذف",
                callback_data=f"rs_{idx}"
            )
        ])

    keyboard.append([InlineKeyboardButton("➕ افزودن روش جدید", callback_data="as_new")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def admin_edit_shipping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("es_", ""))
    shipping_list = context.user_data.get("admin_shipping_list", [])
    
    if idx >= len(shipping_list):
        await query.edit_message_text("❌ روش پیدا نشد!")
        return MAIN_MENU
    
    method = shipping_list[idx]
    context.user_data["editing_shipping"] = method

    data = load_data()
    current_cost = data["shipping_options"].get(method, 0)

    await query.edit_message_text(
        f"✏️ ویرایش هزینه ارسال\n\n"
        f"🚚 روش: {method}\n"
        f"💰 هزینه فعلی: {format_price(current_cost)}\n\n"
        f"لطفا هزینه جدید را به تومان وارد کنید:\n(فقط عدد، مثلا: 50000)"
    )
    return ADMIN_NEW_SHIPPING_PRICE

async def save_shipping_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_price = int(update.message.text.replace(",", "").replace("،", "").strip())
    except ValueError:
        await update.message.reply_text("❌ لطفا فقط عدد وارد کنید!")
        return ADMIN_NEW_SHIPPING_PRICE

    method = context.user_data.get("editing_shipping")
    data = load_data()

    if method in data["shipping_options"]:
        old_price = data["shipping_options"][method]
        data["shipping_options"][method] = new_price
        save_data(data)

        await update.message.reply_text(
            f"✅ هزینه ارسال تغییر کرد!\n\n"
            f"🚚 روش: {method}\n"
            f"💰 قبلی: {format_price(old_price)}\n"
            f"💰 جدید: {format_price(new_price)}"
        )

    keyboard = [
        [InlineKeyboardButton("📦 مدیریت هزینه ارسال", callback_data="admin_shipping")],
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("چه کاری انجام بدم؟", reply_markup=reply_markup)
    return MAIN_MENU

async def admin_remove_shipping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("rs_", ""))
    shipping_list = context.user_data.get("admin_shipping_list", [])
    
    if idx >= len(shipping_list):
        await query.edit_message_text("❌ روش پیدا نشد!")
        return MAIN_MENU
    
    method = shipping_list[idx]
    data = load_data()

    if method in data["shipping_options"]:
        del data["shipping_options"][method]
        save_data(data)
        text = f"✅ روش ارسال «{method}» حذف شد!"
    else:
        text = "❌ روش ارسال پیدا نشد!"

    keyboard = [
        [InlineKeyboardButton("📦 مدیریت هزینه ارسال", callback_data="admin_shipping")],
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def admin_add_shipping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "➕ افزودن روش ارسال جدید\n\n"
        "نام روش ارسال را وارد کنید:\n(مثلا: باربری، پیک موتوری تهران)"
    )
    return ADMIN_ADD_SHIPPING_NAME

async def get_shipping_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_shipping_name"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ نام: {update.message.text}\n\n"
        f"هزینه ارسال را به تومان وارد کنید:\n(فقط عدد، مثلا: 55000)"
    )
    return ADMIN_ADD_SHIPPING_PRICE

async def get_shipping_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = int(update.message.text.replace(",", "").replace("،", "").strip())
    except ValueError:
        await update.message.reply_text("❌ فقط عدد وارد کنید!")
        return ADMIN_ADD_SHIPPING_PRICE

    name = context.user_data["new_shipping_name"]
    data = load_data()
    data["shipping_options"][name] = price
    save_data(data)

    await update.message.reply_text(
        f"✅ روش ارسال اضافه شد!\n\n"
        f"🚚 نام: {name}\n"
        f"💰 هزینه: {format_price(price)}"
    )

    keyboard = [
        [InlineKeyboardButton("📦 مدیریت هزینه ارسال", callback_data="admin_shipping")],
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("چه کاری انجام بدم؟", reply_markup=reply_markup)
    return MAIN_MENU

# ============ مدیریت اطلاعات پرداخت ============
async def admin_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()

    text = (
        f"💳 مدیریت اطلاعات پرداخت\n\n"
        f"📌 اطلاعات فعلی:\n\n"
        f"💳 شماره کارت: {data.get('card_number', 'تنظیم نشده')}\n"
        f"👤 به نام: {data.get('card_holder', 'تنظیم نشده')}\n\n"
        f"چه چیزی را ویرایش می کنید؟"
    )

    keyboard = [
        [InlineKeyboardButton("💳 ویرایش شماره کارت", callback_data="editcard_number")],
        [InlineKeyboardButton("👤 ویرایش نام صاحب کارت", callback_data="editcard_holder")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def admin_edit_card_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    await query.edit_message_text(
        f"💳 ویرایش شماره کارت\n\n"
        f"شماره کارت فعلی:\n{data.get('card_number', 'تنظیم نشده')}\n\n"
        f"لطفا شماره کارت جدید را وارد کنید:"
    )
    return ADMIN_NEW_CARD_NUMBER

async def save_card_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_card = update.message.text.strip()
    data = load_data()
    data["card_number"] = new_card
    save_data(data)

    await update.message.reply_text(f"✅ شماره کارت تغییر کرد!\n\n💳 جدید: {new_card}")

    keyboard = [
        [InlineKeyboardButton("💳 مدیریت پرداخت", callback_data="admin_payment")],
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("چه کاری انجام بدم؟", reply_markup=reply_markup)
    return MAIN_MENU

async def admin_edit_card_holder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    await query.edit_message_text(
        f"👤 ویرایش نام صاحب کارت\n\n"
        f"نام فعلی: {data.get('card_holder', 'تنظیم نشده')}\n\n"
        f"لطفا نام جدید صاحب کارت را وارد کنید:"
    )
    return ADMIN_NEW_CARD_HOLDER

async def save_card_holder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_holder = update.message.text.strip()
    data = load_data()
    data["card_holder"] = new_holder
    save_data(data)

    await update.message.reply_text(f"✅ نام صاحب کارت تغییر کرد!\n\n👤 جدید: {new_holder}")

    keyboard = [
        [InlineKeyboardButton("💳 مدیریت پرداخت", callback_data="admin_payment")],
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("چه کاری انجام بدم؟", reply_markup=reply_markup)
    return MAIN_MENU

# ============ مدیریت اطلاعات تماس ============
async def admin_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    contact = data.get("contact_info", {})

    text = (
        f"📞 مدیریت اطلاعات تماس\n\n"
        f"📌 اطلاعات فعلی:\n\n"
        f"📱 تلفن: {contact.get('phone', 'تنظیم نشده')}\n"
        f"🏪 آدرس: {contact.get('address', 'تنظیم نشده')}\n"
        f"⏰ ساعت کاری: {contact.get('hours', 'تنظیم نشده')}\n\n"
        f"چه چیزی را ویرایش می کنید؟"
    )

    keyboard = [
        [InlineKeyboardButton("📱 ویرایش شماره تلفن", callback_data="editcontact_phone")],
        [InlineKeyboardButton("🏪 ویرایش آدرس", callback_data="editcontact_address")],
        [InlineKeyboardButton("⏰ ویرایش ساعت کاری", callback_data="editcontact_hours")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return MAIN_MENU

async def admin_edit_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    contact = data.get("contact_info", {})
    await query.edit_message_text(
        f"📱 ویرایش شماره تلفن\n\n"
        f"شماره فعلی: {contact.get('phone', 'تنظیم نشده')}\n\n"
        f"لطفا شماره تلفن جدید را وارد کنید:"
    )
    return ADMIN_NEW_PHONE

async def save_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_phone = update.message.text.strip()
    data = load_data()
    if "contact_info" not in data:
        data["contact_info"] = {}
    data["contact_info"]["phone"] = new_phone
    save_data(data)

    await update.message.reply_text(f"✅ شماره تلفن تغییر کرد!\n\n📱 جدید: {new_phone}")

    keyboard = [
        [InlineKeyboardButton("📞 مدیریت تماس", callback_data="admin_contact")],
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("چه کاری انجام بدم؟", reply_markup=reply_markup)
    return MAIN_MENU

async def admin_edit_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    contact = data.get("contact_info", {})
    await query.edit_message_text(
        f"🏪 ویرایش آدرس فروشگاه\n\n"
        f"آدرس فعلی: {contact.get('address', 'تنظیم نشده')}\n\n"
        f"لطفا آدرس جدید را وارد کنید:"
    )
    return ADMIN_NEW_ADDRESS

async def save_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_address = update.message.text.strip()
    data = load_data()
    if "contact_info" not in data:
        data["contact_info"] = {}
    data["contact_info"]["address"] = new_address
    save_data(data)

    await update.message.reply_text(f"✅ آدرس تغییر کرد!\n\n🏪 جدید: {new_address}")

    keyboard = [
        [InlineKeyboardButton("📞 مدیریت تماس", callback_data="admin_contact")],
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("چه کاری انجام بدم؟", reply_markup=reply_markup)
    return MAIN_MENU

async def admin_edit_hours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    contact = data.get("contact_info", {})
    await query.edit_message_text(
        f"⏰ ویرایش ساعت کاری\n\n"
        f"ساعت فعلی: {contact.get('hours', 'تنظیم نشده')}\n\n"
        f"لطفا ساعت کاری جدید را وارد کنید:"
    )
    return ADMIN_NEW_HOURS

async def save_hours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_hours = update.message.text.strip()
    data = load_data()
    if "contact_info" not in data:
        data["contact_info"] = {}
    data["contact_info"]["hours"] = new_hours
    save_data(data)

    await update.message.reply_text(f"✅ ساعت کاری تغییر کرد!\n\n⏰ جدید: {new_hours}")

    keyboard = [
        [InlineKeyboardButton("📞 مدیریت تماس", callback_data="admin_contact")],
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("چه کاری انجام بدم؟", reply_markup=reply_markup)
    return MAIN_MENU

# ============ لیست سفارشات و آمار ============
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
    admins = data.get("admins", list(DEFAULT_ADMIN_IDS))
    
    total_products = sum(len(prods) for prods in data.get("categories", {}).values())
    total_categories = len(data.get("categories", {}))

    text = (
        f"📊 آمار فروشگاه گهنیج:\n\n"
        f"📦 تعداد سفارشات: {len(orders)}\n"
        f"💰 مجموع فروش: {format_price(sum(o.get('grand_total', 0) for o in orders))}\n"
        f"📂 تعداد دسته ها: {total_categories}\n"
        f"🌿 تعداد کل محصولات: {total_products}\n"
        f"🚚 تعداد روش های ارسال: {len(data.get('shipping_options', {}))}\n"
        f"👥 تعداد مدیران: {len(admins)}"
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
    logger.info(f"Super Admin ID: {SUPER_ADMIN_ID}")
    
    load_data()
    build_cache()

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
                CallbackQueryHandler(admin_price_category, pattern="^apc_"),
                CallbackQueryHandler(admin_select_for_price, pattern="^ep_"),
                CallbackQueryHandler(admin_add_product, pattern="^admin_add$"),
                CallbackQueryHandler(admin_select_cat_for_add, pattern="^ac_"),
                CallbackQueryHandler(admin_remove_product, pattern="^admin_remove$"),
                CallbackQueryHandler(admin_remove_cat, pattern="^rc_"),
                CallbackQueryHandler(confirm_remove, pattern="^rp_"),
                CallbackQueryHandler(admin_cats, pattern="^admin_cats$"),
                CallbackQueryHandler(admin_cat_menu, pattern="^catmnu_"),
                CallbackQueryHandler(admin_cat_move_up, pattern="^cmup_"),
                CallbackQueryHandler(admin_cat_move_down, pattern="^cmdn_"),
                CallbackQueryHandler(admin_edit_cat_name_start, pattern="^ecn_"),
                CallbackQueryHandler(admin_edit_cat_icon_start, pattern="^eci_"),
                CallbackQueryHandler(admin_add_cat_start, pattern="^addcat_new$"),
                CallbackQueryHandler(admin_delete_cat, pattern="^dcat_"),
                CallbackQueryHandler(admin_confirm_delete_cat, pattern="^cdel_"),
                CallbackQueryHandler(admin_shipping, pattern="^admin_shipping$"),
                CallbackQueryHandler(admin_edit_shipping, pattern="^es_"),
                CallbackQueryHandler(admin_remove_shipping, pattern="^rs_"),
                CallbackQueryHandler(admin_add_shipping, pattern="^as_new$"),
                CallbackQueryHandler(admin_payment, pattern="^admin_payment$"),
                CallbackQueryHandler(admin_edit_card_number, pattern="^editcard_number$"),
                CallbackQueryHandler(admin_edit_card_holder, pattern="^editcard_holder$"),
                CallbackQueryHandler(admin_contact, pattern="^admin_contact$"),
                CallbackQueryHandler(admin_edit_phone, pattern="^editcontact_phone$"),
                CallbackQueryHandler(admin_edit_address, pattern="^editcontact_address$"),
                CallbackQueryHandler(admin_edit_hours, pattern="^editcontact_hours$"),
                CallbackQueryHandler(admin_orders, pattern="^admin_orders$"),
                CallbackQueryHandler(admin_stats, pattern="^admin_stats$"),
                CallbackQueryHandler(admin_admins, pattern="^admin_admins$"),
                CallbackQueryHandler(admin_add_admin_start, pattern="^addadmin_new$"),
                CallbackQueryHandler(admin_remove_admin, pattern="^rmadmin_"),
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
            ADMIN_NEW_SHIPPING_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_shipping_price)],
            ADMIN_ADD_SHIPPING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_shipping_name)],
            ADMIN_ADD_SHIPPING_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_shipping_price)],
            ADMIN_NEW_CARD_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_card_number)],
            ADMIN_NEW_CARD_HOLDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_card_holder)],
            ADMIN_NEW_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_phone)],
            ADMIN_NEW_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_address)],
            ADMIN_NEW_HOURS: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_hours)],
            ADMIN_ADD_NEW_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_admin)],
            ADMIN_ADD_CAT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_new_cat_name)],
            ADMIN_ADD_CAT_ICON: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_cat)],
            ADMIN_EDIT_CAT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_edited_cat_name)],
            ADMIN_EDIT_CAT_ICON: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_edited_cat_icon)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    logger.info("Bot started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
