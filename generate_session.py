import os
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

def main():
    # Load local .env if you have API_ID and API_HASH there
    load_dotenv()
    
    api_id = os.getenv('TELEGRAM_API_ID') or input("Enter your API_ID: ")
    api_hash = os.getenv('TELEGRAM_API_HASH') or input("Enter your API_HASH: ")

    print("\nStarting interactive login...")
    # Using StringSession() with nothing inside creates a new in-memory session
    with TelegramClient(StringSession(), int(api_id), api_hash) as client:
        session_string = client.session.save()
        print("\n" + "="*50)
        print("YOUR TELEGRAM_SESSION_STRING:")
        print("="*50)
        print(session_string)
        print("="*50)
        print("\nCopy the long string above and paste it into your Streamlit Cloud Secrets.")

if __name__ == "__main__":
    main()