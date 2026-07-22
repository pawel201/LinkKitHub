from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import datetime
import os
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

Base = declarative_base()
SQLALCHEMY_DATABASE_URL = "sqlite:///./linkkithub.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
from sqlalchemy.ext.declarative import declarative_base


# Naya automation rule table jisme follow-gate check ka flag bhi hai
class AutomationRuleDB(Base):
    __tablename__ = "automation_rules"
 
    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(String, index=True)
    keyword = Column(String, index=True)
    comment_reply = Column(String)
    dm_message = Column(String)
    require_follow = Column(Boolean, default=False) # Ye raha wo checkbox wala optional flag

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Sabhi websites ko allow karega
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "linkkithub.db")


# ========================================================
# PYDANTIC DATA VALIDATION MODELS
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

class RuleCreate(BaseModel):
    creator_id: str
    keyword: str
    comment_reply: str
    dm_message: str
    require_follow: bool = False

@app.post("/api/automation/rule")
def create_automation_rule(rule: RuleCreate):
    db = SessionLocal()
    db_rule = AutomationRuleDB(
        creator_id=rule.creator_id,
        keyword=rule.keyword.upper(),
        comment_reply=rule.comment_reply,
        dm_message=rule.dm_message,
        require_follow=rule.require_follow
    )
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    db.close()
    return {"status": "success", "message": "Automation rule saved successfully!"}
# ========================================================
# CORE HELPER UTILITIES
# ========================================================
def simulate_smtp_email_dispatch(user_id: int, recipient: str, subject: str, body: str):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO email_logs (user_id, recipient_email, subject, body) VALUES (?, ?, ?, ?)",
            (user_id, recipient.strip().lower(), subject.strip(), body.strip())
        )
        conn.commit()
        conn.close()
    except Exception as e: 
        print(f"❌ [SMTP REGISTRY FAIL]: {e}")

def get_uid_from_username(cursor, username: str):
    cursor.execute("SELECT id FROM users WHERE username = ?", (username.strip().lower(),))
    res = cursor.fetchone()
    if not res: 
        raise HTTPException(status_code=404, detail="Identity username registry missing.")
    return res[0]


# ========================================================
# DATABASE INITIALIZATION ENGINE
# ========================================================
def init_db():
    print("\n🔥 [STARTUP ENGINE] --> Synchronizing SaaS Subscription Grids...")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 🆕 Added plan_type to users table
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, plan_type TEXT DEFAULT "free")')
    cursor.execute('CREATE TABLE IF NOT EXISTS keyword_rules (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, keyword TEXT NOT NULL, reply_text TEXT NOT NULL, UNIQUE(user_id, keyword))')
    cursor.execute('CREATE TABLE IF NOT EXISTS analytics (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, sender_id TEXT NOT NULL, keyword_triggered TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)')
    cursor.execute('CREATE TABLE IF NOT EXISTS link_in_bio (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, title TEXT NOT NULL, url TEXT NOT NULL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, email TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, email))')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profile_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            username TEXT NOT NULL,
            bio_title TEXT NOT NULL,
            bio_desc TEXT NOT NULL,
            avatar_url TEXT,
            theme TEXT NOT NULL,
            consultation_price REAL DEFAULT 49.00,
            button_style TEXT DEFAULT 'solid',
            font_family TEXT DEFAULT 'sans'
        )
    ''')
    
    cursor.execute('CREATE TABLE IF NOT EXISTS link_clicks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, link_title TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)')
    cursor.execute('CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT NOT NULL, email TEXT NOT NULL, booking_date TEXT NOT NULL, booking_time TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS digital_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            download_url TEXT NOT NULL,
            price REAL DEFAULT 0.00
        )
    ''')
    
    cursor.execute('CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, amount REAL NOT NULL, item_type TEXT NOT NULL, item_title TEXT NOT NULL, customer_email TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)')
    cursor.execute('CREATE TABLE IF NOT EXISTS email_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, recipient_email TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)')
    cursor.execute('CREATE TABLE IF NOT EXISTS custom_domains (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE NOT NULL, custom_domain TEXT UNIQUE NOT NULL)')
    
    # Migrations for existing databases
    try:
        cursor.execute("PRAGMA table_info(users)")
        user_cols = [row[1] for row in cursor.fetchall()]
        if user_cols and "plan_type" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN plan_type TEXT DEFAULT 'free'")
            conn.commit()
    except Exception: pass

    try:
        cursor.execute("PRAGMA table_info(profile_settings)")
        existing_cols = [row[1] for row in cursor.fetchall()]
        if existing_cols:
            if "consultation_price" not in existing_cols:
                cursor.execute("ALTER TABLE profile_settings ADD COLUMN consultation_price REAL DEFAULT 49.00")
            if "button_style" not in existing_cols:
                cursor.execute("ALTER TABLE profile_settings ADD COLUMN button_style TEXT DEFAULT 'solid'")
            if "font_family" not in existing_cols:
                cursor.execute("ALTER TABLE profile_settings ADD COLUMN font_family TEXT DEFAULT 'sans'")
            conn.commit()
    except Exception: pass

    try:
        cursor.execute("PRAGMA table_info(digital_products)")
        prod_cols = [row[1] for row in cursor.fetchall()]
        if prod_cols and "price" not in prod_cols:
            cursor.execute("ALTER TABLE digital_products ADD COLUMN price REAL DEFAULT 0.00")
            conn.commit()
    except Exception: pass
    
    conn.commit()
    conn.close()
    print("✅ [TABLE STATUS] --> System schemas successfully verified and active.\n")


# ========================================================
# TENANT IDENTITY & SUBSCRIPTION APIS
# ========================================================
@app.post("/api/auth/signup")
async def register_new_tenant(payload: UserSignup):
    clean_user = payload.username.strip().lower()
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # Default plan is 'free'
        cursor.execute("INSERT INTO users (username, email, password, plan_type) VALUES (?, ?, ?, 'free')", (clean_user, payload.email.strip().lower(), payload.password))
        new_uid = cursor.lastrowid
        cursor.execute("INSERT INTO profile_settings (user_id, username, bio_title, bio_desc, avatar_url, theme, consultation_price, button_style, font_family) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (new_uid, payload.username.strip(), "Welcome to My Page!", "Explore links below to connect.", "", "midnight", 49.00, "solid", "sans"))
        cursor.execute("INSERT INTO link_in_bio (user_id, title, url) VALUES (?, ?, ?)", (new_uid, "My Masterclass Channel 🚀", "https://linkkithub.dev"))
        conn.commit()
        conn.close()
        return {"status": "SUCCESS", "message": "Account created successfully!"}
    except sqlite3.IntegrityError: 
        raise HTTPException(status_code=400, detail="Username or Email already registered.")

@app.post("/api/auth/login")
async def login_tenant(payload: UserLogin):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 🆕 Extract plan_type during login
    cursor.execute("SELECT id, username, plan_type FROM users WHERE username = ? AND password = ?", (payload.username.strip().lower(), payload.password))
    row = cursor.fetchone()
    conn.close()
    if row: 
        return {"status": "SUCCESS", "user_id": row[0], "username": row[1], "plan": row[2]}
    raise HTTPException(status_code=401, detail="Invalid credentials.")

@app.post("/api/subscription/upgrade")
async def upgrade_plan(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET plan_type = 'pro' WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS", "message": "Plan upgraded to Pro!"}


# ========================================================
# BACKEND CRUD CONTROL WORKSPACE MANAGERS
# ========================================================
@app.get("/api/profile")
async def get_profile_settings(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT username, bio_title, bio_desc, avatar_url, theme, consultation_price, button_style, font_family FROM profile_settings WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row: 
        return {"username": row[0], "bio_title": row[1], "bio_desc": row[2], "avatar_url": row[3], "theme": row[4], "consultation_price": row[5], "button_style": row[6], "font_family": row[7]}
    raise HTTPException(status_code=404, detail="Missing user customization profile.")

@app.post("/api/profile")
async def update_profile_settings(profile: ProfileUpdate):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE profile_settings SET username = ?, bio_title = ?, bio_desc = ?, avatar_url = ?, theme = ?, consultation_price = ?, button_style = ?, font_family = ? WHERE user_id = ?", (profile.username.strip(), profile.bio_title.strip(), profile.bio_desc.strip(), profile.avatar_url.strip(), profile.theme.strip(), profile.consultation_price, profile.button_style.strip(), profile.font_family.strip(), profile.user_id))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.post("/api/rules")
async def add_keyword_rule(rule: RuleCreate):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO keyword_rules (user_id, keyword, reply_text) VALUES (?, ?, ?)", (rule.user_id, rule.keyword.lower().strip(), rule.reply_text.strip()))
        conn.commit()
        conn.close()
        return {"status": "SUCCESS"}
    except sqlite3.IntegrityError: 
        raise HTTPException(status_code=400, detail="Automation keyword already mapped.")

@app.delete("/api/rules/{user_id}/{keyword}")
async def delete_keyword_rule(user_id: int, keyword: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM keyword_rules WHERE user_id = ? AND keyword = ?", (user_id, keyword.lower().strip()))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.post("/api/links")
async def add_bio_link(link: LinkCreate):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO link_in_bio (user_id, title, url) VALUES (?, ?, ?)", (link.user_id, link.title.strip(), link.url.strip()))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.delete("/api/links")
async def delete_bio_link(user_id: int, title: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM link_in_bio WHERE user_id = ? AND title = ?", (user_id, title.strip()))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.post("/api/products")
async def upload_new_product(prod: ProductCreate):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO digital_products (user_id, title, download_url, price) VALUES (?, ?, ?, ?)", (prod.user_id, prod.title.strip(), prod.download_url.strip(), prod.price))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.delete("/api/products/{user_id}/{product_id}")
async def remove_digital_product(user_id: int, product_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM digital_products WHERE user_id = ? AND id = ?", (user_id, product_id))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.delete("/api/leads/{user_id}/{email}")
async def remove_lead_entry(user_id: int, email: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM leads WHERE user_id = ? AND email = ?", (user_id, email.strip().lower()))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.delete("/api/bookings/{user_id}/{booking_id}")
async def cancel_appointment_entry(user_id: int, booking_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookings WHERE user_id = ? AND id = ?", (user_id, booking_id))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.delete("/api/automation-logs/clear")
async def clear_automation_logs(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM analytics WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.delete("/api/email-logs/clear")
async def clear_automated_email_logs(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM email_logs WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.get("/api/domain")
async def get_custom_domain(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT custom_domain FROM custom_domains WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return {"custom_domain": row[0]} if row else {"custom_domain": ""}

@app.post("/api/domain")
async def save_custom_domain(payload: DomainCreate):
    clean_domain = payload.custom_domain.strip().lower()
    if not clean_domain: 
        raise HTTPException(status_code=400, detail="Domain cannot be blank.")
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO custom_domains (user_id, custom_domain) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET custom_domain=excluded.custom_domain", (payload.user_id, clean_domain))
        conn.commit()
        conn.close()
        return {"status": "SUCCESS"}
    except sqlite3.IntegrityError: 
        raise HTTPException(status_code=400, detail="Domain configuration linked elsewhere.")

@app.delete("/api/domain/{user_id}")
async def delete_custom_domain(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM custom_domains WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}


# ========================================================
# PUBLIC PUBLIC GATEWAYS RESOLUTIONS
# ========================================================
@app.get("/api/auth/resolve-domain")
async def resolve_domain(domain: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT u.username FROM users u JOIN custom_domains d ON u.id = d.user_id WHERE d.custom_domain = ?", (domain.strip().lower(),))
    row = cursor.fetchone()
    conn.close()
    if row: 
        return {"username": row[0]}
    raise HTTPException(status_code=404, detail="White-label host domain mapping missing.")

@app.get("/api/public-profile")
async def get_public_profile(username: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    uid = get_uid_from_username(cursor, username)
    cursor.execute("SELECT username, bio_title, bio_desc, avatar_url, theme, consultation_price, button_style, font_family FROM profile_settings WHERE user_id = ?", (uid,))
    row = cursor.fetchone()
    conn.close()
    return {"username": row[0], "bio_title": row[1], "bio_desc": row[2], "avatar_url": row[3], "theme": row[4], "consultation_price": row[5], "button_style": row[6], "font_family": row[7]}

@app.get("/api/public-links")
async def get_public_bio_links_tenant(username: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    uid = get_uid_from_username(cursor, username)
    cursor.execute("SELECT title, url, (SELECT COUNT(*) FROM link_clicks WHERE user_id = link_in_bio.user_id AND link_title = link_in_bio.title) as clicks FROM link_in_bio WHERE user_id = ?", (uid,))
    links = [{"title": l[0], "url": l[1], "clicks": l[2]} for l in cursor.fetchall()]
    conn.close()
    return links

@app.get("/api/public-products")
async def get_public_products_tenant(username: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    uid = get_uid_from_username(cursor, username)
    cursor.execute("SELECT id, title, download_url, price FROM digital_products WHERE user_id = ?", (uid,))
    prods = [{"id": r[0], "title": r[1], "download_url": r[2], "price": r[3]} for r in cursor.fetchall()]
    conn.close()
    return prods

@app.post("/api/click")
async def log_link_click_tenant(username: str, title: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    uid = get_uid_from_username(cursor, username)
    cursor.execute("INSERT INTO link_clicks (user_id, link_title) VALUES (?, ?)", (uid, title.strip()))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS"}

@app.post("/api/leads")
async def capture_new_lead_tenant(lead: LeadCreate):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        uid = get_uid_from_username(cursor, lead.username)
        cursor.execute("INSERT INTO leads (user_id, email) VALUES (?, ?)", (uid, lead.email.strip().lower()))
        conn.commit()
        
        subject = "Welcome Insider! 🎁 Your Premium Creator Growth Drop is here!"
        body = "Hey! Thank you for subscribing to my private LinkKitHub newsletter channel. Get ready for premium strategy updates!"
        simulate_smtp_email_dispatch(uid, lead.email, subject, body)
        return {"status": "SUCCESS"}
    except sqlite3.IntegrityError: 
        raise HTTPException(status_code=400, detail="This email is already subscribed!")
    finally: conn.close()

@app.post("/api/checkout/process")
async def authorize_premium_checkout(order: OrderCreate):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        uid = get_uid_from_username(cursor, order.username)
        cursor.execute("INSERT INTO transactions (user_id, amount, item_type, item_title, customer_email) VALUES (?, ?, ?, ?, ?)", (uid, order.amount, order.item_type, order.item_title.strip(), order.customer_email.strip().lower()))
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
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    uid = get_uid_from_username(cursor, booking.username)
    cursor.execute("INSERT INTO bookings (user_id, name, email, booking_date, booking_time) VALUES (?, ?, ?, ?, ?)", (uid, booking.name.strip(), booking.email.strip().lower(), booking.booking_date.strip(), booking.booking_time.strip()))
    cursor.execute("INSERT INTO transactions (user_id, amount, item_type, item_title, customer_email) VALUES (?, ?, ?, ?, ?)", (uid, booking.amount, "Consultation Slot 🗓️", f"1:1 Sync: {booking.booking_time}", booking.email.strip().lower()))
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
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM analytics WHERE user_id = ?", (user_id,))
    total_replies = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM leads WHERE user_id = ?", (user_id,))
    real_leads_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM link_clicks WHERE user_id = ?", (user_id,))
    real_clicks_count = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ?", (user_id,))
    revenue_aggregate = cursor.fetchone()[0]
    total_revenue = round(revenue_aggregate, 2) if revenue_aggregate else 0.0
    cursor.execute("SELECT keyword, reply_text FROM keyword_rules WHERE user_id = ?", (user_id,))
    active_rules = [{"keyword": r[0], "reply_text": r[1]} for r in cursor.fetchall()]
    cursor.execute("SELECT email, timestamp FROM leads WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
    captured_emails = [{"email": row[0], "date": row[1]} for row in cursor.fetchall()]
    cursor.execute("SELECT id, name, email, booking_date, booking_time FROM bookings WHERE user_id = ? ORDER BY booking_date ASC, booking_time ASC", (user_id,))
    active_bookings = [{"id": row[0], "name": row[1], "email": row[2], "date": row[3], "time": row[4]} for row in cursor.fetchall()]
    cursor.execute("SELECT id, sender_id, keyword_triggered, timestamp FROM analytics WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10", (user_id,))
    automation_logs = [{"id": log[0], "sender_id": log[1], "keyword": log[2], "date": log[3]} for log in cursor.fetchall()]
    cursor.execute("SELECT id, title, download_url, price FROM digital_products WHERE user_id = ? ORDER BY id DESC", (user_id,))
    stored_products = [{"id": row[0], "title": row[1], "download_url": row[2], "price": row[3]} for row in cursor.fetchall()]
    cursor.execute("SELECT amount, item_type, item_title, customer_email, timestamp FROM transactions WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5", (user_id,))
    recent_sales = [{"amount": row[0], "type": row[1], "title": row[2], "email": row[3], "date": row[4]} for row in cursor.fetchall()]
    cursor.execute("SELECT recipient_email, subject, timestamp FROM email_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10", (user_id,))
    outbound_emails = [{"recipient": row[0], "subject": row[1], "date": row[2]} for row in cursor.fetchall()]
    
    dates_list = [(datetime.date.today() - datetime.timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    clicks_map = {d: 0 for d in dates_list}
    rev_map = {d: 0.0 for d in dates_list}

    cursor.execute("SELECT DATE(timestamp), COUNT(*) FROM link_clicks WHERE user_id = ? GROUP BY DATE(timestamp)", (user_id,))
    for r in cursor.fetchall():
        if r[0] in clicks_map: clicks_map[r[0]] = r[1]

    cursor.execute("SELECT DATE(timestamp), SUM(amount) FROM transactions WHERE user_id = ? GROUP BY DATE(timestamp)", (user_id,))
    for r in cursor.fetchall():
        if r[0] in rev_map: rev_map[r[0]] = round(r[1], 2)

    chart_data = {
        "labels": [datetime.datetime.strptime(d, "%Y-%m-%d").strftime("%b %d") for d in dates_list],
        "clicks": [clicks_map[d] for d in dates_list],
        "revenue": [rev_map[d] for d in dates_list]
    }
    
    conn.close()
    return {
        "total_replies": total_replies, "total_clicks": real_clicks_count, "lead_captures": real_leads_count, "total_revenue": total_revenue, "recent_sales": recent_sales, "active_rules": active_rules, "captured_emails": captured_emails, "active_bookings": active_bookings, "automation_logs": automation_logs, "stored_products": stored_products, "outbound_emails": outbound_emails, "chart_data": chart_data
    }

# ========================================================
# 🤖 META INSTAGRAM AUTOMATION WEBHOOK ENGINE
# ========================================================
import json

VERIFY_TOKEN = "linkkithub_secret_token_123"

# 1. Meta Webhook Verification Endpoint (Meta checks this when connecting)
@app.get("/webhook/instagram")
async def verify_instagram_webhook(request: Request):
    query_params = request.query_params
    mode = query_params.get("hub.mode")
    token = query_params.get("hub.verify_token")
    challenge = query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ [META WEBHOOK] Verified successfully!")
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification token mismatch")


class SimulatedComment(BaseModel):
    username: str
    follower_id: str
    comment_text: str

# 2. Webhook Event Receiver (Simulated for testing)
@app.post("/api/simulate-insta-comment")
async def simulate_instagram_comment(payload: SimulatedComment):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Find the creator by username
        cursor.execute("SELECT id FROM users WHERE username = ?", (payload.username.strip().lower(),))
        user_res = cursor.fetchone()
        
        if not user_res:
            return {"status": "IGNORED", "reason": "Creator not found on LinkKitHub"}
            
        user_id = user_res[0]
        incoming_text = payload.comment_text.strip().lower()

        # Check if the comment matches any saved keyword rule
        cursor.execute("SELECT keyword, reply_text FROM keyword_rules WHERE user_id = ?", (user_id,))
        rules = cursor.fetchall()
        
        matched_rule = None
        for rule in rules:
            if rule[0] in incoming_text:  # Keyword match
                matched_rule = rule
                break
                
        if matched_rule:
            keyword_triggered = matched_rule[0]
            reply_text = matched_rule[1]
            
            # Log this in Analytics (This will show up in Dashboard!)
            cursor.execute("INSERT INTO analytics (user_id, sender_id, keyword_triggered) VALUES (?, ?, ?)", 
                           (user_id, payload.follower_id, keyword_triggered))
            conn.commit()
            
            print(f"🚀 [AUTO-DM SENT] To: {payload.follower_id} | Message: {reply_text}")
            return {"status": "SUCCESS", "action": "AUTO_DM_SENT", "message_delivered": reply_text}
        
        return {"status": "IGNORED", "reason": "No keyword matched"}

    except Exception as e:
        print(f"❌ Webhook Error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")
    finally:
        conn.close()
 
init_db()