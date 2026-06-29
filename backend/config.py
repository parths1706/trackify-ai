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

GROQ_MODEL_LARGE = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_MODEL_SMALL = "llama-3.1-8b-instant"
GEMINI_API_KEY = get_secret("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = get_secret("GEMINI_MODEL") or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "trackify-ai")

import os as _os
_os.environ["LANGCHAIN_TRACING_V2"] = "true"
_os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
_os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT

