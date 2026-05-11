import os
import datetime
import streamlit as st
import services.llm_service as llm_service
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(page_title="Trackify AI", page_icon="⏱️", layout="wide")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! I'm Trackify AI. Ask me anything about your team's time logs, projects, or productivity.", "time": datetime.datetime.now().strftime("%H:%M")}
    ]

# Premium Light Theme CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global resets */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        background-color: #F7F8FA !important;
        color: #1A1A1A;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E5E7EB;
        width: 220px !important;
    }
    
    .sidebar-logo {
        padding: 24px 20px;
        font-size: 20px;
        font-weight: 700;
        color: #0075FF;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .sidebar-item {
        padding: 12px 20px;
        margin: 4px 12px;
        border-radius: 8px;
        color: #404040;
        font-weight: 500;
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 12px;
        transition: all 0.2s;
        cursor: pointer;
    }
    
    .sidebar-item:hover {
        background-color: #F3F4F6;
    }
    
    .sidebar-item.active {
        background-color: #E8F0FF;
        color: #0075FF;
    }

    /* Top Header Bar */
    .header-bar {
        position: fixed;
        top: 0;
        left: 220px;
        right: 0;
        height: 64px;
        background-color: #FFFFFF;
        border-bottom: 1px solid #E5E7EB;
        display: flex;
        align-items: center;
        padding: 0 40px;
        z-index: 99;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    .header-title {
        font-weight: 700;
        font-size: 18px;
        color: #1A1A1A;
    }
    
    .header-subtitle {
        font-size: 12px;
        color: #6B7280;
        margin-left: 12px;
        margin-top: 2px;
    }

    /* Chat Area */
    .chat-wrapper {
        max-width: 780px;
        margin: 80px auto 120px auto;
        padding: 0 20px;
    }

    /* Avatars */
    .avatar {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 10px;
        font-weight: 700;
        flex-shrink: 0;
    }
    .avatar-ai { background-color: #E8F0FF; color: #0075FF; }
    .avatar-user { background-color: #F3F4F6; color: #6B7280; }

    /* Message Bubbles */
    .message-row {
        display: flex;
        gap: 16px;
        margin-bottom: 24px;
        width: 100%;
    }
    .message-row.user { flex-direction: row-reverse; }

    .bubble {
        padding: 12px 16px;
        border-radius: 12px;
        font-size: 15px;
        line-height: 1.6;
        max-width: 85%;
        position: relative;
    }
    
    .bubble-bot {
        background-color: #FFFFFF;
        color: #1A1A1A;
        border: 1px solid #E5E7EB;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02), 0 1px 3px rgba(0,0,0,0.08);
        border-top-left-radius: 2px;
    }
    
    .bubble-user {
        background-color: #0075FF;
        color: #FFFFFF;
        border-top-right-radius: 2px;
    }

    .timestamp {
        font-size: 11px;
        color: #9CA3AF;
        margin-top: 6px;
    }
    .message-row.user .timestamp { text-align: right; }

    /* Suggestion Chips */
    .chip-container {
        display: flex;
        gap: 8px;
        margin-top: 16px;
        flex-wrap: wrap;
    }
    
    .chip {
        padding: 8px 16px;
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 20px;
        font-size: 13px;
        color: #4B5563;
        cursor: pointer;
        transition: all 0.2s;
    }
    .chip:hover {
        border-color: #0075FF;
        color: #0075FF;
        background-color: #F0F7FF;
    }

    /* Pinned Input Bar */
    .input-container {
        position: fixed;
        bottom: 0;
        left: 220px;
        right: 0;
        background-color: #F7F8FA;
        padding: 20px 40px 32px 40px;
        z-index: 100;
    }
    
    .input-box {
        max-width: 780px;
        margin: 0 auto;
        position: relative;
    }

    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stHeader"] {background: rgba(0,0,0,0);}
    
    /* Center columns correctly */
    [data-testid="stVerticalBlock"] {
        gap: 0 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("""
        <div class="sidebar-logo">
            <span style="background:#0075FF; color:white; padding:4px 8px; border-radius:6px; font-size:16px;">T</span>
            Trackify AI
        </div>
        <div class="sidebar-item active">📊 Dashboard</div>
        <div class="sidebar-item">📑 Reports</div>
        <div class="sidebar-item">📂 Projects</div>
        <div class="sidebar-item">👥 Team</div>
    """, unsafe_allow_html=True)

# Top Header
st.markdown("""
    <div class="header-bar">
        <div class="header-title">Chat Assistant</div>
        <div class="header-subtitle">Powered by Groq • llama-3.1-8b</div>
    </div>
""", unsafe_allow_html=True)

# Chat Area
st.markdown('<div class="chat-wrapper">', unsafe_allow_html=True)

for msg in st.session_state.messages:
    is_bot = msg["role"] == "assistant"
    row_class = "bot" if is_bot else "user"
    avatar_class = "avatar-ai" if is_bot else "avatar-user"
    avatar_text = "AI" if is_bot else "You"
    bubble_class = "bubble-bot" if is_bot else "bubble-user"
    
    st.markdown(f"""
        <div class="message-row {row_class}">
            <div class="avatar {avatar_class}">{avatar_text}</div>
            <div style="flex-grow: 1; max-width: 85%;">
                <div class="bubble {bubble_class}">{msg['content']}</div>
                <div class="timestamp">{msg['time']}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Show suggestion chips only after the first welcome message
    if is_bot and msg == st.session_state.messages[0] and len(st.session_state.messages) == 1:
        st.markdown("""
            <div style="margin-left: 48px;">
                <div class="chip-container">
                    <div class="chip">Who logged most hours this week?</div>
                    <div class="chip">Show idle team members</div>
                    <div class="chip">Which project is over budget?</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Input area
prompt = st.chat_input("Ask about your team...")

if prompt:
    # Add user message
    now = datetime.datetime.now().strftime("%H:%M")
    st.session_state.messages.append({"role": "user", "content": prompt, "time": now})
    
    # Process with Groq function calling via llm_service
    with st.spinner("Analyzing your data..."):
        try:
            response = llm_service.chat(st.session_state.messages)
            st.session_state.messages.append({"role": "assistant", "content": response, "time": now})
        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"Connection Error: {str(e)}", "time": now})
    
    st.rerun()
