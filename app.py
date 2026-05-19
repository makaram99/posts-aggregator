import streamlit as st
import os
import json

st.set_page_config(page_title="Telegram Aggregator", page_icon="📱", layout="wide")

# Read API secrets from Streamlit Cloud Secrets management FIRST
# This ensures environment variables are set before other modules are imported
# Map each secret individually to ensure they are available to the telegram_client module
for key in ["TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_SESSION_STRING"]:
    if key in st.secrets:
        os.environ[key] = str(st.secrets[key])

from telegram_client import fetch_recent_posts, get_joined_channels

# Global CSS to support Right-to-Left (RTL) for Arabic text and multi-lingual alignment
st.markdown("""
    <style>
    .stMarkdown, div[data-testid="stExpander"], p, span {
        unicode-bidi: plaintext;
        text-align: start;
    }
    </style>
""", unsafe_allow_html=True)

# Persistence Helpers
DATA_FILE = "posts_history.json"

def save_data():
    """Saves posts and last_ids to a local JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump({
            "posts": st.session_state.posts,
            "last_ids": st.session_state.last_ids
        }, f)

def load_data():
    """Loads posts and last_ids from the local JSON file."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return {"posts": [], "last_ids": {}}
    return {"posts": [], "last_ids": {}}

# Initialize Session State tracking
if "posts" not in st.session_state:
    saved_data = load_data()
    st.session_state.posts = saved_data.get("posts", [])
    st.session_state.last_ids = saved_data.get("last_ids", {})

def change_status(post_id, new_status):
    for post in st.session_state.posts:
        if post["id"] == post_id:
            post["status"] = new_status
            save_data()
            break

# Sidebar Configuration for Fetching Data
st.sidebar.title("Configuration")

if "available_channels" not in st.session_state:
    with st.spinner("Loading channels..."):
        try:
            st.session_state.available_channels = get_joined_channels()
        except Exception as e:
            st.sidebar.error(f"Connection Error: {str(e)}")
            st.session_state.available_channels = []

if not st.session_state.available_channels:
    if not os.environ.get("TELEGRAM_SESSION_STRING"):
        st.sidebar.error("❌ TELEGRAM_SESSION_STRING is missing in Secrets.")
    elif not os.environ.get("TELEGRAM_API_ID"):
        st.sidebar.error("❌ TELEGRAM_API_ID is missing in Secrets.")
    else:
        st.sidebar.warning("⚠️ Session found but not authorized. Your string might be expired or invalid.")

channel_options = {c['name']: c['username'] or c['id'] for c in st.session_state.available_channels}
selected_channel_name = st.sidebar.selectbox("Select Channel", options=list(channel_options.keys()))
fetch_limit = st.sidebar.slider("Max posts to fetch", min_value=1, max_value=100, value=20)

if st.sidebar.button("Fetch & Summarize Posts", type="primary"):
    if selected_channel_name:
        target_entity = channel_options[selected_channel_name]
        with st.spinner("Connecting to Telegram & running AI analysis..."):
            try:
                # Get the last ID we fetched for this specific channel
                last_id = st.session_state.last_ids.get(str(target_entity), 0)
                
                # Fetch posts newer than last_id
                raw_posts = fetch_recent_posts(target_entity, limit=fetch_limit, min_id=last_id)
                
                if raw_posts:
                    # Update last_id with the max ID from the new posts
                    st.session_state.last_ids[str(target_entity)] = max(p["id"] for p in raw_posts)

                processed_posts = []
                for p in raw_posts:
                    ai_title = " ".join(p["original_text"].split()[:10]) + "..." if len(p["original_text"].split()) > 10 else p["original_text"]
                    p["title"] = ai_title
                    # Add channel name for display
                    p["channel_display"] = selected_channel_name
                    processed_posts.append(p) # Keep newest at top (Telegram returns newest first)
                
                # Append to existing posts (keep old posts)
                st.session_state.posts = processed_posts + st.session_state.posts
                save_data()
                
                if not raw_posts:
                    st.sidebar.info("No new posts found.")
                else:
                    st.sidebar.success(f"Fetched {len(processed_posts)} new posts!")
            except Exception as e:
                st.sidebar.error(f"Error fetching data: {str(e)}")
    else:
        st.sidebar.warning("Please select a channel.")

# Main Application Frame Display
st.title("📱 Telegram Post Aggregator")
st.markdown("Filter, read, and manage your channel subscriptions efficiently.")
st.divider()

# UNREAD COLUMN
with st.expander("🔵 To Read", expanded=True):
    unread_posts = [p for p in st.session_state.posts if p["status"] == "unread"]
    if not unread_posts:
        st.info("No unread posts available.")
    else:
        # Display 3 posts per row
        num_columns = 3
        for i in range(0, len(unread_posts), num_columns):
            cols = st.columns(num_columns)
            for j, post in enumerate(unread_posts[i:i + num_columns]):
                with cols[j]:
                    with st.container(border=True):
                        st.markdown(f"**{post['title']}**")
                        st.caption(f"Source: {post.get('channel_display', post['channel'])}")
                        with st.expander("Read Full Post"):
                            st.write(post["original_text"])
                            st.divider()
                            c1, c2 = st.columns(2)
                            c1.button("Mark Read", key=f"read_{post['id']}", on_click=change_status, args=(post["id"], "read"), type="primary", use_container_width=True)
                            c2.button("Skip", key=f"skip_{post['id']}", on_click=change_status, args=(post["id"], "skipped"), use_container_width=True)

# READ COLUMN
with st.expander("🟢 Completed", expanded=False):
    read_posts = [p for p in st.session_state.posts if p["status"] == "read"]
    if not read_posts:
        st.info("No completed posts available.")
    else:
        num_columns = 3
        for i in range(0, len(read_posts), num_columns):
            cols = st.columns(num_columns)
            for j, post in enumerate(read_posts[i:i + num_columns]):
                with cols[j]:
                    with st.container(border=True):
                        st.markdown(f"**{post['title']}**")
                        st.caption(f"Source: {post.get('channel_display', post['channel'])}")
                        with st.expander("View Post"):
                            st.write(post["original_text"])
                            st.button("Move to Unread", key=f"unr_r_{post['id']}", on_click=change_status, args=(post["id"], "unread"), use_container_width=True)

# SKIPPED COLUMN
with st.expander("🔴 Skipped", expanded=False):
    skipped_posts = [p for p in st.session_state.posts if p["status"] == "skipped"]
    if not skipped_posts:
        st.info("No skipped posts available.")
    else:
        num_columns = 3
        for i in range(0, len(skipped_posts), num_columns):
            cols = st.columns(num_columns)
            for j, post in enumerate(skipped_posts[i:i + num_columns]):
                with cols[j]:
                    with st.container(border=True):
                        st.markdown(f"**{post['title']}**")
                        st.caption(f"Source: {post.get('channel_display', post['channel'])}")
                        with st.expander("View Post"):
                            st.write(post["original_text"])
                            st.button("Restore to Unread", key=f"unr_s_{post['id']}", on_click=change_status, args=(post["id"], "unread"), use_container_width=True)