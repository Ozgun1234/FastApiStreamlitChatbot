import os
import json
import time
import requests
import streamlit as st
from typing import List, Dict, Any

# 🔧 Streamlit first-call rule
st.set_page_config(page_title="Gemini Chat", layout="centered")

# WebSocket headers (Streamlit private API) – güvenli yakalama
try:
    from streamlit.web.server.websocket_headers import _get_websocket_headers
    ws_headers: Dict[str, str] = _get_websocket_headers() or {}
except Exception:
    ws_headers = {}

"""
Gemini Chat – Streamlit UI (Polished)
- Cookie & auth header'ları WebSocket üzerinden okuyup backend'e forward eder
- Nginx/Laravel billing zincirine uyumludur
- Non-stream ve stream modlarını destekler (text/plain chunk)
- Chat geçmişi, system prompt, temperature ve token limiti ayarları
- Retry, Clear Chat, transcript indirme, latency ölçümü

ENV VARS
- BACKEND_API_URL (default: http://nginx/api/ai-ui-proxy/gemini_chat_backend/chat)

Backend beklenen response formatı:
{
  "status": 200,
  "message": "...assistant reply..."
}
"""

# ---------- Config ----------
BACKEND_API_URL = os.getenv(
    "BACKEND_API_URL",
    "http://localhost:8002/chat"
)

# ---------- Cookie & Header Extraction (WebSocket) ----------
raw_cookie = ws_headers.get("Cookie", "")

cookie_dict: Dict[str, str] = {}
for kv in raw_cookie.split(";"):
    if "=" in kv:
        k, v = kv.strip().split("=", 1)
        cookie_dict[k] = v

USER_ID = cookie_dict.get("uc_user")
SESSION_ID = cookie_dict.get("uc_session")
PLAN = cookie_dict.get("uc_plan")
BALANCE = cookie_dict.get("uc_balance")
ACCESS_TOKEN = cookie_dict.get("access_token")

# Kimlik: yumuşak uyarı
if not USER_ID:
    st.warning("Kimlik bilgisi (uc_user) bulunamadı. Giriş yapmadıysan bazı işlemler reddedilebilir.")

# ---------- State ----------
initial_history: List[Dict[str, str]] = [
    {"role": "system", "content": "You are a helpful assistant that answers in short and clear sentences."}
]
st.session_state.history = initial_history
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = st.session_state.history[0]["content"]
if "last_request_headers" not in st.session_state:
    st.session_state.last_request_headers = {}
if "last_request_body" not in st.session_state:
    st.session_state.last_request_body = {}
if "last_assistant" not in st.session_state:
    st.session_state.last_assistant = ""

# ---------- Sidebar Settings ----------
with st.sidebar:
    st.header("⚙️ Ayarlar")
    model = st.selectbox("Model", ["gemini-1.5-flash", "gemini-1.5-pro"], index=0)
    temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)
    max_output_tokens = st.slider("Max Output Tokens", 64, 2048, 512, 64)
    stream = st.toggle("Stream Mode", value=True)

    st.divider()
    st.subheader("🧠 System Prompt")
    new_sys = st.text_area("", value=st.session_state.system_prompt, height=100)
    col_sp1, col_sp2 = st.columns(2)
    if col_sp1.button("System prompt'u uygula"):
        st.session_state.system_prompt = new_sys
        # history'deki ilk system mesajını güncelle
        found = False
        for m in st.session_state.history:
            if m.get("role") == "system":
                m["content"] = st.session_state.system_prompt
                found = True
                break
        if not found:
            st.session_state.history.insert(0, {"role": "system", "content": st.session_state.system_prompt})
        st.toast("System prompt güncellendi.")
    if col_sp2.button("Clear chat"):
        st.session_state.history = [{"role": "system", "content": st.session_state.system_prompt}]
        st.session_state.last_assistant = ""
        st.toast("Sohbet temizlendi.")

    st.divider()
    st.subheader("🔐 Kimlik Özeti")
    st.write(f"**User**: {USER_ID or '-'}")
    st.write(f"**Plan**: {PLAN or '-'} | **Bakiye**: {BALANCE or '-'}")
    if st.checkbox("WebSocket Headerlarını Göster"):
        st.code(json.dumps(ws_headers, indent=2))
    if st.checkbox("Cookie Dict Göster"):
        st.code(json.dumps(cookie_dict, indent=2))

# ---------- Title ----------
st.title("💬 Gemini Chat")
st.caption("Cookie forward + streaming destekli chatbot UI")

# ---------- Chat Display ----------
for msg in st.session_state.history:
    role = msg.get("role")
    content = msg.get("content", "")
    if role == "user":
        with st.chat_message("user"):
            st.markdown(content)
    elif role == "assistant":
        with st.chat_message("assistant"):
            st.markdown(content)
    elif role == "system":
        st.info(f"**System:** {content}")

# ---------- User Input ----------
user_input = st.chat_input("Mesajınızı yazın…")

# ---------- Helpers ----------
def build_forward_headers() -> Dict[str, str]:
    return {
        "X-UC-User": USER_ID or "",
        "X-UC-Session": SESSION_ID or "",
        "X-UC-Plan": PLAN or "",
        "X-UC-Balance": BALANCE or "",
        "X-Client": "streamlit-ui"
    }


def send_non_stream(payload: Dict[str, Any]) -> Dict[str, Any]:
    headers = build_forward_headers()
    cookies = {"access_token": ACCESS_TOKEN} if ACCESS_TOKEN else {}
    t0 = time.perf_counter()
    resp = requests.post(BACKEND_API_URL, json=payload, headers=headers, cookies=cookies, timeout=60)
    latency_ms = int((time.perf_counter() - t0) * 1000)

    st.session_state.last_request_headers = dict(resp.request.headers)
    st.session_state.last_request_body = payload

    try:
        body = resp.json()
    except Exception:
        body = {"status": resp.status_code, "message": resp.text}

    body["latency_ms"] = latency_ms
    return body


def send_stream(payload: Dict[str, Any]) -> Dict[str, Any]:
    headers = build_forward_headers()
    cookies = {"access_token": ACCESS_TOKEN} if ACCESS_TOKEN else {}

    t0 = time.perf_counter()
    with requests.post(BACKEND_API_URL, json=payload, headers=headers, cookies=cookies, stream=True) as resp:
        st.session_state.last_request_headers = dict(resp.request.headers)
        st.session_state.last_request_body = payload

        if resp.status_code != 200:
            # Hata durumunda JSON dene, değilse plain
            try:
                body = resp.json()
            except Exception:
                body = {"status": resp.status_code, "message": resp.text}
            body["latency_ms"] = int((time.perf_counter() - t0) * 1000)
            return body

        assistant_placeholder = st.empty()
        collected = ""
        # iter_lines, unicode ve satır bölmeleri için daha güvenli
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            collected += line
            assistant_placeholder.markdown(collected)
        return {"status": 200, "message": collected, "latency_ms": int((time.perf_counter() - t0) * 1000)}


# ---------- Send & Render ----------
if user_input:
    st.session_state.history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    payload = {
        "messages": st.session_state.history,
        "temperature": float(temperature),
        "max_output_tokens": int(max_output_tokens),
        "stream": bool(stream),
        "model": model
    }

    with st.chat_message("assistant"):
        if stream:
            result = send_stream(payload)
        else:
            with st.spinner("Yanıt hazırlanıyor…"):
                result = send_non_stream(payload)
            st.markdown(result.get("message", ""))

    status = result.get("status", 500)
    message = result.get("message", "")
    latency_ms = result.get("latency_ms")

    if status == 200 and message:
        st.session_state.history.append({"role": "assistant", "content": message})
        st.session_state.last_assistant = message
        if latency_ms is not None:
            st.caption(f"⏱️ Latency: {latency_ms} ms")
    else:
        st.error(f"Error {status}: {message}")

# ---------- Footer Tools ----------
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("↻ Yeniden sor (son mesaj)") and st.session_state.history:
        # Son user mesajını bul ve yeniden gönder
        for m in reversed(st.session_state.history):
            if m.get("role") == "user":
                st.session_state.history = [st.session_state.history[0]] + [m]
                st.experimental_rerun()
        st.warning("Yeniden sorulacak bir kullanıcı mesajı bulunamadı.")
with col2:
    if st.session_state.last_assistant:
        st.download_button(
            "⬇️ Son yanıtı indir",
            data=st.session_state.last_assistant.encode("utf-8"),
            file_name="assistant_reply.txt",
            mime="text/plain"
        )
with col3:
    if st.button("📄 Transcript indir"):
        transcript = "\n".join([
            f"{m['role']}: {m['content']}" for m in st.session_state.history
        ])
        st.download_button(
            label="Transcript'i indir",
                            data=transcript.encode("utf-8"),
                            file_name="transcript.txt",
                            mime="text/plain",
                            key="dl_transcript"
                        )

# ---------- Debug / Dev Panel ----------
st.divider()
st.subheader("🔍 Debug Panel (geliştiriciye yönelik)")
colA, colB = st.columns(2)
with colA:
    st.caption("Son gönderilen request headers")
    if st.session_state.last_request_headers:
        st.code(json.dumps(st.session_state.last_request_headers, indent=2))
    else:
        st.write("—")
with colB:
    st.caption("Son gönderilen request body")
    if st.session_state.last_request_body:
        st.code(json.dumps(st.session_state.last_request_body, indent=2))
    else:
        st.write("—")

st.caption(f"Backend: {BACKEND_API_URL}")
