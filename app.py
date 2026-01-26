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

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="Elena AI - Premium", page_icon="👑", layout="wide")

# --- 2. إدارة البيانات والأكواد (Single-use System) ---
if "IF_VALID_CODES" not in st.session_state:
    st.session_state.IF_VALID_CODES = ["ELENA-PRO-2026", "ETHAN-VIP"]

if "registered_users" not in st.session_state:
    st.session_state.registered_users = [] # قائمة لتخزين بيانات الداخلين

if "user_status" not in st.session_state: st.session_state.user_status = "Standard"
if "courses" not in st.session_state: st.session_state.courses = {}
if "timeline_data" not in st.session_state: st.session_state.timeline_data = ""

# --- 3. محرك السيلينيوم المطور للتحليل التلقائي ---
def run_selenium_task(username, password, task_type="timeline", target_url=None):
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
        p_in = driver.find_element(By.ID, "password")
        p_in.send_keys(password)
        p_in.send_keys(Keys.ENTER)
        time.sleep(10)
        
        if task_type == "timeline":
            body = driver.find_element(By.TAG_NAME, "body").text
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='course/view.php?id=']")
            course_map = {l.text.strip(): l.get_attribute("href") for l in links if len(l.text) > 5}
            return {"text": body, "courses": course_map}
        
        elif task_type == "deep_analyze":
            driver.get(target_url)
            time.sleep(5)
            # سحب نصوص الواجبات والمحتوى لتحليله
            course_content = driver.find_element(By.ID, "region-main").text
            return {"content": course_content}
            
    except Exception as e: return {"error": str(e)}
    finally: driver.quit()

# --- 4. نظام الدخول وتسجيل البيانات ---
if "is_logged_in" not in st.session_state:
    st.markdown("<h1 style='text-align:center;'>🚀 Elena Portal</h1>", unsafe_allow_html=True)
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("دخول"):
        role = "developer" if u == "ethan" else "user"
        st.session_state.update({"is_logged_in": True, "user_role": role, "username": u})
        # إضافة المستخدم للقائمة لمراقبة المدير
        st.session_state.registered_users.append({"name": u, "role": role, "status": "Prime" if role=="developer" else "Standard"})
        st.rerun()
    st.stop()

# --- 5. الواجهة والتبويبات ---
tabs = st.tabs(["📅 المخطط الذكي", "📚 تحليل المقررات", "💬 Ask Elena", "🛠️ لوحة المدير"])

# المخطط الذكي (يعرض البيانات كما كانت سابقاً)
with tabs[0]:
    if st.session_state.timeline_data:
        st.subheader("🗓️ تحليل الجدول الدراسي")
        with st.spinner("إيلينا تحلل مواعيدك..."):
            analysis = st.session_state.chat_session.send_message(f"حلل هذه المواعيد ورتبها لي كجدول: {st.session_state.timeline_data}")
            st.markdown(analysis.text)
    else: st.info("قم بعمل مزامنة أولاً.")

# تحليل المقررات (تلقائي بالكامل)
with tabs[1]:
    if st.session_state.courses:
        sel_course = st.selectbox("اختر المساق للتحليل العميق:", list(st.session_state.courses.keys()))
        if st.button("تحليل المساق بالكامل 🔍"):
            with st.spinner("السيرفر يقوم بسحب الواجبات والملفات الآن..."):
                res = run_selenium_task(st.session_state.u_id, st.session_state.u_pass, "deep_analyze", st.session_state.courses[sel_course])
                if "content" in res:
                    st.session_state.last_analysis = res['content']
                    st.success("تم سحب البيانات! توجه لقسم Ask Elena لرؤية التلخيص.")
    else: st.warning("لا توجد بيانات مقررات.")

# Ask Elena (مكان التلخيص)
with tabs[2]:
    if "last_analysis" in st.session_state:
        st.subheader("🤖 تلخيص إيلينا الذكي للمساق")
        summary_prompt = f"لخص لي هذا المساق، استخرج الواجبات المطلوبة وتواريخها المهمة: {st.session_state.last_analysis}"
        summary = st.session_state.chat_session.send_message(summary_prompt)
        st.write(summary.text)
    
    chat = st.chat_input("اسأل عن أي شيء آخر...")

# لوحة المدير (الإضافات الجديدة)
with tabs[3]:
    if st.session_state.user_role == "developer":
        st.header("🛠️ إدارة المنصة (إيثان)")
        
        col1, col2 = st.columns(2)
        col1.metric("عدد المستخدمين", len(st.session_state.registered_users))
        col2.metric("الأكواد المتبقية", len(st.session_state.IF_VALID_CODES))
        
        st.subheader("👥 قائمة المستخدمين المتصلين")
        st.table(st.session_state.registered_users)
        
        st.subheader("🔑 إدارة الأكواد (استخدام مرة واحدة)")
        new_c = st.text_input("أضف كود جديد")
        if st.button("إضافة كود"):
            st.session_state.IF_VALID_CODES.append(new_c)
            st.rerun()
    else: st.error("غير مسموح لك بالدخول هنا.")

# --- القائمة الجانبية (Sidebar) ---
with st.sidebar:
    st.header("⚙️ المزامنة")
    st.session_state.u_id = st.text_input("ID الجامعي")
    st.session_state.u_pass = st.text_input("باسورد المودل", type="password")
    if st.button("🚀 Sync Now"):
        res = run_selenium_task(st.session_state.u_id, st.session_state.u_pass, "timeline")
        if "courses" in res:
            st.session_state.courses = res['courses']
            st.session_state.timeline_data = res['text']
            st.success("تمت المزامنة!")
            st.rerun()
    
    if st.session_state.user_status == "Standard":
        code = st.text_input("أدخل كود التفعيل")
        if st.button("تفعيل بريميوم"):
            if code in st.session_state.IF_VALID_CODES:
                st.session_state.user_status = "Prime"
                st.session_state.IF_VALID_CODES.remove(code) # حذف الكود ليعمل مرة واحدة فقط
                st.success("مبروك! تم التفعيل وحذف الكود من النظام.")
                st.rerun()
