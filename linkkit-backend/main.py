from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import DictCursor
import datetime
import os
import random
import requests

VERIFY_TOKEN = "linkkithub_secret_token_123"
META_ACCESS_TOKEN = "IGAAdxm9UFqplBZAFk0aXBibFpmSFlLTXdJOVdDTHhSd2s5eE44RmpUSDdVanVCOGkzaTlWdG5TMDRSWm5GbEN2Q0hKdExOajlLSXlua3ExTTV3VEp6WEtUR2s4aG1Tbnd2Tk5BLTlWMDJtNG9JejhaVkQ5YmxWUlRuZAS1TSEhDcwZDZD"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================================================
# DATABASE CONFIGURATION & HELPER
# ========================================================
# DATABASE_URL env variable Render se aayega
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/linkkithub")

def get_db_connection():
    """
    Centralized PostgreSQL database connection helper.
    """
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# ========================================================
# PYDANTIC DATA VALIDATION MODELS (Unchanged)
# ========================================================
class UserSignup(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class RuleCreate(BaseModel):
    user_id: int
    keyword: str
    reply_text: str

class AutomationRuleCreate(BaseModel):
    creator_id: str
    keyword: str
    comment_reply: str
    dm_message: str
    require_follow: bool = False

class LinkCreate(BaseModel):
    user_id: int
    title: str
    url: str

class LeadCreate(BaseModel):
    username: str  
    email: str

class ProfileUpdate(BaseModel):
    user_id: int
    username: str
    bio_title: str
    bio_desc: str
    avatar_url: str
    theme: str
    consultation_price: float
    button_style: str  
    font_family: str   

class BookingCreate(BaseModel):
    username: str
    name: str
    email: str
    booking_date: str
    booking_time: str
    amount: float  

class ProductCreate(BaseModel):
    user_id: int
    title: str
    download_url: str
    price: float       

class OrderCreate(BaseModel):
    username: str
    amount: float
    item_type: str
    item_title: str
    customer_email: str

class DomainCreate(BaseModel):
    user_id: int
    custom_domain: str

class AdvancedSignup(BaseModel):
    first_name: str
    last_name: str
    email: str
    country_code: str
    phone_number: str
    password: str

class OTPRequest(BaseModel):
    email: str

class ForgotPasswordRequest(BaseModel):
    identifier: str  

class ResetPasswordModel(BaseModel):
    email: str
    otp_code: str
    new_password: str

# ========================================================
# CORE HELPER UTILITIES
# ========================================================
def simulate_smtp_email_dispatch(user_id: int, recipient: str, subject: str, body: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO email_logs (user_id, recipient_email, subject, body) VALUES (%s, %s, %s, %s)",
            (user_id, recipient.strip().lower(), subject.strip(), body.strip())
        )
        conn.commit()
        conn.close()
    except Exception as e: 
        print(f"❌ [SMTP REGISTRY FAIL]: {e}")

def get_uid_from_username(cursor, username: str):
    cursor.execute("SELECT id FROM users WHERE username = %s", (username.strip().lower(),))
    res = cursor.fetchone()
    if not res: 
        raise HTTPException(status_code=404, detail="Identity username registry missing.")
    return res[0]

# ========================================================
# DATABASE INITIALIZATION ENGINE (PostgreSQL)
# ========================================================
def init_db():
    print("\n🔥 [STARTUP ENGINE] --> Synchronizing PostgreSQL Schemas...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username VARCHAR UNIQUE NOT NULL, email VARCHAR UNIQUE NOT NULL, password VARCHAR NOT NULL, plan_type VARCHAR DEFAULT \'free\')')
        
        cursor.execute('CREATE TABLE IF NOT EXISTS keyword_rules (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, keyword VARCHAR NOT NULL, reply_text VARCHAR NOT NULL, require_follow BOOLEAN DEFAULT FALSE, UNIQUE(user_id, keyword))')
        
        cursor.execute('CREATE TABLE IF NOT EXISTS analytics (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, sender_id VARCHAR NOT NULL, keyword_triggered VARCHAR NOT NULL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        cursor.execute('CREATE TABLE IF NOT EXISTS link_in_bio (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, title VARCHAR NOT NULL, url VARCHAR NOT NULL)')
        cursor.execute('CREATE TABLE IF NOT EXISTS leads (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, email VARCHAR NOT NULL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, email))')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profile_settings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                username VARCHAR NOT NULL,
                bio_title VARCHAR NOT NULL,
                bio_desc VARCHAR NOT NULL,
                avatar_url VARCHAR,
                theme VARCHAR NOT NULL,
                consultation_price NUMERIC DEFAULT 49.00,
                button_style VARCHAR DEFAULT 'solid',
                font_family VARCHAR DEFAULT 'sans',
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('CREATE TABLE IF NOT EXISTS link_clicks (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, link_title VARCHAR NOT NULL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        cursor.execute('CREATE TABLE IF NOT EXISTS bookings (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, name VARCHAR NOT NULL, email VARCHAR NOT NULL, booking_date VARCHAR NOT NULL, booking_time VARCHAR NOT NULL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS digital_products (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title VARCHAR NOT NULL,
                download_url VARCHAR NOT NULL,
                price NUMERIC DEFAULT 0.00
            )
        ''')
        
        cursor.execute('CREATE TABLE IF NOT EXISTS transactions (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, amount NUMERIC NOT NULL, item_type VARCHAR NOT NULL, item_title VARCHAR NOT NULL, customer_email VARCHAR NOT NULL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        cursor.execute('CREATE TABLE IF NOT EXISTS email_logs (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, recipient_email VARCHAR NOT NULL, subject VARCHAR NOT NULL, body VARCHAR NOT NULL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        cursor.execute('CREATE TABLE IF NOT EXISTS custom_domains (id SERIAL PRIMARY KEY, user_id INTEGER UNIQUE NOT NULL, custom_domain VARCHAR UNIQUE NOT NULL)')
        
        conn.commit()
        conn.close()
        print("✅ [TABLE STATUS] --> PostgreSQL schemas successfully verified and active.\n")
    except Exception as e:
        print(f"❌ [DB INIT ERROR] -> Make sure DATABASE_URL is correct. Error: {e}")

# Call init_db on startup
init_db()

# ========================================================
# 🔐 ADVANCED AUTHENTICATION & OTP SYSTEM
# ========================================================
@app.post("/api/auth/request-otp")
async def request_otp(payload: OTPRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = %s", (payload.email.strip().lower(),))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Yeh Email ID pehle se registered hai!")
    conn.close()
    
    generated_otp = str(random.randint(100000, 999999))
    print(f"🔑 [SIMULATED OTP for {payload.email}]: {generated_otp}")
    return {"status": "SUCCESS", "message": "OTP sent successfully!", "debug_otp": generated_otp}

@app.post("/api/auth/advanced-signup")
async def advanced_signup(payload: AdvancedSignup):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE email = %s", (payload.email.strip().lower(),))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Yeh Email ID pehle se registered hai!")
    
    try:
        base_username = (payload.first_name.strip() + payload.last_name.strip()).lower()
        base_username = "".join(e for e in base_username if e.isalnum())
        if not base_username:
            base_username = payload.email.split('@')[0].lower()
            
        unique_suffix = str(random.randint(100, 999))
        assigned_username = base_username + unique_suffix
        
        # In PostgreSQL, we use RETURNING id to get the auto-incremented ID
        cursor.execute(
            "INSERT INTO users (username, email, password, plan_type) VALUES (%s, %s, %s, 'free') RETURNING id",
            (assigned_username, payload.email.strip().lower(), payload.password)
        )
        new_uid = cursor.fetchone()[0]
        
        cursor.execute(
            "INSERT INTO profile_settings (user_id, username, bio_title, bio_desc, avatar_url, theme, consultation_price, button_style, font_family) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (new_uid, assigned_username, f"{payload.first_name} {payload.last_name}", "Welcome to my creator page!", "", "midnight", 49.00, "solid", "sans")
        )
        
        simulate_smtp_email_dispatch(new_uid, payload.email, "Welcome to LinkKitHub! 🚀", f"Hello {payload.first_name}, aapka account successfully create ho gaya hai. Aapka assigned username hai: @{assigned_username}")
        
        conn.commit()
        conn.close()
        
        return {
            "status": "SUCCESS", 
            "message": "Account created successfully.", 
            "assigned_username": assigned_username
        }
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/login")
async def login_tenant(payload: UserLogin):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    login_id = payload.username.strip().lower()
    if login_id.startswith('@'):
        login_id = login_id[1:]
        
    cursor.execute("""
        SELECT id, username, plan_type 
        FROM users 
        WHERE (username = %s OR email = %s) AND password = %s
    """, (login_id, login_id, payload.password))
    
    row = cursor.fetchone()
    conn.close()
    
    if row: 
        return {"status": "SUCCESS", "user_id": row[0], "username": row[1], "plan": row[2]}
    raise HTTPException(status_code=401, detail="Invalid credentials. Username/Email ya Password galat hai.")

@app.post("/api/auth/forgot-password")
async def forgot_password_request(payload: ForgotPasswordRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, email FROM users WHERE email = %s OR username = %s", (payload.identifier.strip().lower(), payload.identifier.strip().lower()))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="Yeh identity hamare database mein nahi mili.")
    
    user_id, email = user
    reset_otp = str(random.randint(100000, 999999))
    
    simulate_smtp_email_dispatch(user_id, email, "🔑 Password Reset OTP", f"Aapka password reset code hai: {reset_otp}")
    conn.close()
    
    return {"status": "SUCCESS", "message": "Reset code sent to email!", "debug_otp": reset_otp}

@app.post("/api/auth/reset-password")
async def reset_password_confirm(payload: ResetPasswordModel):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password = %s WHERE email = %s", (payload.new_password, payload.email.strip().lower()))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS", "message": "Password successfully updated!"}


# ========================================================
# 💳 PAYMENT GATEWAY & PRO UPGRADE API
# ========================================================
class PaymentVerify(BaseModel):
    user_id: int
    gateway: str  
    payment_id: str
    amount: float

@app.post("/api/payment/verify-and-upgrade")
async def verify_payment_and_upgrade(payload: PaymentVerify):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE users SET plan_type = 'pro' WHERE id = %s", (payload.user_id,))
        cursor.execute(
            "INSERT INTO transactions (user_id, amount, item_type, item_title, customer_email) VALUES (%s, %s, %s, %s, %s)",
            (payload.user_id, payload.amount, f"Subscription ({payload.gateway.upper()})", "LinkKitHub PRO Lifetime/Monthly", "creator@linkkithub.dev")
        )
        
        conn.commit()
        conn.close()
        return {"status": "SUCCESS", "message": "Payment verified and account upgraded to PRO!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment processing failed: {str(e)}")


# ========================================================
# BACKEND CRUD CONTROL WORKSPACE MANAGERS
# ========================================================
@app.get("/api/profile")
async def get_profile_settings(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, bio_title, bio_desc, avatar_url, theme, consultation_price, button_style, font_family FROM profile_settings WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row: 
        return {"username": row[0], "bio_title": row[1], "bio_desc": row[2], "avatar_url": row[3], "theme": row[4], "consultation_price": float(row[5]), "button_style": row[6], "font_family": row[7]}
    raise HTTPException(status_code=404, detail="Missing user customization profile.")

@app.post("/api/profile")
async def update_profile_settings(profile: ProfileUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE profile_settings SET username = %s, bio_title = %s, bio_desc = %s, avatar_url = %s, theme = %s, consultation_price = %s, button_style = %s, font_family = %s WHERE user_id = %s", (profile.username.strip(), profile.bio_title.strip(), profile.bio_desc.strip(), profile.avatar_url.strip(), profile.theme.strip(), profile.consultation_price, profile.button_style.strip(), profile.font_family.strip(), profile.user_id))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.post("/api/automation/rule")
def create_automation_rule(rule: AutomationRuleCreate):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        user_id = int(rule.creator_id)
        
        cursor.execute(
            "INSERT INTO keyword_rules (user_id, keyword, reply_text, require_follow) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT(user_id, keyword) DO UPDATE SET reply_text=EXCLUDED.reply_text, require_follow=EXCLUDED.require_follow",
            (user_id, rule.keyword.lower().strip(), rule.dm_message.strip(), rule.require_follow)
        )
        conn.commit()
        conn.close()
        return {"status": "SUCCESS", "message": "Automation rule saved successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/api/rules")
async def add_keyword_rule(rule: RuleCreate):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO keyword_rules (user_id, keyword, reply_text) VALUES (%s, %s, %s)", (rule.user_id, rule.keyword.lower().strip(), rule.reply_text.strip()))
        conn.commit()
        conn.close()
        return {"status": "SUCCESS"}
    except Exception: 
        raise HTTPException(status_code=400, detail="Automation keyword already mapped.")

@app.delete("/api/rules/{user_id}/{keyword}")
async def delete_keyword_rule(user_id: int, keyword: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM keyword_rules WHERE user_id = %s AND keyword = %s", (user_id, keyword.lower().strip()))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.post("/api/links")
async def add_bio_link(link: LinkCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO link_in_bio (user_id, title, url) VALUES (%s, %s, %s)", (link.user_id, link.title.strip(), link.url.strip()))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.delete("/api/links")
async def delete_bio_link(user_id: int, title: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM link_in_bio WHERE user_id = %s AND title = %s", (user_id, title.strip()))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.post("/api/products")
async def upload_new_product(prod: ProductCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO digital_products (user_id, title, download_url, price) VALUES (%s, %s, %s, %s)", (prod.user_id, prod.title.strip(), prod.download_url.strip(), prod.price))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.delete("/api/products/{user_id}/{product_id}")
async def remove_digital_product(user_id: int, product_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM digital_products WHERE user_id = %s AND id = %s", (user_id, product_id))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.delete("/api/leads/{user_id}/{email}")
async def remove_lead_entry(user_id: int, email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM leads WHERE user_id = %s AND email = %s", (user_id, email.strip().lower()))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.delete("/api/bookings/{user_id}/{booking_id}")
async def cancel_appointment_entry(user_id: int, booking_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookings WHERE user_id = %s AND id = %s", (user_id, booking_id))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.delete("/api/automation-logs/clear")
async def clear_automation_logs(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM analytics WHERE user_id = %s", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.delete("/api/email-logs/clear")
async def clear_automated_email_logs(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM email_logs WHERE user_id = %s", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.get("/api/domain")
async def get_custom_domain(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT custom_domain FROM custom_domains WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return {"custom_domain": row[0]} if row else {"custom_domain": ""}

@app.post("/api/domain")
async def save_custom_domain(payload: DomainCreate):
    clean_domain = payload.custom_domain.strip().lower()
    if not clean_domain: 
        raise HTTPException(status_code=400, detail="Domain cannot be blank.")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO custom_domains (user_id, custom_domain) VALUES (%s, %s) ON CONFLICT(user_id) DO UPDATE SET custom_domain=EXCLUDED.custom_domain", (payload.user_id, clean_domain))
        conn.commit()
        conn.close()
        return {"status": "SUCCESS"}
    except Exception: 
        raise HTTPException(status_code=400, detail="Domain configuration linked elsewhere.")

@app.delete("/api/domain/{user_id}")
async def delete_custom_domain(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM custom_domains WHERE user_id = %s", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}


# ========================================================
# PUBLIC GATEWAYS RESOLUTIONS
# ========================================================
@app.get("/api/auth/resolve-domain")
async def resolve_domain(domain: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT u.username FROM users u JOIN custom_domains d ON u.id = d.user_id WHERE d.custom_domain = %s", (domain.strip().lower(),))
    row = cursor.fetchone()
    conn.close()
    if row: 
        return {"username": row[0]}
    raise HTTPException(status_code=404, detail="White-label host domain mapping missing.")

@app.get("/api/public-profile")
async def get_public_profile(username: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    uid = get_uid_from_username(cursor, username)
    cursor.execute("SELECT username, bio_title, bio_desc, avatar_url, theme, consultation_price, button_style, font_family FROM profile_settings WHERE user_id = %s", (uid,))
    row = cursor.fetchone()
    conn.close()
    return {"username": row[0], "bio_title": row[1], "bio_desc": row[2], "avatar_url": row[3], "theme": row[4], "consultation_price": float(row[5]), "button_style": row[6], "font_family": row[7]}

@app.get("/api/public-links")
async def get_public_bio_links_tenant(username: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    uid = get_uid_from_username(cursor, username)
    cursor.execute("SELECT title, url, (SELECT COUNT(*) FROM link_clicks WHERE user_id = link_in_bio.user_id AND link_title = link_in_bio.title) as clicks FROM link_in_bio WHERE user_id = %s", (uid,))
    links = [{"title": l[0], "url": l[1], "clicks": l[2]} for l in cursor.fetchall()]
    conn.close()
    return links

@app.get("/api/public-products")
async def get_public_products_tenant(username: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    uid = get_uid_from_username(cursor, username)
    cursor.execute("SELECT id, title, download_url, price FROM digital_products WHERE user_id = %s", (uid,))
    prods = [{"id": r[0], "title": r[1], "download_url": r[2], "price": float(r[3])} for r in cursor.fetchall()]
    conn.close()
    return prods

@app.post("/api/click")
async def log_link_click_tenant(username: str, title: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    uid = get_uid_from_username(cursor, username)
    cursor.execute("INSERT INTO link_clicks (user_id, link_title) VALUES (%s, %s)", (uid, title.strip()))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.post("/api/leads")
async def capture_new_lead_tenant(lead: LeadCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        uid = get_uid_from_username(cursor, lead.username)
        cursor.execute("INSERT INTO leads (user_id, email) VALUES (%s, %s)", (uid, lead.email.strip().lower()))
        conn.commit()
        
        subject = "Welcome Insider! 🎁 Your Premium Creator Growth Drop is here!"
        body = "Hey! Thank you for subscribing to my private LinkKitHub newsletter channel."
        simulate_smtp_email_dispatch(uid, lead.email, subject, body)
        return {"status": "SUCCESS"}
    except Exception: 
        raise HTTPException(status_code=400, detail="This email is already subscribed!")
    finally: conn.close()

@app.post("/api/checkout/process")
async def authorize_premium_checkout(order: OrderCreate):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        uid = get_uid_from_username(cursor, order.username)
        cursor.execute("INSERT INTO transactions (user_id, amount, item_type, item_title, customer_email) VALUES (%s, %s, %s, %s, %s)", (uid, order.amount, order.item_type, order.item_title.strip(), order.customer_email.strip().lower()))
        conn.commit()
        conn.close()
        
        subject = f"📦 Delivery Receipt: Your order for '{order.item_title}' is confirmed!"
        body = f"Thank you for your secure payout payment of ${order.amount}. Your premium digital file download is ready."
        simulate_smtp_email_dispatch(uid, order.customer_email, subject, body)
        return {"status": "SUCCESS"}
    except Exception as e: 
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bookings")
async def process_new_appointment_tenant(booking: BookingCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    uid = get_uid_from_username(cursor, booking.username)
    cursor.execute("INSERT INTO bookings (user_id, name, email, booking_date, booking_time) VALUES (%s, %s, %s, %s, %s)", (uid, booking.name.strip(), booking.email.strip().lower(), booking.booking_date.strip(), booking.booking_time.strip()))
    cursor.execute("INSERT INTO transactions (user_id, amount, item_type, item_title, customer_email) VALUES (%s, %s, %s, %s, %s)", (uid, booking.amount, "Consultation Slot 🗓️", f"1:1 Sync: {booking.booking_time}", booking.email.strip().lower()))
    conn.commit()
    conn.close()
    
    subject = "🗓️ Scheduled: Your 1:1 Coaching Appointment is Confirmed!"
    body = f"Hello {booking.name}. Your direct consultation sync has been successfully reserved for {booking.booking_date} at {booking.booking_time} IST."
    simulate_smtp_email_dispatch(uid, booking.email, subject, body)
    return {"status": "SUCCESS"}


# ========================================================
# SAAS METRICS ANALYTICS SYSTEM
# ========================================================
@app.get("/api/analytics")
async def get_dashboard_analytics_tenant(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM analytics WHERE user_id = %s", (user_id,))
    total_replies = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM leads WHERE user_id = %s", (user_id,))
    real_leads_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM link_clicks WHERE user_id = %s", (user_id,))
    real_clicks_count = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE user_id = %s", (user_id,))
    revenue_aggregate = cursor.fetchone()[0]
    total_revenue = round(float(revenue_aggregate), 2) if revenue_aggregate else 0.0
    
    cursor.execute("SELECT keyword, reply_text FROM keyword_rules WHERE user_id = %s", (user_id,))
    active_rules = [{"keyword": r[0], "reply_text": r[1]} for r in cursor.fetchall()]
    
    cursor.execute("SELECT email, timestamp FROM leads WHERE user_id = %s ORDER BY timestamp DESC", (user_id,))
    captured_emails = [{"email": row[0], "date": row[1].isoformat() if row[1] else ""} for row in cursor.fetchall()]
    cursor.execute("SELECT id, name, email, booking_date, booking_time FROM bookings WHERE user_id = %s ORDER BY booking_date ASC, booking_time ASC", (user_id,))
    active_bookings = [{"id": row[0], "name": row[1], "email": row[2], "date": row[3], "time": row[4]} for row in cursor.fetchall()]
    cursor.execute("SELECT id, sender_id, keyword_triggered, timestamp FROM analytics WHERE user_id = %s ORDER BY timestamp DESC LIMIT 10", (user_id,))
    automation_logs = [{"id": log[0], "sender_id": log[1], "keyword": log[2], "date": log[3].isoformat() if log[3] else ""} for log in cursor.fetchall()]
    cursor.execute("SELECT id, title, download_url, price FROM digital_products WHERE user_id = %s ORDER BY id DESC", (user_id,))
    stored_products = [{"id": row[0], "title": row[1], "download_url": row[2], "price": float(row[3])} for row in cursor.fetchall()]
    cursor.execute("SELECT amount, item_type, item_title, customer_email, timestamp FROM transactions WHERE user_id = %s ORDER BY timestamp DESC LIMIT 5", (user_id,))
    recent_sales = [{"amount": float(row[0]), "type": row[1], "title": row[2], "email": row[3], "date": row[4].isoformat() if row[4] else ""} for row in cursor.fetchall()]
    cursor.execute("SELECT recipient_email, subject, timestamp FROM email_logs WHERE user_id = %s ORDER BY timestamp DESC LIMIT 10", (user_id,))
    outbound_emails = [{"recipient": row[0], "subject": row[1], "date": row[2].isoformat() if row[2] else ""} for row in cursor.fetchall()]
    
    dates_list = [(datetime.date.today() - datetime.timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    clicks_map = {d: 0 for d in dates_list}
    rev_map = {d: 0.0 for d in dates_list}

    cursor.execute("SELECT DATE(timestamp), COUNT(*) FROM link_clicks WHERE user_id = %s GROUP BY DATE(timestamp)", (user_id,))
    for r in cursor.fetchall():
        dt_str = r[0].isoformat() if isinstance(r[0], datetime.date) else r[0]
        if dt_str in clicks_map: clicks_map[dt_str] = r[1]

    cursor.execute("SELECT DATE(timestamp), SUM(amount) FROM transactions WHERE user_id = %s GROUP BY DATE(timestamp)", (user_id,))
    for r in cursor.fetchall():
        dt_str = r[0].isoformat() if isinstance(r[0], datetime.date) else r[0]
        if dt_str in rev_map: rev_map[dt_str] = round(float(r[1]), 2)

    chart_data = {
        "labels": [datetime.datetime.strptime(d, "%Y-%m-%d").strftime("%b %d") for d in dates_list],
        "clicks": [clicks_map[d] for d in dates_list],
        "revenue": [rev_map[d] for d in dates_list]
    }
    
    conn.close()
    return {
        "total_replies": total_replies, "total_clicks": real_clicks_count, "lead_captures": real_leads_count, "total_revenue": total_revenue, "recent_sales": recent_sales, "active_rules": active_rules, "captured_emails": captured_emails, "active_bookings": active_bookings, "automation_logs": automation_logs, "stored_products": stored_products, "outbound_emails": outbound_emails, "chart_data": chart_data
    }

from fastapi import Request, Response, HTTPException
from pydantic import BaseModel

# ========================================================
# 🤖 META INSTAGRAM AUTOMATION WEBHOOK ENGINE
# ========================================================
VERIFY_TOKEN = "linkkithub_secret_token_123"

# 1. GET ROUTE (For Meta Verification)
@app.get("/webhook/instagram")
async def verify_instagram_webhook(request: Request):
    query_params = request.query_params
    mode = query_params.get("hub.mode")
    token = query_params.get("hub.verify_token")
    challenge = query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ [META WEBHOOK] Verified successfully!")
        # Meta ko strictly Plain Text chahiye hota hai
        return Response(content=challenge, media_type="text/plain")
        
    raise HTTPException(status_code=403, detail="Verification token mismatch")

# 2. POST ROUTE (For Real Instagram Comments from Meta)
@app.post("/webhook/instagram")
async def receive_instagram_webhook(request: Request):
    try:
        body = await request.json()
        print(f"📥 [WEBHOOK DATA]: {body}")
        
        # Check karte hain ki kya ye Instagram se aaya hai
        if body.get("object") == "instagram":
            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    # Agar event "comments" ka hai
                    if change.get("field") == "comments":
                        value = change.get("value", {})
                        comment_text = value.get("text", "").lower()
                        sender_id = value.get("from", {}).get("id")
                        
                        print(f"💬 [NEW COMMENT] User {sender_id} said: {comment_text}")
                        
                        # 🚀 SIMPLE TEST RULE: Agar comment me "link" ya "ready" hai
                        if "link" in comment_text or "ready" in comment_text:
                            reply_message = "Hello! 👋 Yeh raha aapka LinkKitHub link: https://linkkithub.com/spencer_2.00 🚀"
                            send_instagram_dm(sender_id, reply_message)
                            
        return Response(content="EVENT_RECEIVED", status_code=200)
    except Exception as e:
        print(f"❌ Webhook Error: {e}")
        return Response(content="ERROR", status_code=500)

# ========================================================
# 🚀 AUTO-DM SENDER FUNCTION
# ========================================================
def send_instagram_dm(recipient_id, message_text):
    # Meta Graph API ka URL
    url = "https://graph.facebook.com/v18.0/me/messages"
    
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        print(f"✅ [DM SENT SUCCESS] To: {recipient_id}")
    else:
        print(f"❌ [DM FAILED] Error: {response.text}")

# ========================================================
# 🧪 SIMULATOR ROUTE (For Testing Dashboard Logic)
# ========================================================
class SimulatedComment(BaseModel):
    username: str
    follower_id: str
    comment_text: str

@app.post("/api/simulate-insta-comment")
async def simulate_instagram_comment(payload: SimulatedComment):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE username = %s", (payload.username.strip().lower(),))
        user_res = cursor.fetchone()
        
        if not user_res:
            return {"status": "IGNORED", "reason": "Creator not found on LinkKitHub"}
            
        user_id = user_res[0]
        incoming_text = payload.comment_text.strip().lower()

        cursor.execute("SELECT keyword, reply_text, require_follow FROM keyword_rules WHERE user_id = %s", (user_id,))
        rules = cursor.fetchall()
        
        matched_rule = None
        for rule in rules:
            if rule[0] in incoming_text:  
                matched_rule = rule
                break
                
        if matched_rule:
            keyword_triggered = matched_rule[0]
            reply_text = matched_rule[1]
            require_follow = bool(matched_rule[2])
            
            if require_follow:
                reply_text = f"⚠️ [Follow-Gated Check] Pehle hamari profile ko follow karo, tabhi link milega! 🚀\n\nDirect Link: {reply_text}"

            cursor.execute("INSERT INTO analytics (user_id, sender_id, keyword_triggered) VALUES (%s, %s, %s)", 
                           (user_id, payload.follower_id, keyword_triggered))
            conn.commit()
            
            print(f"🚀 [AUTO-DM SENT] To: {payload.follower_id} | Message: {reply_text}")
            return {"status": "SUCCESS", "action": "AUTO_DM_SENT", "message_delivered": reply_text}
        
        return {"status": "IGNORED", "reason": "No keyword matched"}

    except Exception as e:
        print(f"❌ Simulator Error: {e}")
        raise HTTPException(status_code=500, detail="Simulator processing failed")
    finally:
        conn.close()

# ========================================================
# 👑 ENHANCED SUPER ADMIN & AUTHENTICATION APIs
# ========================================================
@app.get("/api/admin/users-detailed")
async def get_all_users_detailed():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id, u.username, u.email, u.password, u.plan_type, p.bio_title, p.theme 
        FROM users u 
        LEFT JOIN profile_settings p ON u.id = p.user_id 
        ORDER BY u.id DESC
    """)
    users = [{
        "id": row[0],
        "username": row[1],
        "email": row[2],
        "password": row[3],
        "plan": row[4].upper(),
        "bio_title": row[5] or "Not Configured",
        "theme": row[6] or "default"
    } for row in cursor.fetchall()]
    conn.close()
    return users

@app.delete("/api/admin/users/purge/{user_id}")
async def purge_user_completely(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT username, email FROM users WHERE id = %s", (user_id,))
        user_record = cursor.fetchone()
        
        if not user_record:
            conn.close()
            raise HTTPException(status_code=404, detail="User entity not found.")

        cursor.execute("DELETE FROM profile_settings WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM keyword_rules WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM link_in_bio WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM digital_products WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM leads WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM bookings WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM transactions WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM email_logs WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM custom_domains WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM link_clicks WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM analytics WHERE user_id = %s", (user_id,))
        
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        
        conn.commit()
        conn.close()
        return {"status": "SUCCESS", "message": "User entity and complete relational registry successfully purged."}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))