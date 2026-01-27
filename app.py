import streamlit as st
import smtplib
import random
import json
import os
import PyPDF2
import io
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
import time
import pytz

# إعداد Groq باستخدام الـ Secrets
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_API_KEY)
except KeyError:
    st.error("خطأ: مفتاح GROQ_API_KEY غير موجود في الـ Secrets!")
    st.stop()

cookies = EncryptedCookieManager(prefix="elena/", password="EM2006_secret_key")
if not cookies.ready():
    st.stop()

if "driver" not in st.session_state:
    with st.spinner("جاري تهيئة إيلينا على السيرفر السحابي... 👑"):
        options = Options()
        options.add_argument('--headless') # ضروري جداً على السيرفر
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        # المسار الافتراضي لكروميوم على سيرفرات ستريم ليت
        options.binary_location = "/usr/bin/chromium" 

        try:
            # استخدام ChromeDriverManager مع تحديد ChromeType.CHROMIUM
            service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
            st.session_state.driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            st.error(f"فشل تشغيل المتصفح على السيرفر: {e}")

# الجسر لضمان تعريف كلمة driver في كل الملف
driver = st.session_state.get("driver")

def get_course_content(course_url):
    # نتحقق أولاً هل المتصفح شغال؟
    if "driver" not in st.session_state:
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
        
def summarize_content(text_to_analyze, type="ملف"):
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": f"أنت مساعد أكاديمي خبير. قم بتلخيص هذا الـ {type} بشكل نقاط مركزة ومفيدة للطالب."},
                {"role": "user", "content": f"المحتوى المراد تلخيصه:\n\n{text_to_analyze[:15000]}"} 
            ],
        )
        summary = response.choices[0].message.content
        
        # التعديل هون: حفظ التلخيص عشان إيلينا تشوفه في الشات
        st.session_state.last_summary = summary 
        
        return summary
    except Exception as e:
        return f"حدث خطأ في التلخيص: {e}"
    
# --- الدالة السحرية لحل مشكلة الوقت (فلسطين UTC+2) ---
def get_local_time():
    # بنحدد المنطقة الزمنية لغزة/القدس
    local_tz = pytz.timezone('Asia/Gaza')
    # بنجيب الوقت الحالي بناءً على المنطقة
    return datetime.now(local_tz)
# --- 1. إعدادات الصفحة والتصميم ---
# --- 1. إعداد الصفحة والتصميم (أول شيء في الكود) ---
st.set_page_config(page_title="Elena AI", page_icon="👑", layout="wide")

# --- 2. ستايل الـ CSS المطور ---
st.markdown("""
    <style>
    /* خلفية التطبيق المتدرجة */
    .stApp { 
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); 
        color: white; 
    }
    /* ستايل السايدبار */
    [data-testid="stSidebar"] { 
        background-color: rgba(15, 12, 41, 0.8); 
    }
    /* صندوق تسجيل الدخول */
    .login-box {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 40px;
        border-radius: 20px;
        border: 1px solid rgba(255, 215, 0, 0.3);
        text-align: center;
    }
    /* بادج البريميوم المطور */
    .prime-badge { 
        background: linear-gradient(45deg, #f39c12, #f1c40f); 
        color: black; 
        padding: 4px 12px; 
        border-radius: 12px; 
        font-weight: bold; 
        font-size: 18px;
        box-shadow: 0 4px 15px rgba(243, 156, 18, 0.3);
    }
    </style>
    """, unsafe_allow_html=True)

def load_db():
    if not os.path.exists("users_db.json"):
        with open("users_db.json", "w") as f:
            json.dump({}, f)
    with open("users_db.json", "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_db(db):
    with open("users_db.json", "w") as f:
        json.dump(db, f, indent=4)
# --- 3. التعرف التلقائي (هاد اللي كان بيعمل NameError) ---
if "username" in cookies and cookies["username"] != "" and not st.session_state.get("is_logged_in"):
    saved_user = cookies["username"]
    db = load_db() # هلقيت البرنامج شايفها 100%
    
    # إذا كان المستخدم هو المطور (إيثان)
    if saved_user == "ethan":
        st.session_state.update({
            "is_logged_in": True,
            "username": "Ethan",
            "user_role": "developer",
            "user_status": "Prime"
        })
    # إذا كان طالب عادي
    elif saved_user in db:
        st.session_state.update({
            "is_logged_in": True,
            "username": saved_user,
            "user_role": "user",
            "user_status": db[saved_user].get("status", "Standard"),
            # ملاحظة: استرجاع بيانات الجامعة من قاعدة البيانات مباشرة لضمان بقائها بعد الريفرش
            "u_id": db[saved_user].get("u_id", ""), 
            "u_pass": db[saved_user].get("u_pass", "")
        })

# --- 2. تهيئة الجلسة والداتا ---
if "is_logged_in" not in st.session_state: st.session_state.is_logged_in = False
if "user_status" not in st.session_state: st.session_state.user_status = "Standard"
if "courses" not in st.session_state: st.session_state.courses = {}
if "timeline_data" not in st.session_state: st.session_state.timeline_data = ""
if "IF_VALID_CODES" not in st.session_state: st.session_state.IF_VALID_CODES = ["ELENA-PRO-2026", "ETHAN-VIP"]

EMAIL_ADDRESS = "ehabalhayekm@gmail.com" 
EMAIL_PASSWORD = "hvvh duch onfd xxdv" 
DB_FILE = "users_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

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
if st.session_state.get("is_synced") and st.session_state.get("student_name"):
    st.success(f"🔗 متصل الآن بحسابك الجامعي باسم: **{st.session_state.student_name}**")
else:
    st.warning("⚠️ حسابك غير مرتبط بالمودل حالياً (توجه للإعدادات للمزامنة)")

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
        with st.spinner("إيلينا تجمع جدولك ومهامك القادمة..."):
            try:
                driver.get("https://moodle.iugaza.edu.ps/my/#")
                time.sleep(4)
                
                events = driver.find_elements(By.CSS_SELECTOR, ".event-list-item")
                timeline_data = []
                for event in events:
                    name = event.find_element(By.CSS_SELECTOR, ".event-name").text
                    date = event.find_element(By.CSS_SELECTOR, ".event-date").text
                    timeline_data.append({"المهمة/المحاضرة": name, "الموعد": date})
                
                st.session_state.user_schedule = timeline_data
                st.success("✅ تم سحب المخطط الزمني بنجاح!")
                st.rerun() # لإظهار الجدول فوراً
            except Exception as e:
                st.error(f"فشل السحب: تأكد من تسجيل الدخول. الخطأ: {e}")

    # عرض البيانات والتحليل
    if st.session_state.get("user_schedule"):
        st.write("### 📋 جدول المهام القادمة:")
        
        # ركز في المسافات هنا:
        if isinstance(st.session_state.user_schedule, list) and len(st.session_state.user_schedule) > 0:
            st.table(st.session_state.user_schedule) # هذه داخل الـ if الأولى
        elif isinstance(st.session_state.user_schedule, str):
            st.info(st.session_state.user_schedule) # هذه داخل الـ elif
        else:
            st.write("📅 لا توجد فعاليات قادمة حالياً. اضغط على زر المزامنة لتحديث البيانات.")
        
        if st.button("🧐 اطلب من إيلينا تحليل جدولك"):
            with st.spinner("إيلينا تدرس المواعيد لتنظيم وقتك..."):
                try:
                    # تحويل الجدول لنص يفهمه الذكاء الاصطناعي
                    schedule_text = "\n".join([f"- {i['المهمة/المحاضرة']} موعدها: {i['الموعد']}" for i in st.session_state.user_schedule])
                    
                    prompt = f"""
                    هذا هو المخطط الزمني لمهامي الجامعية القادمة:
                    {schedule_text}
                    
                    بصفتك "إيلينا" المساعدة الذكية، قومي بما يلي:
                    1. لخصي لي أهم المواعيد القريبة.
                    2. اقترحي لي ترتيباً للأولويات (شو أدرس أول؟).
                    3. أعطني نصيحة لتجنب ضغط الدراسة بناءً على هذه المواعيد.
                    أجيبيني بأسلوبك المشجع والمرتب.
                    """
                    
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "أنتِ إيلينا، مساعدة أكاديمية ذكية جداً في تنظيم الوقت."},
                            {"role": "user", "content": prompt}
                        ]
                    )
                    
                    st.markdown("---")
                    st.info("💡 **تحليل إيلينا الذكي:**")
                    st.write(response.choices[0].message.content)
                    
                except Exception as e:
                    st.error(f"عذراً، واجهت إيلينا مشكلة في التحليل: {e}")
        
# --- داخل تبويب المساقات ---
with tabs[1]:
    st.subheader("📖 مستكشف المقررات الذكي")
    
    # 1. زر التحديث
    if st.button("🔄 تحديث قائمة المقررات الرسمية"):
        with st.spinner("إيلينا تتواصل مع المودل لجلب موادك..."):
            try:
                driver.get("https://moodle.iugaza.edu.ps/my/#")
                time.sleep(4) 
                
                course_elements = driver.find_elements(By.CSS_SELECTOR, "h4.multiline a")
                if not course_elements:
                    course_elements = driver.find_elements(By.CSS_SELECTOR, ".coursename a")
                
                if course_elements:
                    real_courses = {elem.text.strip(): elem.get_attribute("href") for elem in course_elements if elem.text.strip()}
                    st.session_state.my_real_courses = real_courses
                    st.success(f"✅ تم العثور على {len(real_courses)} مواد!")
                    st.rerun()
                else:
                    st.warning("⚠️ لم نجد مواد، تأكد من تسجيل الدخول.")
            except Exception as e:
                st.error(f"فشل جلب المواد: {e}")

    # 2. عرض القائمة المنسدلة (تظهر فقط إذا كانت البيانات موجودة)
    if "my_real_courses" in st.session_state and st.session_state.my_real_courses:
        selected_course = st.selectbox("اختر المادة:", list(st.session_state.my_real_courses.keys()))
        
        if st.button(f"استكشاف محتويات: {selected_course}"):
            with st.spinner(f"جاري الدخول لصفحة {selected_course}..."):
                course_url = st.session_state.my_real_courses[selected_course]
                st.session_state.current_course_links = get_course_content(course_url)
                # تصفير التلخيصات القديمة عند دخول مادة جديدة
                st.session_state.summarized_items = [] 

    # 3. عرض الملفات والروابط المستخرجة
    if "current_course_links" in st.session_state:
        st.write(f"### محتويات المادة:")
        for i, link in enumerate(st.session_state.current_course_links):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1: st.write(f"📄 {link['name']}")
            with col2: st.link_button("فتح", link['url'])
            with col3:
                is_done = link['url'] in st.session_state.get("summarized_items", [])
                btn_label = "✅ تم التلخيص" if is_done else "🪄 تلخيص ذكي"
                
                if st.button(btn_label, key=f"sum_{i}"):
                    with st.spinner("إيلينا تقرأ وتلخص..."):
                        # ملاحظة: تأكد من تعريف دالة summarize_content في كودك
                        # summary = summarize_content(link['url']) 
                        
                        if "summarized_items" not in st.session_state:
                            st.session_state.summarized_items = []
                        st.session_state.summarized_items.append(link['url'])
                        
                        st.info("✨ تم التلخيص! [اضغط هنا للانتقال لتبويب الشات](/?tab=Ask+Elena)") 
                        st.rerun()
                            
# 3. الدرجات (الشغالة تمام)
with tabs[2]:
    st.subheader("📊 تقرير الأداء الشامل (كويزات وامتحانات)")
    
    if st.button("🚀 سحب كشف الدرجات التفصيلي", use_container_width=True):
        with st.spinner("إيلينا تدخل لدفتر الدرجات..."):
            try:
                driver.get("https://moodle.iugaza.edu.ps/grade/report/user/index.php")
                time.sleep(4)
                
                grade_table = driver.find_element(By.CSS_SELECTOR, "table.user-grade")
                rows = grade_table.find_elements(By.TAG_NAME, "tr")
                
                detailed_grades = []
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) > 1:
                        # جلب اسم النشاط والدرجة
                        item_name = row.find_element(By.TAG_NAME, "th").text
                        grade = cells[0].text 
                        detailed_grades.append({"النشاط": item_name, "الدرجة": grade})
                
                st.session_state.detailed_grades = detailed_grades
                st.success("تم جلب كافة درجات الكويزات والامتحانات!")
                st.rerun() # تحديث الصفحة لعرض الجدول فوراً
            except Exception as e:
                st.error(f"حدث خطأ في سحب التفاصيل: {e}")

    # --- التعديل هنا: يجب أن يكون الكود مزاحاً للداخل ليكون تابعاً لـ if ---
    if st.session_state.get("detailed_grades"):
        st.write("### 📋 كشف الدرجات المكتشف:")
        st.table(st.session_state.detailed_grades)
        
        if st.button("🤖 اطلبي نصيحة إيلينا للتطوير", use_container_width=True):
            with st.spinner("إيلينا تحلل أداءك الأكاديمي..."):
                try:
                    grades_summary = "\n".join([f"- {g['النشاط']}: {g['الدرجة']}" for g in st.session_state.detailed_grades])
                    
                    prompt = f"""
                    هذه درجاتي في الأنشطة والكويزات المختلفة:
                    {grades_summary}
                    
                    بناءً على هذه النتائج، يا إيلينا:
                    1. قيمي أدائي العام (ممتاز، يحتاج تحسين، إلخ).
                    2. حددي لي المواد أو الأنشطة التي يبدو أنني أعاني فيها.
                    3. أعطيني 3 نصائح عملية لأرفع درجاتي في الامتحانات النهائية.
                    4. كيف يمكنني استغلال نقاط قوتي الموضحة في الدرجات العالية؟
                    """
                    
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "أنتِ إيلينا، خبيرة في الاستراتيجيات الدراسية والتفوق الأكاديمي."},
                            {"role": "user", "content": prompt}
                        ]
                    )
                    st.markdown("---")
                    st.success("📈 **تحليل الأداء من إيلينا:**")
                    st.write(response.choices[0].message.content)
                except Exception as e:
                    st.error(f"خطأ في تحليل الدرجات: {e}")
        
# --- 4. الشات مع إيلينا ---
with tabs[3]:
        st.caption("🤖 إيلينا - مستشارك الأكاديمي الشامل (بذاكرة متصلة)")
        
        # 1. تجميع البيانات من النوافذ الأخرى (الذاكرة المركزية)
        schedule_context = st.session_state.get("user_schedule", "لا يوجد بيانات جدول حالياً.")
        # تأكدنا هنا من استخدام الاسم الصحيح للدرجات
        grades_context = st.session_state.get("detailed_grades", "لا يوجد بيانات علامات حالياً.")
        last_summary = st.session_state.get("last_summary", "لم يتم تلخيص ملفات مؤخراً.")

        # 2. إعداد "السياق" 
        instruction = f"""
        أنتِ إيلينا، مساعدة أكاديمية ذكية وودودة لطلاب الجامعة، مبرمجة بواسطة إيثان.
        لديكِ وصول كامل لبيانات الطالب الحالية في التطبيق:
        
        📅 المخطط الزمني للطالب:
        {str(schedule_context)}
        
        📊 سجل الدرجات التفصيلي:
        {str(grades_context)}
        
        📝 آخر ملخص لمادة دراسية:
        {str(last_summary)}
        
        استخدمي هذه المعلومات للإجابة على أي سؤال. إذا سألك الطالب 'شو علي دراسة؟' أو 'كيف وضعي في المواد؟' استخدمي البيانات أعلاه للرد بدقة.
        ناديه باسمه 'إيثان' دائماً.
        """

        # تأكد من أن بقية الكود (messages, chat_input) داخل نفس مستوى الإزاحة
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # عرض الرسائل السابقة
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if chat_input := st.chat_input("اسأل إيلينا عن أي شيء في حسابك..."):
            st.session_state.messages.append({"role": "user", "content": chat_input})
            with st.chat_message("user"):
                st.markdown(chat_input)

            with st.chat_message("assistant"):
                try:
                    with st.spinner("إيلينا تحلل بياناتك وتكتب... ✍️"):
                        full_messages = [
                            {"role": "system", "content": instruction},
                            *st.session_state.messages
                        ]
                        
                        chat_completion = client.chat.completions.create(
                            model="llama-3.3-70b-versatile", 
                            messages=full_messages,
                        )
                        response_text = chat_completion.choices[0].message.content
                        st.markdown(response_text)
                        st.session_state.messages.append({"role": "assistant", "content": response_text})
                except Exception as e:
                    st.error(f"عذراً، حدث خطأ في الاتصال: {e}")

        # زر مسح الذاكرة
        if st.button("🗑️ مسح محادثة إيلينا"):
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
    # عرض تاريخ انتهاء الاشتراك بتنسيق لوني احترافي
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
    
    # 2. قسم المزامنة (أصبح الآن داخل السايدبار)
    st.header("⚙️ المزامنة")
    uid = st.text_input("الرقم الجامعي", value=st.session_state.get("u_id", ""))
    upass = st.text_input("كلمة المرور", type="password", value=st.session_state.get("u_pass", ""))

    if st.button("🚀 Sync Now", use_container_width=True):
        if uid and upass:
            with st.spinner("جاري المزامنة..."):
                res = run_selenium_task(uid, upass, "timeline")
                if res and "courses" in res:
                    # تخزين البيانات
                    st.session_state.update({
                        "u_id": uid,
                        "u_pass": upass,
                        "my_real_courses": res['courses'],
                        "user_schedule": res.get('timeline_list', []), 
                        "student_name": res.get('student_name', 'طالب مجتهد'),
                        "is_synced": True
                    })
                    
                    # تحديث العداد
                    try:
                        db = load_db()
                        email_u = st.session_state.get("user_email")
                        if email_u and st.session_state.user_role != "developer" and st.session_state.user_status != "Prime":
                            if email_u not in db: db[email_u] = {}
                            db[email_u]["sync_count"] = db[email_u].get("sync_count", 0) + 1
                            save_db(db)
                    except: pass

                    st.success(f"✅ أهلاً {st.session_state.student_name}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ فشلت المزامنة.")
        else:
            st.warning("⚠️ أدخل البيانات")

    st.markdown("---")
    
    # 3. الإعدادات المتقدمة (داخل السايدبار)
    with st.expander("⚙️ الإعدادات المتقدمة"):
        if st.button("🔴 تسجيل الخروج", use_container_width=True):
            st.components.v1.html(
                """
                <script>
                localStorage.clear(); sessionStorage.clear();
                window.parent.location.href = window.parent.location.origin + window.parent.location.pathname;
                </script>
                """, height=0
            )
            st.session_state.clear()
            st.stop()

    # 4. كود المطور
    if st.session_state.get("user_role") == "developer":
        if st.button("🧹 Clear Cache", use_container_width=True):
            st.cache_data.clear()
            st.success("تم مسح الكاش!")






































































