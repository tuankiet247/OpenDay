from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
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
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import re

# Load environment variables
load_dotenv()

app = FastAPI()

# --- Google Sheets Setup ---
SCOPES = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
          "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

def get_google_sheet_client():
    # Check for credentials in environment variable first (Best for Render/Cloud)
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    
    if creds_json:
        try:
            creds_dict = json.loads(creds_json)
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            client = gspread.authorize(creds)
            return client
        except Exception as e:
            print(f"⚠️ Error authenticating with GOOGLE_CREDENTIALS_JSON: {e}")
            return None
            
    # Fallback to file (Best for Local Development)
    creds_file = 'env.json' 
    if os.path.exists(creds_file):
        try:
            creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
            client = gspread.authorize(creds)
            return client
        except Exception as e:
            print(f"⚠️ Error authenticating with file '{creds_file}': {e}")
            return None
            
    print(f"⚠️ Warning: neither 'GOOGLE_CREDENTIALS_JSON' env var nor '{creds_file}' found. Google Sheets integration will not work.")
    return None


async def init_sheet_headers():
    """Ensure Google Sheet has correct headers and formatting"""
    client = await asyncio.to_thread(get_google_sheet_client)
    if not client:
        return

    try:
        spreadsheet_url = "https://docs.google.com/spreadsheets/d/1RTxOi5IYcYDL5VaCAiwK9B0T15K5ntSnWLJ4EwD_Rlg/edit?usp=sharing"
        sheet = await asyncio.to_thread(client.open_by_url, spreadsheet_url)
        worksheet = await asyncio.to_thread(sheet.get_worksheet, 0)
        
        target_headers = ["Họ và tên", "Số điện thoại", "Email", "Tỉnh thành", "Trường THPT", "Kết quả AI đề xuất"]
        
        current_headers = await asyncio.to_thread(worksheet.row_values, 1)
        
        if current_headers == target_headers:
            print("✅ Google Sheet already has correct headers.")
        elif not current_headers:
            print("⏳ Google Sheet is empty. Adding headers...")
            await asyncio.to_thread(worksheet.append_row, target_headers)
            print("✅ Headers added.")
        else:
            print("⚠️ Google Sheet has different headers. Updating row 1...")
            # Updating cells logic adapted for async context if needed, but append_row is safer for simple init
            # For robustness, let's just update the first row cells using range
            cell_list = await asyncio.to_thread(worksheet.range, 'A1:F1')
            for i, cell in enumerate(cell_list):
                if i < len(target_headers):
                    cell.value = target_headers[i]
            await asyncio.to_thread(worksheet.update_cells, cell_list)
            print("✅ Headers updated.")

        # Freeze the first row
        await asyncio.to_thread(worksheet.freeze, rows=1)
        print("✅ Header row frozen.")

    except Exception as e:
        print(f"⚠️ Error initializing Google Sheet: {e}")

# Initialize sheet headers on startup
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(init_sheet_headers())

async def save_student_info(student_data):
    """Save student info to Google Sheet"""
    client = await asyncio.to_thread(get_google_sheet_client)
    if not client:
        return

    try:
        # Spreadsheet URL from user
        spreadsheet_url = "https://docs.google.com/spreadsheets/d/1RTxOi5IYcYDL5VaCAiwK9B0T15K5ntSnWLJ4EwD_Rlg/edit?usp=sharing"
        
        # Open the spreadsheet by URL
        try:
            sheet = await asyncio.to_thread(client.open_by_url, spreadsheet_url)
        except gspread.SpreadsheetNotFound:
            print(f"⚠️ Spreadsheet not found. Please check permissions for the URL.")
            return

        # Select the first worksheet
        worksheet = await asyncio.to_thread(sheet.get_worksheet, 0)
        
        # Prepare row data: Name, Phone, Email, Province, School, AI Result
        row = [
            student_data.get('student_name', ''),
            student_data.get('student_phone', ''),
            student_data.get('student_email', ''),
            student_data.get('student_province', ''),
            student_data.get('student_school', ''),
            student_data.get('predicted_major', '')
        ]
        
        # Append row
        await asyncio.to_thread(worksheet.append_row, row)
        print(f"✅ Saved data for {student_data.get('student_name')}")

    except Exception as e:
        print(f"⚠️ Error saving to Google Sheet: {e}")


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
        return data.get('questions', [])
    except FileNotFoundError:
        print("⚠️ Warning: 'questions.json' not found.")
        return []
    except json.JSONDecodeError as e:
        print(f"⚠️ Error decoding 'questions.json': {e}")
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
    system_prompt = await asyncio.to_thread(load_system_prompt)
    
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
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "FPTU Career Chatbot",
            }
        )
        
        max_retries = 5
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                completion = await client.chat.completions.create(
                    model="qwen/qwen3-next-80b-a3b-instruct:free", 
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": f"[CÂU TRẢ LỜI CỦA HỌC SINH]\n{user_answers_text}\n\nLưu ý: Hãy trả lời hoàn toàn bằng Tiếng Việt. Đảm bảo phản hồi đầy đủ cả 4 phần trong định dạng đầu ra."
                        }
                    ],
                    temperature=0.7,
                    top_p=0.9,
                    max_tokens=3000, 
                    extra_body={
                        "repetition_penalty": 1.1
                    }
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
@app.head("/")
async def read_root(request: Request):
    """
    Render landing/registration page.
    """
    return templates.TemplateResponse("register.html", {
        "request": request,
        "version": int(time.time())
    })

@app.post("/quiz", response_class=HTMLResponse)
async def start_quiz(
    request: Request,
    student_name: str = Form(...),
    student_phone: str = Form(...),
    student_email: str = Form(...),
    student_province: str = Form(...),
    student_school: str = Form(...),
    student_cccd: str = Form(...)
):
    """
    Handle registration and show quiz.
    """
    all_questions = await asyncio.to_thread(load_questions)
    # Randomly select 15 questions if available
    if len(all_questions) >= 15:
        selected_questions = random.sample(all_questions, 15)
    else:
        selected_questions = all_questions
    
    # Pass student info to the quiz page
    student_info = {
        "student_name": student_name,
        "student_phone": student_phone,
        "student_email": student_email,
        "student_province": student_province,
        "student_school": student_school,
        "student_cccd": student_cccd
    }

    return templates.TemplateResponse("index.html", {
        "request": request,
        "questions": selected_questions,
        "student_info": student_info,
        "version": int(time.time())
    })

@app.post("/submit", response_class=HTMLResponse)
async def submit_quiz(request: Request):
    form_data = await request.form()
    
    # Reconstruct the questions/answers mapping
    # Since we don't have the question text in the form keys (only IDs like q_1),
    # we need to look up the text.
    # To do this efficiently, let's load all questions and create a map.
    
    all_questions = await asyncio.to_thread(load_questions)
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
            "advice": "⚠️ Bạn chưa trả lời câu hỏi nào. Vui lòng quay lại và hoàn thành bài trắc nghiệm.",
            "version": int(time.time())
        })

    print(f"--- User Answers ---\n{answers_text}\n--------------------")

    # Generate advice
    advice_markdown = await generate_ai_advice(answers_text)
    
    # Extract predicted major
    predicted_major = "Không xác định"
    # Regex to find "### 1. 🌌 KẾT QUẢ ĐỊNH VỊ: [Major Name]"
    match = re.search(r"### 1\. 🌌 KẾT QUẢ ĐỊNH VỊ:\s*(.+)", advice_markdown)
    if match:
        predicted_major = match.group(1).strip()
        # Clean up any potential markdown formatting like bolding
        predicted_major = predicted_major.replace("*", "").strip()

    # Extract student info
    student_data = {
        'student_name': form_data.get('student_name'),
        'student_phone': form_data.get('student_phone'),
        'student_email': form_data.get('student_email'),
        'student_province': form_data.get('student_province'),
        'student_school': form_data.get('student_school'),
        'student_cccd': form_data.get('student_cccd'),
        'predicted_major': predicted_major,
        'career_advice': advice_markdown
    }
    
    # Save to Google Sheet (run in background)
    asyncio.create_task(save_student_info(student_data))

    # Convert Markdown to HTML for display
    advice_html = await asyncio.to_thread(markdown.markdown, advice_markdown)
    
    return templates.TemplateResponse("result.html", {
        "request": request,
        "advice": advice_html,
        "version": int(time.time())
    })

@app.get("/favicon.ico")
async def favicon():
    """Handle favicon requests"""
    favicon_path = os.path.join("static", "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    # Return empty response if favicon doesn't exist
    return HTMLResponse(content="", status_code=204)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
