import streamlit as st
import google.generativeai as genai
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import time

# --- 1. إعدادات الصفحة والتصميم (Advanced UI) ---
st.set_page_config(page_title="Elena AI - Premium Portal", page_icon="👑", layout="wide")

# CSS لإخفاء GitHub وإضافة لمسات البرو ونظام الاشتراك
st.markdown("""
    <style>
    /* إخفاء أيقونة جيت هب والقوائم الافتراضية */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        color: white;
    }
    
    /* أيقونة الاشتراك فوق على اليمين */
    .upgrade-button {
        position: fixed;
        top: 15px;
        right: 15px;
        background: linear-gradient(45deg, #FFD700, #FFA500);
        padding: 10px 20px;
        border-radius: 25px;
        color: black !important;
        font-weight: bold;
        text-decoration: none;
        z-index: 9999;
        box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3);
        border: none;
    }

    .prime-badge {
        background: linear-gradient(45deg, #f39c12, #f1c40f);
        color: black;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 14px;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 10px;
    }

    /* تجميل المدخلات */
    .stTextInput>div>div>input {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: white !important;
        border-radius: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. إدارة الأكواد والحسابات ---
# أكواد التفعيل التي يمكنك بيعها للطلاب
IF_VALID_CODES = ["ELENA-PRO-2026", "ETHAN-GIFT", "STUDENT-VIP"]

if "user_status" not in st.session_state:
    st.session_state.user_status = "Standard" # Default status

# --- 3. إعدادات الذكاء الاصطناعي ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("⚠️ يرجى ضبط GEMINI_API_KEY")

if "chat_session" not in st.session_state:
    model = genai.GenerativeModel("models/gemini-flash-latest")
    st.session_state.chat_session = model.start_chat(history=[])

if "courses" not in st.session_state: st.session_state.courses = {}
if "sync_count" not in st.session_state: st.session_state.sync_count = 0

# --- 4. محرك السيلينيوم (نفس وظائفه السابقة) ---
def run_selenium_task(username, password, task_type="timeline", course_url=None):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.binary_location = "/usr/bin/chromium" 
    try:
        service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get("https://sso.iugaza.edu.ps/saml/module.php/core/loginuserpass")
        time.sleep(2)
        driver.find_element(By.ID, "username").send_keys(username)
        p_field = driver.find_element(By.ID, "password")
        p_field.send_keys(password)
        p_field.send_keys(Keys.ENTER)
        time.sleep(10)
        
        if task_type == "timeline":
            text = driver.find_element(By.TAG_NAME, "body").text
            els = driver.find_elements(By.CSS_SELECTOR, "a[href*='course/view.php?id=']")
            courses = {el.text.strip(): el.get_attribute("href") for el in els if len(el.text) > 5}
            return {"text": text, "courses": courses}
        # ... (باقي المهام: الدرجات والمصادر)
    except Exception as e: return {"error": str(e)}
    finally: driver.quit()

# --- 5. نظام تسجيل الدخول المزدوج ---
def check_login():
    if "is_logged_in" not in st.session_state:
        st.session_state.is_logged_in = False

    if not st.session_state.is_logged_in:
        st.markdown("<h1 style='text-align: center; color: #00dbde;'>🚀 Elena Premium Portal</h1>", unsafe_allow_html=True)
        st.write("<p style='text-align: center;'>بوابة الطلاب المتقدمة - المطور: <b>إيهاب الحايك</b></p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            method = st.tabs(["👤 اسم المستخدم", "📧 Google Login"])
            
            with method[0]:
                u_in = st.text_input("Username")
                p_in = st.text_input("Password", type="password")
                if st.button("دخول للنظام"):
                    if u_in == "ethan" and p_in == "EM2006":
                        st.session_state.is_logged_in = True
                        st.session_state.user_role = "developer"
                        st.session_state.user_status = "Prime"
                        st.rerun()
                    elif u_in == "user" and p_in == "user1234":
                        st.session_state.is_logged_in = True
                        st.session_state.user_role = "user"
                        st.rerun()
                    else: st.error("بيانات خاطئة")
            
            with method[1]:
                st.info("تسجيل الدخول عبر Google متاح حالياً للمشتركين المسجلين مسبقاً.")
                st.button("Continue with Google", disabled=True)
        return False
    return True

# --- 6. واجهة الموقع بعد الدخول ---
if check_login():
    # عرض أيقونة الاشتراك في حال كان المستخدم Standard
    if st.session_state.user_status == "Standard":
        if st.button("👑 Upgrade to Prime", key="up_btn"):
            st.session_state.show_upgrade = True

    # هيدر الترحيب
    role_name = "إيثان" if st.session_state.user_role == "developer" else "طالب إيلينا"
    badge = '<span class="prime-badge">PRIME MEMBER 👑</span>' if st.session_state.user_status == "Prime" else ""
    st.markdown(f"<h2>أهلاً {role_name} {badge}</h2>", unsafe_allow_html=True)

    # نافذة الاشتراك (Upgrade Section)
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
                code_in = st.text_input("أدخل كود الاشتراك:")
                if st.button("تفعيل الآن"):
                    if code_in in IF_VALID_CODES:
                        st.session_state.user_status = "Prime"
                        st.success("تم التفعيل! أنت الآن مستخدم برايم.")
                        time.sleep(1)
                        st.rerun()
                    else: st.error("الكود غير صالح")

    # تحديد الليمت بناءً على الرتبة
    if st.session_state.user_status == "Prime":
        limit_val = "Unlimited ♾️"
    else:
        limit_val = f"{10 - st.session_state.sync_count} / 10"
        if (10 - st.session_state.sync_count) <= 0:
            st.error("🚫 استنفدت محاولاتك. يرجى الترقية لبرايم.")
            st.stop()

    with st.sidebar:
        st.header("📊 Account Status")
        st.write(f"Plan: **{st.session_state.user_status}**")
        st.write(f"Syncs left: **{limit_val}**")
        st.markdown("---")
        u_id = st.text_input("الرقم الجامعي")
        u_pass = st.text_input("كلمة مرور الموديل", type="password")
        if st.button("🚀 Sync Data"):
            st.session_state.sync_count += 1
            with st.spinner("Elena is working..."):
                res = run_selenium_task(u_id, u_pass, "timeline")
                if "error" in res: st.error(res['error'])
                else:
                    st.session_state.timeline_data = res['text']
                    st.session_state.courses = res['courses']
                    st.success("Done!")

    # التبويبات الرئيسية
    tabs = st.tabs(["📅 Smart Planner", "📚 Resources", "📊 Grades", "💬 Ask Elena"])
    
    with tabs[0]:
        if "timeline_data" in st.session_state:
            if st.button("رتب لي جدول دراستي 📅"):
                p = f"رتب المهام حسب الأولوية في جدول: {st.session_state.timeline_data}"
                resp = st.session_state.chat_session.send_message(p)
                st.write(resp.text)
        else: st.info("قم بالمزامنة أولاً")

    with tabs[3]:
        st.caption("🤖 إيلينا في وضع الذكاء الأكاديمي المتطور")
        if chat_input := st.chat_input("اسأل إيلينا..."):
            with st.chat_message("assistant"):
                response = st.session_state.chat_session.send_message(chat_input)
                st.write(response.text)

