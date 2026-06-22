# database.py
import motor.motor_asyncio
import config

client = motor.motor_asyncio.AsyncIOMotorClient(config.MONGO_URL)
db = client[config.DB_NAME]

# Collections
child_bots_collection = db["child_bots"]
sessions_collection = db["user_sessions"]

async def add_child_bot(owner_id, bot_token):
    await child_bots_collection.update_one(
        {"owner_id": owner_id}, 
        {"$set": {"bot_token": bot_token}}, 
        upsert=True
    )

async def get_child_bot(owner_id):
    bot = await child_bots_collection.find_one({"owner_id": owner_id})
    return bot["bot_token"] if bot else None

async def update_session(user_id, **kwargs):
    await sessions_collection.update_one(
        {"user_id": user_id}, 
        {"$set": kwargs}, 
        upsert=True
    )

async def get_session(user_id):
    session = await sessions_collection.find_one({"user_id": user_id})
    if session:
        return (
            session.get("source_chat_id"),
            session.get("dest_chat_id"),
            session.get("first_link"),
            session.get("last_link"),
            session.get("caption_text"),
            session.get("topic_keyword")
        )
    return None

