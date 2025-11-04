# app.py
# --- Minimal Chatbot with Messaging Logic ---
import requests
import streamlit as st

# UCANBLEHUB ESSENTIAL NEVER DELETE OR CHANGE
from config import BACKEND_URL
# UCANBLEHUB ESSENTIAL NEVER DELETE OR CHANGE
from utils import send_message

st.set_page_config(page_title="Simple Chatbot", layout="wide")

# --- State Initialization ---
if "history" not in st.session_state:
    st.session_state.history = []
if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None
if "session" not in st.session_state:
    st.session_state.session = requests.Session()

# --- Custom CSS ---
st.markdown("""
<style>
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #2b313e;
        margin-left: 20%;
    }
    .ai-message {
        background-color: #1e2530;
        margin-right: 20%;
    }
    .message-label {
        font-weight: bold;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
    }
    .message-content {
        font-size: 1rem;
        white-space: pre-wrap;
    }
    .stForm {
        border: none;
    }
</style>
""", unsafe_allow_html=True)

# --- Main Chat Interface ---
st.title("Chatbot")

# Chat history display
chat_container = st.container()
with chat_container:
    for msg in st.session_state.history:
        if msg["sender"] == "You":
            if msg["type"] == "image":
                st.image(msg["content"], width=300)
            else:
                st.markdown(f"""
                <div class="chat-message user-message">
                    <div class="message-label">You</div>
                    <div class="message-content">{msg["content"]}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-message ai-message">
                <div class="message-label">AI</div>
                <div class="message-content">{msg["content"]}</div>
            </div>
            """, unsafe_allow_html=True)

st.divider()

# Image upload section
col1, col2 = st.columns([3, 1])

with col1:
    uploaded_file = st.file_uploader(
        "Upload an image (optional):", 
        type=["jpg", "jpeg", "png"],
        key="file_uploader"
    )

if uploaded_file:
    st.image(uploaded_file, caption="Image Preview", width=250)
    st.session_state.uploaded_image = uploaded_file
    
    if st.button("Clear Image", key="clear_img_btn"):
        st.session_state.uploaded_image = None
        uploaded_file = None
        st.rerun()

# Message input form
with st.form(key="message_form", clear_on_submit=True):
    user_input = st.text_area(
        "Message:", 
        placeholder="Type a message and press Ctrl+Enter to send",
        height=100,
        key="text_input"
    )
    
    col_btn1, col_btn2 = st.columns([5, 1])
    
    with col_btn1:
        submit_button = st.form_submit_button("Send", type="primary", use_container_width=True)
    
    with col_btn2:
        clear_button = st.form_submit_button("Clear", use_container_width=True)
    
    if clear_button:
        st.session_state.history = []
        st.session_state.uploaded_image = None
        st.rerun()
    
    if submit_button:
        # Check if there's content to send
        has_text = user_input and user_input.strip()
        has_image = st.session_state.uploaded_image is not None
        
        if has_text or has_image:
            # Determine if sending with image or text only
            if has_image:
                # Add image to history
                st.session_state.history.append({
                    "type": "image", 
                    "sender": "You", 
                    "content": st.session_state.uploaded_image
                })
                
                # Add text prompt to history
                prompt = user_input.strip() if has_text else "What's in this image?"
                st.session_state.history.append({
                    "type": "text", 
                    "sender": "You", 
                    "content": prompt
                })
                
                # Send to backend
                with st.spinner("Processing..."):
                    assistant_message, error = send_message(
                        st.session_state.session, 
                        BACKEND_URL + "/chat", 
                        prompt, 
                        st.session_state.uploaded_image
                    )
                
                # Clear uploaded image after sending
                st.session_state.uploaded_image = None
                
            else:
                # Text only
                st.session_state.history.append({
                    "type": "text", 
                    "sender": "You", 
                    "content": user_input
                })
                
                with st.spinner("Thinking..."):
                    assistant_message, error = send_message(
                        st.session_state.session, 
                        BACKEND_URL + "/chat", 
                        user_input
                    )
            
            # Add AI response
            if error:
                st.error(error)
            elif assistant_message:
                st.session_state.history.append({
                    "type": "text", 
                    "sender": "AI", 
                    "content": assistant_message
                })
            
            st.rerun()