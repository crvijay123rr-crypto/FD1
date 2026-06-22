# bot.py
import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
import config
import database

# Bot Initialize
app = Client(
    "Interactive_Forward_Bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.MASTER_BOT_TOKEN
)

user_steps = {}

@app.on_message(filters.command("start") & filters.private)
def start(client, message):
    user_id = message.from_user.id
    user_steps[user_id] = {"step": "idle"}
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Bot", callback_data="add_bot")],
        [InlineKeyboardButton("🔗 Set Channel Links", callback_data="set_channels")],
        [InlineKeyboardButton("📝 Set Custom Caption", callback_data="set_caption")],
        [InlineKeyboardButton("🏷️ Define Topic Keyword", callback_data="set_topic")],
        [InlineKeyboardButton("🚀 Forward All (Start)", callback_data="forward_all")]
    ])
    
    welcome = (
        f"<b>Hey {message.from_user.first_name}! 👋</b>\n\n"
        "Premium Forwarder Control Panel (MongoDB Active).\n"
        "<i>Apne buttons ke throw steps follow karein:</i>"
    )
    message.reply_text(welcome, reply_markup=keyboard, parse_mode="html")

@app.on_callback_query()
def callback_handler(client, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data
    
    if data == "add_bot":
        user_steps[user_id] = {"step": "waiting_bot_token"}
        query.message.reply_text("🤖 Kripya apne bot ka token bhejein:")
        query.answer()
        
    elif data == "set_channels":
        user_steps[user_id] = {"step": "waiting_channels"}
        query.message.reply_text("🔗 Source aur Destination Channel ID space dekar bhejein:\n<i>Ex: -100123456789 -100987654321</i>", parse_mode="html")
        query.answer()
        
    elif data == "set_caption":
        user_steps[user_id] = {"step": "waiting_caption"}
        query.message.reply_text("📝 Naya caption text bhejein jo forwarded files mein add hoga:")
        query.answer()

    elif data == "set_topic":
        user_steps[user_id] = {"step": "waiting_topic"}
        query.message.reply_text("🏷️ Wo word/keyword likhein jiske aage ka naam Topic Summary banega:", parse_mode="html")
        query.answer()

    elif data == "forward_all":
        query.answer()
        asyncio.create_task(process_forwarding(client, query.message, user_id))

@app.on_message(filters.text & filters.private & ~filters.command("start"))
async def text_input_handler(client, message):
    user_id = message.from_user.id
    text = message.text
    
    if user_id not in user_steps or user_steps[user_id]["step"] == "idle":
        await message.reply_text("❌ Invalid action. /start dabakar menu open karein.")
        return
        
    current_step = user_steps[user_id]["step"]
    
    if current_step == "waiting_bot_token":
        await database.add_child_bot(user_id, text)
        await message.reply_text("✅ Child Bot Token successfully saved to MongoDB!")
        user_steps[user_id]["step"] = "idle"
        
    elif current_step == "waiting_channels":
        try:
            source, dest = text.split()
            await database.update_session(user_id, source_chat_id=source, dest_chat_id=dest)
            user_steps[user_id]["step"] = "waiting_first_link"
            await message.reply_text(f"✅ Channels Saved!\nSource: <code>{source}</code> | Dest: <code>{dest}</code>\n\n🔗 Ab is process ke liye <b>First Link/Message ID</b> bhejein:", parse_mode="html")
        except Exception:
            await message.reply_text("⚠️ Galat format. Donu IDs space dekar likhein, jaise: `-100123 -100456`")
            
    elif current_step == "waiting_first_link":
        await database.update_session(user_id, first_link=text)
        user_steps[user_id]["step"] = "waiting_last_link"
        await message.reply_text("🔗 First Link save ho gayi! Ab **Last Link / Last Message ID** bhejein:")

    elif current_step == "waiting_last_link":
        await database.update_session(user_id, last_link=text)
        user_steps[user_id]["step"] = "idle"
        await message.reply_text("🎉 Last Link bhi save ho gayi! Main menu me jakar 'Forward All' par click karein.")

    elif current_step == "waiting_caption":
        await database.update_session(user_id, caption_text=text)
        await message.reply_text("✅ Premium Caption update ho gaya!")
        user_steps[user_id]["step"] = "idle"

    elif current_step == "waiting_topic":
        await database.update_session(user_id, topic_keyword=text)
        await message.reply_text(f"✅ Topic Keyword set to: <code>{text}</code>.", parse_mode="html")
        user_steps[user_id]["step"] = "idle"

async def process_forwarding(client, message, user_id):
    session = await database.get_session(user_id)
    if not session:
        await message.reply_text("❌ Pehle apne channels aur links setup karein!")
        return
        
    source_chat, dest_chat, first_link, last_link, caption, topic_keyword = session
    
    if not source_chat or not dest_chat:
        await message.reply_text("❌ Channel IDs missing hain. Setup complete karein.")
        return

    status_msg = await message.reply_text("🔄 Forwarding process shuru ho raha hai... Kripya intezaar karein.")
    
    try:
        start_id = int(first_link.split("/")[-1]) if "/" in first_link else int(first_link)
        end_id = int(last_link.split("/")[-1]) if "/" in last_link else int(last_link)
    except:
        await message.reply_text("❌ First ya Last link format theek nahi hai, sirf numbers ya message link dalein.")
        return

    msg_count = 0
    topics_found = []

    for msg_id in range(start_id, end_id + 1):
        try:
            msg = await client.get_messages(int(source_chat), msg_id)
            if msg:
                new_msg = await msg.copy(chat_id=int(dest_chat))
                msg_count += 1
                
                if msg.caption and topic_keyword in msg.caption:
                    extracted_topic = msg.caption.split(topic_keyword)[1].strip().split("\n")[0]
                    if extracted_topic not in topics_found:
                        topics_found.append(extracted_topic)
                        
                await asyncio.sleep(0.5)
        except Exception as e:
            pass 

    if msg_count > 0:
        summary_links = ""
        inline_btns = []
        
        for topic in topics_found:
            summary_links += f"\n🔗 <a href='https://t.me/{dest_chat}/{msg_count}'>#{topic}</a>"
            inline_btns.append([InlineKeyboardButton(f"📁 {topic}", url=f"https://t.me/{dest_chat}/{msg_count}")])

        final_summary_text = (
            f"✨ <b>All Files Forwarded Successfully!</b>\n\n"
            f"📂 <b>Topic Summary:</b>\n{summary_links}"
        )
        
        await client.send_message(
            chat_id=int(dest_chat),
            text=final_summary_text,
            parse_mode="html",
            reply_markup=InlineKeyboardMarkup(inline_btns)
        )

    await status_msg.edit_text(f"🎉 **Done!** {msg_count} items successfully forward ho chuke hain.")

print("🤖 Premium Interactive Bot with MongoDB is Live...")
app.run()

