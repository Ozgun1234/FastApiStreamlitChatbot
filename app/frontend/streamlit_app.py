import requests
import streamlit as st

# UCANBLEHUB ESSENTIAL NEVER DELETE OR CHANGE
from config import BACKEND_BASE_URL
# UCANBLEHUB ESSENTIAL NEVER DELETE OR CHANGE
from utils import send_message

st.set_page_config(page_title="Ucanble Hub Chatbot", page_icon="💡", layout="wide")
# --- State Initialization ---
if "response" not in st.session_state:
    st.session_state.response = None

# UCANBLEHUB ESSENTIAL NEVER DELETE OR CHANGE - Session for HTTP connection pooling and cookie management
if "session" not in st.session_state:
    st.session_state.session = requests.Session()

# --- Main Interface ---

st.title("💡 Ucanble Hub Asistanı")
st.markdown("Merhaba! 'Ucanble Hub' projenin teknik asistanıyım. Sorularını aşağıya yazabilirsin.")

# Sohbet geçmişini saklamak için Streamlit'in session state'ini kullanıyoruz
if "messages" not in st.session_state:
    st.session_state.messages = []

# Geçmiş mesajları görüntüle
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Kullanıcı girişi
if prompt := st.chat_input("Sorunuzu buraya yazın..."):
    # Kullanıcı mesajını geçmişe ekle ve göster
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # FastAPI servisine istek gönder
    try:
        headers = {"Content-Type": "application/json"}
        data = {"message": prompt}
        response, error =  send_message(
            st.session_state.session, 
            "ask",
            prompt  # Message to send from frontend to backend
        )
        print(response, error)
        if error:
            st.error(f"API Hatası: {error}")
            st.session_state.messages.append({"role": "assistant", "content": f"API Hatası: {error}"})
        else:
            assistant_response = response or "Üzgünüm, yanıt alınamadı."
        
        # Asistan yanıtını geçmişe ekle ve göster
        st.session_state.messages.append({"role": "assistant", "content": assistant_response})
        with st.chat_message("assistant"):
            st.markdown(assistant_response)

    except requests.exceptions.ConnectionError:
        st.error("FastAPI servisine bağlanılamadı. Lütfen sunucunun çalıştığından emin olun.")
        st.session_state.messages.append({"role": "assistant", "content": "FastAPI servisine bağlanılamadı."})
    except requests.exceptions.RequestException as e:
        st.error(f"Bir hata oluştu: {e}")
        st.session_state.messages.append({"role": "assistant", "content": f"Bir hata oluştu: {e}"})
