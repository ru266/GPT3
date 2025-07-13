import os
import requests
import json
from user_agent import generate_user_agent as gg # لتوليد User-Agent ديناميكي
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler
from telegram.constants import ParseMode # لاستخدام Markdown/HTML في الرسائل

# --- إعدادات البوت ---
# قم بتغيير هذا بـ Bot Token الخاص بك من BotFather
# يفضل تحميله كمتغير بيئة (environment variable) لأمان أفضل
BOT_TOKEN = os.getenv("7332424799:AAGWLtN942LEWbxtlBnxF-fk4pQp2GVP-QM", "ضع_رمز_توكن_البوت_الخاص_بك_هنا")

# تعريف الحالات لمحادثة البوت
CHOOSING_ACTION, TYPING_PROMPT_AI1, TYPING_PROMPT_AI2, TYPING_PROMPT_IMAGE = range(4)

# --- دوال استدعاء APIs الذكاء الاصطناعي ---

async def call_ai_type1(user_message: str) -> str:
    """
    يتصل بـ API aicodegenerator.ifscswiftcodeapp.in لتوليد النصوص.
    ملاحظة: هذا الـ API يعتمد على كوكيز وهيدرات محددة وقد لا يكون مستقراً أو مصمماً للاستخدام العام.
    """
    cookies = {
        '_ga': 'GA1.1.677392249.1751447114',
        '_ga_D0G2X82ND0': 'GS2.1.s1751447113$o1$g1$t1751447119$j54$l0$h0',
        '_ga_3FXGGN6M9L': 'GS2.1.s1751447113$o1$g1$t1751447119$j54$l0$h0',
    }

    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,ar;q=0.8',
        'content-type': 'application/json',
        'origin': 'https://aicodegenerator.ifscswiftcodeapp.in',
        'priority': 'u=1, i',
        'referer': 'https://aicodegenerator.ifscswiftcodeapp.in/',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': gg(), # توليد User-Agent ديناميكي
    }

    json_data = {
        'message': [
            {'type': 'text', 'text': user_message},
        ],
        'chatId': '175144712783', # هذا الـ chatId ثابت، قد تحتاج إلى تغييره أو جعله ديناميكياً إذا كان الـ API يتطلب ذلك
        'generatorType': 'CodeGenerator', # حتى لو كان لـ "أي شيء" كما أشرت
    }

    try:
        response = requests.post(
            'https://aicodegenerator.ifscswiftcodeapp.in/api.php',
            cookies=cookies,
            headers=headers,
            json=json_data,
            timeout=15 # تحديد مهلة للطلب
        ).json()
        return response.get('response', 'فشل في الحصول على استجابة من API الأول.')
    except requests.exceptions.RequestException as e:
        return f"حدث خطأ في الاتصال بـ API الذكاء الاصناعي الأول: {e}"
    except json.JSONDecodeError:
        return "حدث خطأ في تحليل استجابة API الذكاء الاصناعي الأول."

async def call_ai_type2(user_message: str) -> str:
    """
    يتصل بـ API api4dev.ir/ai/ لتوليد النصوص.
    """
    try:
        # استخدام requests.utils.quote لترميز النص للاستخدام في URL
        return requests.get(
            f"http://api4dev.ir/ai/?text={requests.utils.quote(user_message)}",
            timeout=8
        ).text
    except requests.exceptions.RequestException as e:
        return f"❗عطل في الاتصال بـ API الذكاء الاصطناعي الثاني: {e}"

async def generate_image(prompt: str) -> str:
    """
    يتصل بـ API http://185.158.132.66:2010/api/tnt/tnt-black-image لتوليد الصور.
    """
    headers = {'Content-Type': 'application/json'} # تحديد أن نوع المحتوى هو JSON
    json_data = { "User-Prompt": prompt }

    try:
        response = requests.post(
            "http://185.158.132.66:2010/api/tnt/tnt-black-image",
            headers=headers,
            json=json_data,
            timeout=30 # مهلة أطول لتوليد الصور
        ).json()

        # *** هام جداً: ستحتاج لتعديل هذا الجزء بناءً على الاستجابة الفعلية لـ API الصور ***
        # افترض أن الـ API يرجع URL الصورة في مفتاح 'imageUrl' أو 'url' أو 'image'
        if 'imageUrl' in response:
            return response['imageUrl']
        elif 'url' in response:
            return response['url']
        elif 'image' in response:
            return response['image']
        else:
            # إذا لم يتم العثور على المفتاح المتوقع، اطبع الاستجابة الكاملة للمساعدة في التصحيح
            print(f"Image API response missing expected key: {json.dumps(response, indent=2)}")
            return "لم يتم العثور على رابط الصورة في الاستجابة. يرجى المحاولة مرة أخرى أو الإبلاغ عن المشكلة."

    except requests.exceptions.RequestException as e:
        return f"حدث خطأ في الاتصال بـ API توليد الصور: {e}"
    except json.JSONDecodeError:
        return "حدث خطأ في تحليل استجابة API توليد الصور."

# --- دوال معالجة أوامر البوت ---

async def start(update: Update, context) -> int:
    """
    يرسل رسالة البدء الجميلة مع الأزرار.
    """
    user = update.effective_user
    welcome_message = (
        f"🌟 *مرحباً بك يا {user.first_name}!* 🌟\n\n"
        "أنا بوت الذكاء الاصطناعي المتطور الخاص بك، جاهز للمساعدة في كل ما تحتاج!\n\n"
        "اختر أحد الخيارات أدناه لتبدأ:"
    )

    keyboard = [
        [
            InlineKeyboardButton("✨ ذكاء اصطناعي (النوع 1)", callback_data='ai_type1'),
            InlineKeyboardButton("🔮 ذكاء اصطناعي (النوع 2)", callback_data='ai_type2'),
        ],
        [
            InlineKeyboardButton("🖼️ توليد صورة", callback_data='generate_image'),
        ],
        [
            InlineKeyboardButton("❌ إلغاء", callback_data='cancel'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    return CHOOSING_ACTION # ينتقل إلى حالة اختيار الإجراء

async def button_callback(update: Update, context) -> int:
    """
    يتعامل مع ضغطات الأزرار المضمنة.
    """
    query = update.callback_query
    await query.answer() # يجب استدعاء query.answer() لإنهاء الاستعلام

    action = query.data

    if action == 'ai_type1':
        context.user_data['selected_ai_type'] = 'ai_type1'
        await query.edit_message_text(
            "👍 *أحسنت!* لقد اخترت الذكاء الاصطناعي من النوع 1.\n"
            "الآن، أرسل لي طلبك أو سؤالك الذي تريد أن أجيب عليه."
            "\n\nأو يمكنك استخدام /cancel للإلغاء."
            , parse_mode=ParseMode.MARKDOWN
        )
        return TYPING_PROMPT_AI1

    elif action == 'ai_type2':
        context.user_data['selected_ai_type'] = 'ai_type2'
        await query.edit_message_text(
            "👍 *ممتاز!* لقد اخترت الذكاء الاصطناعي من النوع 2.\n"
            "الآن، أرسل لي طلبك أو سؤالك الذي تريد أن أجيب عليه."
            "\n\nأو يمكنك استخدام /cancel للإلغاء."
            , parse_mode=ParseMode.MARKDOWN
        )
        return TYPING_PROMPT_AI2

    elif action == 'generate_image':
        context.user_data['selected_ai_type'] = 'image_gen'
        await query.edit_message_text(
            "🎨 *رائع!* يمكنك الآن أن تطلب مني توليد صورة.\n"
            "الرجاء وصف الصورة التي تريدها بالتفصيل (باللغة الإنجليزية يفضل).\n"
            "مثال: `A cat wearing a wizard hat, magical forest background, highly detailed.`"
            "\n\nأو يمكنك استخدام /cancel للإلغاء."
            , parse_mode=ParseMode.MARKDOWN
        )
        return TYPING_PROMPT_IMAGE

    elif action == 'cancel':
        await query.edit_message_text(
            "👋 تم الإلغاء. يمكنك البدء من جديد باستخدام أمر /start."
        )
        return ConversationHandler.END # ينهي المحادثة

async def handle_prompt_ai1(update: Update, context) -> int:
    """
    يعالج طلب المستخدم للذكاء الاصطناعي من النوع 1.
    """
    user_message = update.message.text
    await update.message.reply_text("⏳ جاري معالجة طلبك باستخدام الذكاء الاصطناعي الأول...")

    response_text = await call_ai_type1(user_message)
    await update.message.reply_text(
        f"🤖 *استجابة الذكاء الاصطناعي الأول:*\n\n{response_text}",
        parse_mode=ParseMode.MARKDOWN
    )
    # بعد الرد، أعد المستخدم إلى قائمة البدء أو أنهِ المحادثة
    await start(update, context) # عرض قائمة البدء مرة أخرى
    return CHOOSING_ACTION

async def handle_prompt_ai2(update: Update, context) -> int:
    """
    يعالج طلب المستخدم للذكاء الاصطناعي من النوع 2.
    """
    user_message = update.message.text
    await update.message.reply_text("⏳ جاري معالجة طلبك باستخدام الذكاء الاصطناعي الثاني...")

    response_text = await call_ai_type2(user_message)
    await update.message.reply_text(
        f"🔮 *استجابة الذكاء الاصطناعي الثاني:*\n\n{response_text}",
        parse_mode=ParseMode.MARKDOWN
    )
    await start(update, context)
    return CHOOSING_ACTION

async def handle_image_prompt(update: Update, context) -> int:
    """
    يعالج طلب المستخدم لتوليد صورة.
    """
    user_prompt = update.message.text
    await update.message.reply_text("⏳ جاري توليد صورتك... قد يستغرق هذا بعض الوقت.")

    image_url = await generate_image(user_prompt)

    if image_url.startswith('http'): # تحقق إذا كانت الاستجابة رابط URL
        await update.message.reply_photo(
            photo=image_url,
            caption="✨ هذه هي صورتك التي تم توليدها!"
        )
    else:
        await update.message.reply_text(
            f"❌ حدث خطأ أثناء توليد الصورة: {image_url}"
        )

    await start(update, context)
    return CHOOSING_ACTION

async def cancel(update: Update, context) -> int:
    """
    ينهي المحادثة.
    """
    await update.message.reply_text(
        "👋 تم الإلغاء. يمكنك البدء من جديد باستخدام أمر /start."
    )
    return ConversationHandler.END

# --- دالة Main لتشغيل البوت ---

def main() -> None:
    """يشغل البوت."""
    # بناء تطبيق البوت
    application = Application.builder().token(BOT_TOKEN).build()

    # تعريف ConversationHandler لإدارة تدفق المحادثة
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)], # نقطة الدخول: أمر /start

        states={
            CHOOSING_ACTION: [
                CallbackQueryHandler(button_callback, pattern='^(ai_type1|ai_type2|generate_image|cancel)$'),
            ],
            TYPING_PROMPT_AI1: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prompt_ai1)],
            TYPING_PROMPT_AI2: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prompt_ai2)],
            TYPING_PROMPT_IMAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_image_prompt)],
        },

        fallbacks=[CommandHandler("cancel", cancel)], # المعالج الاحتياطي: أمر /cancel
    )

    application.add_handler(conv_handler)

    # إضافة معالج لـ /start إذا تم استدعاؤه خارج المحادثة (للتشغيل الجديد)
    application.add_handler(CommandHandler("start", start)) 

    # تشغيل البوت
    print("Bot started...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
