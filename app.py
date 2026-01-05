import streamlit as st
import json
import random
import pandas as pd
import os
import time
from openai import OpenAI
from dotenv import load_dotenv
from pyngrok import ngrok

# Load environment variables
load_dotenv()

# --- Cấu hình Ngrok ---
def setup_ngrok():
    # Lấy Auth Token từ biến môi trường
    ngrok_auth_token = os.getenv("NGROK_AUTH_TOKEN")
    if ngrok_auth_token:
        ngrok.set_auth_token(ngrok_auth_token)
    
    try:
        tunnels = ngrok.get_tunnels()
        if not tunnels:
            public_url = ngrok.connect(8501).public_url
            print(f"🚀 Public URL: {public_url}")
        else:
            print(f"🚀 Public URL: {tunnels[0].public_url}")
    except Exception as e:
        print(f"Ngrok error: {e}")

setup_ngrok()

# --- Cấu hình trang ---
st.set_page_config(
    page_title="FPTU Quy Nhơn Career Chatbot",
    page_icon="🎓",
    layout="centered"
)

# --- CSS Tùy chỉnh (Giao diện Tech & Orange) ---
def local_css():
    st.markdown("""
    <style>
        /* Import Font */
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Roboto:wght@300;400;700&display=swap');

        /* Tổng thể */
        .stApp {
            /* Gradient Xanh Đen Phản Quang (Deep Blue Black with Glow) */
            background: radial-gradient(circle at 50% -10%, #203a43 0%, #0f2027 40%, #000000 100%);
            background-attachment: fixed;
            color: #e0e0e0;
            font-family: 'Roboto', sans-serif;
        }

        /* Tiêu đề chính */
        h1 {
            font-family: 'Orbitron', sans-serif;
            background: -webkit-linear-gradient(45deg, #FF6600, #FF9E00);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 2px;
            text-shadow: 0 0 20px rgba(255, 102, 0, 0.5);
            margin-bottom: 30px;
        }

        /* Header H2, H3 */
        h2, h3 {
            background: -webkit-linear-gradient(45deg, #FF8C00, #FFD700);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            border-left: 5px solid #FF6600;
            padding-left: 15px;
            margin-top: 20px;
            font-family: 'Orbitron', sans-serif;
        }

        /* Form Container */
        [data-testid="stForm"] {
            background: linear-gradient(145deg, rgba(15, 32, 39, 0.8), rgba(32, 58, 67, 0.6));
            border: 1px solid rgba(255, 102, 0, 0.3);
            border-top: 3px solid #FF6600;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(10px);
        }

        /* Câu hỏi */
        .question-text {
            font-size: 1.2rem;
            font-weight: 700;
            color: #FF9E00; /* Cam vàng sáng */
            margin-bottom: 15px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
            background: rgba(0,0,0,0.2);
            padding: 10px 15px;
            border-radius: 8px;
            border-left: 4px solid #FF6600;
        }

        /* Radio Buttons */
        .stRadio > label {
            display: none;
        }

        /* Đảm bảo widget radio chiếm hết chiều rộng */
        [data-testid="stRadio"] {
            width: 100% !important;
        }
        
        /* Container của các lựa chọn */
        div[role="radiogroup"] {
            width: 100% !important;
            background: rgba(255, 255, 255, 0.05);
            padding: 15px 20px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: inset 0 0 20px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
            box-sizing: border-box;
            display: flex;
            flex-direction: row;
            flex-wrap: wrap;
            gap: 20px;
            align-items: center;
        }
        
        div[role="radiogroup"]:hover {
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 102, 0, 0.5);
            box-shadow: 0 0 15px rgba(255, 102, 0, 0.1);
        }

        /* Text của từng lựa chọn */
        div[role="radiogroup"] label p {
            font-size: 17px !important;
            color: #e0e0e0 !important;
            font-weight: 400;
            padding: 5px 0;
            transition: color 0.2s;
        }
        
        div[role="radiogroup"] label:hover p {
            color: #FF6600 !important;
            font-weight: 600;
        }

        /* Buttons (Submit & Reset) */
        .stButton > button {
            background: linear-gradient(90deg, #FF6600, #FF4500);
            color: white !important;
            border: none;
            border-radius: 5px;
            padding: 12px 24px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: all 0.3s ease;
            width: 100%;
            box-shadow: 0 4px 15px rgba(255, 69, 0, 0.3);
            font-family: 'Orbitron', sans-serif;
        }
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(255, 69, 0, 0.5);
            background: linear-gradient(90deg, #FF4500, #FF6600);
        }

        /* Divider */
        hr {
            border-color: #333;
            margin: 20px 0;
        }

        /* Kết quả AI */
        .stMarkdown {
            line-height: 1.6;
        }
        
        /* Spinner */
        .stSpinner > div {
            border-top-color: #FF6600 !important;
        }

        /* Alert/Info/Success Box */
        .stAlert {
            background-color: rgba(255, 102, 0, 0.1);
            border: 1px solid #FF6600;
            color: #e0e0e0;
            border-radius: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- Hàm hỗ trợ ---

@st.cache_data
def load_questions():
    """Đọc file questions.json"""
    try:
        with open('questions.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['questions']
    except FileNotFoundError:
        st.error("Không tìm thấy file questions.json")
        return []

def load_system_prompt():
    """Đọc file System_prompt.txt"""
    try:
        with open('System_prompt.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Bạn là một chuyên gia tư vấn hướng nghiệp."

# --- Giả lập hoặc tích hợp AI ---
def generate_ai_advice(user_answers_text):
    """
    Hàm này sẽ gọi AI để xử lý sử dụng Qwen qua OpenRouter.
    """
    system_prompt = load_system_prompt()
    
    # Lấy API Key từ biến môi trường
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        return "⚠️ **Lỗi:** Chưa tìm thấy `OPENROUTER_API_KEY`. Vui lòng tạo file `.env` và thêm API Key vào."

    try:
        # Cấu hình OpenRouter Client
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "http://localhost:8501",
                "X-Title": "FPTU Career Chatbot",
            }
        )
        
        with st.spinner('Chuyên gia AI đang phân tích hồ sơ của bạn...'):
            completion = client.chat.completions.create(
                model="google/gemini-2.0-flash-exp:free", # Sử dụng model ổn định hơn
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"[CÂU TRẢ LỜI CỦA HỌC SINH]\n{user_answers_text}\n\nLưu ý: Hãy trả lời hoàn toàn bằng Tiếng Việt."
                    }
                ]
            )
            return completion.choices[0].message.content
            
    except Exception as e:
        return f"⚠️ **Đã xảy ra lỗi khi gọi OpenRouter AI:**\n\n{str(e)}"

# --- Quản lý trạng thái (Session State) ---
if 'step' not in st.session_state:
    st.session_state.step = 1 # 1: Quiz, 2: Result

if 'selected_questions' not in st.session_state:
    # Load câu hỏi ngay từ đầu
    all_questions = load_questions()
    if len(all_questions) >= 15:
        st.session_state.selected_questions = random.sample(all_questions, 15)
    else:
        st.session_state.selected_questions = all_questions

if 'user_answers' not in st.session_state:
    st.session_state.user_answers = {}

# --- Giao diện chính ---

st.title("🎓 Hướng Nghiệp FPTU Quy Nhơn AI Campus")

# === BƯỚC 1: LÀM TRẮC NGHIỆM ===
if st.session_state.step == 1:
    st.header("🧩 Trắc nghiệm tính cách & Sở thích")
    st.write("Hãy chọn phương án mô tả đúng nhất về bạn.")
    
    with st.form("quiz_form"):
        answers = {}
        for i, q in enumerate(st.session_state.selected_questions):
            st.markdown(f'<div class="question-text">Câu {i+1}: {q["text"]}</div>', unsafe_allow_html=True)
            # Tạo radio button cho các options
            # Sử dụng key là id câu hỏi để unique
            options = [opt['label'] for opt in q['options']]
            choice = st.radio(
                "Lựa chọn:", 
                options, 
                key=f"q_{q['id']}", 
                index=None,
                label_visibility="collapsed",
                horizontal=True
            )
            answers[q['text']] = choice
            st.markdown("---")
        
        submit_quiz = st.form_submit_button("Xem kết quả tư vấn ✨")
        
        if submit_quiz:
            # Kiểm tra xem đã trả lời hết chưa
            if None in answers.values():
                st.warning("Bạn hãy hoàn thành tất cả các câu hỏi nhé!")
            else:
                st.session_state.user_answers = answers
                st.session_state.step = 2
                st.rerun()

# === BƯỚC 2: KẾT QUẢ TƯ VẤN ===
elif st.session_state.step == 2:
    st.header("🌟 Lời khuyên từ Chuyên gia AI")
    
    if 'advice' not in st.session_state:
        # Tổng hợp câu trả lời thành text để gửi cho AI
        answers_text = ""
        for q_text, ans in st.session_state.user_answers.items():
            answers_text += f"- {q_text}: {ans}\n"
        
        # Gọi hàm AI
        st.session_state.advice = generate_ai_advice(answers_text)
    
    st.markdown(st.session_state.advice)
    
    if st.button("Làm lại từ đầu 🔄"):
        st.session_state.step = 1
        st.session_state.user_answers = {}
        if 'advice' in st.session_state:
            del st.session_state.advice
        # Xóa câu hỏi cũ để random lại
        if 'selected_questions' in st.session_state:
            del st.session_state.selected_questions
        st.rerun()