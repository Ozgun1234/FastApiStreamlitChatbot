import requests
import streamlit as st

# UCANBLEHUB ESSENTIAL NEVER DELETE OR CHANGE
from config import BACKEND_BASE_URL
# UCANBLEHUB ESSENTIAL NEVER DELETE OR CHANGE
from utils import send_message

st.set_page_config(page_title="Simple Chatbot", layout="wide")

# --- State Initialization ---
if "response" not in st.session_state:
    st.session_state.response = None

# UCANBLEHUB ESSENTIAL NEVER DELETE OR CHANGE - Session for HTTP connection pooling and cookie management
if "session" not in st.session_state:
    st.session_state.session = requests.Session()

# --- Main Interface ---
st.title("Backend Test")

st.write("Click the button to send a test message to the backend")

if st.button("Test Backend", type="primary"):
    with st.spinner("Sending test message..."):
        message, error = send_message(
            st.session_state.session, 
            "chat",
            "Naber kanka nasılsın?"  # Message to send from frontend to backend
        )
        
        if error:
            st.error(f"Error: {error}")
            st.session_state.response = None
        else:
            st.session_state.response = message
            st.success("Message sent successfully!")

if st.button("Upload Test PDF", type="primary"):
    with st.spinner("Uploading test PDF..."):
        message, error = send_message(
            st.session_state.session, 
            "upload_pdf",
            None  # No message needed for PDF upload in this mock
        )
        
        if error:
            st.error(f"Error: {error}")
            st.session_state.response = None
        else:
            st.session_state.response = message
            st.success("PDF uploaded successfully!")

if st.session_state.response:
    st.divider()
    st.subheader("Backend Response:")
    st.write(st.session_state.response)