import os
import streamlit as st
from dotenv import load_dotenv

# Load local .env if it exists from the root directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

def get_secret(key):
    """Helper to get secret from Streamlit Cloud or local environment."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key)

GROQ_API_KEY = get_secret("GROQ_API_KEY")
MONGODB_URI = get_secret("MONGODB_URI")
MONGODB_DB = get_secret("MONGODB_DB")
MODEL = "llama-3.1-8b-instant"
