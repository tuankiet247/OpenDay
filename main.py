from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import random
import os
import time
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv
import markdown

# Load environment variables
load_dotenv()

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# --- Helper Functions ---

def load_questions():
    """Read questions.json"""
    try:
        with open('questions.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['questions']
    except FileNotFoundError:
        return []

def load_system_prompt():
    """Read System_prompt.txt"""
    try:
        with open('System_prompt.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Bạn là một chuyên gia tư vấn hướng nghiệp."

async def generate_ai_advice(user_answers_text):
    """
    Call AI to generate advice using OpenRouter.
    """
    system_prompt = load_system_prompt()
    
    # Get API Key
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        return "⚠️ **Lỗi:** Chưa tìm thấy `OPENROUTER_API_KEY`. Vui lòng tạo file `.env` và thêm API Key vào."

    try:
        # Configure OpenRouter Client
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "FPTU Career Chatbot",
            }
        )
        
        max_retries = 5
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                completion = await client.chat.completions.create(
                    model="google/gemini-2.5-flash-lite", # Thay đổi model sang bản ổn định hơn
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
                print(f"Attempt {attempt+1} failed: {e}") # Log lỗi ra terminal
                if ("429" in str(e) or "400" in str(e)) and attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                raise e
            
    except Exception as e:
        return f"⚠️ **Đã xảy ra lỗi khi gọi OpenRouter AI:**\n\n{str(e)}"

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    all_questions = load_questions()
    # Randomly select 15 questions if available
    if len(all_questions) >= 15:
        selected_questions = random.sample(all_questions, 15)
    else:
        selected_questions = all_questions
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "questions": selected_questions
    })

@app.post("/submit", response_class=HTMLResponse)
async def submit_quiz(request: Request):
    form_data = await request.form()
    
    # Reconstruct the questions/answers mapping
    # Since we don't have the question text in the form keys (only IDs like q_1),
    # we need to look up the text.
    # To do this efficiently, let's load all questions and create a map.
    
    all_questions = load_questions()
    question_map = {str(q['id']): q['text'] for q in all_questions}
    
    answers_text = ""
    for key, value in form_data.items():
        if key.startswith("q_"):
            q_id = key.replace("q_", "")
            if q_id in question_map:
                q_text = question_map[q_id]
                answers_text += f"- {q_text}: {value}\n"
    
    if not answers_text:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "advice": "⚠️ Bạn chưa trả lời câu hỏi nào. Vui lòng quay lại và hoàn thành bài trắc nghiệm."
        })

    print(f"--- User Answers ---\n{answers_text}\n--------------------")

    # Generate advice
    advice_markdown = await generate_ai_advice(answers_text)
    
    # Convert Markdown to HTML for display
    advice_html = markdown.markdown(advice_markdown)
    
    return templates.TemplateResponse("result.html", {
        "request": request,
        "advice": advice_html
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
