import streamlit as st
import smtplib
import random
import json
import os
import io
import requests
import sys
from urllib.parse import urlparse, parse_qs
from groq import Groq
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from datetime import datetime, timedelta
from email.message import EmailMessage
from streamlit_cookies_manager import EncryptedCookieManager
from PyPDF2 import PdfReader
from youtube_transcript_api import YouTubeTranscriptApi
import time
import pytz

LOCAL_MODE = os.environ.get("ELENA_LOCAL", "") == "1" or os.name == "nt"

def get_chrome_binary_path():
    env_path = os.environ.get("CHROME_BINARY")
    if env_path and os.path.exists(env_path):
        return env_path

    if os.name == "nt":
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Chromium\Application\chrome.exe",
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    else:
        candidates = [
            "/opt/render/project/.render/chrome/opt/google/chrome/google-chrome",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium",
        ]

    for path in candidates:
        if os.path.exists(path):
            return path
    return None

def init_shared_driver():
    if st.session_state.get("driver") is not None:
        return st.session_state.driver

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-logging')
    options.add_argument('--log-level=3')

    chrome_binary = get_chrome_binary_path()
    chrome_type = ChromeType.CHROMIUM
    if chrome_binary:
        options.binary_location = chrome_binary
        if "chrome" in chrome_binary.lower() and "chromium" not in chrome_binary.lower():
            chrome_type = ChromeType.GOOGLE

    try:
        service = Service(ChromeDriverManager(chrome_type=chrome_type).install())
        st.session_state.driver = webdriver.Chrome(service=service, options=options)
        st.success("✅ إيلينا متصلة وجاهزة للعمل!")
    except Exception as e:
        st.error(f"❌ فشل تشغيل المتصفح: {e}")
        st.info("نصيحة: تأكد من وجود ملف render-build.sh لو كنت تستخدم Render.")
        st.session_state.driver = None

    return st.session_state.driver

# إعداد Groq باستخدام الـ Secrets
def get_groq_api_key():
    env_key = os.environ.get("GROQ_API_KEY")
    if env_key:
        return env_key
    try:
        return st.secrets.get("GROQ_API_KEY")
    except Exception:
        return None

GROQ_API_KEY = get_groq_api_key() or "<YOUR_GROQ_API_KEY>"

if not GROQ_API_KEY:
    st.error("❌ خطأ: مفتاح GROQ_API_KEY غير موجود في إعدادات السيرفر!")
    st.stop()
else:
    client = Groq(api_key=GROQ_API_KEY)

cookies = EncryptedCookieManager(prefix="elena/", password="EM2006_secret_key")
if not cookies.ready():
    st.stop()

if not LOCAL_MODE and "driver" not in st.session_state:
    with st.spinner("جاري تهيئة إيلينا على السيرفر السحابي... 👑"):
        init_shared_driver()
            
# الجسر لضمان تعريف كلمة driver في كل الملف
driver = st.session_state.get("driver")

def get_course_content(course_url):
    # نتحقق أولاً هل المتصفح شغال؟
    if "driver" not in st.session_state or st.session_state.get("driver") is None:
        init_shared_driver()
    if "driver" not in st.session_state or st.session_state.get("driver") is None:
        st.error("⚠️ المتصفح غير جاهز!")
        return []
        
    local_driver = st.session_state.driver # استخدام الدرايفر من الجلسة
    
    try:
        # 1. الدخول لرابط المادة المحدد باستخدام local_driver
        local_driver.get(course_url)
        time.sleep(4) 
        
        links_found = []
        
        # 2. البحث عن الروابط
        elements = local_driver.find_elements(By.CSS_SELECTOR, "div.activityinstance a")
        
        if not elements: 
            elements = local_driver.find_elements(By.TAG_NAME, "a")

        for elem in elements:
            href = elem.get_attribute("href")
            text = elem.text
            
            if href:
                if any(ext in href for ext in [".pdf", "resource", "url", "video", "youtube"]):
                    if "forcedownload=1" in href or "mod/resource" in href or "mod/url" in href:
                        links_found.append({
                            "name": text if text else "ملف/رابط غير مسمى",
                            "url": href
                        })
        
        return links_found
    except Exception as e:
        st.error(f"خطأ في جلب المحتوى: {e}")
        return []
        
def summarize_content(text_to_analyze, content_type="ملف"):
    """Summarize content using Groq AI with proper error handling."""
    if not text_to_analyze or not text_to_analyze.strip():
        return "المحتوى فارغ ولا يمكن تلخيصه."
    
    try:
        # Limit text to prevent token overflow
        truncated_text = text_to_analyze[:15000]
        
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": f"أنت مساعد أكاديمي خبير. قم بتلخيص هذا الـ {content_type} بشكل نقاط مركزة ومفيدة للطالب."},
                {"role": "user", "content": f"المحتوى المراد تلخيصه:\n\n{truncated_text}"}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        summary = response.choices[0].message.content
        st.session_state.last_summary = summary
        return summary
    except Exception as e:
        st.error(f"خطأ في الاتصال بـ AI: {e}")
        return f"حدث خطأ في التلخيص: {str(e)}"
    
# --- الدالة السحرية لحل مشكلة الوقت (فلسطين UTC+2) ---
def get_local_time():
    # بنحدد المنطقة الزمنية لغزة/القدس
    local_tz = pytz.timezone('Asia/Gaza')
    # بنجيب الوقت الحالي بناءً على المنطقة
    return datetime.now(local_tz)
# --- 1. إعدادات الصفحة والتصميم ---
# --- 1. إعداد الصفحة والتصميم (أول شيء ��ي الكود) ---
st.set_page_config(page_title="Elena AI", page_icon="👑", layout="wide")

# --- 2. ستايل الـ CSS المطور ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"]  {
        font-family: 'Cairo', sans-serif;
        text-align: right;
        direction: rtl;
    }
    .stButton>button {
        border-radius: 10px;
        transition: 0.3s;
    }
    .stButton>button:hover {
        border-color: #ff4b4b;
        color: #ff4b4b;
    }
    </style>
    """, unsafe_layout=True)

# Database helpers defined above - removed duplicate
# --- 3. التعرف التلقائي (هاد اللي كان بيعمل NameError) ---
if st.query_params.get("logout") == "true":
    st.session_state["is_logged_in"] = False
    if "username" in cookies:
        del cookies["username"]
        cookies.save()
    st.query_params.clear() # تنظيف الرابط
    st.rerun() # إعادة تشغيل نظيفة

# 2. الكود اللي إنت بعته (فحص الدخول التلقائي)
if "username" in cookies and cookies["username"] != "" and not st.session_state.get("is_logged_in"):
    saved_user = cookies["username"]
    db = load_db()
    
    if saved_user == "ethan":
        st.session_state.update({
            "is_logged_in": True,
            "username": "Ethan",
            "user_role": "developer",
            "user_status": "Prime"
        })
    elif saved_user in db:
        st.session_state.update({
            "is_logged_in": True,
            "username": saved_user,
            "user_role": "user",
            "user_status": db[saved_user].get("status", "Standard"),
            "u_id": db[saved_user].get("u_id", ""), 
            "u_pass": db[saved_user].get("u_pass", "")
        })

# --- 2. Session State Initialization ---
def init_session_state():
    """Initialize all session state variables with defaults."""
    defaults = {
        "is_logged_in": False,
        "user_status": "Standard",
        "user_role": "user",
        "username": "",
        "courses": {},
        "timeline_data": "",
        "messages": [],
        "pdf_memories": {},
        "summarized_items": [],
        "knowledge_base": {},
        "deep_scan_progress": [],
        "IF_VALID_CODES": ["ELENA-PRO-2026", "ETHAN-VIP"],
        "u_id": "",
        "u_pass": "",
        "is_synced": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# Configuration Constants
EMAIL_ADDRESS = "ehabalhayekm@gmail.com" 
EMAIL_PASSWORD = "hvvh duch onfd xxdv" 
DB_FILE = "users_db.json"
MAX_FREE_SYNCS = 10
PDF_TEXT_LIMIT = 8000
GROQ_MODEL = "llama-3.3-70b-versatile"

# Database helpers (single definition)
def load_db():
    """Load user database from JSON file."""
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_db(data):
    """Save user database to JSON file."""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        st.error(f"فشل حفظ البيانات: {e}")

def send_otp(target_email, code):
    """Send OTP via email with proper validation and error handling."""
    # Validate email format
    if not target_email or '@' not in target_email:
        return False
    
    try:
        msg = EmailMessage()
        msg.set_content(
            f"""مرحباً بك في منصة إيلينا AI!
            
            كود التحقق الخاص بك هو: {code}
            
            هذا الكود صالح لمرة واحدة فقط.
            إذا لم تطلب هذا الكود، يرجى تجاهل هذه الرسالة.
            
            مع تحيات فريق إيلينا
            """
        )
        msg['Subject'] = "تفعيل حساب إيلينا AI"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = target_email
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        return True
    except smtplib.SMTPException as e:
        st.error(f"خطأ في إرسال البريد: {e}")
        return False
    except Exception as e:
        st.error(f"خطأ غير متوقع: {e}")
        return False

def get_youtube_summary(video_url):
    """Extract and summarize YouTube video transcripts."""
    if not video_url:
        return "❌ الرجاء إدخال را��ط فيديو صحيح."
    
    try:
        # Resolve redirects (Moodle etc.)
        resolved_url = video_url
        try:
            resp = requests.get(video_url, allow_redirects=True, timeout=10)
            if resp.url:
                resolved_url = resp.url
        except Exception:
            resolved_url = video_url

        # Extract video ID with improved patterns
        video_id = None
        parsed = urlparse(resolved_url)

        if "v=" in resolved_url:
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        elif "youtu.be/" in resolved_url:
            video_id = parsed.path.lstrip("/").split("/")[0]
        elif "/embed/" in parsed.path:
            video_id = parsed.path.split("/embed/")[-1].split("/")[0]
        elif "/shorts/" in parsed.path:
            video_id = parsed.path.split("/shorts/")[-1].split("/")[0]

        if not video_id or len(video_id) != 11:
            return "❌ عذراً، لم أستطع التعرف على رابط الفيديو بشكل صحيح."

        # Fetch transcript with language priority
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            # Try Arabic first, then English, then any available
            try:
                transcript = transcript_list.find_transcript(['ar'])
            except:
                try:
                    transcript = transcript_list.find_transcript(['en'])
                except:
                    transcript = transcript_list.find_generated_transcript(['en'])
            
            data = transcript.fetch()
            full_text = " ".join([item['text'] for item in data])
            
            if not full_text.strip():
                return "❌ النص المستخرج فارغ."
                
        except Exception as e:
            return "❌ هذا الفيديو لا يحتوي على نص تلقائي (Transcripts) مفعل، لا أستطيع قراءته."

        # Send to Groq for summarization
        truncated_text = full_text[:PDF_TEXT_LIMIT]
        prompt = f"""
        أنت مساعد أكاديمي ذكي. قم بتلخيص هذه المحاضرة بدقة واحترافية.
        استخدم النقاط، واذكر أهم المفاهيم العلمية الواردة.
        
        النص: {truncated_text}
        """

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"خطأ في معالجة الفيديو: {e}")
        return f"❌ خطأ تقني: {str(e)}"

def deep_scan_course(username, password, course_url, progress_callback=None):
    """Deep scan a course: click all links, extract content intelligently."""
    if not username or not password or not course_url:
        return {"error": "بيانات غير كاملة."}
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')

    chrome_binary = get_chrome_binary_path()
    if chrome_binary:
        options.binary_location = chrome_binary

    driver = None
    knowledge_base = {}
    
    try:
        service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
        
        # Login
        driver.get("https://sso.iugaza.edu.ps/saml/module.php/core/loginuserpass")
        time.sleep(3)
        driver.find_element(By.ID, "username").send_keys(username)
        p_field = driver.find_element(By.ID, "password")
        p_field.send_keys(password)
        p_field.send_keys(Keys.ENTER)
        time.sleep(12)
        
        # Navigate to course
        driver.get(course_url)
        time.sleep(5)
        
        # Find all resource links
        link_elements = driver.find_elements(By.CSS_SELECTOR, ".activityinstance a, .aalink")
        links_to_scan = []
        
        for elem in link_elements:
            try:
                name = elem.text.strip()
                url = elem.get_attribute("href")
                if url and name and "course/view.php" not in url:
                    links_to_scan.append({"name": name, "url": url})
            except:
                continue
        
        total_links = len(links_to_scan)
        if progress_callback:
            progress_callback(f"🔍 وجدت {total_links} عنصر للمسح...")
        
        # Scan each link
        for idx, link in enumerate(links_to_scan, 1):
            try:
                if progress_callback:
                    progress_callback(f"📖 [{idx}/{total_links}] معالجة: {link['name']}")
                
                url_lower = link['url'].lower()
                content = ""
                content_type = "unknown"
                
                # YouTube video detection
                if any(x in url_lower for x in ["youtube", "youtu.be", "vimeo"]) or "watch?v=" in url_lower:
                    try:
                        # Extract video ID
                        video_id = None
                        if "v=" in link['url']:
                            video_id = link['url'].split("v=")[-1].split("&")[0]
                        elif "youtu.be/" in link['url']:
                            video_id = link['url'].split("youtu.be/")[-1].split("?")[0]
                        
                        if video_id and len(video_id) == 11:
                            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                            try:
                                transcript = transcript_list.find_transcript(['ar'])
                            except:
                                transcript = transcript_list.find_transcript(['en'])
                            
                            data = transcript.fetch()
                            content = " ".join([item['text'] for item in data])
                            content_type = "video"
                    except:
                        content = "[فشل استخراج نص الفيديو]"
                        content_type = "video"
                
                # PDF detection
                elif ".pdf" in url_lower or "mod/resource" in url_lower:
                    try:
                        cookies = {c['name']: c['value'] for c in driver.get_cookies()}
                        response = requests.get(link['url'], cookies=cookies, timeout=15)
                        
                        if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
                            pdf_file = io.BytesIO(response.content)
                            reader = PdfReader(pdf_file)
                            pdf_text = ""
                            for page in reader.pages:
                                pdf_text += page.extract_text() + "\n"
                            content = pdf_text[:20000]  # Limit size
                            content_type = "pdf"
                        else:
                            # Try clicking and extracting
                            driver.get(link['url'])
                            time.sleep(4)
                            content = driver.find_element(By.TAG_NAME, "body").text[:20000]
                            content_type = "page"
                    except:
                        content = "[فشل استخراج محتوى PDF]"
                        content_type = "pdf"
                
                # Regular page/resource
                else:
                    try:
                        driver.get(link['url'])
                        time.sleep(4)
                        try:
                            content = driver.find_element(By.ID, "region-main").text
                        except:
                            content = driver.find_element(By.TAG_NAME, "body").text
                        content = content[:20000]  # Limit size
                        content_type = "page"
                    except:
                        content = "[فشل الوصول للصفحة]"
                        content_type = "page"
                
                # Store in knowledge base
                if content and len(content.strip()) > 50:
                    knowledge_base[link['name']] = {
                        "content": content,
                        "type": content_type,
                        "url": link['url']
                    }
                
            except Exception as e:
                if progress_callback:
                    progress_callback(f"⚠️ خطأ في {link['name']}: {str(e)[:50]}")
                continue
        
        if progress_callback:
            progress_callback(f"✅ اكتمل المسح! تم معالجة {len(knowledge_base)} عنصر بنجاح.")
        
        return {"knowledge_base": knowledge_base, "success": True}
        
    except Exception as e:
        return {"error": f"خطأ في المسح العميق: {str(e)}"}
    finally:
        if driver:
            driver.quit()

def run_selenium_task(username, password, task_type="timeline", target_url=None):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')

    chrome_binary = get_chrome_binary_path()
    if chrome_binary:
        options.binary_location = chrome_binary

    driver = None
    try:
        service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # 1. الدخول عبر بوابة SSO
        driver.get("https://sso.iugaza.edu.ps/saml/module.php/core/loginuserpass")
        time.sleep(3)
        
        driver.find_element(By.ID, "username").send_keys(username)
        p_field = driver.find_element(By.ID, "password")
        p_field.send_keys(password)
        p_field.send_keys(Keys.ENTER)
        
        # انتظر التحويل للمودل (وقت كافٍ للتحميل)
        time.sleep(15) 

        # 2. سحب الاسم الحقيقي (تجربة عدة سيلكتورز)
        student_name = "طالب جامعي"
        for sel in [".usertext", ".userbutton span", ".username"]:
            try:
                name_element = driver.find_element(By.CSS_SELECTOR, sel)
                if name_element.text.strip():
                    student_name = name_element.text.strip()
                    break
            except: continue

        if task_type == "timeline":
            # سحب الكورسات من الداشبورد
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='course/view.php?id=']")
            course_map = {}
            for l in links:
                t = l.text.strip()
                if len(t) > 10 and t not in course_map: # فلترة الأسماء القصيرة
                    course_map[t] = l.get_attribute("href")
            
            # سحب المخطط الزمني
            timeline_events = []
            try:
                events = driver.find_elements(By.CSS_SELECTOR, "[data-region='event-list-item'] a, .event-name")
                timeline_events = [e.text.strip() for e in events if e.text.strip()]
            except: pass
            
            return {"courses": course_map, "student_name": student_name, "timeline_list": timeline_events}

        elif task_type == "grades":
            if target_url:
                g_url = target_url.replace("course/view.php", "grade/report/user/index.php")
                driver.get(g_url)
                time.sleep(10)
                try:
                    # محاولة سحب جدول الدرجات بأكثر من طريقة
                    grade_data = driver.find_element(By.CSS_SELECTOR, "table.user-grade, table").text
                    return {"data": grade_data, "student_name": student_name}
                except:
                    return {"error": "لم يتم العثور على جدول الدرجات."}

        elif task_type == "browse":
            if target_url:
                driver.get(target_url)
                time.sleep(8)
                # سحب النصوص
                try: content = driver.find_element(By.ID, "region-main").text
                except: content = driver.find_element(By.TAG_NAME, "body").text
                
                # سحب الروابط والملفات (PDF, Folders, Links)
                found_links = []
                link_elements = driver.find_elements(By.CSS_SELECTOR, ".instancename, .aalink")
                for elem in link_elements:
                    try:
                        name = elem.text.strip()
                        # العثور على الرابط الأقرب للعنصر
                        parent = elem.find_element(By.XPATH, "./..") if elem.tag_name != 'a' else elem
                        url = parent.get_attribute("href")
                        if url and name and "course/view.php" not in url:
                            found_links.append({"name": name, "url": url})
                    except: continue
                
                return {"course_content": content, "course_links": found_links, "student_name": student_name}

        elif task_type == "scrape_pdf":
                if target_url:
                    try:
                        # سحب الكوكيز عشانrequests يعرف إننا مسجلين دخول
                        cookies = {c['name']: c['value'] for c in driver.get_cookies()}
                        # تنزيل الملف
                        response = requests.get(target_url, cookies=cookies, timeout=15)
                        
                        if response.status_code == 200:
                            pdf_file = io.BytesIO(response.content)
                            reader = PdfReader(pdf_file)
                            pdf_text = ""
                            # استخراج النص من كل الصفحات
                            for page in reader.pages:
                                pdf_text += page.extract_text() + "\n"
                            
                            return {"pdf_text": pdf_text, "student_name": student_name}
                        else:
                            return {"error": f"فشل التحميل، كود الخطأ: {response.status_code}"}
                    except Exception as e:
                        return {"error": f"مشكلة في قراءة الـ PDF: {str(e)}"}

    except Exception as e:
        return {"error": str(e)}
    finally:
        if driver: driver.quit()
# --- 4. واجهة تسجيل الدخول المطورة ---
if not st.session_state.get("is_logged_in"):
    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("<h1 style='color: #FFD700;'>👑 Elena AI Portal</h1>", unsafe_allow_html=True)
        
        tab_login, tab_signup = st.tabs(["🔑 تسجيل دخول", "📝 تسجيل جديد"])
        db = load_db()

        with tab_login:
            u = st.text_input("اسم المستخدم", key="l_u")
            p = st.text_input("كلمة السر", type="password", key="l_p")
            
            uid_input = st.text_input("الرقم الجامعي (اختياري)", key="l_uid")
            upass_input = st.text_input("باسورد الجامعة (اختياري)", type="password", key="l_upass")

            col_in, col_forgot = st.columns(2)
            
            if col_in.button("دخول للنظام", use_container_width=True):
                # 1. حالة المطور (إيثان)
                if u == "ethan" and p == "EM2006":
                    cookies["username"] = "ethan"
                    cookies.save()
                    st.session_state.update({
                        "is_logged_in": True, 
                        "user_role": "developer", 
                        "user_status": "Prime", 
                        "username": "Ethan",
                        "u_id": uid_input,
                        "u_pass": upass_input
                    })
                    st.rerun()
                
                # 2. حالة الطالب العادي
                elif u in db and db[u]['password'] == p:
                    cookies["username"] = u
                    cookies.save()
                    st.session_state.update({
                        "is_logged_in": True, 
                        "user_role": "user", 
                        "user_status": db[u]['status'], 
                        "username": u,
                        "u_id": uid_input,
                        "u_pass": upass_input
                    })
                    st.rerun()
                else: 
                    st.error("بيانات خاطئة!")

            if col_forgot.button("نسيت كلمة السر؟", use_container_width=True):
                st.session_state.show_reset = True

            # --- استعادة كلمة السر ---
            if st.session_state.get("show_reset"):
                st.markdown("---")
                re_e = st.text_input("إيميلك المسجل:")
                if st.button("إرسال كود الاستعادة"):
                    user_found = next((user for user, info in db.items() if info.get('email') == re_e), None)
                    if user_found:
                        otp = random.randint(1000, 9999)
                        if send_otp(re_e, otp):
                            st.session_state.reset_otp, st.session_state.reset_user = otp, user_found
                            st.success("تم إرسال الكود!")
                        else: st.error("خطأ في الإرسال")
                    else: st.error("الإيميل غير مسجل")
                
                if "reset_otp" in st.session_state:
                    c_in = st.text_input("الكود:")
                    n_p = st.text_input("كلمة سر جديدة:", type="password")
                    if st.button("تأكيد التغيير"):
                        if c_in == str(st.session_state.reset_otp):
                            db[st.session_state.reset_user]['password'] = n_p
                            save_db(db)
                            st.success("تم التحديث!")
                            del st.session_state.show_reset
                            st.rerun()
                        else: st.error("الكود خطأ")

        with tab_signup:
            nu = st.text_input("اسم مستخدم جديد", key="s_u")
            ne = st.text_input("Gmail", key="s_e")
            np = st.text_input("كلمة سر جديدة", type="password", key="s_p")
            
            if st.button("إرسال كود التحقق 📧"):
                if nu in db: st.error("موجود مسبقاً")
                elif not ne.endswith("@gmail.com"): st.warning("استخدم Gmail")
                else:
                    otp = random.randint(1000, 9999)
                    if send_otp(ne, otp):
                        st.session_state.temp_otp, st.session_state.temp_data = otp, {"u": nu, "p": np, "e": ne}
                        st.success("تفقد إيميلك")
            
            if "temp_otp" in st.session_state:
                otp_in = st.text_input("أدخل كود التحقق:")
                if st.button("تأكيد الحساب"):
                    if otp_in == str(st.session_state.temp_otp):
                        d = st.session_state.temp_data
                        db[d['u']] = {"password": d['p'], "email": d['e'], "status": "Standard", "sync_count": 0}
                        save_db(db)
                        st.success("تم! سجل دخولك الآن.")
                        del st.session_state.temp_otp
                        st.rerun()
                    else:
                        st.error("الكود غير صحيح")

        st.markdown('</div>', unsafe_allow_html=True)
    st.stop() # يمنع ظهور محتويات التطبيق قبل تسجيل الدخول

# --- 5. الواجهة الرئيسية ---
db = load_db()
current_u = st.session_state.get("username", "user")

# 1. أول خطوة: فحص هل انتهى اشتراك البريميوم؟ (هاد الكود اللي سألت عنه)
if st.session_state.get("user_status") == "Prime":
    expire_str = db.get(current_u, {}).get("expire_at")
    if expire_str:
        expire_dt = datetime.strptime(expire_str, "%Y-%m-%d %H:%M:%S")
        if datetime.now() > expire_dt:
            # الاشتراك خلص! نرجعه للطالب العادي
            db[current_u]["status"] = "Standard"
            save_db(db)
            st.session_state.user_status = "Standard"
            st.warning("⚠️ انتهت مدة اشتراكك البريميوم، تم تحويل حسابك للوضع المجاني.")
            st.rerun()

# 2. ثاني خطوة: تحديث عداد المزامنات (عشان يظهر الرقم الصح)
if current_u in db:
    user_syncs = db[current_u].get("sync_count", 0)
else: 
    user_syncs = 0

# 3. ثالث خطوة: رسم الهيدر والترحيب
badge = '<span class="prime-badge">👑</span>' if st.session_state.user_status == "Prime" else ""
st.markdown(f"## Elena Student AI {badge}", unsafe_allow_html=True)

# هيدر الترحيب (تأكد أن الأسطر تبدأ من بداية السطر تماماً بدون مسافات)
# 2. تحديد الاسم والـ Badge
role_name = "إيثان" if st.session_state.get("user_role") == "developer" else "طالب إيلينا"

if st.session_state.get("user_status") == "Prime":
    # التاج الذهبي اللي رح يضل لحاله
    badge = '<span style="background:#FFD700; color:black; padding:2px 10px; border-radius:10px; font-size:18px; margin-right:10px; font-weight:bold;">PRIME MEMBER 👑</span>'
else:
    # تاج رمادي بسيط أو اتركه فارغاً ""
    badge = '<span style="background:#f0f2f6; color:#666; padding:2px 10px; border-radius:10px; font-size:18px; margin-right:10px;">STANDARD 🎓</span>'

# 3. عرض الترحيب النهائي
st.markdown(f"<h2>أهلاً {role_name} {badge}</h2>", unsafe_allow_html=True)

# --- إضافة حالة الربط مع الجامعة هنا ---
if not st.session_state.get("is_synced", False):
    st.warning("⚠️ حسابك غير مرتبط بالمودل حالياً...")
else:
    st.success(f"🔗 متصل الآن بحسابك: {st.session_state.student_name}")

st.markdown("---")

# --- نافذة الاشتراك (Upgrade Section) ---
if st.session_state.user_status == "Standard":
    with st.expander("⭐ تفعيل عضوية برايم (Prime Membership)"):
        col_pay, col_code = st.columns(2)
        with col_pay:
            st.write("### 💳 طرق الدفع المحلية")
            st.write("- **محفظة جوال باي:** `0594820775`")
            st.write("- **بنك فلسطين:** `1701577` (إيهاب الحايك)")
            st.write("- **تواصل واتساب:** [اضغط هنا للترقية](https://wa.me/+972594820775)")
        
        with col_code:
            st.write("### 🔑 تفعيل بكود")
            # 1. الطالب بيدخل الكود هنا
            code_in = st.text_input("أدخل كود الاشتراك:", key="upgrade_input_field")
            
            # 2. هاد هو الكود اللي سألت عنه (بيبدأ من زر التفعيل)
            if st.button("تفعيل الآن ✅"):
                db = load_db()
                timed_codes = db.get("timed_codes", {})

                if code_in in timed_codes:
                    dur = timed_codes[code_in]
                    
                    # ✅ الحل هنا: استخدام التوقيت المحلي (فلسطين)
                    now = get_local_time() 

                    if dur == "1H": expire_date = now + timedelta(hours=1)
                    elif dur == "1D": expire_date = now + timedelta(days=1)
                    elif dur == "1M": expire_date = now + timedelta(days=30)
                    elif dur == "1Y": expire_date = now + timedelta(days=365)

                    # تحديث بيانات الطالب
                    curr_u = st.session_state.username
                    db[curr_u]["status"] = "Prime"
                    db[curr_u]["expire_at"] = expire_date.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # مسح الكود عشان ما حدا يستخدمه مرتين
                    del db["timed_codes"][code_in]
                    
                    save_db(db)
                    
                    # تحديث الحالة في الجلسة فوراً
                    st.session_state.user_status = "Prime"
                    
                    st.success(f"✅ تم التفعيل بنجاح يا بطل! ينتهي اشتراكك في: {expire_date.strftime('%Y/%m/%d - %I:%M %p')}")
                    st.rerun()
                else:
                    st.error("❌ الكود غير صحيح أو مستخدم مسبقاً.")
                    
# حماية الليمت
if st.session_state.user_role != "developer" and st.session_state.user_status != "Prime":
    remaining = 10 - user_syncs
    st.sidebar.metric("المزامنات المتبقية", f"{remaining} / 10")
    if remaining <= 0:
        st.error("🚫 انتهت محاولاتك المجانية. يرجى الترقية.")
        up_c = st.text_input("كود التفعيل:")
        if st.button("تفعيل"):
            if up_c in st.session_state.IF_VALID_CODES:
                db[current_u]["status"] = "Prime"
                save_db(db)
                st.rerun()
        st.stop()

# --- تنظيم التبويبات والصلاحيات ---
tabs = st.tabs(["📅 المخطط الذكي", "📚 المقررات", "📊 الدرجات", "💬 Ask Elena", "🛠️ الإدارة"])

# 1. المخطط الذكي
with tabs[0]:
    st.subheader("📅 المخطط الزمني الذكي")
    
    # زر السحب من المودل
    if st.button("🔄 سحب المخطط والفعاليات القادمة", use_container_width=True):
        uid = st.session_state.get("u_id")
        upass = st.session_state.get("u_pass")
        
        if uid and upass:
            with st.spinner("إيلينا تجمع جدولك ومهامك القادمة..."):
                res = run_selenium_task(uid, upass, "timeline")
                
                if res and "timeline" in res:
                    st.session_state.user_schedule = res["timeline"]
                    if "courses" in res:
                        st.session_state.my_real_courses = res["courses"]
                    st.success("✅ تم تحديث المخطط الزمني والمقررات!")
                    st.rerun()
                else:
                    st.error("❌ فشل السحب: تأكد من وجود فعاليات في المودل.")
        else:
            st.warning("⚠️ يرجى تسجيل الدخول أولاً من القائمة الجانبية.")

    # عرض البيانات والتحليل
    schedule_data = st.session_state.get("user_schedule")
    
    if schedule_data:
        st.write("### 📋 جدول المهام القادمة:")
        
        if isinstance(schedule_data, list) and len(schedule_data) > 0:
            st.table(schedule_data)
            
            # صف الأزرار
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🧐 تحليل سريع هنا"):
                    with st.spinner("إيلينا تدرس المواعيد..."):
                        try:
                            # بناء النص للتحليل السريع
                            stext = "\n".join([f"- {i.get('المهمة/المحاضرة', 'مهمة')} ({i.get('الموعد', 'ميعاد غير محدد')})" for i in schedule_data])
                            prompt = f"حللي جدولي الجامعي ورتبي أولوياتي بأسلوب مشجع:\n{stext}"
                            response = client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=[
                                    {"role": "system", "content": "أنتِ إيلينا، خبيرة تنظيم وقت وتخاطبين إيثان."},
                                    {"role": "user", "content": prompt}
                                ]
                            )
                            st.info(response.choices[0].message.content)
                        except: st.error("خطأ في الاتصال بالـ AI.")

            with col2:
                # زر الانتقال للشات
                if st.button("💬 حللي ما عليّ اليوم (Ask Elena)", use_container_width=True):
                    try:
                        # بناء النص لإرساله لتبويب إيلينا
                        items = []
                        for i in schedule_data:
                            if isinstance(i, dict):
                                n = i.get('المهمة/المحاضرة', 'مهمة')
                                d = i.get('الموعد', 'غير محدد')
                                items.append(f"- {n} بتاريخ {d}")
                            else:
                                items.append(f"- {str(i)}")
                        
                        full_schedule_text = "\n".join(items)
            
                        if "messages" not in st.session_state: 
                            st.session_state.messages = []
                        
                        # إضافة الرسالة لذاكرة الشات
                        st.session_state.messages.append({
                            "role": "user", 
                            "content": f"إيلينا، هاد جدولي لليوم، حلليه وانصحيني شو أعمل:\n{full_schedule_text}"
                        })
                        
                        st.success("تم إرسال الجدول! انتقل لتبويب Ask Elena 🤖")
                        st.balloons() 
                        
                    except Exception as e:
                        st.error(f"حدث خطأ: {str(e)}")
        else:
            st.info("📅 الجدول فارغ حالياً.")
    else:
        st.write("📅 اضغط على زر السحب لتحديث بياناتك.")
        
# --- داخل تبويب المساقات ---
with tabs[1]:
    st.subheader("📖 مستكشف المقررات الذكي")
    
    # 1. زر التحديث لجلب أسماء المواد
    if st.button("🔄 تحديث قائمة المقررات الرسمية"):
        uid = st.session_state.get("u_id")
        upass = st.session_state.get("u_pass")
        if uid and upass:
            with st.spinner("إيلينا تتواصل مع المودل..."):
                res = run_selenium_task(uid, upass, "timeline")
                if res and "courses" in res:
                    st.session_state.my_real_courses = res["courses"]
                    st.success(f"✅ تم العثور على {len(res['courses'])} مواد!")
                    st.rerun()
        else:
            st.warning("⚠️ يرجى المزامنة أولاً من القائمة الجانبية.")

    st.markdown("---")

    # 2. عرض القائمة المنسدلة والتصفح
    if st.session_state.get("my_real_courses"):
        selected_course = st.selectbox("اختر المادة لتصفح محتوياتها:", list(st.session_state.my_real_courses.keys()))
        course_url = st.session_state.my_real_courses[selected_course]
        
        col_browse, col_deep = st.columns(2)
        
        with col_browse:
            if st.button("🔍 تصفح سريع", use_container_width=True):
                uid = st.session_state.get("u_id")
                upass = st.session_state.get("u_pass")
                
                if uid and upass:
                    with st.spinner("جاري سحب الملفات والروابط..."):
                        res = run_selenium_task(uid, upass, "browse", course_url)
                        if res and "course_content" in res:
                            st.session_state.current_course_content = res["course_content"]
                            st.session_state.current_course_links = res.get("course_links", [])
                            st.session_state.summarized_items = [] 
                            st.success("✨ تم سحب محتوى المادة بنجاح!")
                else:
                    st.error("⚠️ بيانات المودل غير متوفرة، أعد المزامنة.")
        
        with col_deep:
            if st.button("🧠 مسح عميق (Deep Scan)", use_container_width=True, type="primary"):
                uid = st.session_state.get("u_id")
                upass = st.session_state.get("u_pass")
                
                if uid and upass:
                    progress_placeholder = st.empty()
                    status_text = st.empty()
                    
                    def update_progress(msg):
                        st.session_state.deep_scan_progress.append(msg)
                        status_text.text(msg)
                    
                    with st.spinner(f"🚀 جاري المسح العميق لمادة {selected_course}..."):
                        st.session_state.deep_scan_progress = []
                        result = deep_scan_course(uid, upass, course_url, update_progress)
                        
                        if result.get("success"):
                            # Store in session state with course name
                            if selected_course not in st.session_state.knowledge_base:
                                st.session_state.knowledge_base[selected_course] = {}
                            
                            st.session_state.knowledge_base[selected_course] = result["knowledge_base"]
                            
                            st.success(f"✅ تم المسح العميق بنجاح! تم استخراج {len(result['knowledge_base'])} عنصر.")
                            st.balloons()
                            
                            # Show summary
                            with st.expander("📊 ملخص المسح العميق"):
                                for name, data in result["knowledge_base"].items():
                                    icon = "📺" if data['type'] == 'video' else "📄" if data['type'] == 'pdf' else "📃"
                                    st.write(f"{icon} **{name}** - {len(data['content'])} حرف")
                        else:
                            st.error(f"❌ {result.get('error', 'فشل المسح')}")
                else:
                    st.warning("⚠️ يرجى المزامنة مع المودل أولاً.")

    # 3. عرض الملفات والروابط مع ميزة السحب العميق (PDF Scraping)
    if st.session_state.get("current_course_links"):
        st.write(f"### 📄 الملفات والروابط المكتشفة:")
        
        for i, link in enumerate(st.session_state.current_course_links):
            # --- الفحص الذكي لنوع الرابط ---
            url_low = link['url'].lower()
            name_low = link['name'].lower()
            
            # تمييز اليوتيوب حتى لو الرابط داخلي من المودل
            is_youtube = any(x in url_low for x in ["youtube", "youtu.be", "vimeo"]) or "فيديو" in name_low or "video" in name_low
            icon = "📺" if is_youtube else "📄"
            
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(f"{icon} **{link['name']}**")
                with col2:
                    st.link_button("📂 فتح", link['url'], use_container_width=True)
                with col3:
                    summarized = st.session_state.get("summarized_items", [])
                    is_done = link['url'] in summarized
                    btn_label = "✅ تم" if is_done else ("🧠 تلخيص" if is_youtube else "🪄 قراءة")
                    
                    if st.button(btn_label, key=f"sum_{i}", use_container_width=True):
                        if is_youtube:
                            with st.spinner(f"إيلينا تحلل الفيديو: {link['name']}..."):
                                summary = get_youtube_summary(link['url'])
                                if "messages" not in st.session_state: st.session_state.messages = []
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": f"🎬 **تلخيص فيديو:** {link['name']}\n\n{summary}"
                                })
                                st.session_state.summarized_items.append(link['url'])
                                st.success("✅ تم التلخيص في الشات!")
                                st.rerun()
                        else:
                            with st.spinner(f"إيلينا تقرأ الملف: {link['name']}..."):
                                uid = st.session_state.get("u_id")
                                upass = st.session_state.get("u_pass")
                                res = run_selenium_task(uid, upass, "scrape_pdf", link['url'])
                                
                                if res and "pdf_text" in res:
                                    if "pdf_memories" not in st.session_state: st.session_state.pdf_memories = {}
                                    st.session_state.pdf_memories[link['name']] = res["pdf_text"]
                                    st.session_state.summarized_items.append(link['url'])
                                    if "messages" not in st.session_state: st.session_state.messages = []
                                    st.session_state.messages.append({
                                        "role": "assistant",
                                        "content": f"📄 **قرأت الملف:** {link['name']}\n\nصار عندي علم بمحتواه، اسألني عنه في الشات!"
                                    })
                                    st.success("✅ تم سحب النص!")
                                    st.rerun()
                                else:
                                    st.error("❌ تعذر السحب. قد يكون الملف صورة أو رابط خارجي.")
                                                
with tabs[2]:
    st.subheader("📊 تقرير الأداء الشامل (كويزات وامتحانات)")
    st.caption("اختر المادة لسحب كشف درجاتها وتحليله بواسطة إيلينا")

    # 1. فحص إذا كانت المواد موجودة أصلاً
    if "my_real_courses" in st.session_state and st.session_state.my_real_courses:
        
        # قائمة لاختيار المادة المراد سحب درجاتها
        course_names = list(st.session_state.my_real_courses.keys())
        selected_course_for_grades = st.selectbox("اختر المادة:", course_names, key="grade_selector")
        target_course_url = st.session_state.my_real_courses[selected_course_for_grades]

        # زر سحب الدرجات للمادة المختارة
        if st.button(f"🚀 سحب درجات {selected_course_for_grades}", use_container_width=True):
            uid = st.session_state.get("u_id")
            upass = st.session_state.get("u_pass")
            
            if uid and upass:
                with st.spinner(f"إيلينا تفتح سجل درجات {selected_course_for_grades}..."):
                    # إرسال رابط المادة المختارة تحديداً لمهمة الدرجات
                    res = run_selenium_task(uid, upass, "grades", target_course_url) 
                    
                    if res and "data" in res:
                        # تخزين الدرجات مع اسم المادة عشان إيلينا تعرف عن شو بتحكي
                        st.session_state.detailed_grades_text = res["data"]
                        st.session_state.last_grade_course = selected_course_for_grades
                        st.success(f"✅ تم جلب درجات مادة {selected_course_for_grades} بنجاح!")
                        st.rerun()
                    else:
                        st.error("❌ فشل سحب الدرجات. تأكد أن المادة تحتوي على جدول درجات.")
            else:
                st.warning("⚠️ سجل دخول أولاً من القائمة الجانبية!")
    else:
        st.info("💡 يا إيثان، روح على التبويب الأول واضغط 'تحديث قائمة المقررات' عشان تظهر المواد هون.")

    # 2. عرض النتائج وتحليل إيلينا
    if st.session_state.get("detailed_grades_text"):
        current_course = st.session_state.get("last_grade_course", "المادة المختارة")
        st.markdown(f"### 📋 كشف درجات: {current_course}")
        
        # عرض الدرجات في منطقة نصية
        st.text_area("البيانات الخام من المودل:", st.session_state.detailed_grades_text, height=200)
    
        # زر طلب نصيحة إيلينا
        if st.button("🤖 اطلبي نصيحة إيلينا للتطوير", use_container_width=True):
            with st.spinner("إيلينا تراجع درجاتك وتقارنها بالمعايير..."):
                try:
                    prompt = f"""
                    أهلاً إيلينا، هذه درجاتي في مادة ({current_course}) المسحوبة من المودل:
                    ---
                    {st.session_state.detailed_grades_text}
                    ---
                    بناءً على هذه الأرقام:
                    1. ما هو تقديري الحالي في هذه المادة؟
                    2. ما هي نقاط قوتي ونقاط ضعفي بناءً على العلامات (مثلاً: علامة الكويز نازلة بس الامتحان عالية)؟
                    3. أعطيني خطة عمل من 3 خطوات لتحسين علامتي في الامتحان النهائي لهذه المادة تحديداً.
                    """
                    
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "أنتِ إيلينا، مستشارة أكاديمية ذكية جداً. تحللين الأرقام بدقة وتخاطبين إيثان بأسلوب محفز وعملي."},
                            {"role": "user", "content": prompt}
                        ]
                    )
                    st.markdown("---")
                    st.success(f"📈 **تحليل إيلينا لمادة {current_course}:**")
                    st.write(response.choices[0].message.content)
                except Exception as e:
                    st.error(f"حدث خطأ في التحليل: {e}")
        
# --- 4. الشات مع إيلينا ---
with tabs[3]:
    st.subheader("🤖 إيلين�� - المحلل الأكاديمي العميق")
    st.caption("مربع الدردشة ثابت في الأسفل لسهولة التواصل")
    
    # Knowledge Base Status Bar
    knowledge_base = st.session_state.get("knowledge_base", {})
    if knowledge_base:
        with st.expander("📚 قاعدة المعرفة الحالية - انقر لعرض التفاصيل", expanded=False):
            for course_name, items in knowledge_base.items():
                st.markdown(f"### 📖 {course_name}")
                for item_name, data in items.items():
                    icon = "📺" if data['type'] == 'video' else "📄" if data['type'] == 'pdf' else "📃"
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"{icon} {item_name}")
                    with col2:
                        st.caption(f"{len(data['content'])} حرف")
                    with col3:
                        st.caption(data['type'])
                st.markdown("---")
            
            if st.button("🗑️ مسح قاعدة المعرفة", type="secondary"):
                st.session_state.knowledge_base = {}
                st.rerun()
    else:
        st.info("💡 لم يتم إجراء مسح عميق بعد. انتقل لتبويب المقررات واستخدم 'مسح عميق' لبناء قاعدة المعرفة.")

    # 1. تجهيز البيانات من المسح العميق (Deep Scan Knowledge Base)
    knowledge_base = st.session_state.get("knowledge_base", {})
    pdf_memories = st.session_state.get("pdf_memories", {})
    
    # Build comprehensive context from Deep Scan
    deep_context = ""
    source_map = {}  # Track sources for citations
    
    for course_name, items in knowledge_base.items():
        deep_context += f"\n\n═══════ مادة: {course_name} ═══════\n"
        for item_name, data in items.items():
            content_preview = data['content'][:8000]  # Limit per item
            item_type = data['type']
            icon = "📺" if item_type == 'video' else "📄" if item_type == 'pdf' else "📃"
            
            deep_context += f"\n{icon} [{item_name}]:\n{content_preview}\n---\n"
            source_map[item_name] = {"course": course_name, "type": item_type}
    
    # Add individual PDF memories
    pdf_context = ""
    for name, text in pdf_memories.items():
        pdf_context += f"\n--- ملف: {name} ---\n{text[:6000]}\n"
        source_map[name] = {"course": "محتوى فردي", "type": "pdf"}
    
    course_data = st.session_state.get("current_course_content", "")
    
    # Show knowledge base status
    total_sources = len(source_map)
    if total_sources > 0:
        st.info(f"💡 إيلينا لديها حالياً {total_sources} مصدر في قاعدة المعرفة")

    # 2. 🔥 Enhanced System Prompt with Source Citation 🔥
    instruction = f"""
    أنتِ إيلينا، المحللة الأكاديمية الذكية الخاصة بإيثان. لديكِ قاعدة معرفة كاملة من المسح العميق للمواد.
    
    📚 قاعدة المعرفة المتاحة:
    {deep_context}
    {pdf_context}
    {course_data[:2000]}
    
    🎯 قواعد الإجابة الإلزامية:
    1. **الاقتباس المباشر**: عند الإجابة، اذكري اسم الملف/الفيديو المصدر بين قوسين [المصدر: اسم الملف]
    2. **الدقة التامة**: استخرجي القوانين، الأرقام، المسائل، والتعاريف كما وردت بالضبط
    3. **التنقيب العميق**: ابحثي في كل المصادر المتاحة وقارني المعلومات
    4. **الأسئلة المتوقعة**: استخرجيها من النقاط الصعبة في النصوص الفعلية، لا تخمني
    5. **الربط الذكي**: إذا كان السؤال عن موضوع معين، اجمعي المعلومات من كل الملفات ذات الصلة
    6. **الشفافية**: إذا لم تجدي المعلومة في المصادر المتاحة، قولي ذلك صراحة
    
    💬 أسلوب الرد:
    - ابدأي بذكر المصادر التي استخدمتها
    - قدمي الإجابة بتفصيل مع الاستشهاد
    - اختمي بنصيحة عملية أو خطوة تالية
    
    مثال على الرد الصحيح:
    "بناءً على [المصدر: محاضرة الفصل الثاني - PDF] و [المصدر: شرح الدكتور - فيديو]، 
    القانون الأول ينص على... وفي الملف تم ذكر مثال عملي في الصفحة..."
    """
    
    # Add individual PDF memories
    pdf_context = ""
    for name, text in pdf_memories.items():
        pdf_context += f"\n--- ملف: {name} ---\n{text[:6000]}\n"
        source_map[name] = {"course": "محتوى فردي", "type": "pdf"}
    
    course_data = st.session_state.get("current_course_content", "")
    
    # Show knowledge base status
    total_sources = len(source_map)
    if total_sources > 0:
        st.info(f"💡 إيلينا لديها حالياً {total_sources} مصدر في قاعدة المعرفة")

    # 2. 🔥 Enhanced System Prompt with Source Citation 🔥
    instruction = f"""
    أنتِ إيلينا، المحللة الأكاديمية الذكية الخاصة بإيثان. لديكِ قاعدة معرفة كاملة من المسح العميق للمواد.
    
    📚 قاعدة المعرفة المتاحة:
    {deep_context}
    {pdf_context}
    {course_data[:2000]}
    
    🎯 قواعد الإجابة الإلزامية:
    1. **الاقتباس المباشر**: عند الإجابة، اذكري اسم الملف/الفيديو المصدر ب��ن قوسين [المصدر: اسم الملف]
    2. **الدقة التامة**: استخرجي القوانين، الأرقام، المسائل، والتعاريف كما وردت بالضبط
    3. **التنقيب العميق**: ابحثي في كل المصادر المتاحة وقارني المعلومات
    4. **الأسئلة المتوقعة**: استخرجيها من النقاط الصعبة في النصوص الفعلية، لا تخمني
    5. **الربط الذكي**: إذا كان السؤال عن موضوع معين، اجمعي المعلومات من كل الملفات ذات الصلة
    6. **الشفافية**: إذا لم تجدي المعلومة في المصادر المتاحة، قولي ذلك صراحة
    
    💬 أسلوب الرد:
    - ابدأي بذكر المصادر التي استخدمتها
    - قدمي الإجابة بتفصيل مع الاستشهاد
    - اختمي بنصيحة عملية أو خطوة تالية
    
    مثال على الرد الصحيح:
    "بناءً على [المصدر: محاضرة الفصل الثاني - PDF] و [المصدر: شرح الدكتور - فيديو]، 
    القانون الأول ينص على... وفي الملف تم ذكر مثال عملي في الصفحة..."
    """

    # 3. عرض الرسايل (Container)
    # ملاحظة: شلت الـ height عشان الـ chat_input يثبت تلقائياً في قاع الصفحة (Fixed Bottom)
    chat_container = st.container()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # عرض سجل المحادثة
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # 4. 🔥 مربع الكتابة (Sticky/Fixed Input) 🔥
    # لما يكون st.chat_input آخر عنصر في الـ tab، بضل ثابت تحت
    if chat_input := st.chat_input("اسألي إيلينا عن أي تفصيل في ملفاتك..."):
        # إضافة رسالة إيثان للسجل
        st.session_state.messages.append({"role": "user", "content": chat_input})
        
        # عرض رسالة إيثان فوراً
        with chat_container:
            with st.chat_message("user"):
                st.markdown(chat_input)

        # توليد رد إيلينا
        with chat_container:
            with st.chat_message("assistant"):
                try:
                    with st.spinner("إيلينا تغوص في الملفات..."):
                        response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile", 
                            messages=[{"role": "system", "content": instruction}] + st.session_state.messages,
                            temperature=0.4
                        )
                        answer = response.choices[0].message.content
                        st.markdown(answer)
                        # حفظ الرد في السجل
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                except Exception as e:
                    st.error(f"عذراً إيثان، واجهت مشكلة: {e}")
        
        # تحديث الصفحة لضمان ترتيب الرسايل وبقاء المربع تحت
        st.rerun()

    # 5. زر المسح (Sidebar عشان يضل الشات نظيف)
    if st.sidebar.button("🗑️ مسح محادثة إيلينا", key="clear_chat"):
        st.session_state.messages = []
        st.rerun()
                
# --- 5. لوحة التحكم (المطور فقط) ---
with tabs[4]:
    # 1. الفحص الرئيسي: هل المستخدم هو المطور (إيثان)؟
    if st.session_state.get("user_role") == "developer":
        role_name = "إيثان"
        st.subheader(f"🛠️ لوحة تحكم المطور: {role_name}")
        
        # --- قسم سجل النشاط ---
        if st.button("📊 عرض سجل النشاط"):
            if os.path.exists("activity_log.json"):
                with open("activity_log.json", "r") as f:
                    logs = json.load(f)
                st.table(logs[-10:])
            else:
                st.info("لا يوجد سجلات حالياً.")
        
        db = load_db()
        
        # --- 1. إحصائيات المستخدمين ---
        st.write("👥 بيانات النظام والمستخدمين:")
        st.json(db)
        
        st.markdown("---")
        
        # --- 2. توليد أكواد زمنية ---
        st.write("🔑 **توليد أكواد بريميوم زمنية**")
        col_c, col_t = st.columns([2, 1])
        with col_c:
            new_c = st.text_input("أدخل الكود الجديد:", key="admin_code_in")
        with col_t:
            duration = st.selectbox("المدة:", ["1H", "1D", "1M", "1Y"], key="dur_in")
            
        if st.button("حفظ الكود الزمني ✅", use_container_width=True):
            if new_c:
                if "timed_codes" not in db: db["timed_codes"] = {}
                db["timed_codes"][new_c] = duration
                save_db(db)
                st.success(f"تم حفظ الكود {new_c} لمدة {duration}")
                st.rerun()
            else: 
                st.warning("اكتب الكود أولاً")

        if "timed_codes" in db and db["timed_codes"]:
            st.write("📋 الأكواد المتوفرة حالياً:", db["timed_codes"])

        st.markdown("---")

        # --- 3. إدارة الاشتراكات (إلغاء الاشتراك) ---
        st.write("🚫 **إدارة الاشتراكات الفعالة**")
        prime_users = [u for u, data in db.items() if isinstance(data, dict) and data.get("status") == "Prime"]
        
        if prime_users:
            selected_user = st.selectbox("اختر مستخدم لإلغاء اشتراكه:", prime_users)
            if st.button(f"إلغاء اشتراك {selected_user} فوراً ⚠️"):
                db[selected_user]["status"] = "Standard"
                if "expire_at" in db[selected_user]:
                    del db[current_u]["expire_at"] # ملاحظة: تأكد إنها selected_user مش current_u
                save_db(db)
                st.error(f"تم سحب رتبة البريميوم من {selected_user}")
                st.rerun()
        else:
            st.info("لا يوجد مستخدمين بريميوم حالياً.")

    # 2. إذا لم يكن المطور (else واحدة فقط في النهاية)
    else:
        st.error("🚫 عذراً، هذا التبويب مخصص للمطور (إيثان) فقط.")
        
# --- 1. الدوال (لازم تكون برة التبويبات وفي مستوى الصفر من المسافات) ---
def get_local_time():
    # توقيت فلسطين (UTC+2)
    return datetime.utcnow() + timedelta(hours=2)

# --- 2. السايدبار (مستقل تماماً وفي مستوى الصفر) ---
with st.sidebar:
    st.markdown("---")
    # 1. عرض تاريخ انتهاء الاشتراك بتنسيق لوني احترافي
    if st.session_state.get("user_status") == "Prime":
        db = load_db() 
        current_u = st.session_state.get("username", "user")
        expire_str = db.get(current_u, {}).get("expire_at")
        
        if expire_str:
            try:
                dt_obj = datetime.strptime(expire_str, "%Y-%m-%d %H:%M:%S")
                pretty_date = dt_obj.strftime("%Y/%m/%d - %I:%M %p")
                
                # حساب الوقت المتبقي (توقيت فلسطين)
                time_diff = dt_obj - get_local_time()
                total_seconds = time_diff.total_seconds()
                
                if total_seconds > 0:
                    if total_seconds > 86400: # أكثر من يوم
                        st.success(f"👑 **عضوية برايم نشطة**\n\n📅 ينتهي في: {pretty_date}")
                    else: # أقل من يوم
                        st.warning(f"⏳ **اشتراكك أوشك على الانتهاء!**\n\n📅 الموعد: {pretty_date}")
                else:
                    # تنفيذ الإلغاء التلقائي
                    db[current_u]["status"] = "Standard"
                    if "expire_at" in db[current_u]:
                        del db[current_u]["expire_at"]
                    save_db(db)
                    
                    st.session_state.user_status = "Standard"
                    st.error("⚠️ **انتهى الاشتراك!**\n\nتم تحويل حسابك للوضع العادي.")
                    st.rerun() 
            except Exception as e:
                st.info(f"📅 ينتهي اشتراكك في: {expire_str}")

    st.markdown("---")
    
    # 2. قسم المزامنة
    st.header("⚙️ المزامنة")
    uid = st.text_input("الرقم الجامعي", value=st.session_state.get("u_id", ""))
    upass = st.text_input("كلمة المرور", type="password", value=st.session_state.get("u_pass", ""))

    if st.button("🚀 Sync Now", use_container_width=True):
        if uid and upass:
            with st.spinner("جاري المزامنة وسحب بياناتك من المودل..."):
                # استدعاء دالة السيلينيوم
                res = run_selenium_task(uid, upass, "timeline")
                
                if res and "courses" in res:
                    # تخزين البيانات في الجلسة (Session State)
                    st.session_state.update({
                        "u_id": uid,
                        "u_pass": upass,
                        "my_real_courses": res['courses'],
                        "user_schedule": res.get('timeline_list', []), 
                        "student_name": res.get('student_name', 'مستخدم إيلينا'), # هنا سيظهر اسمك الحقيقي لو السيلينيوم سحبه صح
                        "is_synced": True
                    })
                    
                    # تحديث عداد المزامنات في قاعدة البيانات
                    try:
                        db = load_db()
                        email_u = st.session_state.get("user_email")
                        if email_u and st.session_state.user_role != "developer" and st.session_state.user_status != "Prime":
                            if email_u not in db: 
                                db[email_u] = {}
                            db[email_u]["sync_count"] = db[email_u].get("sync_count", 0) + 1
                            save_db(db)
                    except:
                        pass

                    # رسالة النجاح والترحيب بالاسم المسحوب
                    st.success(f"✅ تم الربط! أهلاً بك يا {st.session_state.student_name}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ فشلت المزامنة، يرجى التأكد من صحة بيانات المودل أو المحاولة لاحقاً.")
        else:
            st.warning("⚠️ يرجى إدخال الرقم الجامعي وكلمة المرور أولاً.")

    st.markdown("---")
    
    # 3. الإعدادات المتقدمة
    with st.expander("⚙️ الإعدادات المتقدمة"):
        if st.button("🔴 تسجيل الخروج النهائي", use_container_width=True):
            # 1. مسح الكوكيز (عشان ما يرجع يدخلك أوتوماتيك)
            if "username" in cookies:
                del cookies["username"]
                cookies.save()
            
            # 2. تصفير الـ Session State بالكامل
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            # 3. الضربة القاضية: مسح الـ LocalStorage والتوجيه لرابط الخروج
            st.components.v1.html(
                """
                <script>
                    // مسح الخزنة الدائمة في المتصفح
                    window.parent.localStorage.clear();
                    window.parent.sessionStorage.clear();
                    
                    // التوجيه لرابط فيه علامة logout عشان نضمن إنه الكوكيز ما ترجع
                    let currentPath = window.parent.location.origin + window.parent.location.pathname;
                    window.parent.location.href = currentPath + '?logout=true';
                </script>
                """,
                height=0,
            )
            st.success("جاري تسجيل الخروج...")
            st.stop()

    # 4. كود المطور (إيثان)
    if st.session_state.get("user_role") == "developer":
    with st.expander("🛠️ لوحة تحكم المطور"):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧹 مسح الكاش"):
                st.cache_data.clear()
        with col2:
            # زر لتحميل قاعدة البيانات للمراجعة
            if os.path.exists("users_db.json"):
                with open("users_db.json", "rb") as f:
                    st.download_button("📂 تحميل قاعدة البيانات", f, file_name="users_db.json")
