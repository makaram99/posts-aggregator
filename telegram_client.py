import os
import asyncio
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')

def _ensure_event_loop():
    """Ensures that an asyncio event loop exists in the current thread."""
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

def _get_client():
    """Helper to initialize the TelegramClient with current environment variables."""
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    session_str = os.getenv('TELEGRAM_SESSION_STRING', '').strip()
    
    if not api_id or not api_hash:
        raise ValueError("TELEGRAM_API_ID or TELEGRAM_API_HASH is missing from environment/secrets.")

    # Use StringSession if string is provided, otherwise fallback to local file
    session = StringSession(session_str) if session_str else 'aggregator_session'
    return TelegramClient(session, int(api_id), api_hash)

def get_joined_channels():
    """Fetches a list of joined channels/megagroups."""
    _ensure_event_loop()
    client = _get_client()
    try:
        client.connect()
        if not client.is_user_authorized():
            # Return empty to avoid hanging on a login prompt in the console
            return []
        
        channels = []
        # Limit to 200 dialogs to prevent timeout/hang on accounts with many chats
        for dialog in client.get_dialogs(limit=200):
            if dialog.is_channel:
                channels.append({
                    "name": dialog.name,
                    "id": dialog.id,
                    "username": getattr(dialog.entity, 'username', None)
                })
        return channels
    finally:
        client.disconnect()

def fetch_recent_posts(channel_entity, limit=10, min_id=0):
    """Fetches messages newer than min_id from a specific channel."""
    _ensure_event_loop()
    client = _get_client()
    try:
        client.connect()
        if not client.is_user_authorized():
            return []
            
        posts = []
        # get_messages with min_id fetches posts newer than that ID
        messages = client.get_messages(channel_entity, limit=limit, min_id=min_id)
        for msg in messages:
            if msg.message:  # Only grab text-based posts
                # Determine status based on reactions
                status = "read" if msg.reactions else "unread"
                
                posts.append({
                    "id": msg.id,
                    "channel": str(channel_entity),
                    "original_text": msg.message,
                    "status": status
                })
        return posts
    finally:
        client.disconnect()