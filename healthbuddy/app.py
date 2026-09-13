import os
import sys
import base64
import random
import time
import io
from typing import List, Dict, Optional
from dotenv import load_dotenv
import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai import types
from google.genai import errors

# Optional TTS audio generation
try:
    from gtts import gTTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

# ==============================================================================
# 1. PAGE CONFIGURATION & METADATA
# ==============================================================================
st.set_page_config(
    page_title="SOU HEALTHCARE 🩺 | Health Awareness & SDG 3 AI",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# 2. ASSET HELPERS (BASE64 LOGO ENCODING)
# ==============================================================================
@st.cache_data
def get_logo_base64() -> str:
    """Loads the SOU Healthcare logo as base64 string across local and cloud environments."""
    # 1. Try direct import from embedded logo_data module
    try:
        from logo_data import LOGO_BASE64
        if LOGO_BASE64:
            return LOGO_BASE64
    except Exception:
        pass

    try:
        from healthbuddy.logo_data import LOGO_BASE64
        if LOGO_BASE64:
            return LOGO_BASE64
    except Exception:
        pass

    # 2. Filesystem search fallback
    base_dirs = [
        os.path.dirname(os.path.abspath(__file__)),
        os.getcwd(),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."),
    ]
    filenames = ["sou_logo.jpg", "sou_logo.png", "logo.jpg", "logo.png"]
    subdirs = ["assets", "healthbuddy/assets", "static", ""]
    
    possible_paths = []
    for b in base_dirs:
        for s in subdirs:
            for f in filenames:
                possible_paths.append(os.path.normpath(os.path.join(b, s, f)))
                
    for p in possible_paths:
        if os.path.exists(p) and os.path.isfile(p):
            try:
                with open(p, "rb") as img_file:
                    b64 = base64.b64encode(img_file.read()).decode("utf-8")
                    mime = "png" if p.lower().endswith(".png") else "jpeg"
                    return f"data:image/{mime};base64,{b64}"
            except Exception:
                continue
    return ""



LOGO_URI = get_logo_base64()

# ==============================================================================
# 3. ENVIRONMENT & GEMINI CLIENT INITIALIZATION
# ==============================================================================
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY and hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

if not GEMINI_API_KEY or GEMINI_API_KEY == "paste-your-key-here":
    st.error(
        """
        ### ⚠️ Missing Gemini API Key
        The application could not find a valid `GEMINI_API_KEY`.
        
        **How to configure:**
        1. Open or create the `.env` file in the project directory.
        2. Add your key: `GEMINI_API_KEY=your_actual_key_here`
        3. Restart the Streamlit application.
        """
    )
    st.stop()

@st.cache_resource
def get_gemini_client(api_key: str):
    """Initializes and caches the official Google GenAI client."""
    return genai.Client(api_key=api_key)

try:
    client = get_gemini_client(GEMINI_API_KEY)
except Exception as e:
    st.error(f"Failed to initialize Gemini API client: {str(e)}")
    st.stop()

# Primary and fallback models
PRIMARY_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODELS = ["gemini-3.1-flash-lite", "gemini-3.5-flash"]

# ==============================================================================
# 4. CUSTOM IMMERSIVE HEALTHCARE STYLING (CSS)
# ==============================================================================
st.markdown(
    """
    <style>
    /* Google Fonts Import */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Outfit:wght@400;600;700;800&display=swap');

    /* Force Light Theme at root across all platforms & devices */
    :root, html, body, [data-theme="dark"], [data-theme="light"], .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        color-scheme: light !important;
        supported-color-schemes: light !important;
        --text-color: #0f172a !important;
        --text-color-primary: #0f172a !important;
        --text-color-secondary: #475569 !important;
        --background-color: #f8fafc !important;
        --secondary-background-color: #ffffff !important;
        --primary-color: #0d9488 !important;
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Gemini-Inspired Luminous Gradient Light Background */
    .stApp, [data-testid="stAppViewContainer"], [data-theme="dark"] .stApp {
        background: 
            radial-gradient(ellipse 90% 55% at 50% -15%, rgba(56, 189, 248, 0.22), transparent 70%),
            radial-gradient(ellipse 65% 45% at 5% 25%, rgba(45, 212, 191, 0.20), transparent 60%),
            radial-gradient(ellipse 60% 50% at 95% 20%, rgba(168, 85, 247, 0.18), transparent 60%),
            radial-gradient(ellipse 75% 60% at 50% 100%, rgba(14, 165, 233, 0.16), transparent 65%),
            radial-gradient(ellipse 40% 40% at 85% 75%, rgba(244, 114, 182, 0.12), transparent 55%),
            linear-gradient(180deg, #f8fafc 0%, #f1f5f9 50%, #f8fafc 100%) !important;
        background-attachment: fixed !important;
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
    }

    /* Header Bar transparent styling */
    header[data-testid="stHeader"], [data-theme="dark"] header[data-testid="stHeader"] {
        background: transparent !important;
    }
    header[data-testid="stHeader"] * {
        color: #0f172a !important;
    }

    /* =========================================================================
       SIDEBAR & LEFT PANEL CUSTOM STYLES
       ========================================================================= */
    section[data-testid="stSidebar"], [data-theme="dark"] section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.97) 0%, rgba(240, 253, 250, 0.95) 50%, rgba(248, 250, 252, 0.98) 100%) !important;
        backdrop-filter: blur(24px) !important;
        -webkit-backdrop-filter: blur(24px) !important;
        border-right: 1px solid rgba(13, 148, 136, 0.2) !important;
        box-shadow: 4px 0 30px rgba(13, 148, 136, 0.06) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div {
        color: #1e293b !important;
        -webkit-text-fill-color: #1e293b !important;
    }

    .sidebar-brand-card {
        background: linear-gradient(135deg, #042f2e 0%, #0d5c63 45%, #0f766e 80%, #0369a1 100%);
        border-radius: 20px;
        padding: 1.3rem 1.1rem;
        color: white;
        text-align: center;
        box-shadow: 0 12px 28px -6px rgba(15, 58, 64, 0.35), 0 0 20px rgba(45, 212, 191, 0.28);
        margin-bottom: 1rem;
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }

    .sidebar-brand-card::after {
        content: "";
        position: absolute;
        top: -40%;
        right: -30%;
        width: 150px;
        height: 150px;
        background: radial-gradient(circle, rgba(96, 165, 250, 0.35) 0%, transparent 70%);
        border-radius: 50%;
        pointer-events: none;
    }

    .brand-avatar-img {
        width: 68px;
        height: 68px;
        margin: 0 auto 0.6rem auto;
        border-radius: 50%;
        object-fit: cover;
        border: 2.5px solid rgba(255, 255, 255, 0.85);
        box-shadow: 0 8px 22px rgba(0, 0, 0, 0.28), 0 0 14px rgba(45, 212, 191, 0.5);
        display: block;
        transition: transform 0.3s ease;
    }
    .brand-avatar-img:hover {
        transform: scale(1.05) rotate(2deg);
    }

    .brand-name {
        font-family: 'Outfit', sans-serif;
        font-size: 1.3rem;
        font-weight: 800;
        letter-spacing: -0.4px;
        color: #ffffff;
        margin: 0;
        line-height: 1.2;
        text-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }

    .brand-tag {
        font-size: 0.76rem;
        color: #ccfbf1;
        font-weight: 600;
        margin-top: 0.25rem;
        letter-spacing: 0.2px;
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(255, 255, 255, 0.18);
        border: 1px solid rgba(255, 255, 255, 0.3);
        padding: 3px 12px;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 700;
        color: #a5f3fc;
        margin-top: 0.6rem;
    }

    .status-dot {
        width: 7px;
        height: 7px;
        background-color: #34d399;
        border-radius: 50%;
        box-shadow: 0 0 10px #34d399;
        display: inline-block;
        animation: pulseDot 2s infinite;
    }

    @keyframes pulseDot {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(0.85); }
    }

    .sidebar-section-title {
        font-size: 0.8rem;
        font-weight: 800;
        color: #0f766e;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        margin-top: 0.8rem;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    /* History Session Items in Sidebar */
    .history-item {
        background: rgba(255, 255, 255, 0.8);
        border: 1px solid rgba(13, 148, 136, 0.16);
        border-radius: 12px;
        padding: 0.55rem 0.75rem;
        margin-bottom: 0.45rem;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .history-item:hover {
        background: rgba(240, 253, 250, 0.95);
        border-color: #0d9488;
        transform: translateX(2px);
    }

    /* Professional Emergency Hotlines Card */
    .emergency-hotline-card {
        background: linear-gradient(135deg, #450a0a 0%, #881337 50%, #991b1b 100%);
        border: 1.5px solid rgba(254, 205, 211, 0.35);
        border-radius: 16px;
        padding: 1rem 1.1rem;
        color: white;
        margin-top: 0.9rem;
        box-shadow: 0 10px 25px -4px rgba(153, 27, 27, 0.35), 0 0 15px rgba(239, 68, 68, 0.2);
        position: relative;
        overflow: hidden;
    }
    .emergency-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(255, 255, 255, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.35);
        padding: 3px 9px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.4px;
        margin-bottom: 0.45rem;
    }
    .emergency-pulse {
        width: 8px;
        height: 8px;
        background: #ef4444;
        border-radius: 50%;
        box-shadow: 0 0 10px #f87171;
        animation: emergencyPulse 1.2s infinite;
    }
    @keyframes emergencyPulse {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.4); opacity: 0.6; }
    }
    .hotline-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 6px;
        margin-top: 0.6rem;
    }
    .hotline-btn-link {
        background: rgba(255, 255, 255, 0.16);
        border: 1px solid rgba(255, 255, 255, 0.25);
        border-radius: 8px;
        padding: 5px 8px;
        font-size: 0.74rem;
        font-weight: 700;
        color: #ffffff !important;
        text-decoration: none;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 4px;
        transition: all 0.2s;
    }
    .hotline-btn-link:hover {
        background: rgba(255, 255, 255, 0.3);
        transform: translateY(-1px);
        color: #ffffff !important;
    }

    /* =========================================================================
       HERO BANNER & HEADER
       ========================================================================= */
    .brand-hero {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(240, 253, 250, 0.92) 50%, rgba(224, 242, 254, 0.92) 100%);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(13, 148, 136, 0.22);
        border-radius: 24px;
        padding: 1.6rem 2rem;
        margin-bottom: 1.4rem;
        box-shadow: 0 12px 35px -8px rgba(13, 148, 136, 0.12), 0 0 20px rgba(56, 189, 248, 0.1);
        display: flex;
        align-items: center;
        gap: 1.6rem;
    }
    .hero-logo-img {
        width: 82px;
        height: 82px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid #0d9488;
        box-shadow: 0 8px 24px rgba(13, 148, 136, 0.35);
        flex-shrink: 0;
        animation: heroFloat 6s ease-in-out infinite;
    }
    @keyframes heroFloat {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-4px); }
    }
    .hero-text-container {
        flex: 1;
    }
    .brand-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: linear-gradient(135deg, rgba(13, 148, 136, 0.12) 0%, rgba(2, 132, 199, 0.12) 100%);
        border: 1px solid rgba(13, 148, 136, 0.3);
        color: #0f766e;
        padding: 4px 14px;
        border-radius: 9999px;
        font-size: 0.74rem;
        font-weight: 800;
        letter-spacing: 0.5px;
        margin-bottom: 0.4rem;
    }
    .brand-title {
        font-family: 'Outfit', sans-serif;
        font-size: 2.2rem;
        font-weight: 800;
        color: #042f2e;
        margin: 0;
        line-height: 1.15;
        letter-spacing: -0.5px;
    }
    .brand-subtitle {
        color: #475569;
        font-size: 0.95rem;
        font-weight: 500;
        margin-top: 0.35rem;
    }

    /* Small Step Box */
    .small-step-box {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(240, 253, 250, 0.92) 100%);
        backdrop-filter: blur(14px);
        border: 1px solid rgba(13, 148, 136, 0.2);
        border-left: 5px solid #0d9488;
        border-radius: 16px;
        padding: 0.9rem 1.2rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 6px 20px -4px rgba(15, 23, 42, 0.05);
    }
    .small-step-box h4 {
        margin: 0 0 0.25rem 0;
        color: #0f766e;
        font-size: 0.92rem;
        font-weight: 700;
    }
    .small-step-box p {
        margin: 0;
        color: #334155;
        font-size: 0.85rem;
        line-height: 1.45;
    }

    /* Action Cards */
    .card-container {
        background: rgba(255, 255, 255, 0.88);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(13, 148, 136, 0.16);
        border-radius: 18px;
        padding: 1.2rem 1.1rem;
        transition: all 0.28s cubic-bezier(0.4, 0, 0.2, 1);
        min-height: 155px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        margin-bottom: 0.9rem;
        box-shadow: 0 6px 20px -4px rgba(15, 23, 42, 0.05);
    }
    .card-container:hover {
        transform: translateY(-4px);
        border-color: #0d9488;
        box-shadow: 0 14px 30px -6px rgba(13, 148, 136, 0.18);
        background: #ffffff;
    }
    .card-icon {
        font-size: 1.7rem;
        margin-bottom: 0.4rem;
    }
    .card-title {
        font-size: 1rem;
        font-weight: 700;
        color: #042f2e;
        margin-bottom: 0.3rem;
    }
    .card-desc {
        font-size: 0.82rem;
        color: #475569;
        line-height: 1.4;
    }

    /* =========================================================================
       CHAT MESSAGES STYLING & BULLETPROOF CROSS-PLATFORM DARK MODE CONTRAST
       ========================================================================= */
    .stChatMessage, 
    div[data-testid="stChatMessage"],
    div[data-testid="stChatMessageContent"] {
        background: #ffffff !important;
        background: rgba(255, 255, 255, 0.98) !important;
        backdrop-filter: blur(14px) !important;
        -webkit-backdrop-filter: blur(14px) !important;
        border: 1.5px solid rgba(13, 148, 136, 0.28) !important;
        border-radius: 18px !important;
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        padding: 1.1rem 1.3rem !important;
        margin-bottom: 0.9rem !important;
        box-shadow: 0 6px 24px -4px rgba(15, 23, 42, 0.08) !important;
    }

    /* Target all message elements explicitly to override Streamlit dark mode text inheritance */
    div[data-testid="stChatMessage"] *,
    div[data-testid="stChatMessageContent"] *,
    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] *,
    div[data-testid="stChatMessageContent"] [data-testid="stMarkdownContainer"] *,
    div[data-testid="stChatMessage"] p,
    div[data-testid="stChatMessage"] span,
    div[data-testid="stChatMessage"] div,
    div[data-testid="stChatMessage"] li,
    div[data-testid="stChatMessage"] ul,
    div[data-testid="stChatMessage"] ol,
    div[data-testid="stChatMessage"] strong,
    div[data-testid="stChatMessage"] b,
    div[data-testid="stChatMessage"] em,
    div[data-testid="stChatMessage"] i,
    div[data-testid="stChatMessage"] table,
    div[data-testid="stChatMessage"] tr,
    div[data-testid="stChatMessage"] td,
    div[data-testid="stChatMessage"] th {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
    }

    /* Headings inside chat messages */
    div[data-testid="stChatMessage"] h1,
    div[data-testid="stChatMessage"] h2,
    div[data-testid="stChatMessage"] h3,
    div[data-testid="stChatMessage"] h4,
    div[data-testid="stChatMessage"] h5,
    div[data-testid="stChatMessage"] h6,
    div[data-testid="stChatMessageContent"] h1,
    div[data-testid="stChatMessageContent"] h2,
    div[data-testid="stChatMessageContent"] h3,
    div[data-testid="stChatMessageContent"] h4,
    div[data-testid="stChatMessageContent"] h5,
    div[data-testid="stChatMessageContent"] h6 {
        color: #042f2e !important;
        -webkit-text-fill-color: #042f2e !important;
        font-weight: 800 !important;
        font-family: 'Outfit', sans-serif !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.35rem !important;
    }

    /* Bullet points styling */
    div[data-testid="stChatMessage"] li {
        margin-bottom: 0.25rem !important;
        line-height: 1.5 !important;
    }
    div[data-testid="stChatMessage"] li::marker {
        color: #0d9488 !important;
    }

    /* Blockquote styling */
    div[data-testid="stChatMessage"] blockquote {
        border-left: 4px solid #0d9488 !important;
        background: rgba(240, 253, 250, 0.9) !important;
        color: #134e4a !important;
        -webkit-text-fill-color: #134e4a !important;
        padding: 0.6rem 1rem !important;
        border-radius: 0 12px 12px 0 !important;
        margin: 0.6rem 0 !important;
    }
    div[data-testid="stChatMessage"] blockquote * {
        color: #134e4a !important;
        -webkit-text-fill-color: #134e4a !important;
    }

    /* User Message distinct background styling */
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]),
    div[data-testid="stChatMessage"]:has(span[data-testid="stIconMaterial"]),
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background: #f0fdfa !important;
        background: linear-gradient(135deg, #f0fdfa 0%, #e0f2fe 100%) !important;
        border: 1.5px solid rgba(13, 148, 136, 0.35) !important;
    }

    /* Code blocks retain dark IDE look with crisp syntax contrast */
    div[data-testid="stChatMessage"] pre,
    div[data-testid="stChatMessage"] pre code,
    div[data-testid="stChatMessage"] code {
        background-color: #0f172a !important;
        color: #38bdf8 !important;
        -webkit-text-fill-color: #38bdf8 !important;
        border-radius: 8px !important;
        padding: 0.2rem 0.45rem !important;
        font-family: monospace !important;
    }

    /* Audio Player in Chat */
    audio {
        width: 100% !important;
        border-radius: 30px !important;
        margin-top: 0.4rem !important;
        margin-bottom: 0.2rem !important;
    }

    /* Action Buttons & Exploration Chips */
    .stButton > button,
    button[kind="secondary"],
    div[data-testid="stButton"] > button {
        background: #ffffff !important;
        color: #0f766e !important;
        -webkit-text-fill-color: #0f766e !important;
        border: 1.5px solid rgba(13, 148, 136, 0.3) !important;
        border-radius: 14px !important;
        font-weight: 700 !important;
        font-size: 0.84rem !important;
        box-shadow: 0 2px 10px rgba(13, 148, 136, 0.08) !important;
        transition: all 0.22s ease !important;
    }
    .stButton > button:hover,
    button[kind="secondary"]:hover,
    div[data-testid="stButton"] > button:hover {
        background: linear-gradient(135deg, #f0fdfa 0%, #e0f2fe 100%) !important;
        border-color: #0d9488 !important;
        color: #042f2e !important;
        -webkit-text-fill-color: #042f2e !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 16px rgba(13, 148, 136, 0.18) !important;
    }
    .stButton > button[kind="primary"],
    div[data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(135deg, #0d9488 0%, #0284c7 100%) !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        border: none !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 14px rgba(13, 148, 136, 0.35) !important;
    }

    /* Typing Indicator */
    .typing-container {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        padding: 8px 18px;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(14px);
        border: 1px solid rgba(13, 148, 136, 0.3);
        border-radius: 20px;
        margin-bottom: 8px;
        box-shadow: 0 4px 15px rgba(13, 148, 136, 0.1);
    }
    .typing-text {
        font-size: 0.86rem;
        font-weight: 700;
        color: #0f766e;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .typing-dots {
        display: inline-flex;
        gap: 4px;
        align-items: center;
    }
    .typing-dot {
        width: 6px;
        height: 6px;
        background: linear-gradient(135deg, #0d9488, #0284c7);
        border-radius: 50%;
        animation: typingBounce 1.4s infinite ease-in-out both;
    }
    .typing-dot:nth-child(1) { animation-delay: -0.32s; }
    .typing-dot:nth-child(2) { animation-delay: -0.16s; }
    .typing-dot:nth-child(3) { animation-delay: 0s; }

    @keyframes typingBounce {
        0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
        40% { transform: scale(1.2); opacity: 1; }
    }

    /* =========================================================================
       TASKBAR & BOTTOM CHAT INPUT CONTAINER WITH MOBILE DARK MODE FIX
       ========================================================================= */
    div[data-testid="stBottom"], div.stChatFloatingInputContainer {
        background: linear-gradient(180deg, rgba(248, 250, 252, 0) 0%, rgba(248, 250, 252, 0.94) 35%, #f1f5f9 100%) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        padding-bottom: 0.8rem !important;
        border-top: 1px solid rgba(13, 148, 136, 0.15) !important;
    }

    div[data-testid="stChatInput"],
    div[data-testid="stChatInput"] > div {
        background: #ffffff !important;
        backdrop-filter: blur(24px) !important;
        -webkit-backdrop-filter: blur(24px) !important;
        border: 1.5px solid rgba(56, 189, 248, 0.5) !important;
        border-radius: 32px !important;
        padding: 0.35rem 0.75rem !important;
        box-shadow: 0 14px 42px -6px rgba(13, 148, 136, 0.18),
                    0 0 28px rgba(56, 189, 248, 0.22),
                    0 1px 3px rgba(0, 0, 0, 0.04) !important;
        transition: all 0.28s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    div[data-testid="stChatInput"]:focus-within {
        border-color: #0d9488 !important;
        box-shadow: 0 18px 50px -6px rgba(13, 148, 136, 0.28),
                    0 0 35px rgba(45, 212, 191, 0.35) !important;
        transform: translateY(-2px);
    }
    div[data-testid="stChatInput"] textarea,
    div[data-testid="stChatInput"] [data-testid="stChatInputTextArea"],
    div[data-testid="stChatInput"] textarea:focus {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        font-size: 0.95rem !important;
        font-weight: 500 !important;
        background: #ffffff !important;
        padding: 0.35rem 0.6rem !important;
        line-height: 1.45 !important;
        caret-color: #0d9488 !important;
    }
    div[data-testid="stChatInput"] textarea::placeholder {
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        opacity: 0.9 !important;
    }
    div[data-testid="stChatInput"] button {
        background: linear-gradient(135deg, #0d9488 0%, #0284c7 100%) !important;
        border: none !important;
        border-radius: 50% !important;
        width: 36px !important;
        height: 36px !important;
        color: white !important;
        -webkit-text-fill-color: white !important;
        box-shadow: 0 4px 14px rgba(13, 148, 136, 0.38) !important;
        margin-left: 4px !important;
    }
    div[data-testid="stChatInput"] button svg {
        fill: white !important;
        color: white !important;
    }

    /* Form inputs and interactive controls text color enforcement */
    input, textarea, select, 
    div[data-testid="stTextInput"] input,
    div[data-testid="stSelectbox"] *,
    div[data-testid="stRadio"] *,
    div[data-testid="stSlider"] *,
    div[data-baseweb="select"] * {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
    }

    /* File Badge */
    .file-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: linear-gradient(135deg, #f0fdfa, #e0f2fe);
        border: 1px solid rgba(13, 148, 136, 0.28);
        border-radius: 10px;
        padding: 4px 12px;
        font-size: 0.8rem;
        font-weight: 600;
        color: #0369a1;
        margin-bottom: 6px;
    }

    /* Health Awareness Score Animated Visuals */
    .score-hero-card {
        background: linear-gradient(135deg, #042f2e 0%, #0d5c63 50%, #0369a1 100%);
        border-radius: 24px;
        padding: 2rem;
        color: white;
        text-align: center;
        box-shadow: 0 16px 40px -8px rgba(13, 148, 136, 0.35);
        margin: 1.2rem 0;
        position: relative;
        overflow: hidden;
    }
    .score-circle-wrapper {
        width: 140px;
        height: 140px;
        margin: 0 auto 1rem auto;
        border-radius: 50%;
        background: conic-gradient(#14b8a6 var(--score-deg, 280deg), rgba(255,255,255,0.15) 0deg);
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0 30px rgba(45, 212, 191, 0.5);
        animation: scorePop 1s ease-out;
    }
    .score-circle-inner {
        width: 114px;
        height: 114px;
        border-radius: 50%;
        background: #042f2e;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    .score-number {
        font-family: 'Outfit', sans-serif;
        font-size: 2.3rem;
        font-weight: 800;
        line-height: 1;
        color: #5eead4;
    }
    .score-denom {
        font-size: 0.75rem;
        color: #94a3b8;
        font-weight: 600;
    }
    @keyframes scorePop {
        0% { transform: scale(0.7); opacity: 0; }
        100% { transform: scale(1); opacity: 1; }
    }

    .pillar-bar-container {
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid rgba(13, 148, 136, 0.18);
        border-radius: 14px;
        padding: 0.8rem 1.1rem;
        margin-bottom: 0.7rem;
    }
    .pillar-header {
        display: flex;
        justify-content: space-between;
        font-size: 0.84rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.35rem;
    }
    .pillar-bar-bg {
        width: 100%;
        height: 8px;
        background: #e2e8f0;
        border-radius: 4px;
        overflow: hidden;
    }
    .pillar-bar-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 1s ease-in-out;
    }

    /* Myth Buster Cards */
    .myth-card {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(14px);
        border: 1px solid rgba(13, 148, 136, 0.2);
        border-radius: 16px;
        padding: 1.1rem;
        margin-bottom: 0.8rem;
        transition: transform 0.2s;
    }
    .myth-card:hover {
        transform: translateY(-2px);
        border-color: #0d9488;
    }
    .myth-tag {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 800;
        margin-bottom: 0.4rem;
    }
    .myth-tag-busted { background: #fee2e2; color: #991b1b; }
    .myth-tag-verified { background: #dcfce7; color: #166534; }
    .myth-tag-partial { background: #fef3c7; color: #92400e; }

    /* Persistent Disclaimer */
    .disclaimer-banner {
        background: rgba(241, 245, 249, 0.9);
        border: 1px solid rgba(203, 213, 225, 0.8);
        border-radius: 12px;
        padding: 0.8rem 1.1rem;
        font-size: 0.76rem;
        color: #64748b;
        line-height: 1.45;
        text-align: center;
        margin-top: 1.8rem;
    }

    /* Mobile theme overrides */
    @media (prefers-color-scheme: dark) {
        :root, html, body, .stApp {
            color-scheme: light !important;
            background-color: #f8fafc !important;
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
        }
        div[data-testid="stChatMessage"],
        div[data-testid="stChatMessageContent"],
        div[data-testid="stChatMessage"] *,
        div[data-testid="stChatMessageContent"] *,
        div[data-testid="stChatMessage"] p,
        div[data-testid="stChatMessage"] span,
        div[data-testid="stChatMessage"] div,
        div[data-testid="stChatMessage"] li,
        div[data-testid="stChatMessage"] h1,
        div[data-testid="stChatMessage"] h2,
        div[data-testid="stChatMessage"] h3,
        div[data-testid="stChatMessage"] h4,
        div[data-testid="stChatMessage"] h5,
        div[data-testid="stChatMessage"] h6,
        div[data-testid="stChatMessage"] strong,
        div[data-testid="stChatMessage"] b,
        div[data-testid="stChatMessage"] em,
        div[data-testid="stChatMessage"] blockquote,
        div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
        div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] * {
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
        }
        div[data-testid="stChatMessage"] {
            background: #ffffff !important;
            border: 1.5px solid rgba(13, 148, 136, 0.28) !important;
        }
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]),
        div[data-testid="stChatMessage"]:has(span[data-testid="stIconMaterial"]),
        div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
            background: #f0fdfa !important;
            background: linear-gradient(135deg, #f0fdfa 0%, #e0f2fe 100%) !important;
        }
        .stButton > button,
        button[kind="secondary"],
        div[data-testid="stButton"] > button {
            background: #ffffff !important;
            color: #0f766e !important;
            -webkit-text-fill-color: #0f766e !important;
            border: 1.5px solid rgba(13, 148, 136, 0.3) !important;
        }
        div[data-testid="stChatInput"],
        div[data-testid="stChatInput"] > div,
        div[data-testid="stChatInput"] textarea {
            background: #ffffff !important;
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
        }
    }

    /* Explicit Streamlit dark theme attribute overrides */
    [data-theme="dark"] .stApp,
    [data-theme="dark"] div[data-testid="stChatMessage"],
    [data-theme="dark"] div[data-testid="stChatMessage"] *,
    [data-theme="dark"] div[data-testid="stChatMessageContent"] *,
    [data-theme="dark"] [data-testid="stMarkdownContainer"] * {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
    }
    [data-theme="dark"] div[data-testid="stChatMessage"] {
        background: #ffffff !important;
        border-color: rgba(13, 148, 136, 0.28) !important;
    }
    [data-theme="dark"] .stButton > button,
    [data-theme="dark"] button[kind="secondary"] {
        background: #ffffff !important;
        color: #0f766e !important;
        -webkit-text-fill-color: #0f766e !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# 5. MULTI-SESSION CHAT STATE MANAGEMENT
# ==============================================================================
if "sessions" not in st.session_state:
    st.session_state.sessions = {
        "session_1": {
            "title": "Welcome Consultation",
            "messages": [],
            "timestamp": time.strftime("%b %d, %H:%M"),
        }
    }

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = "session_1"

if "active_tab" not in st.session_state:
    st.session_state.active_tab = "💬 Chat Assistant"

if "response_mode" not in st.session_state:
    st.session_state.response_mode = "⚡ Quick Answer"

if "daily_step_idx" not in st.session_state:
    st.session_state.daily_step_idx = 0

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

if "health_score_data" not in st.session_state:
    st.session_state.health_score_data = None

if "last_voice_bytes" not in st.session_state:
    st.session_state.last_voice_bytes = None

# Ensure active session exists
if st.session_state.current_session_id not in st.session_state.sessions:
    st.session_state.current_session_id = list(st.session_state.sessions.keys())[0]

current_chat = st.session_state.sessions[st.session_state.current_session_id]

# Micro-habits list for "Small Step for Today"
SMALL_STEPS = [
    {
        "title": "Hydration Milestone 💧",
        "desc": "Drink a full glass of fresh water right now. Mild dehydration often mimics fatigue and brain fog.",
    },
    {
        "title": "2-Minute Gentle Neck & Shoulder Release 🧘",
        "desc": "Step away from your screen, gently roll your shoulders backward 10 times, and take 3 deep belly breaths.",
    },
    {
        "title": "4-7-8 Calming Breath Reset 🫁",
        "desc": "Inhale quietly through your nose for 4 seconds, hold your breath for 7 seconds, and exhale completely for 8 seconds.",
    },
    {
        "title": "Post-Meal 10-Minute Walk 🚶",
        "desc": "A gentle 10-minute stroll after a meal assists healthy glucose regulation and promotes digestive comfort.",
    },
    {
        "title": "Pre-Bed Digital Sunset 🌙",
        "desc": "Aim to switch off bright screens 30 minutes before sleep tonight to allow natural melatonin production.",
    },
    {
        "title": "Rainbow Plate Variety 🥗",
        "desc": "Challenge yourself to include at least two different naturally colored vegetables in your next meal.",
    },
]

# ==============================================================================
# 6. SAFETY-FIRST SYSTEM PROMPT BUILDER
# ==============================================================================
def build_system_instruction(response_mode: str) -> str:
    """Builds a comprehensive, competition-grade system instruction ensuring strict SDG 3 alignment and safety."""
    
    mode_guidance = {
        "⚡ Quick Answer": (
            "Format your answer compactly. Provide direct, highly actionable bullet points. "
            "Keep the response focused and concise (under 160 words) without unnecessary fluff."
        ),
        "📚 Detailed Explanation": (
            "Provide a comprehensive, educational explanation. Include background context, "
            "the physiological/lifestyle mechanism, practical step-by-step strategies, and evidence-based insights."
        ),
        "🌱 Simple Language": (
            "Use clear, friendly, and non-technical language. Explain concepts using relatable everyday analogies. "
            "Avoid complex medical terminology so users of all reading levels understand effortlessly."
        ),
    }.get(response_mode, "Provide clear and structured information.")

    return f"""
You are SOU HEALTHCARE (HealthBuddy AI), a compassionate, highly knowledgeable, and responsible Health Awareness Assistant dedicated to United Nations Sustainable Development Goal 3 (SDG 3: Good Health & Well-being).

YOUR CORE PURPOSE:
1. Promote general health education, health literacy, and health awareness.
2. Provide preventive health knowledge, hygiene awareness, infection prevention, and lifestyle education.
3. Guide users toward healthy daily habits: balanced nutrition, hydration, regular movement, restorative sleep, screen mindfulness, and stress management.
4. Support maternal, child, adult, and geriatric wellness awareness.

CRITICAL IDENTITY RULES:
- You are an AI Health Awareness Assistant.
- You are NOT a doctor, physician, hospital, emergency medical service, or licensed healthcare professional.
- You CANNOT diagnose medical conditions, formulate clinical diagnoses, or prescribe treatments.
- You NEVER claim certainty regarding a user's medical condition.

CRITICAL SAFETY & MEDICAL RESPONSIBILITY GUIDELINES:
1. STRICT NO-DIAGNOSIS RULE:
   - If a user describes symptoms (e.g. fever, rash, pain, cough), NEVER say: "You have [Condition]".
   - Instead, explain educational possibilities calmly: "Symptoms like these can stem from various causes. A qualified healthcare professional can conduct a proper examination."
2. MEDICATION SAFETY:
   - Never prescribe, recommend dosage adjustments, or advise discontinuing prescription medications.
   - For queries about medications, explain general pharmacological education neutrally and advise discussing with a prescribing physician or pharmacist.
3. EMERGENCY & LIFE-THREATENING PROTOCOL:
   - If the user mentions severe red-flag symptoms (e.g., crushing chest pain, pain radiating to left arm/jaw, severe shortness of breath, sudden facial drooping or limb weakness, coughing blood, severe allergic anaphylaxis, acute trauma):
     IMMEDIATELY advise them to call emergency services (911 in US/Canada, 112 in Europe/India, 999 in UK, or local emergency number) or go to the nearest emergency room without delay.
4. MENTAL HEALTH CRISIS PROTOCOL:
   - If a user expresses thoughts of self-harm, suicide, or severe despair:
     Respond with deep warmth, validation, and zero judgment. Provide immediate crisis resources:
     * US & Canada: Call or text 988 (Suicide & Crisis Lifeline)
     * UK: Call 111 or text SHOUT to 85258
     * India / International: Contact 112 or local emergency services, or visit befrienders.org / iasp.info.

RESPONSE FORMATTING:
- Response Mode selected by user: {response_mode}
- Mode Directive: {mode_guidance}
- Format with clean Markdown headers, bullet points, bold key terms.
- Prioritize actionable lifestyle and preventive guidance.
"""

# Helper function for generating audio
def generate_speech_audio(text: str) -> Optional[bytes]:
    """Generates MP3 audio for the given text using gTTS."""
    if not TTS_AVAILABLE:
        return None
    try:
        clean_text = text.replace("*", "").replace("#", "").replace("`", "").replace(">", "").strip()
        if len(clean_text) > 400:
            clean_text = clean_text[:400] + "... consult a medical professional for individual guidance."
        fp = io.BytesIO()
        tts = gTTS(text=clean_text, lang="en", slow=False)
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.getvalue()
    except Exception:
        return None

# ==============================================================================
# 7. SIDEBAR NAVIGATION & LATEST CONVERSATION HISTORY
# ==============================================================================
with st.sidebar:
    # Merged SOU Healthcare Logo & Branding
    st.markdown(
        f"""
        <div class="sidebar-brand-card">
            {f'<img src="{LOGO_URI}" class="brand-avatar-img" alt="SOU Healthcare Logo">' if LOGO_URI else '<div style="font-size:2.2rem;margin-bottom:0.4rem;">🩺</div>'}
            <div class="brand-name">SOU HEALTHCARE</div>
            <div class="brand-tag">SDG 3 • Good Health & Well-being</div>
            <div class="status-pill">
                <span class="status-dot"></span> Gemini 3.5 Flash • Active
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Navigation Mode Selector
    st.markdown(
        """
        <div class="sidebar-section-title">
            <span>🧭</span> Platform Hub
        </div>
        """,
        unsafe_allow_html=True,
    )
    nav_tab = st.radio(
        "Navigate Platform:",
        ["💬 Chat Assistant", "📊 Health Awareness Score", "🧙‍♂️ Myth Buster AI", "🌿 Daily Wellness Check-In"],
        index=["💬 Chat Assistant", "📊 Health Awareness Score", "🧙‍♂️ Myth Buster AI", "🌿 Daily Wellness Check-In"].index(st.session_state.active_tab),
        label_visibility="collapsed"
    )
    if nav_tab != st.session_state.active_tab:
        st.session_state.active_tab = nav_tab
        st.rerun()

    # Response Depth Mode Selector
    st.markdown(
        """
        <div class="sidebar-section-title">
            <span>⚡</span> Intelligence Depth
        </div>
        """,
        unsafe_allow_html=True,
    )
    selected_mode = st.radio(
        "Select assistant response depth:",
        ["⚡ Quick Answer", "📚 Detailed Explanation", "🌱 Simple Language"],
        index=["⚡ Quick Answer", "📚 Detailed Explanation", "🌱 Simple Language"].index(st.session_state.response_mode),
        label_visibility="collapsed",
        help="Quick Answer gives concise key takeaways; Detailed provides in-depth education; Simple uses everyday metaphors.",
    )
    st.session_state.response_mode = selected_mode

    st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

    # LATEST CONVERSATION HISTORY (ChatGPT / Claude style)
    st.markdown(
        """
        <div class="sidebar-section-title">
            <span>💬</span> Recent Consultations
        </div>
        """,
        unsafe_allow_html=True,
    )

    # New Chat Button
    if st.button("➕ New Consultation", use_container_width=True, type="primary"):
        new_id = f"session_{int(time.time())}"
        st.session_state.sessions[new_id] = {
            "title": f"Consultation #{len(st.session_state.sessions) + 1}",
            "messages": [],
            "timestamp": time.strftime("%b %d, %H:%M"),
        }
        st.session_state.current_session_id = new_id
        st.session_state.active_tab = "💬 Chat Assistant"
        st.session_state.pending_prompt = None
        st.rerun()

    # List of past conversation sessions
    session_keys = list(st.session_state.sessions.keys())
    session_keys.reverse()  # Show newest first

    for sid in session_keys:
        sess = st.session_state.sessions[sid]
        is_active = (sid == st.session_state.current_session_id)
        
        col_s_main, col_s_del = st.columns([5, 1])
        with col_s_main:
            button_label = f"{'🟢 ' if is_active else '💬 '}{sess['title'][:22]}"
            if st.button(
                button_label,
                key=f"sess_btn_{sid}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
                help=f"Created {sess.get('timestamp', '')}"
            ):
                st.session_state.current_session_id = sid
                st.session_state.active_tab = "💬 Chat Assistant"
                st.rerun()
        with col_s_del:
            if len(st.session_state.sessions) > 1:
                if st.button("✕", key=f"del_sess_{sid}", help="Delete this consultation"):
                    del st.session_state.sessions[sid]
                    if st.session_state.current_session_id == sid:
                        st.session_state.current_session_id = list(st.session_state.sessions.keys())[0]
                    st.rerun()

    # Upgraded Professional Emergency Hotlines Card
    st.markdown(
        """
        <div class="emergency-hotline-card">
            <div class="emergency-badge">
                <span class="emergency-pulse"></span> 24/7 CRISIS & TRIAGE
            </div>
            <div style="font-size: 0.88rem; font-weight: 800; margin-bottom: 0.2rem;">
                🚨 Emergency Medical Hotlines
            </div>
            <div style="font-size: 0.74rem; opacity: 0.9; line-height: 1.35;">
                In life-threatening situations or acute symptoms, call local emergency services immediately:
            </div>
            <div class="hotline-grid">
                <a href="tel:112" class="hotline-btn-link">🇮🇳/🇪🇺 112 (All-in-One)</a>
                <a href="tel:911" class="hotline-btn-link">🇺🇸 911 (US/CA)</a>
                <a href="tel:999" class="hotline-btn-link">🇬🇧 999 (UK)</a>
                <a href="tel:988" class="hotline-btn-link">🧠 988 (Crisis)</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # UN SDG 3 Indicator Card
    st.markdown(
        """
        <div style="font-size: 0.74rem; color: #475569; line-height: 1.4; padding: 0.7rem 0.8rem; background: rgba(255,255,255,0.85); border-radius: 12px; border: 1px solid rgba(13,148,136,0.18); margin-top: 0.9rem;">
            <strong style="color: #0f766e;">🌍 UN SDG 3 Goal Fit:</strong><br>
            Promoting universal health literacy, disease prevention, and mindful well-being.
        </div>
        <div style="font-size: 0.72rem; color: #94a3b8; line-height: 1.35; padding: 0.4rem; text-align: center; margin-top: 0.3rem;">
            🛡️ AI Health Awareness Platform • Not Medical Advice
        </div>
        """,
        unsafe_allow_html=True,
    )

# ==============================================================================
# 8. MAIN HERO BANNER (WITH MERGED SOU HEALTHCARE LOGO)
# ==============================================================================
logo_hero_html = f'<img src="{LOGO_URI}" class="hero-logo-img" alt="SOU Healthcare">' if LOGO_URI else '<div style="font-size:3rem;">🩺</div>'

st.markdown(
    f"""
    <div class="brand-hero">
        {logo_hero_html}
        <div class="hero-text-container">
            <div class="brand-badge">
                <span>🌍</span> UN SDG 3: GOOD HEALTH & WELL-BEING
            </div>
            <h1 class="brand-title">SOU HEALTHCARE 🩺</h1>
            <div class="brand-subtitle">
                Your premier AI companion for health literacy, preventive wellness, and evidence-based living.
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# 9. INNOVATIVE FEATURE: "SMALL STEP FOR TODAY" (DAILY HABIT)
# ==============================================================================
step = SMALL_STEPS[st.session_state.daily_step_idx % len(SMALL_STEPS)]
col_step1, col_step2 = st.columns([4, 1])

with col_step1:
    st.markdown(
        f"""
        <div class="small-step-box">
            <h4>✨ Small Step for Today: {step['title']}</h4>
            <p>{step['desc']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_step2:
    st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
    if st.button("Next Tip 🔄", use_container_width=True, help="Show another wellness micro-habit"):
        st.session_state.daily_step_idx += 1
        st.rerun()

# ==============================================================================
# 10. SECTION ROUTING: ACTIVE TAB CONTROLLER
# ==============================================================================

# ------------------------------------------------------------------------------
# TAB A: HEALTH AWARENESS SCORE CALCULATOR (DIAGNOSTIC QUESTIONNAIRE)
# ------------------------------------------------------------------------------
if st.session_state.active_tab == "📊 Health Awareness Score":
    st.markdown("## 📊 Comprehensive Health Awareness Score")
    st.write(
        "Evaluate your daily lifestyle habits across **6 fundamental wellness pillars** defined by WHO & global health guidelines. "
        "Calculate your real-time Health Awareness Score and receive tailored preventive recommendations."
    )

    with st.container(border=True):
        st.markdown("### 📋 6-Pillar Lifestyle Evaluation")
        
        c_p1, c_p2 = st.columns(2)
        with c_p1:
            st.markdown("#### 1. 😴 Sleep & Circadian Health")
            q_sleep_hrs = st.slider("Average sleep duration (hours/night):", 3.0, 12.0, 7.5, 0.5)
            q_sleep_rest = st.radio("How rested do you feel upon waking?", ["Refreshed & Energized (100%)", "Adequately Rested (75%)", "Somewhat Groggy (50%)", "Exhausted / Restless (20%)"], index=1)
            
            st.markdown("#### 2. 🥗 Nutrition & Mindful Hydration")
            q_water = st.slider("Daily water intake (glasses / 250ml each):", 1, 16, 8)
            q_diet = st.radio("Daily diet composition:", ["Whole foods, veggies & lean protein daily", "Mostly balanced with occasional processed food", "Irregular meals / High fast-food consumption"], index=1)

            st.markdown("#### 3. 🏃 Physical Movement & Exercise")
            q_activity = st.radio(
                "Weekly physical activity level:",
                ["150+ mins moderate exercise (brisk walk, gym, sports)", "60-120 mins light-to-moderate movement", "Sedentary (< 30 mins active movement/week)"],
                index=0
            )

        with c_p2:
            st.markdown("#### 4. 🧼 Hygiene & Preventive Habits")
            q_hygiene = st.radio(
                "Preventive hygiene & dental routine:",
                ["Regular handwashing, 2x daily brushing/flossing, routine checkups", "Moderate routine, occasional missed steps", "Infrequent preventive care"],
                index=0
            )

            st.markdown("#### 5. 🧠 Stress Management & Coping")
            q_stress = st.select_slider("Daily perceived stress level:", options=["Low & Manageable", "Moderate / Balanced", "High / Frequent Pressure", "Overwhelming"], value="Moderate / Balanced")
            q_mindfulness = st.checkbox("I take at least 5-10 minutes daily for intentional relaxation or breathing exercises", value=True)

            st.markdown("#### 6. 📱 Screen & Digital Hygiene")
            q_screen = st.radio(
                "Evening screen habits before bed:",
                ["Screen-free 30+ mins before sleep / Blue-light filter", "Phone use in bed until falling asleep", "Heavy late-night screen exposure"],
                index=0
            )

        calculate_btn = st.button("🎯 Calculate My Health Awareness Score", type="primary", use_container_width=True)

        if calculate_btn:
            s_pts = 18 if (7.0 <= q_sleep_hrs <= 9.0) else (14 if (6.0 <= q_sleep_hrs < 7.0 or 9.0 < q_sleep_hrs <= 10.0) else 8)
            if "Refreshed" in q_sleep_rest: s_pts += 2
            elif "Exhausted" in q_sleep_rest: s_pts -= 4

            w_pts = 10 if q_water >= 8 else (7 if q_water >= 5 else 4)
            d_pts = 8 if "Whole foods" in q_diet else (5 if "Mostly balanced" in q_diet else 2)
            nutr_pts = w_pts + d_pts

            act_pts = 18 if "150+" in q_activity else (12 if "60-120" in q_activity else 5)
            hyg_pts = 16 if "Regular" in q_hygiene else (11 if "Moderate" in q_hygiene else 5)

            str_map = {"Low & Manageable": 12, "Moderate / Balanced": 10, "High / Frequent Pressure": 6, "Overwhelming": 2}
            stress_pts = str_map.get(q_stress, 8) + (4 if q_mindfulness else 0)

            scr_pts = 14 if "Screen-free" in q_screen else (8 if "Phone use" in q_screen else 4)

            total_score = max(10, min(100, s_pts + nutr_pts + act_pts + hyg_pts + stress_pts + scr_pts))
            
            st.session_state.health_score_data = {
                "total": total_score,
                "sleep": int((s_pts / 18) * 100),
                "nutrition": int((nutr_pts / 18) * 100),
                "activity": int((act_pts / 18) * 100),
                "hygiene": int((hyg_pts / 16) * 100),
                "stress": int((stress_pts / 16) * 100),
                "screen": int((scr_pts / 14) * 100),
            }

    # Render Animated Score Display if available
    if st.session_state.health_score_data:
        score = st.session_state.health_score_data["total"]
        deg = int((score / 100) * 360)

        tier_title = "🌟 Optimal Wellness Master" if score >= 85 else ("💪 Strong Awareness & Consistency" if score >= 70 else ("🌱 Growth Zone (Building Habits)" if score >= 50 else "⚠️ Needs Attention & Focus"))
        tier_desc = (
            "Outstanding! Your habits demonstrate excellent health awareness and consistent preventive lifestyle choices."
            if score >= 85 else
            "Great job! You have strong foundational awareness with a few targeted areas for refinement."
            if score >= 70 else
            "You are in the habit-building phase. Implementing small micro-adjustments will yield major health gains."
        )

        st.markdown(
            f"""
            <div class="score-hero-card">
                <div class="score-circle-wrapper" style="--score-deg: {deg}deg;">
                    <div class="score-circle-inner">
                        <div class="score-number">{score}</div>
                        <div class="score-denom">OUT OF 100</div>
                    </div>
                </div>
                <h3 style="margin: 0; color: #ccfbf1; font-size: 1.4rem;">{tier_title}</h3>
                <p style="margin: 0.4rem auto 0 auto; max-width: 550px; font-size: 0.88rem; color: #e0f2fe; line-height: 1.45;">
                    {tier_desc}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 6 Pillars Breakdown
        st.markdown("### 📊 6 Pillars Breakdown")
        col_b1, col_b2 = st.columns(2)
        
        pillars = [
            ("😴 Sleep & Circadian Health", st.session_state.health_score_data["sleep"], "#0284c7"),
            ("🥗 Nutrition & Hydration", st.session_state.health_score_data["nutrition"], "#0d9488"),
            ("🏃 Physical Movement", st.session_state.health_score_data["activity"], "#10b981"),
            ("🧼 Hygiene & Prevention", st.session_state.health_score_data["hygiene"], "#6366f1"),
            ("🧠 Stress & Mental Well-being", st.session_state.health_score_data["stress"], "#8b5cf6"),
            ("📱 Screen & Digital Hygiene", st.session_state.health_score_data["screen"], "#ec4899"),
        ]

        for idx, (p_name, p_val, p_color) in enumerate(pillars):
            target_col = col_b1 if idx % 2 == 0 else col_b2
            with target_col:
                st.markdown(
                    f"""
                    <div class="pillar-bar-container">
                        <div class="pillar-header">
                            <span>{p_name}</span>
                            <span style="color: {p_color};">{p_val}%</span>
                        </div>
                        <div class="pillar-bar-bg">
                            <div class="pillar-bar-fill" style="width: {p_val}%; background: {p_color};"></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        if st.button("✨ Ask Gemini for My Personalized Action Plan →", type="primary", use_container_width=True):
            st.session_state.pending_prompt = (
                f"I just scored {score}/100 on my SOU HEALTHCARE Awareness Assessment. "
                f"Here is my pillar breakdown:\n"
                f"- Sleep: {st.session_state.health_score_data['sleep']}%\n"
                f"- Nutrition & Hydration: {st.session_state.health_score_data['nutrition']}%\n"
                f"- Physical Activity: {st.session_state.health_score_data['activity']}%\n"
                f"- Hygiene & Prevention: {st.session_state.health_score_data['hygiene']}%\n"
                f"- Stress Management: {st.session_state.health_score_data['stress']}%\n"
                f"- Screen Habits: {st.session_state.health_score_data['screen']}%\n\n"
                f"Please provide 3 high-impact, easy-to-implement micro-habits tailored to my lowest scoring pillars to help me improve my overall health awareness and daily wellness."
            )
            st.session_state.active_tab = "💬 Chat Assistant"
            st.rerun()

# ------------------------------------------------------------------------------
# TAB B: MYTH BUSTER AI 🧙‍♂️
# ------------------------------------------------------------------------------
elif st.session_state.active_tab == "🧙‍♂️ Myth Buster AI":
    st.markdown("## 🧙‍♂️ Myth Buster AI: Science vs. Fiction")
    st.write(
        "Misinformation can harm health. SOU HEALTHCARE's Myth Buster AI verifies common wellness claims using **peer-reviewed clinical consensus and global health standards**."
    )

    st.markdown("### 🔍 Click to Debunk Popular Health Myths")
    
    popular_myths = [
        {
            "myth": "Drinking ice-cold water freezes digestive fats and slows metabolism.",
            "verdict": "BUSTED",
            "tag_class": "myth-tag-busted",
            "prompt": "Debunk the myth: Does drinking ice-cold water freeze fats in your stomach and slow metabolism?",
        },
        {
            "myth": "Detox teas and 3-day juice cleanses purge built-up toxins from your liver.",
            "verdict": "BUSTED",
            "tag_class": "myth-tag-busted",
            "prompt": "Debunk the myth: Do commercial detox teas and juice cleanses actually detoxify liver or kidneys?",
        },
        {
            "myth": "Cracking your knuckle joints causes long-term arthritis.",
            "verdict": "BUSTED",
            "tag_class": "myth-tag-busted",
            "prompt": "Debunk the myth: Does cracking your knuckles lead to arthritis or joint damage?",
        },
        {
            "myth": "Antibiotics are required to treat severe common colds and flu.",
            "verdict": "DANGEROUS MYTH",
            "tag_class": "myth-tag-busted",
            "prompt": "Explain why antibiotics are ineffective against viral colds and flu, and the danger of antibiotic resistance.",
        },
        {
            "myth": "Eating carbohydrates after 6:00 PM automatically turns into stored body fat.",
            "verdict": "BUSTED",
            "tag_class": "myth-tag-busted",
            "prompt": "Debunk the myth: Does eating carbs after 6 PM automatically make you gain body fat?",
        },
        {
            "myth": "Taking vitamin C supplements completely prevents catching viral colds.",
            "verdict": "PARTIALLY ACCURATE",
            "tag_class": "myth-tag-partial",
            "prompt": "Fact-check: Does megadosing Vitamin C prevent the common cold, or what is its true biological role?",
        },
    ]

    col_m1, col_m2 = st.columns(2)
    for idx, item in enumerate(popular_myths):
        target_col = col_m1 if idx % 2 == 0 else col_m2
        with target_col:
            st.markdown(
                f"""
                <div class="myth-card">
                    <span class="myth-tag {item['tag_class']}">{item['verdict']}</span>
                    <div style="font-weight: 700; font-size: 0.92rem; color: #0f172a; margin-bottom: 0.35rem;">
                        "{item['myth']}"
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"🔍 Debunk with AI →", key=f"btn_myth_{idx}", use_container_width=True):
                st.session_state.pending_prompt = item["prompt"]
                st.session_state.active_tab = "💬 Chat Assistant"
                st.rerun()

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Custom Myth Checker Input
    st.markdown("### 🧪 Test ANY Health Belief or Viral Claim")
    custom_myth = st.text_input(
        "Enter any health claim heard on TikTok, Instagram, WhatsApp, or family conversations:",
        placeholder="e.g., 'Does putting onions in socks cure a fever?' or 'Does eating carrots give night vision?'",
    )
    if st.button("🧙‍♂️ Bust This Myth with AI", type="primary", use_container_width=True):
        if custom_myth.strip():
            st.session_state.pending_prompt = (
                f"Please act as SOU HEALTHCARE Myth Buster AI. Fact-check and scientifically evaluate this claim:\n"
                f"Claim: '{custom_myth}'\n\n"
                f"Structure your response with:\n"
                f"1. 🏷️ Verdict: (❌ BUSTED MYTH / ⚠️ PARTIALLY ACCURATE / ✅ SCIENTIFICALLY VALID)\n"
                f"2. 🔬 Biological & Scientific Reality (what really happens in the human body)\n"
                f"3. 🛡️ Safe, Evidence-Based Takeaway for Everyday Life."
            )
            st.session_state.active_tab = "💬 Chat Assistant"
            st.rerun()

# ------------------------------------------------------------------------------
# TAB C: DAILY WELLNESS CHECK-IN
# ------------------------------------------------------------------------------
elif st.session_state.active_tab == "🌿 Daily Wellness Check-In":
    st.markdown("## 🌿 Daily Wellness Reflection")
    st.caption("Log your daily wellness factors for holistic self-awareness. This is educational and not a medical evaluation.")
    
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            sleep_hours = st.slider("😴 Sleep last night (hours)", min_value=0.0, max_value=12.0, value=7.5, step=0.5)
            sleep_quality = st.selectbox("🛌 Sleep Quality", ["Restful & Deep", "Adequate", "Restless", "Poor / Insufficient"])
            water_intake = st.slider("💧 Water intake today (glasses)", min_value=0, max_value=15, value=7)
        
        with c2:
            activity = st.selectbox(
                "🏃 Physical Movement",
                ["Moderate workout (30+ mins)", "Brisk walking / Light movement", "Mostly sedentary today", "Intense sports/training"]
            )
            stress_level = st.select_slider("🧠 Stress Level Today", options=[1, 2, 3, 4, 5], value=2, format_func=lambda x: f"Level {x}/5")
            mood = st.selectbox("😊 Overall Mood", ["😊 Joyful / Motivated", "🙂 Calm & Content", "😐 Neutral / Fine", "😔 Low / Tired", "😫 Stressed / Overwhelmed"])

        if st.button("🌱 Generate My Wellness Reflection", type="primary", use_container_width=True):
            checkin_prompt = (
                f"I just completed my Daily Wellness Check-In with SOU HEALTHCARE:\n"
                f"- Sleep: {sleep_hours} hours ({sleep_quality})\n"
                f"- Hydration: {water_intake} glasses of water\n"
                f"- Physical Activity: {activity}\n"
                f"- Stress Level: {stress_level} out of 5\n"
                f"- Mood: {mood}\n\n"
                f"Please provide an encouraging, supportive, and educational reflection with 2-3 gentle micro-adjustments "
                f"for my day. Emphasize general wellness, avoid medical diagnoses, and remind me of healthy lifestyle balance."
            )
            st.session_state.pending_prompt = checkin_prompt
            st.session_state.active_tab = "💬 Chat Assistant"
            st.rerun()

# ------------------------------------------------------------------------------
# TAB D: CORE CHAT ASSISTANT & WELCOME HUB
# ------------------------------------------------------------------------------
if st.session_state.active_tab == "💬 Chat Assistant":
    # 1. Welcome Cards when no messages in active session
    if len(current_chat["messages"]) == 0:
        st.markdown("### 👋 How can SOU HEALTHCARE support your well-being today?")
        st.write("Choose an essential health awareness topic below, speak directly with your voice, or type any question in the taskbar.")

        action_cards = [
            {
                "icon": "🥗",
                "title": "Healthy Lifestyle",
                "desc": "Discover sustainable daily habits, wholesome routines, and balanced lifestyle choices.",
                "prompt": "How can I build sustainable, healthy daily habits that stick?",
            },
            {
                "icon": "🍎",
                "title": "Nutrition Awareness",
                "desc": "Understand balanced eating patterns, mindful hydration, and wholesome nutrition.",
                "prompt": "Give me practical, evidence-based tips for balanced and healthy nutrition.",
            },
            {
                "icon": "🏃",
                "title": "Fitness & Activity",
                "desc": "Explore safe daily physical movement, cardiovascular health, and beginner routines.",
                "prompt": "How can I safely increase my daily physical activity and cardiovascular health?",
            },
            {
                "icon": "😴",
                "title": "Sleep & Wellness",
                "desc": "Master natural sleep hygiene, circadian rhythm support, and restful evening routines.",
                "prompt": "How can I improve my sleep quality and build an effective evening routine?",
            },
            {
                "icon": "🧠",
                "title": "Mental Well-being",
                "desc": "Learn evidence-based stress management, relaxation breathing, and emotional self-care.",
                "prompt": "What are effective, evidence-based techniques for managing everyday stress and mental well-being?",
            },
            {
                "icon": "🧼",
                "title": "Prevention & Hygiene",
                "desc": "Protect your immune system with preventive health measures and proper hygiene habits.",
                "prompt": "What are the most effective daily hygiene and preventive habits for staying healthy?",
            },
        ]

        # 3x2 Grid
        col_grid1, col_grid2, col_grid3 = st.columns(3)
        cols = [col_grid1, col_grid2, col_grid3]

        for idx, card in enumerate(action_cards):
            with cols[idx % 3]:
                st.markdown(
                    f"""
                    <div class="card-container">
                        <div>
                            <div class="card-icon">{card['icon']}</div>
                            <div class="card-title">{card['title']}</div>
                            <div class="card-desc">{card['desc']}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(f"Explore {card['title']} →", key=f"btn_card_{idx}", use_container_width=True):
                    st.session_state.pending_prompt = card["prompt"]
                    st.rerun()

    # 2. Display Chat Messages in Active Session
    for idx, msg in enumerate(current_chat["messages"]):
        if msg["role"] == "user":
            with st.chat_message("user"):
                if msg.get("files"):
                    for fname in msg["files"]:
                        st.markdown(f'<div class="file-badge">📎 {fname}</div>', unsafe_allow_html=True)
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant", avatar="🩺"):
                st.markdown(msg["content"])
                # Voice Audio Playback button for assistant responses
                if TTS_AVAILABLE:
                    col_tts1, col_tts2 = st.columns([1, 4])
                    with col_tts1:
                        if st.button("🔊 Voice Listen", key=f"tts_btn_{idx}", help="Listen to audio narration of this response"):
                            audio_bytes = generate_speech_audio(msg["content"])
                            if audio_bytes:
                                st.audio(audio_bytes, format="audio/mp3", autoplay=True)

    # ==============================================================================
    # 11. RESPONSE GENERATION ENGINE (GEMINI STREAMING + TYPING INDICATOR)
    # ==============================================================================
    def generate_ai_response(prompt_text: str, attached_files=None):
        """Sends prompt and attachments to Gemini API with real-time streaming and typing animation."""
        
        file_names = [getattr(f, "name", "Attached File") for f in attached_files] if attached_files else []
        
        # Append user message to active session
        current_chat["messages"].append({
            "role": "user",
            "content": prompt_text,
            "files": file_names
        })

        # Dynamically auto-title the session based on the first prompt
        if len(current_chat["messages"]) == 1 or current_chat["title"].startswith("Consultation #") or current_chat["title"] == "Welcome Consultation":
            words = prompt_text.strip().split()
            current_chat["title"] = " ".join(words[:4]) + ("..." if len(words) > 4 else "")

        with st.chat_message("user"):
            if file_names:
                for fname in file_names:
                    st.markdown(f'<div class="file-badge">📎 Attached: {fname}</div>', unsafe_allow_html=True)
            st.markdown(prompt_text)

        # Build Gemini message contents
        system_instruction = build_system_instruction(st.session_state.response_mode)
        
        # We maintain a sliding window of the last 10 messages for lightning-fast latency
        history_window = current_chat["messages"][-10:]
        gemini_contents = []
        
        for idx, m in enumerate(history_window):
            role = "user" if m["role"] == "user" else "model"
            parts = [types.Part.from_text(text=m["content"])]
            
            # If this is the current active prompt and there are attached files:
            if idx == len(history_window) - 1 and attached_files:
                for f in attached_files:
                    try:
                        f.seek(0)
                        file_bytes = f.read()
                        mime = getattr(f, "type", "application/octet-stream") or "application/octet-stream"
                        parts.append(types.Part.from_bytes(data=file_bytes, mime_type=mime))
                    except Exception:
                        pass
                    
            gemini_contents.append(types.Content(role=role, parts=parts))

        # Stream assistant response in real-time with typing indicator
        with st.chat_message("assistant", avatar="🩺"):
            typing_placeholder = st.empty()
            typing_placeholder.markdown(
                """
                <div class="typing-container">
                    <div class="typing-text">
                        <span>🩺 SOU HEALTHCARE is typing</span>
                        <div class="typing-dots">
                            <span class="typing-dot"></span>
                            <span class="typing-dot"></span>
                            <span class="typing-dot"></span>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            response_text = ""
            success = False
            
            # Token limits tuned for rapid generation speed
            max_tokens_map = {
                "⚡ Quick Answer": 350,
                "🌱 Simple Language": 500,
                "📚 Detailed Explanation": 950,
            }
            token_limit = max_tokens_map.get(st.session_state.response_mode, 450)

            # Try primary model first, followed by fast fallbacks
            models_to_try = [PRIMARY_MODEL] + [m for m in FALLBACK_MODELS if m != PRIMARY_MODEL]
            
            for model_candidate in models_to_try:
                try:
                    config = types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
                        temperature=0.3,
                        max_output_tokens=token_limit,
                    )
                    
                    def stream_chunks():
                        first_token = True
                        res_stream = client.models.generate_content_stream(
                            model=model_candidate,
                            contents=gemini_contents,
                            config=config,
                        )
                        for chunk in res_stream:
                            if chunk.text:
                                if first_token:
                                    typing_placeholder.empty()
                                    first_token = False
                                yield chunk.text

                    response_text = st.write_stream(stream_chunks())
                    typing_placeholder.empty()
                    if response_text:
                        success = True
                        break
                except errors.APIError as api_err:
                    typing_placeholder.empty()
                    if "429" in str(api_err):
                        st.warning("⚠️ The AI service is temporarily busy. Please wait a few moments and try again.")
                        return
                    elif "400" in str(api_err) or "403" in str(api_err) or "404" in str(api_err):
                        continue
                    else:
                        st.error(f"AI Service notice: {str(api_err)}")
                        return
                except Exception:
                    typing_placeholder.empty()
                    continue

            if not success or not response_text:
                st.error("Unable to connect to the AI service. Please verify your GEMINI_API_KEY in `.env`.")
                return

            current_chat["messages"].append({"role": "model", "content": response_text})

            # Voice Audio player option immediately following response
            if TTS_AVAILABLE:
                audio_bytes = generate_speech_audio(response_text)
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3", autoplay=False)

            # Interactive follow-up suggestion chips
            st.markdown(
                """
                <div style="font-size:0.8rem; font-weight:700; color:#0f766e; margin:0.8rem 0 0.4rem 0;">
                    ✨ What would you like to explore next?
                </div>
                """,
                unsafe_allow_html=True,
            )
            
            col_chip1, col_chip2, col_chip3 = st.columns(3)
            with col_chip1:
                if st.button("🥗 Practical Daily Routines", key=f"chip1_{len(current_chat['messages'])}", use_container_width=True):
                    st.session_state.pending_prompt = "What are 3 practical daily routines to incorporate this into my schedule?"
                    st.rerun()
            with col_chip2:
                if st.button("🛡️ Preventive Self-Care Tips", key=f"chip2_{len(current_chat['messages'])}", use_container_width=True):
                    st.session_state.pending_prompt = "What preventive lifestyle tips can help maintain long-term health in this area?"
                    st.rerun()
            with col_chip3:
                if st.button("🩺 When to Consult a Doctor?", key=f"chip3_{len(current_chat['messages'])}", use_container_width=True):
                    st.session_state.pending_prompt = "What signs or circumstances indicate that someone should consult a medical professional about this?"
                    st.rerun()

    # Handle pending prompts
    if st.session_state.pending_prompt:
        prompt_to_run = st.session_state.pending_prompt
        st.session_state.pending_prompt = None
        generate_ai_response(prompt_to_run)

    # ==============================================================================
    # 12. TASKBAR CHAT INPUT WITH SIDE-POSITIONED MIC BUTTON & AUDIO DOCK
    # ==============================================================================
    
    # Clean Compact Voice Dock on the side (expandable / auto-detecting)
    with st.expander("🎙️ Audio Recording Dock (Optional Alternate Voice Input)", expanded=False):
        taskbar_audio = st.audio_input("Record Voice Query:", key="taskbar_voice_input")
        if taskbar_audio is not None:
            audio_raw = taskbar_audio.getvalue()
            if st.session_state.last_voice_bytes != audio_raw:
                st.session_state.last_voice_bytes = audio_raw
                generate_ai_response(
                    "Here is a voice question regarding health awareness, symptoms, or preventive wellness. Please provide clear educational insights.",
                    attached_files=[taskbar_audio]
                )

    # Main Chat Input with Multimodal File Attachments
    user_input = st.chat_input(
        "💬 Type your question, tap the side 🎙️ mic to speak, or attach files with 📎...",
        accept_file=True,
        file_type=["png", "jpg", "jpeg", "webp", "pdf", "txt", "csv"]
    )

    # In-Bar Browser Web Speech Recognition JavaScript Injector (Positioned cleanly on the right side next to Send)
    components.html(
        """
        <script>
        (function() {
            const doc = window.parent.document;
            
            // Permanently force Light Mode across all browser engines
            function enforceLightMode() {
                try {
                    if (doc.documentElement) {
                        doc.documentElement.setAttribute('data-theme', 'light');
                        doc.documentElement.style.colorScheme = 'light';
                    }
                    if (doc.body) {
                        doc.body.setAttribute('data-theme', 'light');
                        doc.body.style.colorScheme = 'light';
                    }
                    let metaScheme = doc.querySelector('meta[name="color-scheme"]');
                    if (!metaScheme) {
                        metaScheme = doc.createElement('meta');
                        metaScheme.name = 'color-scheme';
                        metaScheme.content = 'light only';
                        if (doc.head) doc.head.appendChild(metaScheme);
                    } else {
                        metaScheme.content = 'light only';
                    }
                } catch (e) {}
            }
            enforceLightMode();
            setInterval(enforceLightMode, 400);

            function injectVoiceMicToTaskbar() {
                const chatInput = doc.querySelector('div[data-testid="stChatInput"]');
                if (!chatInput) return;
                
                // Check if already injected
                let micBtn = doc.getElementById('sou-taskbar-mic-btn');
                
                if (!micBtn) {
                    micBtn = doc.createElement('button');
                    micBtn.id = 'sou-taskbar-mic-btn';
                    micBtn.type = 'button';
                    micBtn.title = '🎙️ Click to Speak (Live Voice Input)';
                    micBtn.innerHTML = `
                        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path>
                            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                            <line x1="12" x2="12" y1="19" y2="22"></line>
                        </svg>
                    `;
                    micBtn.style.cssText = `
                        background: linear-gradient(135deg, #0d9488 0%, #0284c7 100%);
                        color: white;
                        border: none;
                        border-radius: 50%;
                        width: 35px;
                        height: 35px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        cursor: pointer;
                        margin-left: 6px;
                        margin-right: 4px;
                        flex-shrink: 0;
                        transition: all 0.22s ease;
                        box-shadow: 0 4px 12px rgba(13, 148, 136, 0.35);
                        z-index: 999;
                    `;

                    // Position cleanly on the right side right before the Send button
                    const submitBtn = chatInput.querySelector('button');
                    if (submitBtn && submitBtn.parentNode) {
                        submitBtn.parentNode.insertBefore(micBtn, submitBtn);
                    } else {
                        const innerContainer = chatInput.querySelector('div') || chatInput;
                        innerContainer.appendChild(micBtn);
                    }

                    // Setup Speech Recognition
                    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition || window.parent.SpeechRecognition || window.parent.webkitSpeechRecognition;
                    
                    if (SpeechRecognition) {
                        const recognition = new SpeechRecognition();
                        recognition.continuous = false;
                        recognition.interimResults = true;
                        recognition.lang = 'en-US';

                        let isListening = false;

                        micBtn.onclick = function(e) {
                            e.preventDefault();
                            e.stopPropagation();
                            if (!isListening) {
                                try {
                                    recognition.start();
                                } catch(err) {
                                    console.log(err);
                                }
                            } else {
                                recognition.stop();
                            }
                        };

                        recognition.onstart = function() {
                            isListening = true;
                            micBtn.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
                            micBtn.style.boxShadow = '0 0 16px rgba(239, 68, 68, 0.85)';
                            micBtn.style.transform = 'scale(1.1)';
                            micBtn.title = '🎙️ Listening... Speak your question now!';
                        };

                        recognition.onresult = function(event) {
                            let transcript = '';
                            for (let i = event.resultIndex; i < event.results.length; ++i) {
                                transcript += event.results[i][0].transcript;
                            }
                            const textarea = doc.querySelector('div[data-testid="stChatInput"] textarea');
                            if (textarea) {
                                textarea.value = transcript;
                                textarea.dispatchEvent(new Event('input', { bubbles: true }));
                            }
                        };

                        recognition.onend = function() {
                            isListening = false;
                            micBtn.style.background = 'linear-gradient(135deg, #0d9488 0%, #0284c7 100%)';
                            micBtn.style.boxShadow = '0 4px 12px rgba(13, 148, 136, 0.35)';
                            micBtn.style.transform = 'scale(1.0)';
                            micBtn.title = '🎙️ Click to Speak (Live Voice Input)';
                            
                            const textarea = doc.querySelector('div[data-testid="stChatInput"] textarea');
                            if (textarea && textarea.value.trim().length > 0) {
                                textarea.focus();
                            }
                        };

                        recognition.onerror = function(event) {
                            isListening = false;
                            micBtn.style.background = 'linear-gradient(135deg, #0d9488 0%, #0284c7 100%)';
                            micBtn.style.boxShadow = '0 4px 12px rgba(13, 148, 136, 0.35)';
                            micBtn.style.transform = 'scale(1.0)';
                        };
                    }
                }
            }

            injectVoiceMicToTaskbar();
            setInterval(injectVoiceMicToTaskbar, 500);
        })();
        </script>
        """,
        height=0,
        width=0,
    )

    if user_input:
        prompt_text = ""
        attached_files = []
        
        if isinstance(user_input, str):
            prompt_text = user_input
        elif hasattr(user_input, "text"):
            prompt_text = user_input.text or ""
            attached_files = getattr(user_input, "files", []) or []
        elif isinstance(user_input, dict):
            prompt_text = user_input.get("text", "")
            attached_files = user_input.get("files", [])
            
        if not prompt_text and attached_files:
            prompt_text = "Please review this attached health document/image and provide general health awareness, educational explanations, and wellness context."

        generate_ai_response(prompt_text, attached_files=attached_files)

    st.markdown(
        """
        <div style="text-align: center; font-size: 0.74rem; color: #64748b; margin-top: 0.3rem;">
            ✨ <strong>SOU HEALTHCARE AI</strong> • Powered by Gemini 3.5 Flash • Health Awareness & Prevention • Voice & Multimodal 📎
        </div>
        """,
        unsafe_allow_html=True,
    )

# ==============================================================================
# 13. SUBTLE PERSISTENT HEALTHCARE DISCLAIMER
# ==============================================================================
st.markdown(
    """
    <div class="disclaimer-banner">
        <strong>🩺 Health Awareness Disclaimer:</strong> SOU HEALTHCARE is an educational health awareness platform supporting UN Sustainable Development Goal 3 (Good Health & Well-being). It does not provide medical diagnoses, treatment plans, prescriptions, or emergency care. For acute illness, diagnosis, or emergency situations, please consult a qualified healthcare professional or contact local emergency services immediately.
    </div>
    """,
    unsafe_allow_html=True,
)
