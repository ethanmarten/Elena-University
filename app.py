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

# --- 1. إعدادات الأمان والذكاء الاصطناعي ---
st.set_page_config(page_title="Elena AI - Professional Portal", page_icon="🎓", layout="wide")

# استدعاء مفتاح الـ API
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

# --- 2. محرك البحث المطور ---
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

# --- 3. نظام حماية براءة الاختراع (Ethan's Security) ---
def check_password():
    def password_entered():
        # يمكنك تغيير كلمة السر هنا
        if st.session_state["password_input"] == "EM2006": 
            st.session_state["password_correct"] = True
            del st.session_state["password_input"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 Elena Protected Portal")
        st.write("مرحباً بك في إيلينا. هذا المشروع محمي بحقوق الملكية للمطور **ايهاب الحايك**.")
        st.text_input("أدخل كود الوصول لتشغيل النظام:", type="password", on_change=password_entered, key="password_input")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔐 Elena Protected Portal")
        st.text_input("الكود غير صحيح، حاول مرة أخرى:", type="password", on_change=password_entered, key="password_input")
        st.error("🚫 وصول غير مصرح به.")
        return False
    else:
        return True

# --- 4. واجهة المستخدم (لا تعمل إلا بعد تخطي القفل) ---
if check_password():
    st.title("🎓 Elena Academic AI Assistant")
    st.caption("Created by Ethan Marten - Enhanced Private Version")

    with st.sidebar:
        st.header("🔐 User Portal")
        u_id = st.text_input("Student ID")
        u_pass = st.text_input("Password", type="password")
        
        if st.button("🚀 Sync My Data"):
            with st.spinner("Connecting to IUG Portal..."):
                result = run_selenium_task(u_id, u_pass, "timeline")
                if "error" in result:
                    st.error(f"خطأ: {result['error']}")
                else:
                    st.session_state.timeline_data = result['text']
                    st.session_state.courses = result['courses']
                    st.success("تمت المزامنة!")

    tab1, tab2, tab3, tab4 = st.tabs(["📅 Timeline", "📚 Course Resources", "📊 Grades", "💬 Ask Elena"])

    with tab1:
        if "timeline_data" in st.session_state:
            if st.button("Analyze My Deadlines"):
                resp = st.session_state.chat_session.send_message(f"Extract deadlines from: {st.session_state.timeline_data}")
                st.info(resp.text)
        else: st.write("سجل دخولك من القائمة الجانبية أولاً.")

    with tab2:
        if st.session_state.courses:
            selected_course = st.selectbox("اختر المساق للمعاينة العميق:", list(st.session_state.courses.keys()))
            if st.button(f"Fetch Resources for {selected_course}"):
                with st.spinner("Fetching links and content..."):
                    res = run_selenium_task(u_id, u_pass, "course_deep_dive", st.session_state.courses[selected_course])
                    if "resources" in res:
                        st.session_state.current_content = res['text']
                        st.subheader("🔗 Links found in this course:")
                        for link in res['resources']:
                            st.markdown(f"- [{link['name']}]({link['url']})")
                    else: st.error("Failed to fetch.")
        else: st.info("قم بالمزامنة من القائمة الجانبية أولاً.")

    with tab3:
        if st.session_state.courses:
            sel_course_grade = st.selectbox("اختر المساق لرؤية الدرجات:", list(st.session_state.courses.keys()), key="grade_sel")
            if st.button("Check My Grades"):
                with st.spinner("Accessing Gradebook..."):
                    grade_res = run_selenium_task(u_id, u_pass, "get_grades", st.session_state.courses[sel_course_grade])
                    if "grades" in grade_res:
                        st.text_area("Grade Report:", grade_res['grades'], height=200)
                        ai_analysis = st.session_state.chat_session.send_message(f"Analyze these grades for me: {grade_res['grades']}")
                        st.write("🤖 Elena's Analysis:")
                        st.success(ai_analysis.text)
                    else: st.error("Could not find grades.")
        else: st.info("Sync data first.")

    with tab4:
        if chat_input := st.chat_input("Ask Elena about anything..."):
            response = st.session_state.chat_session.send_message(chat_input)
            st.write(response.text)
