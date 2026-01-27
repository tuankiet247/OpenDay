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



# --- Constants ---

TEAM_3_SCHOOLS = [
    "TH, THCS và THPT iSchool Quy Nhơn",
    "THPT Lý Tự Trọng",
    "THPT Nguyễn Du",
    "THPT Nguyễn Hồng Đạo",
    "THPT Nguyễn Hữu Quang",
    "THPT Nguyễn Thái Học",
    "THPT Phan Bội Châu",
    "THPT Số 1 Phù Mỹ",
    "THPT Số 2 An Nhơn",
    "THPT Số 2 Phù Mỹ",
    "THPT Số 3 An Nhơn",
    "THPT Số 3 Tuy Phước",
    "THPT Trưng Vương",
    "THPT Xuân Diệu",
    "TT GDNN-GDTX An Nhơn",
    "TT GDTX tinh Bình Định",
    "Trường THPT Lương Thế Vinh",
    "TH, THCS&THPT Quốc tế Việt Nam Singapore",
    "THCS&THPT iSchool Nha Trang",
    "THPT chuyên Lê Quý Đôn",
    "THPT Đoàn Thị Điểm",
    "THPT Hà Huy Tập",
    "THPT Hermann Gmeiner",
    "THPT Hoàng Hoa Thám",
    "THPT Hoàng Văn Thụ",
    "THPT Huỳnh Thúc Kháng",
    "THPT Lê Hồng Phong",
    "THPT Lê Thánh Tôn",
    "THPT Ngô Gia Tự",
    "THPT Nguyễn Chí Thanh",
    "THPT Nguyễn Huệ",
    "THCS&THPT Nguyễn Thái Bình",
    "THPT Nguyễn Thiện Thuật",
    "THPT Nguyễn Trãi",
    "THPT Nguyễn Văn Trỗi",
    "THPT Phạm Văn Đồng",
    "THPT Tô Văn Ơn",
    "THPT Trần Bình Trọng",
    "THPT Trần Cao Vân",
    "THPT Trần Hưng Đạo",
    "THPT Trần Quý Cáp",
    "Trường THPT Võ Nguyên Giáp",
    "Trường THPT Ba Tơ",
    "Trường THPT Bình Sơn",
    "Trường THPT Phạm Kiệt"
]

TEAM_1_SCHOOLS = [
    "THPT Hùng Vương",
    "THPT Ngô Mây",
    "THPT số 1 Quang Trung",
    "THPT Số 1 An Nhơn",
    "THPT Số 2 Tuy phước",
    "THPT Số 3 Phù Cát",
    "THPT Tăng Bạt Hổ",
    "THPT Trần Cao Vân",
    "THPT Trần Quang Diệu",
    "THPT Vân Canh",
    "THPT Vĩnh Thạnh",
    "THPT Võ Giữ",
    "THPT Mạc Đĩnh Chi",
    "Trường Quốc tế Châu Á Thái Bình Dương",
    "Trường THCS và THPT Phạm Hồng Thái",
    "Trường THCS và THPT Y Đôn",
    "THPT Chu Văn An",
    "Trường THCS&THPT Kpă Klơng",
    "Trường THCS, THPT Nguyễn Văn Cừ",
    "Trường THPT A Sanh",
    "THPT Lý Thường Kiệt",
    "Trường THPT Hà Huy Tập",
    "Trường THPT Huỳnh Thúc Kháng",
    "Trường THPT Lê Hoàn",
    "Trường THPT Lê Hồng Phong",
    "Trường THPT Lê Lợi",
    "Trường THPT Lê Quý Đôn",
    "Nguyễn Khuyến",
    "Trường THPT Lê Thánh Tông",
    "Trường THPT Nguyễn Bỉnh Khiêm",
    "Trường THPT Nguyễn Chí Thanh",
    "Trường THPT Nguyễn Du",
    "Trường THPT Nguyễn Huệ",
    "Trường THPT Nguyễn Thái Học",
    "Trường THPT Nguyễn Trãi",
    "Trường THPT Nguyễn Trường Tộ",
    "Trường THPT Phạm Văn Đồng",
    "Trường THPT Phan Bội Châu",
    "Trường THPT Pleiku",
    "Trường THPT Quang Trung",
    "Trường THPT Trần Hưng Đạo",
    "Trường THPT Trần Phú",
    "Trường THPT Trường Chinh",
    "Trường THPT Võ Văn Kiệt",
    "Trường PT Dân tộc Nội trú tinh"
]

TEAM_2_SCHOOLS = [
    "PTDTNT THPT Bình Định",
    "THPT An Lão",
    "THPT Bùi Thị Xuân",
    "THPT chuyên Chu Văn An",
    "THPT chuyên Lê Quý Đôn",
    "THPT FPT - Thành phố Quy Nhơn",
    "THPT Hoài Ân",
    "THPT Mỹ Thọ",
    "THPT Nguyễn Bỉnh Khiêm",
    "THPT Nguyễn Diêu",
    "THPT Nguyễn Trân",
    "THPT Số 1 Phù Cát",
    "THPT Số 2 Phù Cát",
    "THPT Võ Lai",
    "THPT Binh Dương",
    "Trường THPT Chi Lăng",
    "Trường THPT Chuyên Hùng Vương",
    "Trường THPT Hoàng Hoa Thám",
    "Trường THPT Nguyễn Tất Thành",
    "Trường THPT Trần Quốc Tuấn",
    "Trần Cao Vân",
    "TT GDTX tinh",
    "Trường THPT Ya Ly",
    "THPT Pleime",
    "Phổ thông Duy Tân",
    "THCS và THPT Nguyễn Khuyến",
    "Nguyễn Bá Ngọc",
    "THCS và THPT Nguyễn Viết Xuân",
    "THCS và THPT Võ Nguyên Giáp",
    "THPT Chuyên Lương Văn Chánh",
    "THPT Lê Hồng Phong",
    "THPT Lê Lợi",
    "THPT Lê Thành Phương",
    "THPT Lê Trung Kiên",
    "THPT Nguyễn Trãi",
    "THPT Ngô Gia Tự",
    "THPT Nguyễn Du",
    "Nguyễn Thị Minh Khai",
    "THPT Nguyễn Công Trứ",
    "THPT Nguyễn Huệ",
    "THPT Nguyễn Văn Linh",
    "THPT Phan Bội Châu",
    "THPT Phan Chu Trinh",
    "THPT Phan Đình Phùng",
    "THPT Trần Bình Trọng",
    "Võ Thị Sáu",
    "Trần Quốc Tuấn",
    "THPT Trần Phú",
    "THPT Trần Suyền",
    "THPT Tôn Đức Thắng",
    "THPT Phạm Văn Đồng",
    "THPT Nguyễn Thái Bình",
    "THCS và THPT Chu Văn An",
    "THPT Nguyễn Trường Tộ",
    "THCS và THPT Vạn Tường",
    "Đinh Tiên Hoàng",
    "Trường THPT Lê Trung Đình",
    "Trường THPT Số 1 Tư Nghĩa",
    "Trung tâm GDNN-GDTX huyện Mộ Đức",
    "Trung tâm GDTX tinh Quảng Ngãi"
]

TEAM_4_SCHOOLS = [
    "PTDTNT THCS & THPT Vân Canh",
    "Quốc Học Quy Nhơn",
    "THPT An Lương",
    "THPT Hòa Bình",
    "THPT Ngô Lê Tân",
    "THPT Nguyễn Đình Chiểu",
    "THPT số 1 Nguyễn Huệ",
    "THPT số 1 Nguyễn Trường Tộ",
    "THPT Quy Nhơn",
    "THPT Số 1 Tuy phước",
    "THPT Tam Quan",
    "THPT Tây Sơn",
    "LIÊN CẤP THÀNH PHỐ GIÁO DỤC",
    "THPT Ba Gia",
    "THPT Chu Văn An",
    "THPT chuyên Lê Khiết",
    "THPT Lê Quý Đôn",
    "THPT Lương Thế Vinh",
    "THPT Lý Sơn",
    "THPT Quang Trung",
    "THPT Phạm Văn Đồng",
    "THPT Số 1 Đức Phổ",
    "THPT Số 1 Nghĩa Hành",
    "THPT Số 2 Đức Phổ",
    "THPT Số 2 Mộ Đức",
    "THPT Số 2 Nghĩa Hành",
    "THPT Sơn Mỹ",
    "Sơn hà",
    "Thu Xà",
    "Trần Kỳ Phong",
    "THPT Trần Quốc Tuấn"
]


BLANKS_SCHOOLS = [
    "THPT Nguyễn Trung Trực",
    "Trung tâm GDNN-GDTX Quy Nhơn",
    "TT GDNN-GDTX Phù Cát",
    "Trường THCS và THPT Phạm Kiệt",
    "Trường THPT Dân tộc nội trú tỉnh Quảng Ngãi",
    "Trường THPT Huỳnh Thúc Kháng",
    "Trường THPT Nguyễn Công Phương",
    "Trường THPT Số 2 Tư Nghĩa",
    "Trường THPT Tây Trà",
    "Trường THPT Trà Bồng",
    "Trường THPT Trần Quang Diệu",
    "Trường THPT Tư thục Hoàng Văn Thụ",
    "Trường THPT Nguyễn Trãi",
    "Trường THPT chuyên Lê Quí Đôn",
    "Trường THPT An Phước",
    "Trường THPT Chu Văn An",
    "Trường THPT iSchool",
    "Trường THPT Phan Chu Trinh",
    "Trường THPT Ninh Hải",
    "Trường THPT Tôn Đức Thắng",
    "TTGDTX Ninh Thuận",
    "THCS - THPT Đặng Chí Thanh",
    "THPT Nguyễn Du",
    "TH - THCS - THPT Hoa Sen",
    "THPT Trường Chinh",
    "THPT Tháp Chàm"
]

def check_school_team(school_name):
    """
    Check which team the school belongs to.
    Returns: "team 1", "team 2", "team 3", "team 4", "blanks" or None
    """
    if not school_name:
        return None
    
    school_name_lower = school_name.lower().strip()
    
    # Common prefixes to ignore for better matching
    prefixes = ["trường ", "thpt ", "trường thpt ", "tt ", "trung tâm ", "thcs và thpt ", "thcs & thpt ", "ptdtnt ", "th, ", "th - "]
    
    # Normalize input school name
    normalized_input = school_name_lower
    for prefix in prefixes:
        if normalized_input.startswith(prefix):
            normalized_input = normalized_input[len(prefix):].strip()
    
    # Helper to check against a list
    def check_list(school_list):
        for school in school_list:
            # Normalize list item
            item_normalized = school.lower()
            for prefix in prefixes:
                if item_normalized.startswith(prefix):
                    item_normalized = item_normalized[len(prefix):].strip()
            
            # Check containment
            if normalized_input in item_normalized or item_normalized in normalized_input:
                return True
        return False

    if check_list(BLANKS_SCHOOLS):
        return "blanks"

    if check_list(TEAM_1_SCHOOLS):
        return "team 1"
    
    if check_list(TEAM_2_SCHOOLS):
        return "team 2"
        
    if check_list(TEAM_3_SCHOOLS):
        return "team 3"
        
    if check_list(TEAM_4_SCHOOLS):
        return "team 4"
        
    return None

async def init_sheet_headers():
    """Ensure Google Sheet has correct headers and formatting"""
    client = await asyncio.to_thread(get_google_sheet_client)
    if not client:
        return

    try:
        spreadsheet_url = "https://docs.google.com/spreadsheets/d/1RTxOi5IYcYDL5VaCAiwK9B0T15K5ntSnWLJ4EwD_Rlg/edit?usp=sharing"
        sheet = await asyncio.to_thread(client.open_by_url, spreadsheet_url)
        
        target_headers = ["Họ và tên", "Số điện thoại", "Email", "Tỉnh thành", "Trường THPT", "Kết quả AI đề xuất"]
        
        # --- 1. Init Main Sheet (Sheet1) ---
        worksheet = await asyncio.to_thread(sheet.get_worksheet, 0)
        current_headers = await asyncio.to_thread(worksheet.row_values, 1)
        
        if not current_headers:
            print("⏳ Main Sheet is empty. Adding headers...")
            await asyncio.to_thread(worksheet.append_row, target_headers)
        elif current_headers != target_headers:
             # Just update headers to be sure
            cell_list = await asyncio.to_thread(worksheet.range, 'A1:F1')
            for i, cell in enumerate(cell_list):
                if i < len(target_headers):
                    cell.value = target_headers[i]
            await asyncio.to_thread(worksheet.update_cells, cell_list)
        
        await asyncio.to_thread(worksheet.freeze, rows=1)
        print("✅ Main Sheet (Sheet1) initialized.")

        # --- 2. Init Sub-Sheets (team 1, team 2, team 3, team 4, blanks) ---
        for sheet_title in ["team 1", "team 2", "team 3", "team 4", "blanks"]:
            try:
                # Try to get the sheet
                ws_sub = await asyncio.to_thread(sheet.worksheet, sheet_title)
            except gspread.WorksheetNotFound:
                # Create if not exists
                print(f"⏳ Creating sheet '{sheet_title}'...")
                ws_sub = await asyncio.to_thread(sheet.add_worksheet, title=sheet_title, rows=1000, cols=10)
            
            # Check/init headers
            current_headers_sub = await asyncio.to_thread(ws_sub.row_values, 1)
            if not current_headers_sub:
                await asyncio.to_thread(ws_sub.append_row, target_headers)
            elif current_headers_sub != target_headers:
                cell_list = await asyncio.to_thread(ws_sub.range, 'A1:F1')
                for i, cell in enumerate(cell_list):
                    if i < len(target_headers):
                        cell.value = target_headers[i]
                await asyncio.to_thread(ws_sub.update_cells, cell_list)
            
            await asyncio.to_thread(ws_sub.freeze, rows=1)
            print(f"✅ Sheet '{sheet_title}' initialized.")

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

        # Prepare row data
        row = [
            student_data.get('student_name', ''),
            student_data.get('student_phone', ''),
            student_data.get('student_email', ''),
            student_data.get('student_province', ''),
            student_data.get('student_school', ''),
            student_data.get('predicted_major', '')
        ]

        # 1. Save to Main Worksheet (index 0)
        worksheet = await asyncio.to_thread(sheet.get_worksheet, 0)
        await asyncio.to_thread(worksheet.append_row, row)
        print(f"✅ Saved data for {student_data.get('student_name')} to Main Sheet")
        
        # 2. Check which team the school belongs to (Team 1, 2, 3, 4 or blanks)
        student_school = student_data.get('student_school', '')
        team_name = check_school_team(student_school) # Returns "team 1", "team 2", "team 3", "team 4", "blanks" or None
        
        if team_name:
            try:
                ws_team = await asyncio.to_thread(sheet.worksheet, team_name)
                await asyncio.to_thread(ws_team.append_row, row)
                print(f"✅ Saved data for {student_data.get('student_name')} to '{team_name}' Sheet")
            except gspread.WorksheetNotFound:
                print(f"⚠️ Sheet '{team_name}' not found (should have been created setup).")

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
async def start_quiz(request: Request):
    """
    Handle registration and show quiz.
    """
    form_data = await request.form()
    student_name = form_data.get("student_name", "")
    student_phone = form_data.get("student_phone", "")
    student_email = form_data.get("student_email", "")
    student_province = form_data.get("student_province", "")
    student_school = form_data.get("student_school", "")
    student_cccd = form_data.get("student_cccd", "")

    print(f"DEBUG: Start quiz for {student_name}, School: {student_school}")

    all_questions = await asyncio.to_thread(load_questions)
    # Randomly select 15 questions if available
    if len(all_questions) >= 15:
        selected_questions = random.sample(all_questions, 15)
    else:
        selected_questions = all_questions
    
    # Pass student info to the quiz page - Force string conversion
    student_info = {
        "student_name": str(student_name) if student_name else "",
        "student_phone": str(student_phone) if student_phone else "",
        "student_email": str(student_email) if student_email else "",
        "student_province": str(student_province) if student_province else "",
        "student_school": str(student_school) if student_school else "",
        "student_cccd": str(student_cccd) if student_cccd else ""
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
    
    student_name = form_data.get("student_name", "")
    print(f"DEBUG: Submit received for '{student_name}'. Form keys: {list(form_data.keys())}")
    
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
        'student_name': str(form_data.get('student_name', '')),
        'student_phone': str(form_data.get('student_phone', '')),
        'student_email': str(form_data.get('student_email', '')),
        'student_province': str(form_data.get('student_province', '')),
        'student_school': str(form_data.get('student_school', '')),
        'student_cccd': str(form_data.get('student_cccd', '')),
        'predicted_major': predicted_major,
        'career_advice': advice_markdown
    }
    
    print(f"DEBUG: Processing quiz for {student_data['student_name']} from {student_data['student_school']}")
    
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
