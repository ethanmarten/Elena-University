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

# --- 1. إعدادات الصفحة والتصميم (UI/UX) ---
st.set_page_config(page_title="Elena AI - Professional Portal", page_icon="🎓", layout="wide")

# السحر الجمالي (CSS) لجعل التطبيق يبدو كموقع احترافي مدفوع
st.markdown("""
    <style>
    /* خلفية متدرجة فخمة */
    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        color: white;
    }
    
    /* تجميل الأزرار لتكون متحركة (Neon Effect) */
    .stButton>button {
        border-radius: 20px;
        background: linear-gradient(45deg, #00dbde, #fc00ff);
        color: white;
        border: none;
        padding: 10px 24px;
        transition: all 0.3s ease;
        font-weight: bold;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        width: 100%;
    }
    
    .stButton>button:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.5);
        color: white;
    }
    
    /* تجميل التبويبات (Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 15px;
        background-color: rgba(255, 255, 255, 0.05);
        padding: 10px;
        border-radius: 15px;
        backdrop-filter: blur(10px);
    }

    /* تأثيرات على كروت الدردشة والمحتوى */
    div[data-testid="stExpander"], .stChatMessage, .stTextArea textarea {
        background: rgba(255, 255, 255, 0.07) !important;
        border-radius: 15px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: white !important;
    }
    
    h1, h2, h3, p {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. إعدادات الذكاء الاصطناعي ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("⚠️ يرجى ضبط GEMINI_API_KEY في إعدادات Secrets")

if "chat_session" not in st.session_state:
    model = genai.GenerativeModel("models/gemini-flash-latest")
    st.session_state.chat_session = model.start_chat(history=[])

if "courses" not in st.session_state:
    st.session_state.courses = {}

if "sync_count" not in st.session_state:
    st.session_state.sync_count = 0

# --- 3. محرك البحث (Selenium) ---
def run_selenium_task(username, password, task_type="timeline", course_url=None):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.binary_location = "/usr/bin/chromium" 
    
    try:
        service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.get("https://sso.iugaza.edu.ps/saml/module.php/core/loginuserpass")
        time.sleep(3)
        
        driver.find_element(By.ID, "username").send_keys(username)
        pass_input = driver.find_element(By.ID, "password")
        pass_input.send_keys(password)
        pass_input.send_keys(Keys.ENTER)
        
        time.sleep(12) 

        if task_type == "timeline":
            timeline_text = driver.find_element(By.TAG_NAME, "body").text
            course_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='course/view.php?id=']")
            courses = {el.text.strip(): el.get_attribute("href") for el in course_elements if len(el.text) > 5}
            return {"text": timeline_text, "courses": courses}

        elif task_type == "course_deep_dive":
            driver.get(course_url)
            time.sleep(5)
            all_links = driver.find_elements(By.CSS_SELECTOR, "a.aalink")
            resources = [{"name": link.text, "url": link.get_attribute("href")} for link in all_links if link.text]
            content = driver.find_element(By.TAG_NAME, "body").text
            return {"text": content, "resources": resources}

        elif task_type == "get_grades":
            grade_url = course_url.replace("course/view.php", "grade/report/user/index.php")
            driver.get(grade_url)
            time.sleep(5)
            grades_table = driver.find_element(By.TAG_NAME, "table").text
            return {"grades": grades_table}

    except Exception as e:
        return {"error": str(e)}
    finally:
        if 'driver' in locals():
            driver.quit()

# --- 4. نظام الحماية وتسجيل الدخول المطور ---
def check_login():
    if "is_logged_in" not in st.session_state:
        st.session_state.is_logged_in = False
        st.session_state.user_role = None

    if not st.session_state.is_logged_in:
        st.markdown("<h1 style='text-align: center; color: #00dbde;'>🚀 Elena Premium Portal</h1>", unsafe_allow_html=True)
        st.write("<p style='text-align: center;'>هذا المشروع محمي بحقوق الملكية للمطور <b>إيهاب الحايك</b></p>", unsafe_allow_html=True)
        
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                user_input = st.text_input("اسم المستخدم 👤", key="login_user")
                pass_input = st.text_input("كلمة السر 🔑", type="password", key="login_pass")
                
                if st.button("فتح النظام ✨"):
                    if user_input == "ethan" and pass_input == "EM2006":
                        st.session_state.is_logged_in = True
                        st.session_state.user_role = "developer"
                        st.rerun()
                    elif user_input == "user" and pass_input == "user1234":
                        st.session_state.is_logged_in = True
                        st.session_state.user_role = "user"
                        st.rerun()
                    else:
                        st.error("بيانات الدخول غير صحيحة")
        return False
    return True

# --- 5. تشغيل واجهة الموقع الاحترافية ---
if check_login():
    if st.session_state.user_role == "developer":
        st.markdown("<h1 style='color: #fc00ff;'>👨‍💻 أهلاً بك يا مطوري (إيثان)</h1>", unsafe_allow_html=True)
        limit_status = "Infinity ♾️"
    else:
        st.markdown("<h1 style='color: #00dbde;'>🎓 أهلاً بك في إيلينا</h1>", unsafe_allow_html=True)
        remaining = 10 - st.session_state.sync_count
        limit_status = f"{remaining} / 10"
        if remaining <= 0:
            st.error("🚫 استنفدت محاولاتك المجانية. تواصل مع المطور للترقية.")
            st.stop()

    st.info(f"📍 الحالة: {st.session_state.user_role.upper()} | ⏳ المحاولات المتبقية: {limit_status}")

    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/1904/1904425.png", width=100)
        st.header("🔐 Student ID Sync")
        u_id = st.text_input("الرقم الجامعي")
        u_pass = st.text_input("كلمة السر الجامعية", type="password")
        
        if st.button("🚀 مزامنة البيانات الآن"):
            st.session_state.sync_count += 1
            with st.spinner("Elena is fetching data..."):
                result = run_selenium_task(u_id, u_pass, "timeline")
                if "error" in result:
                    st.error(f"خطأ: {result['error']}")
                else:
                    st.session_state.timeline_data = result['text']
                    st.session_state.courses = result['courses']
                    st.success("تم التحديث!")

    tab1, tab2, tab3, tab4 = st.tabs(["📅 المخطط الذكي", "📚 المصادر", "📊 الدرجات", "💬 اسأل إيلينا"])

    with tab1:
        if "timeline_data" in st.session_state:
            if st.button("📅 رتبي لي دراستي (Smart Plan)"):
                with st.spinner("تحليل البيانات..."):
                    prompt = f"حلل مواعيدي القادمة ورتبها في جدول أولويات دراسي: {st.session_state.timeline_data}"
                    resp = st.session_state.chat_session.send_message(prompt)
                    st.session_state.study_plan = resp.text
            
            if "study_plan" in st.session_state:
                st.markdown(f"<div style='background: rgba(0,0,0,0.2); padding: 20px; border-radius: 15px;'>{st.session_state.study_plan}</div>", unsafe_allow_html=True)
        else: st.warning("قم بالمزامنة أولاً من القائمة الجانبية.")

    with tab2:
        if st.session_state.courses:
            course = st.selectbox("اختر المساق:", list(st.session_state.courses.keys()))
            if st.button("سحب المصادر 🔍"):
                res = run_selenium_task(u_id, u_pass, "course_deep_dive", st.session_state.courses[course])
                if "resources" in res:
                    for link in res['resources']:
                        st.markdown(f"🔗 [{link['name']}]({link['url']})")
        else: st.info("لا توجد بيانات مساقات.")

    with tab3:
        if st.session_state.courses:
            sel_grade = st.selectbox("اختر المساق لعرض العلامات:", list(st.session_state.courses.keys()))
            if st.button("عرض العلامات 📊"):
                with st.spinner("جاري جلب الدرجات..."):
                    grade_res = run_selenium_task(u_id, u_pass, "get_grades", st.session_state.courses[sel_grade])
                    if "grades" in grade_res:
                        st.text_area("تفاصيل الدرجات:", grade_res['grades'], height=150)
                        analysis = st.session_state.chat_session.send_message(f"حلل درجاتي وأخبرني بمستواي: {grade_res['grades']}")
                        st.success(analysis.text)
        else: st.info("قم بالمزامنة أولاً.")

    with tab4:
        st.write("🤖 اسأل إيلينا عن أي شيء يخص دراستك:")
        if chat_input := st.chat_input("سؤالك هنا..."):
            with st.chat_message("assistant"):
                response = st.session_state.chat_session.send_message(chat_input)
                st.write(response.text)
