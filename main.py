import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from instaloader import Instaloader, Post
from io import BytesIO

# توکن ربات تلگرام (از @BotFather بگیر)
TOKEN = "8408562152:AAHyA8gzuG707N9EfifGe8LAbRtTuIAph1I"  # عوضش کن با توکن خودت

# کلید API رایگان Clipdrop (بهترین در جهان برای حذف متن - روزانه ۱۰۰ تا رایگان)
# برو https://clipdrop.co/apis ثبت‌نام کن، یه کلید رایگان بگیر و اینجا بذار
CLIPDROP_API_KEY = "2edfd7ff6795d44df2469531edf3ca51991ffee1100f228ac5638b5855ca29ce6ea7f5f426cd6ae5808c7398fa032a9b"  # عوض کن

L = Instaloader()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 لینک پست اینستاگرام رو بفرست (حتی کاروسل ۵۰ تایی)\n"
        "من همه عکس‌ها رو بدون هیچ متن، استیکر، لوگو و نوشته‌ای برات میفرستم ✅\n\n"
        "بهترین کیفیت ممکن - هوش مصنوعی واقعی"
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    status_msg = await update.message.reply_text("در حال پردازش... ⏳")

    try:
        shortcode = url.split("/p/")[1].split("/")[0] if "/p/" in url else url.split("reel/")[1].split("/")[0] if "reel/" in url else url.split("tv/")[1].split("/")[0]
        post = Post.from_shortcode(L.context, shortcode)

        slides = post.get_islides() if post.typename == "GraphImageCarousel" else [post]
        total = len(list(slides))

        await status_msg.edit_text(f"پست پیدا شد! {total} تا عکس داره، در حال حذف متن‌ها با هوش مصنوعی... 🎨")

        for index, slide in enumerate(slides if post.typename == "GraphImageCarousel" else [post], 1):
            img_url = slide.url

            # ارسال به Clipdrop Remove Text API
            r = requests.post('https://clipdrop-api.co/remove-text/v1',
                files = {'image_file': requests.get(img_url, stream=True).raw},
                data = {'image_url': img_url},
                headers = {'x-api-key': CLIPDROP_API_KEY}
            )

            if r.ok:
                cleaned_image = BytesIO(r.content)
                cleaned_image.name = "cleaned.jpg"

                await update.message.reply_photo(
                    photo=cleaned_image,
                    caption=f"عکس {index}/{total} - کاملاً تمیز شد 🔥"
                )
            else:
                # اگر API خطا داد، عکس خام رو بفرست
                await update.message.reply_photo(
                    photo=img_url,
                    caption=f"عکس {index}/{total} (خام - API موقتاً در دسترس نیست)"
                )

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text("لینک اشتباهه یا پست خصوصی/حذف شده 😔\nدوباره امتحان کن")

# راه‌اندازی ربات
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

print("ربات حرفه‌ای روشن شد! 🚀")
app.run_polling()
