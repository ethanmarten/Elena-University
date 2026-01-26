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
from datetime import datetime, timedelta
from email.message import EmailMessage
from streamlit_cookies_manager import EncryptedCookieManager
import time

cookies = EncryptedCookieManager(prefix="elena/", password="EM2006_secret_key")
if not cookies.ready():
    st.stop()
    
# --- الدالة السحرية لحل مشكلة الوقت (فلسطين UTC+2) ---
def get_local_time():
    # بنجيب توقيت السيرفر العالمي وبنزود ساعتين عشان يطابق ساعتك في غزة
    return datetime.utcnow() + timedelta(hours=2)
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

# --- 3. التعرف التلقائي على المستخدم من الكوكيز ---
# هاد الكود بيمنع خروج المستخدم لما يعمل ريفريش
if "username" in cookies and not st.session_state.get("is_logged_in"):
    saved_user = cookies["username"]
    db = load_db()
    
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

if not st.session_state.is_logged_in:
    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("<h1 style='color: #FFD700;'>👑 Elena AI Portal</h1>", unsafe_allow_html=True)
        
        tab_login, tab_signup = st.tabs(["🔑 تسجيل دخول", "📝 تسجيل جديد"])
        db = load_db()

      with tab_login:
    u = st.text_input("اسم المستخدم", key="l_u")
    p = st.text_input("كلمة السر", type="password", key="l_p")
    
    uid_input = st.text_input("الرقم الجامعي (للمزامنة)", key="l_uid")
    upass_input = st.text_input("باسورد الجامعة (للمزامنة)", type="password", key="l_upass")

    col_in, col_forgot = st.columns(2)
    
    if col_in.button("دخول للنظام", use_container_width=True):
        # 1. حالة المطور (إيثان)
        if u == "ethan" and p == "EM2006":
            # حفظ الكوكي للمطور
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
            # حفظ اسم المستخدم في الكوكيز
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
            nu = st.text_input("اسم مستخدم", key="s_u")
            ne = st.text_input("Gmail", key="s_e")
            np = st.text_input("كلمة سر", type="password", key="s_p")
            
            if st.button("إرسال كود التحقق 📧"):
                if nu in db: st.error("موجود مسبقاً")
                elif not ne.endswith("@gmail.com"): st.warning("استخدم Gmail")
                else:
                    otp = random.randint(1000, 9999)
                    if send_otp(ne, otp):
                        st.session_state.temp_otp, st.session_state.temp_data = otp, {"u": nu, "p": np, "e": ne}
                        st.success("تفقد إيميلك")
            
            if "temp_otp" in st.session_state:
                otp_in = st.text_input("أدخل الكود التحقق:")
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
    st.stop()

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
    if st.session_state.get("timeline_data"):
        if st.button("رتب لي جدول دراستي 📅"):
            p = f"رتب المهام حسب الأولوية في جدول: {st.session_state.timeline_data}"
            resp = st.session_state.chat_session.send_message(p)
            st.write(resp.text)
    else: 
        st.info("قم بالمزامنة أولاً من القائمة الجانبية")

# 2. المقررات
with tabs[1]:
    if st.session_state.get("courses"):
        course = st.selectbox("اختر المساق:", list(st.session_state.courses.keys()))
        if st.button("سحب المصادر 🔍"):
            # التأكد من وجود البيانات قبل التشغيل
            uid = st.session_state.get("u_id")
            upass = st.session_state.get("u_pass")
            if uid and upass:
                res = run_selenium_task(uid, upass, "course_deep_dive", st.session_state.courses[course])
                if "resources" in res:
                    for link in res['resources']:
                        st.markdown(f"🔗 [{link['name']}]({link['url']})")
                else: st.error("لم يتم العثور على مصادر.")
            else: st.warning("أدخل بيانات الجامعة في القائمة الجانبية أولاً.")
    else: 
        st.info("لا توجد بيانات مساقات. اعمل Sync أولاً.")

# 3. الدرجات (الشغالة تمام)
with tabs[2]:
    if st.session_state.get("courses"):
        sel_g = st.selectbox("اختر المادة لعرض الدرجات:", list(st.session_state.courses.keys()), key="g_sel")
        if st.button("جلب الدرجات 📈"):
            uid = st.session_state.get("u_id")
            upass = st.session_state.get("u_pass")
            if uid and upass:
                with st.spinner("جاري جلب بياناتك..."):
                    res = run_selenium_task(uid, upass, "grades", st.session_state.courses[sel_g])
                    if "data" in res: 
                        st.success("تم جلب الدرجات بنجاح!")
                        st.text_area("جدول الدرجات:", res['data'], height=250)
                    else: st.error(f"خطأ: {res.get('error', 'لا يمكن الوصول للدرجات')}")
            else: st.warning("أدخل بيانات الجامعة أولاً.")
    else: 
        st.error("رجاءً قم بعمل 'Sync Now' من القائمة الجانبية أولاً.")

# 4. Ask Elena (تصحيح المسافات والخطأ)
with tabs[3]:
    st.caption("🤖 إيلينا في وضع الذكاء الأكاديمي المتطور")
    if chat_input := st.chat_input("اسأل إيلينا..."):
        with st.chat_message("user"):
            st.write(chat_input)
        with st.chat_message("assistant"):
            response = st.session_state.chat_session.send_message(chat_input)
            st.write(response.text)

with tabs[4]:
    if st.session_state.get("user_role") == "developer":
        role_name = "إيثان"
        st.subheader(f"🛠️ لوحة تحكم المطور: {role_name}")
        
        db = load_db()
        
        # 1. إحصائيات المستخدمين (JSON)
        st.write("👥 بيانات النظام والمستخدمين:")
        st.json(db)
        
        st.markdown("---")
        
        # 2. قسم إضافة الأكواد الزمنية
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
            else: st.warning("اكتب الكود أولاً")

        if "timed_codes" in db and db["timed_codes"]:
            st.write("📋 الأكواد المتوفرة حالياً:", db["timed_codes"])

        st.markdown("---")

        # 3. قسم إدارة المستخدمين (إلغاء الاشتراك)
        st.write("🚫 **إدارة الاشتراكات الفعالة**")
        # فلترة المستخدمين الـ Prime فقط لإلغاء اشتراكهم
        prime_users = [u for u, data in db.items() if isinstance(data, dict) and data.get("status") == "Prime"]
        
        if prime_users:
            selected_user = st.selectbox("اختر مستخدم لإلغاء اشتراكه:", prime_users)
            if st.button(f"إلغاء اشتراك {selected_user} فوراً ⚠️"):
                db[selected_user]["status"] = "Standard"
                # حذف تاريخ الانتهاء إذا وجد
                if "expire_at" in db[selected_user]:
                    del db[selected_user]["expire_at"]
                save_db(db)
                st.error(f"تم سحب رتبة البريميوم من {selected_user}")
                st.rerun()
        else:
            st.info("لا يوجد مستخدمين بريميوم حالياً.")
            
    else:
        st.error("🚫 عذراً، هذا التبويب مخصص للمطور فقط.")
        
# تأكد من وجود هذه الدالة في أعلى الكود
def get_local_time():
    # تعديل الوقت ليكون UTC+2 (توقيت فلسطين)
    return datetime.utcnow() + timedelta(hours=2)

with st.sidebar:
    # --- عرض تاريخ انتهاء الاشتراك بتنسيق لوني احترافي وتحكم تلقائي ---
    if st.session_state.get("user_status") == "Prime":
        db = load_db() 
        current_u = st.session_state.get("username", "user")
        expire_str = db.get(current_u, {}).get("expire_at")
        
        if expire_str:
            try:
                dt_obj = datetime.strptime(expire_str, "%Y-%m-%d %H:%M:%S")
                pretty_date = dt_obj.strftime("%Y/%m/%d - %I:%M %p")
                
                # حساب الوقت المتبقي (UTC+2)
                time_diff = dt_obj - get_local_time()
                total_seconds = time_diff.total_seconds()
                
                if total_seconds > 0:
                    # الحالة: لسا برايم ونشط
                    if total_seconds > 86400: # أكثر من يوم (أخضر)
                        st.success(f"👑 **عضوية برايم نشطة**\n\n📅 ينتهي في: {pretty_date}")
                    else: # أقل من يوم (أصفر)
                        st.warning(f"⏳ **اشتراكك أوشك على الانتهاء!**\n\n📅 الموعد: {pretty_date}")
                else:
                    # الحالة: انتهى الوقت فعلياً (تنفيذ الإلغاء)
                    db[current_u]["status"] = "Standard"
                    if "expire_at" in db[current_u]:
                        del db[current_u]["expire_at"]
                    save_db(db)
                    
                    # تحديث حالة الجلسة فوراً
                    st.session_state.user_status = "Standard"
                    
                    st.error("⚠️ **انتهى الاشتراك!**\n\nتم تحويل حسابك للوضع العادي.")
                    # إعادة تحميل الصفحة ليختفي التاج الذهبي من الهيدر
                    st.rerun() 
            except:
                st.info(f"📅 ينتهي اشتراكك في: {expire_str}")
    
    st.markdown("---")
    st.header("⚙️ المزامنة")
    uid = st.text_input("الرقم الجامعي", value=st.session_state.get("u_id", ""))
    upass = st.text_input("كلمة المرور", type="password", value=st.session_state.get("u_pass", ""))
    
    if st.button("🚀 Sync Now", use_container_width=True):
        if uid and upass:
            with st.spinner("جاري المزامنة... انتظر قليلاً"):
                res = run_selenium_task(uid, upass, "timeline")
                if "courses" in res:
                    st.session_state.update({
                        "courses": res['courses'], 
                        "timeline_data": res['text'], 
                        "u_id": uid, 
                        "u_pass": upass
                    })
                    
                    # تحديث عداد المزامنات (فقط للمستخدم العادي)
                    db = load_db()
                    if st.session_state.user_role != "developer" and st.session_state.user_status != "Prime":
                        db[current_u]["sync_count"] = db.get(current_u, {}).get("sync_count", 0) + 1
                        save_db(db)
                    
                    st.success("تمت المزامنة بنجاح!")
                    st.rerun()
                else:
                    st.error("فشلت المزامنة، تأكد من البيانات.")
        else:
            st.warning("يرجى إدخال الرقم الجامعي وكلمة المرور.")
            
            st.markdown("---")
    with st.expander("⚙️ الإعدادات المتقدمة"):
        if st.button("🔴 تسجيل الخروج", use_container_width=True):
            # مسح بيانات الجلسة بالكامل
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            st.success("تم تسجيل الخروج بنجاح!")
            time.sleep(1)
            st.rerun()

    # خيار مسح الكاش (للمطور)
    if st.session_state.get("user_role") == "developer":
        if st.button("🧹 Clear Cache", use_container_width=True):
            st.cache_data.clear()
            st.success("تم مسح الكاش!")































