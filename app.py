import streamlit as st
import smtplib
import random
import json
import os
import google.generativeai as genai
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from email.message import EmailMessage
import time

# --- 1. إعدادات الصفحة والتصميم (لوحة دخول بوسط الشاشة) ---
st.set_page_config(page_title="Elena AI", page_icon="👑", layout="wide")

st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); color: white; }
    [data-testid="stSidebar"] { background-color: rgba(15, 12, 41, 0.8); }
    
    /* تنسيق لوحة الدخول لتكون في المنتصف */
    .login-box {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 40px;
        border-radius: 20px;
        border: 1px solid rgba(255, 215, 0, 0.3);
        text-align: center;
        margin-top: 50px;
    }
    .prime-badge { background: linear-gradient(45deg, #f39c12, #f1c40f); color: black; padding: 4px 12px; border-radius: 12px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. تهيئة الجلسة (البيانات) ---
if "is_logged_in" not in st.session_state: st.session_state.is_logged_in = False
if "user_status" not in st.session_state: st.session_state.user_status = "Standard"
if "courses" not in st.session_state: st.session_state.courses = {}
if "timeline_data" not in st.session_state: st.session_state.timeline_data = ""
if "IF_VALID_CODES" not in st.session_state: st.session_state.IF_VALID_CODES = ["ELENA-PRO-2026", "ETHAN-VIP"]
if "registered_users" not in st.session_state: st.session_state.registered_users = []

# تهيئة الذكاء الاصطناعي (حل مشكلة الـ AttributeError)
if "chat_session" not in st.session_state:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel("models/gemini-flash-latest")
        st.session_state.chat_session = model.start_chat(history=[])
    except:
        st.warning("⚠️ يرجى التأكد من مفتاح الـ API")

# --- 3. محرك السيلينيوم (Data Engine) ---
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
        p_field = driver.find_element(By.ID, "password")
        p_field.send_keys(password)
        p_field.send_keys(Keys.ENTER)
        time.sleep(8)
        
        if task_type == "timeline":
            body = driver.find_element(By.TAG_NAME, "body").text
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='course/view.php?id=']")
            course_map = {l.text.strip(): l.get_attribute("href") for l in links if len(l.text) > 5}
            return {"text": body, "courses": course_map}
        
        elif task_type == "grades":
            g_url = target_url.replace("course/view.php", "grade/report/user/index.php")
            driver.get(g_url)
            time.sleep(4)
            return {"data": driver.find_element(By.TAG_NAME, "table").text}
    except Exception as e: return {"error": str(e)}
    finally: driver.quit()
        
# إعدادات البريد (إيثان: استخدم الباسورد اللي أعطيتني إياها هنا)
EMAIL_ADDRESS = "ehabalhayekm@gmail.com" 
EMAIL_PASSWORD = "hvvh duch onfd xxdv" 
DB_FILE = "users_db.json"

# دالات إدارة قاعدة البيانات (JSON)
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

# دالة إرسال كود الـ OTP
def send_otp(target_email, code):
    msg = EmailMessage()
    msg.set_content(f"كود التحقق الخاص بك لمنصة إيلينا هو: {code}")
    msg['Subject'] = "تفعيل حساب إيلينا AI"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = target_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        return True
    except: return False

# --- 4. واجهة تسجيل الدخول المطورة (تصميم بوسط الشاشة) ---
if not st.session_state.is_logged_in:
    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("<h1 style='color: #FFD700;'>👑 Elena AI Portal</h1>", unsafe_allow_html=True)
        
        # تبديل بين تسجيل الدخول وإنشاء حساب
        auth_mode = st.tabs(["🔑 دخول", "📝 تسجيل جديد"])
        db = load_db()

        with auth_mode[0]: # قسم تسجيل الدخول
            u = st.text_input("اسم المستخدم")
            p = st.text_input("كلمة السر", type="password")
            if st.button("دخول للنظام", use_container_width=True):
                # فحص المطور (إيثان) أولاً
                if u == "ethan" and p == "EM2006":
                    st.session_state.update({"is_logged_in": True, "user_role": "developer", "user_status": "Prime", "username": "Ethan"})
                    st.rerun()
                # فحص المستخدمين العاديين من الملف
                elif u in db and db[u]['password'] == p:
                    st.session_state.update({"is_logged_in": True, "user_role": "user", "user_status": db[u]['status'], "username": u})
                    st.rerun()
                else: st.error("بيانات خاطئة أو الحساب غير موجود")

        with auth_mode[1]: # قسم إنشاء الحساب
            new_u = st.text_input("اسم مستخدم جديد", key="reg_u")
            new_e = st.text_input("الإيميل الجامعي (Gmail)", key="reg_e")
            new_p = st.text_input("كلمة سر جديدة", type="password", key="reg_p")
            
            if st.button("إرسال كود التحقق 📧", use_container_width=True):
                if new_u in db: st.error("اسم المستخدم مأخوذ!")
                elif not new_e.endswith("@gmail.com"): st.warning("يرجى استخدام Gmail فقط")
                else:
                    otp = random.randint(1000, 9999)
                    if send_otp(new_e, otp):
                        st.session_state.temp_otp = otp
                        st.session_state.temp_data = {"u": new_u, "p": new_p, "e": new_e}
                        st.success(f"تم إرسال الكود إلى {new_e}")
                    else: st.error("فشل إرسال الإيميل، تأكد من إعدادات الـ App Password")

            if "temp_otp" in st.session_state:
                otp_input = st.text_input("أدخل الكود المستلم:")
                if st.button("تأكيد وإنشاء الحساب"):
                    if otp_input == str(st.session_state.temp_otp):
                        data = st.session_state.temp_data
                        db[data['u']] = {"password": data['p'], "email": data['e'], "status": "Standard"}
                        save_db(db)
                        st.balloons()
                        st.success("تم تفعيل حسابك بنجاح! يمكنك الآن الدخول.")
                        del st.session_state.temp_otp
                    else: st.error("الكود خطأ!")
        
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()
# --- 4. واجهة تسجيل الدخول (تصميم بوسط الشاشة) ---
if not st.session_state.is_logged_in:
    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("<h1 style='color: #FFD700;'>👑 Elena AI Portal</h1>", unsafe_allow_html=True)
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة السر", type="password")
        if st.button("دخول للنظام", use_container_width=True):
            if (u == "ethan" and p == "EM2006") or (u == "user" and p == "user1234"):
                role = "developer" if u == "ethan" else "user"
                st.session_state.update({"is_logged_in": True, "user_role": role, "username": u})
                if role == "developer": st.session_state.user_status = "Prime"
                st.session_state.registered_users.append({"User": u, "Status": st.session_state.user_status})
                st.rerun()
            else: st.error("بيانات خاطئة!")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 5. الواجهة الرئيسية ---
badge = '<span class="prime-badge">PRIME 👑</span>' if st.session_state.user_status == "Prime" else ""
st.markdown(f"## Elena Student AI {badge}", unsafe_allow_html=True)

db = load_db()
current_u = st.session_state.get("username", "user")

# 1. تحديث حالة المستخدم من الملف (عشان لو ترقى من الإدارة يتحدث عنده فوراً)
if current_u in db:
    st.session_state.user_status = db[current_u].get("status", "Standard")
    user_syncs = db[current_u].get("sync_count", 0)
else:
    user_syncs = 0

# 2. منطق الحماية والليمت (للمستخدم العادي فقط)
if st.session_state.user_role != "developer":
    if st.session_state.user_status == "Prime":
        st.sidebar.success("عضوية برايم نشطة ♾️")
    else:
        remaining = 10 - user_syncs
        st.sidebar.markdown(f"""
            <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 10px; border-right: 4px solid #FF4B4B;">
                <p style="margin:0; font-size:13px; color: #FF4B4B;">محاولات المزامنة المتبقية</p>
                <h3 style="margin:0;">{remaining} / 10</h3>
            </div>
        """, unsafe_allow_html=True)
        
        # إذا صفر، بنقفل عليه الموقع
        if remaining <= 0:
            st.error("⚠️ انتهت محاولاتك المجانية. يرجى الترقية للاستمرار.")
            st.info("تواصل مع المطور إيثان للحصول على كود التفعيل.")
            
            # خانة ترقية سريعة
            up_code = st.text_input("أدخل كود التفعيل 🔑:", key="lock_upgrade")
            if st.button("تفعيل الحساب"):
                if up_code in st.session_state.IF_VALID_CODES:
                    db[current_u]["status"] = "Prime"
                    st.session_state.IF_VALID_CODES.remove(up_code)
                    save_db(db)
                    st.success("مبروك! صرت برايم، أعد تحميل الصفحة.")
                    st.rerun()
            st.stop() # هاد السطر بيمنعه يشوف التبويبات اللي تحت

# --- 3. تعديل مهم جداً لزر المزامنة (Sidebar) ---
# لازم تروح لزر الـ Sync في الـ Sidebar وتضيف هاد الكود جواه عند نجاح العملية:
# if st.session_state.user_role != "developer":
#     db[current_u]["sync_count"] = db.get(current_u, {}).get("sync_count", 0) + 1
#     save_db(db)

tabs = st.tabs(["📅 المخطط الذكي", "📚 المقررات", "📊 الدرجات", "💬 Ask Elena", "🛠️ الإدارة"])

# المخطط الذكي
with tabs[0]:
    if st.session_state.timeline_data:
        if st.button("تحليل الجدول الدراسي بالذكاء الاصطناعي"):
            res = st.session_state.chat_session.send_message(f"حلل هذه المواعيد: {st.session_state.timeline_data}")
            st.markdown(res.text)
    else: st.info("قم بالمزامنة من القائمة الجانبية.")

# المقررات
with tabs[1]:
    if st.session_state.courses:
        sel = st.selectbox("اختر المادة للتحليل:", list(st.session_state.courses.keys()))
        if st.button("تحليل محتوى المساق"):
            st.write("جاري سحب المحتوى والملفات تلقائياً...")
    else: st.warning("لا توجد بيانات.")

# الدرجات (التي طلبتها)
with tabs[2]:
    if st.session_state.courses:
        sel_g = st.selectbox("اختر المادة لعرض الدرجات:", list(st.session_state.courses.keys()), key="g_sel")
        if st.button("جلب الدرجات 📈"):
            with st.spinner("جاري جلب بياناتك..."):
                res = run_selenium_task(st.session_state.u_id, st.session_state.u_pass, "grades", st.session_state.courses[sel_g])
                if "data" in res: st.text_area("جدول الدرجات:", res['data'], height=250)
    else: st.error("قم بالمزامنة أولاً.")

# Ask Elena
with tabs[3]:
    q = st.chat_input("اسأل إيلينا...")
    if q: st.write(st.session_state.chat_session.send_message(q).text)

# الإدارة (إيثان)
with tabs[4]:
    if st.session_state.user_role == "developer":
        st.write("📊 إحصائيات النظام")
        st.table(st.session_state.registered_users)
        st.write(f"الأكواد المتاحة: {st.session_state.IF_VALID_CODES}")
        new_c = st.text_input("أضف كود جديد")
        if st.button("إضافة"): 
            st.session_state.IF_VALID_CODES.append(new_c)
            st.rerun()
    else: st.error("للمطور فقط.")

# القائمة الجانبية
with st.sidebar:
    st.header("⚙️ المزامنة")
    st.session_state.u_id = st.text_input("الرقم الجامعي")
    st.session_state.u_pass = st.text_input("كلمة المرور", type="password")
    if st.button("🚀 Sync Now"):
        with st.spinner("Elena is working..."):
            res = run_selenium_task(st.session_state.u_id, st.session_state.u_pass, "timeline")
            if "courses" in res:
                st.session_state.courses = res['courses']
                st.session_state.timeline_data = res['text']
                st.rerun()

    if st.session_state.user_status == "Standard":
        c_in = st.text_input("كود البريميوم")
        if st.button("تفعيل"):
            if c_in in st.session_state.IF_VALID_CODES:
                st.session_state.user_status = "Prime"
                st.session_state.IF_VALID_CODES.remove(c_in) # استخدام لمرة واحدة
                st.rerun()



