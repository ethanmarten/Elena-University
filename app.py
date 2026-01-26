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

    /* تجميل الجداول والكروت في لوحة التحكم */
    .admin-card {
        background: rgba(255, 255, 255, 0.05);
        padding: 15px;
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. إدارة البيانات (قاعدة بيانات وهمية للطلاب) ---
if "IF_VALID_CODES" not in st.session_state:
    st.session_state.IF_VALID_CODES = ["ELENA-PRO-2026", "ETHAN-GIFT", "STUDENT-VIP"]

if "users_db" not in st.session_state:
    # بيانات أولية للتجربة
    st.session_state.users_db = [
        {"username": "user", "status": "Standard", "syncs": 0},
        {"username": "student_test", "status": "Prime", "syncs": 5}
    ]

if "user_status" not in st.session_state:
    st.session_state.user_status = "Standard"

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

# --- 4. محرك السيلينيوم ---
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
    except Exception as e: return {"error": str(e)}
    finally: driver.quit()

# --- 5. لوحة تحكم المدير (إيثان) ---
def admin_dashboard():
    st.markdown("## 🛠️ لوحة تحكم المطور (إيثان)")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("إجمالي المستخدمين", len(st.session_state.users_db))
    col2.metric("أعضاء برايم", len([u for u in st.session_state.users_db if u['status'] == 'Prime']))
    col3.metric("الأكواد المتاحة", len(st.session_state.IF_VALID_CODES))

    st.write("---")
    
    # إدارة المستخدمين
    st.subheader("👥 إدارة حسابات الطلاب")
    for i, user in enumerate(st.session_state.users_db):
        with st.container():
            c1, c2, c3, c4 = st.columns([2, 2, 1, 2])
            c1.write(f"👤 {user['username']}")
            c2.write(f"🛡️ {user['status']}")
            c3.write(f"🔄 {user['syncs']}")
            if user['status'] == "Standard":
                if c4.button(f"ترقية لـ Prime", key=f"upgrade_{i}"):
                    st.session_state.users_db[i]['status'] = "Prime"
                    st.success(f"تم ترقية {user['username']}!")
                    st.rerun()

    st.write("---")
    
    # إدارة الأكواد
    st.subheader("🔑 توليد أكواد اشتراك جديدة")
    new_code = st.text_input("اكتب الكود الجديد:")
    if st.button("إضافة الكود"):
        if new_code and new_code not in st.session_state.IF_VALID_CODES:
            st.session_state.IF_VALID_CODES.append(new_code)
            st.success(f"تم إضافة الكود: {new_code}")
        else:
            st.error("الكود فارغ أو موجود مسبقاً")

# --- 6. نظام تسجيل الدخول ---
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
                st.info("تسجيل الدخول عبر Google متاح للمشتركين فقط.")
                st.button("Continue with Google", disabled=True)
        return False
    return True

# --- 7. تشغيل الموقع الرئيسي ---
if check_login():
    # هيدر الترحيب
    role_name = "إيثان" if st.session_state.user_role == "developer" else "طالب إيلينا"
    badge = '<span class="prime-badge">PRIME MEMBER 👑</span>' if st.session_state.user_status == "Prime" else ""
    st.markdown(f"<h2>أهلاً {role_name} {badge}</h2>", unsafe_allow_html=True)

    # تبويبات الموقع
    tab_list = ["📅 Smart Planner", "📚 Resources", "📊 Grades", "💬 Ask Elena"]
    if st.session_state.user_role == "developer":
        tab_list.append("🛠️ Admin Panel")
    
    tabs = st.tabs(tab_list)

    # تبويب المخطط الذكي
    with tabs[0]:
        if st.session_state.user_status == "Standard":
            with st.expander("⭐ تفعيل عضوية برايم (Prime Membership)"):
                col_pay, col_code = st.columns(2)
                with col_pay:
                    st.write("### 💳 دفع محلي")
                    st.write("- **محفظة جوال باي:** `059594820775`\n- **بنك فلسطين:** `1701577`\n- **واتساب:** [راسلني](https://wa.me/+972594820775)")
                with col_code:
                    code_in = st.text_input("أدخل الكود:")
                    if st.button("تفعيل"):
                        if code_in in st.session_state.IF_VALID_CODES:
                            st.session_state.user_status = "Prime"
                            st.success("تم التفعيل!")
                            st.rerun()
        
        if "timeline_data" in st.session_state:
            if st.button("رتب لي جدول دراستي 📅"):
                p = f"رتب المهام حسب الأولوية في جدول: {st.session_state.timeline_data}"
                resp = st.session_state.chat_session.send_message(p)
                st.write(resp.text)
        else: st.info("قم بالمزامنة أولاً من القائمة الجانبية.")

    # تبويب الدردشة
    with tabs[3]:
        st.caption("🤖 إيلينا في وضع الذكاء الأكاديمي")
        if chat_input := st.chat_input("اسأل إيلينا..."):
            with st.chat_message("assistant"):
                response = st.session_state.chat_session.send_message(chat_input)
                st.write(response.text)

    # تبويب لوحة التحكم (يظهر فقط لإيثان)
    if st.session_state.user_role == "developer":
        with tabs[4]:
            admin_dashboard()

    # القائمة الجانبية وحالة الحساب
    with st.sidebar:
        st.header("📊 Account Status")
        limit_val = "Unlimited ♾️" if st.session_state.user_status == "Prime" else f"{10 - st.session_state.sync_count} / 10"
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
                    st.success("تمت المزامنة!")
