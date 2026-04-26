import json
import streamlit as st
import markdown
import smtplib
import random
import json
import os
import io
import requests
import sys
import re
import streamlit.components.v1 as components
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

# --- 1. الثوابت والإعدادات الأساسية ---
LOCAL_MODE = os.environ.get("ELENA_LOCAL", "") == "1" or os.name == "nt"
EMAIL_ADDRESS = "EMAIL_ADDRESS" 
EMAIL_PASSWORD = "EMAIL_PASSWORD" 
DB_FILE = "users_db.json"
MAX_FREE_SYNCS = 10
PDF_TEXT_LIMIT = 8000
GROQ_MODEL = "llama-3.3-70b-versatile"

# --- 1. الثوابت والإعدادات الأساسية ---
LOCAL_MODE = os.environ.get("ELENA_LOCAL", "") == "1" or os.name == "nt"
DB_FILE = "users_db.json"
MAX_FREE_SYNCS = 10
PDF_TEXT_LIMIT = 8000
GROQ_MODEL = "llama-3.3-70b-versatile"

# ==========================================
# --- إعداد الكوكيز (مرة واحدة فقط) ---
# ==========================================
cookies = EncryptedCookieManager(prefix="elena", password="EM2006_secret_key")

if not cookies.ready():
    st.stop()

# ==========================================
# --- 1. تعريف دوال الداتا بيز الأساسية ---
# ==========================================
def load_db():
    """Load user database from JSON file."""
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_db(db_data):
    """Save user database to JSON file."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db_data, f, ensure_ascii=False, indent=4)

# ==========================================
# --- 2. نظام الصفحات (Routing) والـ CSS ---
# ==========================================
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'landing'

st.markdown("""
<style>
    /* زر الرجوع للأعلى */
    #myBtn {
        display: none; position: fixed; bottom: 20px; right: 30px; z-index: 999; 
        font-size: 22px; border: none; outline: none; background-color: #3498db; 
        color: white; cursor: pointer; padding: 10px 15px; border-radius: 50%; 
        box-shadow: 0 4px 8px rgba(0,0,0,0.3); transition: 0.3s;
    }
    #myBtn:hover { background-color: #2980b9; transform: scale(1.1); }
    
    /* تصميم صفحة الهبوط */
    .hero-container { text-align: center; padding: 80px 20px; animation: fadeIn 1.5s; }
    .hero-title { font-size: 4rem; font-weight: 900; color: #2c3e50; margin-bottom: 10px; }
    .hero-subtitle { font-size: 1.5rem; color: #7f8c8d; margin-bottom: 40px; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
</style>

<button onclick="topFunction()" id="myBtn" title="اطلع لفوق">⬆️</button>
<script>
    let mybutton = document.getElementById("myBtn");
    window.addEventListener('scroll', function() {
        if (window.scrollY > 300 || document.documentElement.scrollTop > 300) {
            mybutton.style.display = "block";
        } else {
            mybutton.style.display = "none";
        }
    }, true);
    function topFunction() {
        window.parent.document.querySelector('.main .block-container').scrollTo({top: 0, behavior: 'smooth'});
    }
</script>
""", unsafe_allow_html=True)

# ==========================================
# --- 3. عرض صفحة الهبوط (Landing Page) ---
# ==========================================
if st.session_state.current_page == 'landing':
    st.markdown("""<style>[data-testid="collapsedControl"] { display: none; }</style>""", unsafe_allow_html=True)
    
    st.markdown("""
        <div class="hero-container">
            <h1 class="hero-title">🤖 إيلينا AI</h1>
            <p class="hero-subtitle">مساعدك الأكاديمي الذكي اللي رح يغير طريقة دراستك للأبد.</p>
            <p>تخطيط آلي، تلخيص، اختبارات ذكية، ومزامنة مع جامعتك بضغطة زر!</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 ابدأ مجاناً الآن (إنشاء حساب)", use_container_width=True, type="primary"):
            st.session_state.current_page = 'register'
            st.rerun()
        
        st.markdown("<div style='text-align: center; margin-top: 15px;'>", unsafe_allow_html=True)
        if st.button("لديك حساب؟ تسجيل الدخول", use_container_width=True):
            st.session_state.current_page = 'login'
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.stop() # 🛑 بيوقف الكود هنا

# ==========================================
# --- 2. عرض صفحة تسجيل الدخول (Login Page) ---
# ==========================================
elif st.session_state.current_page == 'login':
    st.markdown("""<style>[data-testid="collapsedControl"] { display: none; }</style>""", unsafe_allow_html=True)
    
    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        st.markdown("<h2 style='text-align: center; margin-top: 40px;'>🔑 الدخول إلى إيلينا</h2>", unsafe_allow_html=True)
        
        with st.container(border=True):
            u = st.text_input("اسم المستخدم", key="l_u")
            p = st.text_input("كلمة السر", type="password", key="l_p")
            
            db = load_db()
            col_in, col_forgot = st.columns(2)
            
            if col_in.button("دخول 🚪", use_container_width=True, type="primary"):
                # دخول المطور إيثان السري 👑
                if u == "ethan" and p == "EM2006":
                    cookies["username"] = "ethan"
                    cookies.save()
                    st.session_state.update({"is_logged_in": True, "user_role": "developer", "user_status": "Prime", "username": "Ethan"})
                    st.session_state.current_page = 'main_app'
                    st.rerun()
                # دخول الطلاب العادي
                elif u in db and db[u]['password'] == p:
                    cookies["username"] = u
                    cookies.save()
                    st.session_state.update({"is_logged_in": True, "user_role": "user", "user_status": db[u].get('status', 'Standard'), "username": u})
                    st.session_state.current_page = 'main_app'
                    st.rerun()
                else: 
                    st.error("❌ بيانات خاطئة!")

            # نظام استعادة كلمة المرور تبعك
            if col_forgot.button("نسيت كلمة السر؟", use_container_width=True):
                st.session_state.show_reset = True

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
                            st.success("تم التحديث! سجل دخولك الآن.")
                            del st.session_state.show_reset
                            st.rerun()
                        else: st.error("الكود خطأ")

        if st.button("⬅️ رجوع للرئيسية", use_container_width=True):
            st.session_state.current_page = 'landing'
            st.rerun()
            
    st.stop()

# ==========================================
# --- 3. عرض صفحة إنشاء الحساب (Register) ---
# ==========================================
elif st.session_state.current_page == 'register':
    st.markdown("""<style>[data-testid="collapsedControl"] { display: none; }</style>""", unsafe_allow_html=True)
    
    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        st.markdown("<h2 style='text-align: center; margin-top: 40px;'>✨ إنشاء حساب جديد</h2>", unsafe_allow_html=True)
        
        with st.container(border=True):
            db = load_db()
            nu = st.text_input("اسم مستخدم جديد", key="s_u")
            ne = st.text_input("Gmail", key="s_e")
            np = st.text_input("كلمة سر جديدة", type="password", key="s_p")
            
            if st.button("إرسال كود التحقق 📧", type="primary", use_container_width=True):
                if nu in db: st.error("موجود مسبقاً")
                elif not ne.endswith("@gmail.com"): st.warning("استخدم Gmail")
                else:
                    otp = random.randint(1000, 9999)
                    if send_otp(ne, otp):
                        st.session_state.temp_otp, st.session_state.temp_data = otp, {"u": nu, "p": np, "e": ne}
                        st.success("تفقد إيميلك")
            
            if "temp_otp" in st.session_state:
                otp_in = st.text_input("أدخل كود التحقق:")
                if st.button("تأكيد الحساب ✅"):
                    if otp_in == str(st.session_state.temp_otp):
                        d = st.session_state.temp_data
                        db[d['u']] = {"password": d['p'], "email": d['e'], "status": "Standard", "sync_count": 0}
                        save_db(db)
                        st.success("تم! جاري تحويلك...")
                        del st.session_state.temp_otp
                        
                        # دخول تلقائي
                        cookies["username"] = d['u']
                        cookies.save()
                        st.session_state.update({"is_logged_in": True, "user_role": "user", "user_status": "Standard", "username": d['u']})
                        st.session_state.current_page = 'main_app'
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("الكود غير صحيح")

        if st.button("⬅️ رجوع للرئيسية", use_container_width=True):
            st.session_state.current_page = 'landing'
            st.rerun()
            
    st.stop() # 🛑 بيوقف الكود هنا

# ==========================================
# --- 6. التطبيق الرئيسي (Main App) ---
# ==========================================
# إظهار القائمة الجانبية لأننا دخلنا التطبيق
st.markdown("""<style>[data-testid="collapsedControl"] { display: block; }</style>""", unsafe_allow_html=True)

# --- 2. تعريف جميع الدوال أولاً لتجنب NameError ---

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

def send_otp(target_email, code):
    if not target_email or '@' not in target_email: return False
    
    # سحب البيانات مباشرة من إعدادات السيرفر الآمنة
    try:
        EMAIL_ADDRESS = st.secrets["GMAIL_USER"]
        EMAIL_PASSWORD = st.secrets["GMAIL_PASS"]
    except Exception:
        st.error("❌ السيرفر لا يستطيع العثور على الباسوورد في الـ Secrets!")
        return False

    try:
        msg = EmailMessage()
        msg.set_content(f"كود التحقق الخاص بك هو: {code}")
        msg['Subject'] = "تفعيل حساب إيلينا AI"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = target_email
        
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=10) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        return True
        
    except Exception as e:
        # كود لكشف ما يراه السيرفر فعلياً (للتأكد)
        st.error(f"تفاصيل الخطأ: {str(e)}")
        st.info(f"🔍 السيرفر يحاول الدخول بإيميل: {EMAIL_ADDRESS}")
        st.info(f"🔍 طول الباسوورد الذي يراه السيرفر: {len(EMAIL_PASSWORD)} حرف (يجب أن يكون 16)")
        return False

def get_youtube_summary(video_url):
    if not video_url:
        return "❌ الرجاء إدخال رابط فيديو صحيح."
    
    try:
        resolved_url = video_url
        try:
            resp = requests.get(video_url, allow_redirects=True, timeout=10)
            if resp.url:
                resolved_url = resp.url
        except Exception:
            resolved_url = video_url

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

        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
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
        return f"❌ خطأ تقني: {str(e)}"

def send_elena_email(receiver_email, subject, html_body):
    try:
        # نسحب نفس الباسوورد اللي زبطناه في الـ Secrets
        EMAIL_ADDRESS = st.secrets["GMAIL_USER"]
        EMAIL_PASSWORD = st.secrets["GMAIL_PASS"]
        
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = f"Elena AI <{EMAIL_ADDRESS}>"
        msg['To'] = receiver_email
        
        # بنخبر الإيميل إنو هاد تصميم HTML مش نص عادي
        msg.set_content("يرجى تفعيل عرض HTML لرؤية الرسالة.")
        msg.add_alternative(html_body, subtype='html')
        
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=10) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        return str(e)

def deep_scan_course(username, password, course_url, progress_callback=None):
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
        
        driver.get("https://sso.iugaza.edu.ps/saml/module.php/core/loginuserpass")
        time.sleep(3)
        driver.find_element(By.ID, "username").send_keys(username)
        p_field = driver.find_element(By.ID, "password")
        p_field.send_keys(password)
        p_field.send_keys(Keys.ENTER)
        time.sleep(12)
        
        driver.get(course_url)
        time.sleep(5)
        
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
        
        for idx, link in enumerate(links_to_scan, 1):
            try:
                if progress_callback:
                    progress_callback(f"📖 [{idx}/{total_links}] معالجة: {link['name']}")
                
                url_lower = link['url'].lower()
                content = ""
                content_type = "unknown"
                
                if any(x in url_lower for x in ["youtube", "youtu.be", "vimeo"]) or "watch?v=" in url_lower:
                    try:
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
                            content = pdf_text[:20000] 
                            content_type = "pdf"
                        else:
                            driver.get(link['url'])
                            time.sleep(4)
                            content = driver.find_element(By.TAG_NAME, "body").text[:20000]
                            content_type = "page"
                    except:
                        content = "[فشل استخراج محتوى PDF]"
                        content_type = "pdf"
                
                else:
                    try:
                        driver.get(link['url'])
                        time.sleep(4)
                        try:
                            content = driver.find_element(By.ID, "region-main").text
                        except:
                            content = driver.find_element(By.TAG_NAME, "body").text
                        content = content[:20000] 
                        content_type = "page"
                    except:
                        content = "[فشل الوصول للصفحة]"
                        content_type = "page"
                
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

def run_selenium_task(username, password, task_type="timeline", target_url=None, base_url="http://elearning.iugaza.edu.ps"):
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
        
        # ==========================================
        # --- نظام الدخول الذكي (متعدد الجامعات) ---
        # ==========================================
        if "iugaza.edu.ps" in base_url:
            # دخول مخصص للجامعة الإسلامية (SSO)
            driver.get("https://sso.iugaza.edu.ps/saml/module.php/core/loginuserpass")
            time.sleep(3)
            driver.find_element(By.ID, "username").send_keys(username)
            p_field = driver.find_element(By.ID, "password")
            p_field.send_keys(password)
            p_field.send_keys(Keys.ENTER)
        else:
            # دخول افتراضي لأي جامعة بتستخدم Moodle عالمياً
            login_url = f"{base_url.rstrip('/')}/login/index.php"
            driver.get(login_url)
            time.sleep(3)
            # المودل الافتراضي بيستخدم هدول الـ IDs
            driver.find_element(By.ID, "username").send_keys(username)
            p_field = driver.find_element(By.ID, "password")
            p_field.send_keys(password)
            p_field.send_keys(Keys.ENTER)
            
        time.sleep(15) # الانتظار لحين تحميل الصفحة الرئيسية بعد الدخول

        # ==========================================
        # --- سحب اسم الطالب ---
        # ==========================================
        student_name = "طالب جامعي"
        
        # 1. المحاولة الأولى: السحب من النصوص في القائمة العلوية
        for sel in [".usertext", ".userbutton .usertext", ".usermenu .usertext", "span.usertext", ".logininfo a"]:
            try:
                name_element = driver.find_element(By.CSS_SELECTOR, sel)
                text = name_element.text.strip()
                if text and len(text) > 3: # التأكد إنه مش نص فارغ
                    student_name = text
                    break
            except: 
                continue
                
        # 2. المحاولة الثانية (الضربة القاضية): السحب من صورة الملف الشخصي
        if student_name == "طالب جامعي":
            try:
                img_elements = driver.find_elements(By.CSS_SELECTOR, "img.userpicture")
                for img in img_elements:
                    alt_text = img.get_attribute("alt") or img.get_attribute("title")
                    if alt_text:
                        # تنظيف النص من الكلمات الزائدة
                        clean_name = alt_text.replace("Picture of", "").replace("صورة", "").strip()
                        if clean_name and len(clean_name) > 3:
                            student_name = clean_name
                            break
            except:
                pass

        # ==========================================
        # --- تنفيذ المهام حسب الطلب ---
        # ==========================================
        if task_type == "timeline":
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='course/view.php?id=']")
            course_map = {}
            for l in links:
                t = l.text.strip()
                if len(t) > 10 and t not in course_map:
                    course_map[t] = l.get_attribute("href")
            
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
                    grade_data = driver.find_element(By.CSS_SELECTOR, "table.user-grade, table").text
                    return {"data": grade_data, "student_name": student_name}
                except:
                    return {"error": "لم يتم العثور على جدول الدرجات."}

        elif task_type == "browse":
            if target_url:
                driver.get(target_url)
                time.sleep(8)
                try: content = driver.find_element(By.ID, "region-main").text
                except: content = driver.find_element(By.TAG_NAME, "body").text
                
                found_links = []
                link_elements = driver.find_elements(By.CSS_SELECTOR, ".instancename, .aalink")
                for elem in link_elements:
                    try:
                        name = elem.text.strip()
                        parent = elem.find_element(By.XPATH, "./..") if elem.tag_name != 'a' else elem
                        url = parent.get_attribute("href")
                        if url and name and "course/view.php" not in url:
                            found_links.append({"name": name, "url": url})
                    except: continue
                
                return {"course_content": content, "course_links": found_links, "student_name": student_name}

        elif task_type == "scrape_pdf":
            if target_url:
                try:
                    cookies = {c['name']: c['value'] for c in driver.get_cookies()}
                    response = requests.get(target_url, cookies=cookies, timeout=15)
                    
                    if response.status_code == 200:
                        pdf_file = io.BytesIO(response.content)
                        reader = PdfReader(pdf_file)
                        pdf_text = ""
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

def get_local_time():
    local_tz = pytz.timezone('Asia/Gaza')
    return datetime.now(local_tz)

def get_groq_api_key():
    env_key = os.environ.get("GROQ_API_KEY")
    if env_key:
        return env_key
    try:
        return st.secrets.get("GROQ_API_KEY")
    except Exception:
        return None

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


# --- 3. إعداد الواجهة والمكتبات (Streamlit setup) ---
st.set_page_config(page_title="Elena AI", page_icon="👑", layout="wide")
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); color: white; }
    [data-testid="stSidebar"] { background-color: rgba(15, 12, 41, 0.8); }
    .login-box { background-color: rgba(255, 255, 255, 0.05); padding: 40px; border-radius: 20px; border: 1px solid rgba(255, 215, 0, 0.3); text-align: center; }
    .prime-badge { background: linear-gradient(45deg, #f39c12, #f1c40f); color: black; padding: 4px 12px; border-radius: 12px; font-weight: bold; font-size: 18px; box-shadow: 0 4px 15px rgba(243, 156, 18, 0.3); }
    </style>
    """, unsafe_allow_html=True)

GROQ_API_KEY = get_groq_api_key() or "<YOUR_GROQ_API_KEY>"
if not GROQ_API_KEY:
    st.error("❌ خطأ: مفتاح GROQ_API_KEY غير موجود في إعدادات السيرفر!")
    st.stop()
else:
    client = Groq(api_key=GROQ_API_KEY)

init_session_state()

if not LOCAL_MODE and "driver" not in st.session_state:
    with st.spinner("جاري تهيئة إيلينا على السيرفر السحابي... 👑"):
        init_shared_driver()

driver = st.session_state.get("driver")

# --- 4. معالجة تسجيل الدخول الأوتوماتيكي واليدوي ---

if st.query_params.get("logout") == "true":
    st.session_state["is_logged_in"] = False
    if "username" in cookies:
        del cookies["username"]
        cookies.save()
    st.query_params.clear() 
    st.rerun() 

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
        
# --- 5. الواجهة الرئيسية (التطبيق بعد الدخول) ---
db = load_db()
current_u = st.session_state.get("username", "user")

if st.session_state.get("user_status") == "Prime":
    expire_str = db.get(current_u, {}).get("expire_at")
    if expire_str:
        expire_dt = datetime.strptime(expire_str, "%Y-%m-%d %H:%M:%S")
        if get_local_time().replace(tzinfo=None) > expire_dt:
            db[current_u]["status"] = "Standard"
            save_db(db)
            st.session_state.user_status = "Standard"
            st.warning("⚠️ انتهت مدة اشتراكك البريميوم، تم تحويل حسابك للوضع المجاني.")
            st.rerun()

user_syncs = db[current_u].get("sync_count", 0) if current_u in db else 0

badge = '<span class="prime-badge">👑</span>' if st.session_state.user_status == "Prime" else ""
st.markdown(f"## Elena Student AI {badge}", unsafe_allow_html=True)

raw_name = st.session_state.get("student_name", "طالب جامعي")
# إزالة الحروف الإنجليزية لو المودل رجع الاسم لغتين
arabic_name = re.sub(r'[A-Za-z]', '', raw_name).strip()
name_parts = arabic_name.split()

if st.session_state.get("user_role") == "developer":
    friendly_name = "إيثان"
elif len(name_parts) >= 2:
    # ياخذ الاسم الأول والأخير (مثلاً: ايهاب الحايك)
    friendly_name = f"{name_parts[0]} {name_parts[-1]}"
elif len(name_parts) == 1:
    friendly_name = name_parts[0]
else:
    friendly_name = "يا بطل"
# الترحيب
role_name = friendly_name
if st.session_state.get("user_status") == "Prime":
    badge = '<span style="background:#FFD700; color:black; padding:2px 10px; border-radius:10px; font-size:18px; margin-right:10px; font-weight:bold;">PRIME MEMBER 👑</span>'
else:
    badge = '<span style="background:#f0f2f6; color:#666; padding:2px 10px; border-radius:10px; font-size:18px; margin-right:10px;">STANDARD 🎓</span>'

st.markdown(f"<h2>أهلاً {role_name} {badge}</h2>", unsafe_allow_html=True)

if not st.session_state.get("is_synced", False):
    st.warning("⚠️ حسابك غير مرتبط بالمودل حالياً...")
else:
    st.success(f"🔗 متصل الآن بحسابك: {st.session_state.student_name}")

st.markdown("---")

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
            code_in = st.text_input("أدخل كود الاشتراك:", key="upgrade_input_field")
            if st.button("تفعيل الآن ✅"):
                db = load_db()
                timed_codes = db.get("timed_codes", {})

                if code_in in timed_codes:
                    dur = timed_codes[code_in]
                    now = get_local_time() 
                    
                    # النظام المحمي لحساب الوقت
                    if dur == "5 Min": 
                        expire_date = now + timedelta(minutes=5)
                    elif dur == "10 Min": 
                        expire_date = now + timedelta(minutes=10)
                    elif dur == "1H": 
                        expire_date = now + timedelta(hours=1)
                    elif dur == "1D": 
                        expire_date = now + timedelta(days=1)
                    elif dur == "1M": 
                        expire_date = now + timedelta(days=30)
                    elif dur == "1Y": 
                        expire_date = now + timedelta(days=365)
                    else:
                        # في حال كان الكود محفوظ بصيغة قديمة أو غير معروفة، نعطيه يوم افتراضي
                        expire_date = now + timedelta(days=1)

                    curr_u = st.session_state.username
                    db[curr_u]["status"] = "Prime"
                    db[curr_u]["expire_at"] = expire_date.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # حذف الكود بعد استخدامه
                    del db["timed_codes"][code_in]
                    save_db(db)
                    
                    st.session_state.user_status = "Prime"
                    st.success(f"✅ تم التفعيل بنجاح! ينتهي اشتراكك في: {expire_date.strftime('%Y/%m/%d - %I:%M %p')}")
                    st.rerun()
                    
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

tabs = st.tabs(["📅 المخطط الذكي", "📚 المقررات", "📊 الدرجات", "💬 Ask Elena", "🛠️ الإدارة"])

with tabs[0]:
    st.subheader("📅 المخطط الزمني الذكي")
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

    schedule_data = st.session_state.get("user_schedule")
    if schedule_data:
        st.write("### 📋 جدول المهام القادمة:")
        if isinstance(schedule_data, list) and len(schedule_data) > 0:
            st.table(schedule_data)
            
            # الأزرار الأصلية
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🧐 تحليل سريع هنا"):
                    with st.spinner("إيلينا تدرس المواعيد..."):
                        try:
                            stext = "\n".join([f"- {i.get('المهمة/المحاضرة', 'مهمة')} ({i.get('الموعد', 'ميعاد غير محدد')})" for i in schedule_data])
                            prompt = f"حللي جدولي الجامعي ورتبي أولوياتي بأسلوب مشجع:\n{stext}"
                            response = client.chat.completions.create(
                                model="llama-3.3-70b-versatile", 
                                messages=[
                                    {"role": "system", "content": f"أنتِ إيلينا، خبيرة تنظيم وقت ذكية. خاطبي الطالب '{friendly_name}' باسمه بأسلوب محفز."}, 
                                    {"role": "user", "content": prompt}
                                ]
                           )
                            st.info(response.choices[0].message.content)
                        except: st.error("خطأ في الاتصال بالـ AI.")
            with col2:
                if st.button("💬 حللي ما عليّ اليوم (Ask Elena)", use_container_width=True):
                    try:
                        items = [f"- {i.get('المهمة/المحاضرة', 'مهمة')} بتاريخ {i.get('الموعد', 'غير محدد')}" if isinstance(i, dict) else f"- {str(i)}" for i in schedule_data]
                        st.session_state.messages.append({"role": "user", "content": f"إيلينا، هاد جدولي لليوم، حلليه وانصحيني شو أعمل:\n" + "\n".join(items)})
                        st.success("تم إرسال الجدول! انتقل لتبويب Ask Elena 🤖")
                        st.balloons() 
                    except Exception as e: st.error(f"حدث خطأ: {str(e)}")
            
            # ==========================================
            # --- ميزة جدول المذاكرة التلقائي ---
            # ==========================================
            st.markdown("---")
            st.subheader("📅 خطة المذاكرة الأسبوعية الذكية")
            st.info("💡 دعي إيلينا توزع لك هذه المهام على أيام الأسبوع لتجنب التراكم والضغط.")
            
            if st.button("🪄 يا إيلينا، وزعي لي دراستي لهذا الأسبوع", use_container_width=True):
                with st.spinner("⏳ إيلينا تقوم بتحليل مواعيدك وتصميم جدول دراسي متوازن..."):
                    tasks_context = "\n".join([
                        f"- المهمة: {i.get('المهمة/المحاضرة', 'مهمة')} | الموعد: {i.get('الموعد', 'غير محدد')}" 
                        if isinstance(i, dict) else f"- {str(i)}" 
                        for i in schedule_data
                    ])
                    
                    planner_prompt = f"""
                    أنتِ إيلينا، مستشارة أكاديمية خبيرة. بناءً على هذه المهام القادمة للطالب {friendly_name}:
                    {tasks_context}
                    
                    قومي بتصميم "جدول مذاكرة أسبوعي" عملي جداً ومقسم على أيام الأسبوع (من السبت للجمعة).
                    - وزعي المهام بحيث لا يتراكم الضغط في يوم واحد.
                    - اقترحي عدد ساعات الدراسة لكل مهمة يومياً.
                    - ضعي نصائح استراحة وتقنية (Pomodoro).
                    - اجعلي الرد بتنسيق Markdown جميل وملون باستخدام الإيموجي الجذابة.
                    """
                    try:
                        response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile", 
                            messages=[
                                {"role": "system", "content": f"أنتِ إيلينا، وتخاطبين الطالب {friendly_name} بأسلوب محفز."}, 
                                {"role": "user", "content": planner_prompt}
                            ]
                        )
                        st.session_state.study_plan = response.choices[0].message.content
                        st.rerun() 
                    except Exception as e:
                        st.error("❌ حدث خطأ أثناء بناء الخطة، حاولي مرة أخرى.")
            
            if "study_plan" in st.session_state:
                with st.expander("✨ خطتك الأسبوعية جاهزة! (انقر للعرض أو الإخفاء)", expanded=True):
                    st.markdown(st.session_state.study_plan)
                    
                    # محتوى HTML الفخم
                    html_content = f"""
                    <!DOCTYPE html>
                    <html dir="rtl" lang="ar">
                    <head>
                        <meta charset="UTF-8">
                        <title>خطة المذاكرة - {friendly_name}</title>
                        <style>
                            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333; line-height: 1.8; padding: 20px; }}
                            .container {{ max-width: 800px; margin: 0 auto; background: #fff; padding: 40px; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.1); }}
                            h1, h2, h3 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; display: inline-block; }}
                            p {{ font-size: 16px; }}
                            ul, ol {{ font-size: 16px; background: #fdfdfd; padding: 20px 40px; border-radius: 8px; border-right: 4px solid #3498db; }}
                            strong {{ color: #e74c3c; }}
                            .header {{ text-align: center; margin-bottom: 30px; }}
                            .footer {{ text-align: center; margin-top: 40px; font-size: 0.9em; color: #95a5a6; border-top: 1px solid #eee; padding-top: 20px; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h1 style="border: none;">📅 خطة المذاكرة الأسبوعية الذكية</h1>
                                <h3 style="border: none; color: #7f8c8d;">تم إعدادها خصيصاً للبطل: {friendly_name} 👑</h3>
                            </div>
                            {markdown.markdown(st.session_state.study_plan)}
                            <div class="footer">
                                تم التوليد بواسطة مساعدك الذكي <b>إيلينا AI</b> 🤖<br>
                                <i>تقدر تحفظ هاد الملف كـ PDF من خلال الضغط على (Ctrl+P) واختيار حفظ كـ PDF.</i>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                    
                    st.download_button(
                        label="📥 تحميل الخطة بتصميم فخم (Smart Doc)",
                        data=html_content,
                        file_name=f"Elena_Study_Plan_{friendly_name}.html",
                        mime="text/html",
                        use_container_width=True
                    )
                    
                    # ==========================================
                    # --- إضافة ميزة الإرسال للإيميل ---
                    # ==========================================
                    st.markdown("---")
                    st.write("📧 **أرسل الخطة إلى إيميلك لتبقى معك دائماً:**")
                    
                    col_em1, col_em2 = st.columns([3, 1])
                    with col_em1:
                        target_email = st.text_input("أدخل إيميلك:", value="", placeholder="example@gmail.com", key="plan_email_input")
                    
                    with col_em2:
                        st.write("") # مسافة لضبط محاذاة الزر
                        if st.button("🚀 إرسال الآن", use_container_width=True):
                            if target_email and '@' in target_email:
                                with st.spinner("جاري إرسال الخطة الفخمة لإيميلك..."):
                                    try:
                                        res = send_elena_email(
                                            target_email, 
                                            f"📅 خطة المذاكرة الأسبوعية من إيلينا - {friendly_name}", 
                                            html_content
                                        )
                                        if res is True:
                                            st.success("✅ تم الإرسال! شيك على صندوق الوارد.")
                                            st.balloons()
                                        else:
                                            st.error(f"❌ فشل الإرسال: {res}")
                                    except Exception as e:
                                        st.error(f"❌ حدث خطأ داخلي: {e}")
                            else:
                                st.warning("⚠️ يرجى كتابة إيميل صحيح أولاً!")

        else: st.info("📅 الجدول فارغ حالياً.")
    else: st.write("📅 اضغط على زر السحب لتحديث بياناتك.")
        
with tabs[1]:
    st.subheader("📖 مستكشف المقررات الذكي")
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
        else: st.warning("⚠️ يرجى المزامنة أولاً من القائمة الجانبية.")

    st.markdown("---")
    if st.session_state.get("my_real_courses"):
        selected_course = st.selectbox("اختر المادة لتصفح محتوياتها:", list(st.session_state.my_real_courses.keys()))
        course_url = st.session_state.my_real_courses[selected_course]
        col_browse, col_deep = st.columns(2)
        with col_browse:
            if st.button("🔍 تصفح سريع", use_container_width=True):
                uid, upass = st.session_state.get("u_id"), st.session_state.get("u_pass")
                if uid and upass:
                    with st.spinner("جاري سحب الملفات والروابط..."):
                        res = run_selenium_task(uid, upass, "browse", course_url)
                        if res and "course_content" in res:
                            st.session_state.current_course_content, st.session_state.current_course_links = res["course_content"], res.get("course_links", [])
                            st.session_state.summarized_items = [] 
                            st.success("✨ تم سحب محتوى المادة بنجاح!")
                else: st.error("⚠️ بيانات المودل غير متوفرة، أعد المزامنة.")
        with col_deep:
            if st.button("🧠 مسح عميق (Deep Scan)", use_container_width=True, type="primary"):
                uid, upass = st.session_state.get("u_id"), st.session_state.get("u_pass")
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
                            if selected_course not in st.session_state.knowledge_base: st.session_state.knowledge_base[selected_course] = {}
                            st.session_state.knowledge_base[selected_course] = result["knowledge_base"]
                            st.success(f"✅ تم المسح العميق بنجاح! تم استخراج {len(result['knowledge_base'])} عنصر.")
                            st.balloons()
                            with st.expander("📊 ملخص المسح العميق"):
                                for name, data in result["knowledge_base"].items():
                                    st.write(f"{'📺' if data['type'] == 'video' else '📄' if data['type'] == 'pdf' else '📃'} **{name}** - {len(data['content'])} حرف")
                        else: st.error(f"❌ {result.get('error', 'فشل المسح')}")
                else: st.warning("⚠️ يرجى المزامنة مع المودل أولاً.")

    if st.session_state.get("current_course_links"):
        st.write(f"### 📄 الملفات والروابط المكتشفة:")
        for i, link in enumerate(st.session_state.current_course_links):
            url_low, name_low = link['url'].lower(), link['name'].lower()
            is_youtube = any(x in url_low for x in ["youtube", "youtu.be", "vimeo"]) or "فيديو" in name_low or "video" in name_low
            icon = "📺" if is_youtube else "📄"
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1: st.markdown(f"{icon} **{link['name']}**")
                with col2: st.link_button("📂 فتح", link['url'], use_container_width=True)
                with col3:
                    is_done = link['url'] in st.session_state.get("summarized_items", [])
                    if st.button("✅ تم" if is_done else ("🧠 تلخيص" if is_youtube else "🪄 قراءة"), key=f"sum_{i}", use_container_width=True):
                        if is_youtube:
                            with st.spinner(f"إيلينا تحلل الفيديو: {link['name']}..."):
                                summary = get_youtube_summary(link['url'])
                                st.session_state.messages.append({"role": "assistant", "content": f"🎬 **تلخيص فيديو:** {link['name']}\n\n{summary}"})
                                st.session_state.summarized_items.append(link['url'])
                                st.success("✅ تم التلخيص في الشات!")
                                st.rerun()
                        else:
                            with st.spinner(f"إيلينا تقرأ الملف: {link['name']}..."):
                                res = run_selenium_task(st.session_state.get("u_id"), st.session_state.get("u_pass"), "scrape_pdf", link['url'])
                                if res and "pdf_text" in res:
                                    st.session_state.pdf_memories[link['name']] = res["pdf_text"]
                                    st.session_state.summarized_items.append(link['url'])
                                    st.session_state.messages.append({"role": "assistant", "content": f"📄 **قرأت الملف:** {link['name']}\n\nصار عندي علم بمحتواه، اسألني عنه في الشات!"})
                                    st.success("✅ تم سحب النص!")
                                    st.rerun()
                                else: st.error("❌ تعذر السحب.")
                                                
with tabs[2]:
    st.subheader("📊 تقرير الأداء الشامل")
    if "my_real_courses" in st.session_state and st.session_state.my_real_courses:
        selected_course_for_grades = st.selectbox("اختر المادة:", list(st.session_state.my_real_courses.keys()), key="grade_selector")
        if st.button(f"🚀 سحب درجات {selected_course_for_grades}", use_container_width=True):
            uid, upass = st.session_state.get("u_id"), st.session_state.get("u_pass")
            if uid and upass:
                with st.spinner(f"إيلينا تفتح سجل درجات {selected_course_for_grades}..."):
                    res = run_selenium_task(uid, upass, "grades", st.session_state.my_real_courses[selected_course_for_grades]) 
                    if res and "data" in res:
                        st.session_state.detailed_grades_text = res["data"]
                        st.session_state.last_grade_course = selected_course_for_grades
                        st.success(f"✅ تم جلب درجات مادة {selected_course_for_grades} بنجاح!")
                        st.rerun()
                    else: st.error("❌ فشل سحب الدرجات.")
            else: st.warning("⚠️ سجل دخول أولاً من القائمة الجانبية!")
    else: st.info(f"💡 يا {friendly_name}، حدث قائمة المقررات أولاً من التبويب الأول لتظهر هنا.")

    if st.session_state.get("detailed_grades_text"):
        current_course = st.session_state.get("last_grade_course", "المادة المختارة")
        st.markdown(f"### 📋 كشف درجات: {current_course}")
        st.text_area("البيانات الخام من المودل:", st.session_state.detailed_grades_text, height=200)
        if st.button("🤖 اطلبي نصيحة إيلينا للتطوير", use_container_width=True):
            with st.spinner("إيلينا تراجع درجاتك..."):
                try:
                    response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile", 
                    messages=[
                        {"role": "system", "content": f"أنتِ إيلينا، مستشارة أكاديمية ذكية. قومي بتحليل درجات الطالب '{friendly_name}' وخاطبيه باسمه بشكل تشجيعي وعملي."}, 
                        {"role": "user", "content": f"هذه درجاتي: {st.session_state.detailed_grades_text}"}
                    ]
                )
                    st.success(f"📈 **تحليل إيلينا:**")
                    st.write(response.choices[0].message.content)
                except Exception as e: st.error(f"حدث خطأ: {e}")
        
with tabs[3]:
    st.subheader("🤖 إيلين - المحلل الأكاديمي العميق")
    
    # 1. قاعدة المعرفة
    knowledge_base = st.session_state.get("knowledge_base", {})
    if knowledge_base:
        with st.expander("📚 قاعدة المعرفة الحالية - انقر لعرض التفاصيل", expanded=False):
            for course_name, items in knowledge_base.items():
                st.markdown(f"### 📖 {course_name}")
                for item_name, data in items.items():
                    st.write(f"{'📺' if data['type'] == 'video' else '📄'} {item_name} - {len(data['content'])} حرف")
            if st.button("🗑️ مسح قاعدة المعرفة"):
                st.session_state.knowledge_base = {}
                st.rerun()

    deep_context = ""
    for course_name, items in knowledge_base.items():
        deep_context += f"\n\n═══════ مادة: {course_name} ═══════\n"
        for item_name, data in items.items(): deep_context += f"\n[{item_name}]:\n{data['content'][:8000]}\n---\n"
    
    pdf_context = ""
    for name, text in st.session_state.get("pdf_memories", {}).items(): pdf_context += f"\n--- ملف: {name} ---\n{text[:6000]}\n"
    
    instruction = f"""أنتِ إيلينا، المحللة الأكاديمية الخاصة بالطالب {friendly_name}. خاطبيه دائماً باسمه ({friendly_name}) بأسلوب ودود.
    المعرفة:
    {deep_context}
    {pdf_context}
    """

    # ==========================================
    # --- 1. قسم الاختبارات (الآن في الأعلى) ---
    # ==========================================
    st.markdown("---")
    st.subheader("📝 اختبر نفسك (Quiz Generator)")
    
    study_context = deep_context + "\n" + pdf_context
    
    if st.button("🧠 ولّدي لي اختبار من هذه الملفات", use_container_width=True):
        if not study_context.strip():
            st.warning(f"⚠️ يا {friendly_name}، يرجى إضافة ملفات لقاعدة المعرفة أو المزامنة مع المودل أولاً!")
        else:
            with st.spinner("⏳ إيلينا تقوم بتحليل المحتوى وتجهيز أسئلة ذكية..."):
                quiz_prompt = f"""
                بناءً على هذا المحتوى، قم بإنشاء 3 أسئلة خيارات متعددة (MCQ).
                يجب أن يكون الرد بصيغة JSON فقط بهذا الشكل بالضبط بدون أي نصوص إضافية:
                [
                    {{"question": "السؤال هنا؟", "options": ["خيار1", "خيار2", "خيار3", "خيار4"], "correct": "خيار2", "explanation": "شرح مبسط للإجابة"}}
                ]
                المحتوى:
                {study_context[:6000]}
                """
                try:
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": quiz_prompt}],
                        temperature=0.3
                    )
                    quiz_json = response.choices[0].message.content.strip()
                    
                    if quiz_json.startswith("```json"): quiz_json = quiz_json[7:-3].strip()
                    elif quiz_json.startswith("```"): quiz_json = quiz_json[3:-3].strip()
                        
                    st.session_state.quiz_data = json.loads(quiz_json)
                    st.session_state.quiz_submitted = False
                    st.rerun() 
                except Exception as e:
                    st.error("❌ حدث خطأ أثناء توليد الاختبار، يرجى المحاولة مرة أخرى.")

    if "quiz_data" in st.session_state:
        st.write("### 🎯 أجب عن الأسئلة التالية:")
        user_answers = {}
        
        for i, q in enumerate(st.session_state.quiz_data):
            st.markdown(f"**{i+1}. {q['question']}**")
            user_answers[i] = st.radio("اختر الإجابة:", q['options'], key=f"quiz_q_{i}", index=None)
            st.write("")
            
        if st.button("✅ تقديم الإجابات ورؤية النتيجة", use_container_width=True):
            st.session_state.quiz_submitted = True
            
        if st.session_state.get("quiz_submitted"):
            st.markdown("---")
            st.write("### 📊 نتيجة الاختبار:")
            score = 0
            incorrect_questions = []
            
            for i, q in enumerate(st.session_state.quiz_data):
                if user_answers[i] == q['correct']:
                    score += 1
                    st.success(f"**السؤال {i+1}:** إجابتك صحيحة! 🎉 ({q['correct']})")
                else:
                    st.error(f"**السؤال {i+1}:** إجابتك خاطئة! ❌ \n\n الإجابة الصحيحة هي: **{q['correct']}**")
                    incorrect_questions.append(q['question'])
                st.info(f"💡 **التوضيح:** {q['explanation']}")
            
            if score == len(st.session_state.quiz_data):
                st.balloons()
                st.success(f"🏆 نتيجتك: {score} من {len(st.session_state.quiz_data)} - أسطورة يا {friendly_name}!")
            else:
                if score > 0:
                    st.warning(f"👍 نتيجتك: {score} من {len(st.session_state.quiz_data)} - وحش، بس راجع المادة كمان مرة يا {friendly_name}.")
                else:
                    st.error(f"💔 نتيجتك: 0 - يبدو إنك محتاج تدرس الملف من أول وجديد يا {friendly_name}!")
                
                st.markdown("---")
                if st.button("👩‍🏫 راجع الشرح مع إيلينا", use_container_width=True):
                    failed_q_text = "\n".join([f"- {q}" for q in incorrect_questions])
                    auto_prompt = f"يا إيلينا، لقد أخطأت في الاختبار في هذه المواضيع:\n{failed_q_text}\n\nهل يمكنك إعادة شرحها لي بتبسيط شديد كأنني مبتدئ مع أمثلة؟"
                    
                    st.session_state.messages.append({"role": "user", "content": auto_prompt})
                    
                    with st.spinner("إيلينا تجهز الشرح المخصص لك..."):
                        try:
                            resp = client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=[{"role": "system", "content": instruction}] + st.session_state.messages
                            )
                            answer = resp.choices[0].message.content
                            st.session_state.messages.append({"role": "assistant", "content": answer})
                            
                            # خدعة Streamlit للقفز التلقائي إلى الشات
                            js = f"""
                            <script>
                                var element = window.parent.document.getElementById('chat-bottom');
                                if (element) {{
                                    element.scrollIntoView({{behavior: "smooth", block: "end", inline: "nearest"}});
                                }}
                            </script>
                            """
                            st.components.v1.html(js, height=0)
                            st.rerun()
                        except Exception as e:
                            st.error("مشكلة في الاتصال بإيلينا.")

    # ==========================================
    # --- 2. قسم الدردشة (الآن في الأسفل) ---
    # ==========================================
    st.markdown("---")
    st.subheader("💬 دردش مع إيلينا حول المادة")
    
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]): st.markdown(message["content"])

    if chat_input := st.chat_input("اسألي إيلينا عن أي تفصيل..."):
        st.session_state.messages.append({"role": "user", "content": chat_input})
        with chat_container:
            with st.chat_message("user"): st.markdown(chat_input)
            with st.chat_message("assistant"):
                try:
                    with st.spinner("إيلينا تغوص في الملفات..."):
                        response = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": instruction}] + st.session_state.messages)
                        answer = response.choices[0].message.content
                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                        st.session_state.scroll_down = True
                except Exception as e: st.error(f"مشكلة: {e}")
        st.rerun()

    if st.sidebar.button("🗑️ مسح محادثة إيلينا", key="clear_chat"):
        st.session_state.messages = []
        st.rerun()

    # تنفيذ كود النزول التلقائي (Auto-Scroll) لو تم تفعيله
    if st.session_state.get("scroll_down"):
        components.html(
            """
            <script>
                // أمر بسيط بينزل الشاشة لآخر الصفحة ببطء وانسيابية
                window.parent.scrollTo({ top: window.parent.document.body.scrollHeight, behavior: 'smooth' });
            </script>
            """, height=0
        )
        st.session_state.scroll_down = False 
        st.markdown("<div id='chat-bottom'></div>", unsafe_allow_html=True)
        
with tabs[4]:
    if st.session_state.get("user_role") == "developer":
        st.subheader("🛠️ لوحة قيادة إيثان (Admin Dashboard)")
        db = load_db()
        
        # ==========================================
        # --- 1. الإحصائيات السريعة ---
        # ==========================================
        st.markdown("### 📊 إحصائيات المنصة الحية")
        
        total_users = 0
        prime_users = 0
        standard_users = 0
        
        # حساب الأرقام من قاعدة البيانات
        for k, v in db.items():
            if k != "timed_codes" and isinstance(v, dict) and "password" in v:
                total_users += 1
                if v.get("status") == "Prime":
                    prime_users += 1
                else:
                    standard_users += 1
        
        active_codes = len(db.get("timed_codes", {}))
        
        # عرض الإحصائيات بشكل مربعات احترافية
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("👥 إجمالي الطلاب", total_users)
        col2.metric("👑 طلاب Prime", prime_users)
        col3.metric("🆓 طلاب Standard", standard_users)
        col4.metric("🔑 أكواد فعالة", active_codes)
        
        st.markdown("---")
        
        # ==========================================
        # --- 2. إدارة وتوليد الأكواد ---
        # ==========================================
        st.markdown("### 🔑 **توليد أكواد بريميوم وتجريبية**")
        col_c, col_t = st.columns([2, 1])
        with col_c: new_c = st.text_input("الكود الجديد:", placeholder="مثال: ELENA-VIP-2026")
        with col_t: duration = st.selectbox("المدة:", ["5 Min", "10 Min", "1H", "1D", "1M", "1Y"])
        
        if st.button("حفظ الكود ✅", use_container_width=True) and new_c:
            if "timed_codes" not in db: db["timed_codes"] = {}
            db["timed_codes"][new_c] = duration
            save_db(db)
            st.success(f"🎉 تم حفظ كود {new_c} لمدة {duration}"); st.rerun()
            
        # عرض الأكواد التي لم تُستخدم بعد لسهولة النسخ
        if active_codes > 0:
            with st.expander("👀 عرض الأكواد الجاهزة (غير المستخدمة)", expanded=True):
                for c, d in db.get("timed_codes", {}).items():
                    st.info(f"**الكود:** `{c}` ⬅️ **المدة:** {d}")
        else:
            st.warning("⚠️ لا يوجد أي أكواد فعالة حالياً، قم بتوليد أكواد جديدة لطلابك.")
            
        st.markdown("---")
        
        # ==========================================
        # --- 3. قاعدة البيانات الخام ---
        # ==========================================
        with st.expander("⚙️ عرض قاعدة البيانات كاملة (للمطورين فقط)"):
            st.json(db)

# --- 6. السايدبار (Sidebar) ---
with st.sidebar:
    st.markdown("---")
    # ==========================================
    # --- 1. نظام اشتراك برايم (Prime) ---
    # ==========================================
    if st.session_state.get("user_status") == "Prime":
        db = load_db() 
        current_u = st.session_state.get("username", "user")
        expire_str = db.get(current_u, {}).get("expire_at")
        if expire_str:
             try:
                dt_obj = datetime.strptime(expire_str, "%Y-%m-%d %H:%M:%S")
                time_diff = dt_obj - get_local_time().replace(tzinfo=None)
                
                if time_diff.total_seconds() > 0:
                    days = time_diff.days
                    hours, remainder = divmod(time_diff.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    
                    time_parts = []
                    if days > 0: time_parts.append(f"{days} يوم")
                    if hours > 0: time_parts.append(f"{hours} ساعة")
                    if minutes > 0: time_parts.append(f"{minutes} دقيقة")
                    time_parts.append(f"{seconds} ثانية")
                    
                    time_left = " و ".join(time_parts)
                    
                    st.success(f"👑 **برايم نشطة**\n\n⏳ **ينتهي خلال:**\n {time_left}\n\n📅 **التاريخ:** {dt_obj.strftime('%Y/%m/%d - %I:%M %p')}")
                    time.sleep(1)
                    st.rerun()
                else:
                    db[current_u]["status"] = "Standard"
                    save_db(db)
                    st.session_state.user_status = "Standard"
                    st.error("⚠️ **انتهى الاشتراك!**")
                    st.rerun() 
             except: 
                st.info(f"ينتهي: {expire_str}")
    st.markdown("---")
    
    # ==========================================
    # --- 2. اختيار الجامعة المتعددة ---
    # ==========================================
    st.header("🏫 اختر جامعتك")
    db = load_db()
    if "universities" not in db:
        # الجامعة الافتراضية
        db["universities"] = {
            "الجامعة الإسلامية بغزة": {"url": "https://sso.iugaza.edu.ps/saml/module.php/core/loginuserpass", "logo": "🎓"}
        }
        save_db(db)
        
    universities = db.get("universities", {})
    uni_list = list(universities.keys()) + ["➕ إضافة رابط جامعة جديدة"]
    
    selected_uni = st.selectbox("🏛️ الجامعة:", uni_list)
    
    if selected_uni == "➕ إضافة رابط جامعة جديدة":
        with st.expander("🔗 إضافة مودل جامعة جديدة", expanded=True):
            new_uni_name = st.text_input("اسم الجامعة (مثال: جامعة الأزهر):")
            new_uni_url = st.text_input("رابط المودل (مثال: https://moodle.univ.edu):")
            if st.button("حفظ الجامعة 💾", use_container_width=True):
                if new_uni_name and new_uni_url:
                    clean_url = new_uni_url.strip().rstrip('/')
                    if not clean_url.startswith("http"):
                        clean_url = "https://" + clean_url
                    db["universities"][new_uni_name] = {"url": clean_url, "logo": "🌍"}
                    save_db(db)
                    st.success("✅ تمت الإضافة بنجاح! جاري التحديث...")
                    time.sleep(1); st.rerun()
                else:
                    st.warning("⚠️ يرجى تعبئة جميع الحقول.")
        st.session_state.moodle_url = "https://sso.iugaza.edu.ps/saml/module.php/core/loginuserpass" # رابط احتياطي أثناء الإضافة
    else:
        st.session_state.moodle_url = universities[selected_uni]["url"]
        st.markdown(f"**الرابط:** `{st.session_state.moodle_url}`")

    st.markdown("---")

    # ==========================================
    # --- 3. تسجيل الدخول والمزامنة ---
    # ==========================================
    st.header("⚙️ المزامنة مع المودل")
    uid = st.text_input("الرقم الجامعي", value=st.session_state.get("u_id", ""))
    upass = st.text_input("كلمة المرور", type="password", value=st.session_state.get("u_pass", ""))

    if st.button("🚀 Sync Now", use_container_width=True) and uid and upass:
        with st.spinner(f"جاري الدخول لمودل ({selected_uni})..."):
            # سحب رابط الجامعة المحددة وتمريره للسكربت
            moodle_link = st.session_state.get("moodle_url", "https://sso.iugaza.edu.ps/saml/module.php/core/loginuserpass")
            res = run_selenium_task(uid, upass, "timeline", base_url=moodle_link)
            
            if res and "courses" in res:
                st.session_state.update({
                    "u_id": uid, 
                    "u_pass": upass, 
                    "my_real_courses": res['courses'], 
                    "user_schedule": res.get('timeline_list', []), 
                    "student_name": res.get('student_name', 'مستخدم'), 
                    "is_synced": True
                })
                st.success("✅ تم الربط بنجاح!"); time.sleep(1); st.rerun()
            else: 
                st.error("❌ فشلت المزامنة. تأكد من البيانات أو توافق رابط الجامعة.")

    with st.expander("⚙️ الإعدادات المتقدمة"):
        if st.button("🔴 تسجيل الخروج النهائي", use_container_width=True):
            # 1. تفريغ الكوكي بدلاً من حذفه (هذه الطريقة مدعومة في كل المتصفحات)
            cookies["username"] = ""
            cookies.save()
            
            # 2. مسح كل الجلسة (Session State)
            for key in list(st.session_state.keys()):
                del st.session_state[key]
                
            st.session_state["is_logged_in"] = False
            
            # 3. استخدام جافاسكريبت يعمل ريفرش للمتصفح بعد ثانية واحدة 
            # (هذا يعطي وقت لمكتبة الكوكيز لترسل أمر المسح للمتصفح)
            st.components.v1.html(
                """
                <script>
                setTimeout(function() {
                    window.location.reload();
                }, 1000);
                </script>
                """,
                height=0
            )
            
            st.warning("🔄 جاري تسجيل الخروج ومسح البيانات , الرجاء عمل ريفرش للصفحة للخروج...")
            st.stop() # إيقاف الكود هنا لمنع أي تداخل
