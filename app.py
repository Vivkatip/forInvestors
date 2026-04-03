import streamlit as st
from datetime import date, datetime, timedelta
import sqlite3
import json
import random
import pandas as pd
import altair as alt

st.set_page_config(page_title="SleepFlow", page_icon="☁️", layout="wide", initial_sidebar_state="expanded")

DB_PATH = "sleepflow_app.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    cur.execute("""CREATE TABLE IF NOT EXISTS sleep_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, log_date TEXT, sleep_hours REAL,
        bedtime TEXT, wake_time TEXT, fall_asleep_minutes INTEGER,
        daytime_activity TEXT, sleep_quality INTEGER, energy_morning TEXT,
        stress_level TEXT, screen_evening TEXT, caffeine_evening TEXT,
        note TEXT, created_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS alarms (
        id INTEGER PRIMARY KEY AUTOINCREMENT, alarm_time TEXT, window_minutes INTEGER,
        days_json TEXT, label TEXT, smart_enabled INTEGER, active INTEGER)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS routines (
        id INTEGER PRIMARY KEY AUTOINCREMENT, routine_date TEXT UNIQUE,
        breath_done INTEGER DEFAULT 0, sound_done INTEGER DEFAULT 0,
        blocked_done INTEGER DEFAULT 0, journal_done INTEGER DEFAULT 0,
        total_points INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, title TEXT,
        description TEXT, icon TEXT DEFAULT '🏆', unlocked INTEGER DEFAULT 0, unlocked_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS focus_blocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, start_time TEXT, end_time TEXT, apps_json TEXT, active INTEGER)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS family_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, role TEXT, points INTEGER, streak INTEGER, sleep_avg REAL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS family_feed (
        id INTEGER PRIMARY KEY AUTOINCREMENT, feed_time TEXT, author TEXT, message TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS daily_quests (
        id INTEGER PRIMARY KEY AUTOINCREMENT, quest_date TEXT, quest_type TEXT,
        quest_text TEXT, completed INTEGER DEFAULT 0, xp_reward INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS user_level (
        id INTEGER PRIMARY KEY, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1,
        coins INTEGER DEFAULT 0, freezes INTEGER DEFAULT 2)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS shop_purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT, item_code TEXT, purchased_at TEXT, active INTEGER DEFAULT 1)""")
    conn.commit()
    seed_defaults(conn)
    conn.close()

def set_setting(key, value):
    conn = get_conn()
    conn.cursor().execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                          (key, json.dumps(value, ensure_ascii=False)))
    conn.commit(); conn.close()

def get_setting(key, default=None):
    conn = get_conn()
    row = conn.cursor().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    if not row: return default
    try: return json.loads(row["value"])
    except: return default

def seed_defaults(conn):
    cur = conn.cursor()
    for k, v in {"theme":"dark","page":"Главная","selected_sound":"Океан","user_name":"Алексей",
                 "breath_cycle_seconds":5,"breath_running":False,"cloud_name":"Соня"}.items():
        cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, json.dumps(v, ensure_ascii=False)))
    if cur.execute("SELECT COUNT(*) c FROM user_level").fetchone()["c"] == 0:
        cur.execute("INSERT INTO user_level(id,xp,level,coins,freezes) VALUES(1,20,2,15,2)")
    if cur.execute("SELECT COUNT(*) c FROM sleep_logs").fetchone()["c"] == 0:
        base = date.today() - timedelta(days=13)
        for d,h,bt,wt,fa,act,q,en,sl,sc,caf,note in [
            (0,6.8,"23:55","06:55",25,"Без активности",6,"Сонно","Высокий","2+ часа","Да","Поздно"),
            (1,7.3,"23:35","07:00",20,"Прогулка",7,"Нормально","Средний","1–2 часа","Нет","Ровнее"),
            (2,7.9,"23:05","07:05",14,"Йога",8,"Хорошо","Низкий","до 1 часа","Нет","Спокойно"),
            (3,8.2,"22:55","07:10",12,"Тренировка",9,"Отлично","Низкий","до 1 часа","Нет","Супер"),
            (4,7.1,"23:40","07:00",22,"Прогулка",7,"Нормально","Средний","1–2 часа","Нет","Норм"),
            (5,6.5,"00:15","06:55",31,"Без активности",5,"Сонно","Высокий","2+ часа","Да","Плохо"),
            (6,7.8,"23:10","07:05",16,"Тренировка",8,"Хорошо","Низкий","до 1 часа","Нет","Хорошо"),
            (7,7.6,"23:20","07:00",18,"Йога",8,"Хорошо","Низкий","до 1 часа","Нет","Ровно"),
            (8,6.9,"23:50","06:55",27,"Без активности",6,"Сонно","Средний","1–2 часа","Да","Просыпался"),
            (9,8.1,"22:58","07:08",11,"Прогулка",9,"Отлично","Низкий","до 1 часа","Нет","Легко"),
            (10,7.4,"23:25","07:03",19,"Активный день",7,"Нормально","Средний","1–2 часа","Нет","Стабильно"),
            (11,8.0,"23:00","07:04",13,"Тренировка",9,"Отлично","Низкий","до 1 часа","Нет","Качество"),
            (12,7.7,"23:12","07:02",15,"Йога",8,"Хорошо","Низкий","до 1 часа","Нет","Комфорт"),
            (13,7.5,"23:18","07:01",16,"Прогулка",8,"Хорошо","Средний","1–2 часа","Нет","Неплохо")]:
            cur.execute("""INSERT INTO sleep_logs(log_date,sleep_hours,bedtime,wake_time,fall_asleep_minutes,
                daytime_activity,sleep_quality,energy_morning,stress_level,screen_evening,caffeine_evening,note,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (str(base+timedelta(days=d)),h,bt,wt,fa,act,q,en,sl,sc,caf,note,datetime.now().isoformat()))
    if cur.execute("SELECT COUNT(*) c FROM alarms").fetchone()["c"] == 0:
        cur.execute("INSERT INTO alarms VALUES(NULL,'07:00',30,?,?,1,1)", (json.dumps(["Пн","Вт","Ср","Чт","Пт"]),"Будни"))
    if cur.execute("SELECT COUNT(*) c FROM routines").fetchone()["c"] == 0:
        for i in range(14):
            d = str(date.today()-timedelta(days=13-i))
            b,s,bl,j = int(i%2==0),1,int(i%3!=0),int(i%2==1)
            cur.execute("INSERT OR IGNORE INTO routines VALUES(NULL,?,?,?,?,?,?)", (d,b,s,bl,j,b*20+s*15+bl*25+j*30))
    if cur.execute("SELECT COUNT(*) c FROM achievements").fetchone()["c"] == 0:
        for c2,t,ds,ic in [("first_breath","Первый вдох","Первая дыхательная сессия","🌬️"),
            ("journal_3","Наблюдатель","Дневник 3 дня подряд","📔"),("sleep_8","Идеальная ночь","8 часов сна","🌙"),
            ("streak_5","Стабильность","Серия 5 дней","🔥"),("streak_10","Мастер","Серия 10 дней","⚡"),
            ("family_join","Вместе","Семейный режим","👨‍👩‍👧"),("coins_100","Копилка","100 монет","💰"),
            ("level_5","Продвинутый","Уровень 5","⭐"),("level_10","Эксперт","Уровень 10","🏅"),
            ("breath_10","Мастер дыхания","10 сессий","🧘")]:
            cur.execute("INSERT INTO achievements(code,title,description,icon,unlocked) VALUES(?,?,?,?,0)", (c2,t,ds,ic))
    if cur.execute("SELECT COUNT(*) c FROM focus_blocks").fetchone()["c"] == 0:
        cur.execute("INSERT INTO focus_blocks VALUES(NULL,'22:30','07:00',?,1)",
                    (json.dumps(["Instagram","TikTok","YouTube","Telegram"]),))
    if cur.execute("SELECT COUNT(*) c FROM family_members").fetchone()["c"] == 0:
        for n,r,p,s,a in [("Алексей","Вы",245,6,7.5),("Анна","Партнёр",290,9,7.9),("Миша","Ребёнок",180,4,9.1)]:
            cur.execute("INSERT INTO family_members VALUES(NULL,?,?,?,?,?)", (n,r,p,s,a))
    if cur.execute("SELECT COUNT(*) c FROM family_feed").fetchone()["c"] == 0:
        for a,m in [("Анна","Вечерний ритуал ✨"),("Миша","Лёг вовремя 🌙"),("Алексей","Запись в дневник 📔")]:
            cur.execute("INSERT INTO family_feed VALUES(NULL,?,?,?)", (datetime.now().isoformat(),a,m))
    conn.commit()

init_db()

boot = {"theme":"dark","page":"Главная","selected_sound":"Океан","user_name":"Алексей",
        "breath_cycle_seconds":5,"breath_running":False,"cloud_name":"Соня"}
for k,v in boot.items():
    if k not in st.session_state:
        st.session_state[k] = get_setting(k, v)

THEMES = {
    "dark": {
        "bg":"#071421","bg2":"#0B2030","card":"#10283D","card2":"#14334F",
        "border":"rgba(190,220,245,0.12)","text":"#F5FBFF","subtext":"#D6E6F3",
        "muted":"#A7BED3","accent":"#78C9FF","accent2":"#9AB8FF",
        "gold":"#FFD76D","danger":"#FF9AAE","success":"#7BE3A9",
        "shadow":"0 8px 32px rgba(0,0,0,0.32)",
        "input_bg":"#0D2235","input_text":"#F5FBFF",
        "sidebar":"#081A28","streak_fire":"#FF9F43","freeze_blue":"#54A0FF",
        "chart1":"#78C9FF","chart2":"#9AB8FF",
        "dd_bg":"#10283D","dd_text":"#F5FBFF","dd_hover":"#1a3a55","dd_border":"rgba(190,220,245,0.18)",
    },
    "light": {
        "bg":"#EAF5FF","bg2":"#DCEEFE","card":"#FFFFFF","card2":"#F8FBFF",
        "border":"#D0E2F2","text":"#14334A","subtext":"#456B86",
        "muted":"#6E8DA6","accent":"#2E92D3","accent2":"#6E8DFF",
        "gold":"#C99112","danger":"#DB5976","success":"#1F9E68",
        "shadow":"0 8px 24px rgba(20,51,74,0.08)",
        "input_bg":"#F0F7FF","input_text":"#14334A",
        "sidebar":"#F0F7FF","streak_fire":"#E67E22","freeze_blue":"#3498DB",
        "chart1":"#2E92D3","chart2":"#6E8DFF",
        "dd_bg":"#FFFFFF","dd_text":"#14334A","dd_hover":"#EAF1F8","dd_border":"#D0E2F2",
    }
}
T = THEMES[st.session_state.theme]

SOUNDS = {
    "Океан":("Глубокий шум волн","https://actions.google.com/sounds/v1/water/ocean_waves.ogg","🌊"),
    "Лес":("Атмосфера леса","https://actions.google.com/sounds/v1/ambiences/forest_ambience.ogg","🌲"),
    "Ручей":("Мягкий поток","https://actions.google.com/sounds/v1/water/stream.ogg","💧"),
    "Камин":("Потрескивание огня","https://actions.google.com/sounds/v1/foley/fireplace.ogg","🔥"),
    "Белый шум":("Нейтральный фон","https://actions.google.com/sounds/v1/ambiences/air_conditioner.ogg","🎛️"),
    "Ветер":("Тихий ветер","https://actions.google.com/sounds/v1/weather/wind_whistling.ogg","🍃"),
}
DISTRACT_APPS = ["Instagram","TikTok","YouTube","Telegram","VK","Discord","Twitch","Netflix","Игры","X/Twitter"]
DAY_NAMES = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
NAV_ITEMS = [("Главная","🏠"),("Дыхание","💨"),("Звуки","🎵"),("Будильник","⏰"),
             ("Фокус","🎯"),("Дневник","📔"),("Статистика","📊"),
             ("Магазин","🛒"),("Семья","👨‍👩‍👧"),("Настройки","⚙️")]
QUEST_PAGE = {"breath":"Дыхание","journal":"Дневник","sound":"Звуки","focus":"Фокус"}
SHOP_ITEMS = [
    {"code":"freeze","name":"❄️ Заморозка","desc":"Сохрани серию","price":20,"currency":"coins","icon":"❄️"},
    {"code":"2x_xp","name":"⭐ 2x XP","desc":"Двойной опыт на день","price":30,"currency":"coins","icon":"⭐"},
    {"code":"custom_sound","name":"🎶 Премиум звуки","desc":"6 доп. звуков","price":50,"currency":"coins","icon":"🎶"},
    {"code":"theme_pack","name":"🎨 Темы","desc":"Доп. цветовые темы","price":40,"currency":"coins","icon":"🎨"},
    {"code":"sub_monthly","name":"👑 Pro (месяц)","desc":"Всё включено","price":299,"currency":"rub","icon":"👑"},
    {"code":"sub_yearly","name":"💎 Pro (год)","desc":"Экономия 40%","price":1990,"currency":"rub","icon":"💎"},
]

def cloud_svg(mood="happy", size="140px"):
    if mood == "happy":
        return f'<svg viewBox="0 0 200 160" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:{size};display:block"><ellipse cx="100" cy="100" rx="70" ry="40" fill="white" opacity=".95"/><circle cx="65" cy="85" r="32" fill="white" opacity=".95"/><circle cx="135" cy="85" r="28" fill="white" opacity=".95"/><circle cx="100" cy="70" r="35" fill="white" opacity=".95"/><circle cx="78" cy="72" r="26" fill="white" opacity=".95"/><circle cx="122" cy="72" r="26" fill="white" opacity=".95"/><circle cx="82" cy="88" r="4" fill="#4A5568"/><circle cx="112" cy="88" r="4" fill="#4A5568"/><circle cx="83" cy="87" r="1.5" fill="white"/><circle cx="113" cy="87" r="1.5" fill="white"/><circle cx="72" cy="96" r="6" fill="#FFB8C6" opacity=".4"/><circle cx="122" cy="96" r="6" fill="#FFB8C6" opacity=".4"/><path d="M86 98 Q97 112 110 98" stroke="#4A5568" stroke-width="2" fill="none" stroke-linecap="round"/><text x="145" y="58" font-size="16" fill="#FFD76D" opacity=".8">✦</text></svg>'
    elif mood == "sleeping":
        return f'<svg viewBox="0 0 200 160" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:{size};display:block"><ellipse cx="100" cy="100" rx="70" ry="40" fill="white" opacity=".95"/><circle cx="65" cy="85" r="32" fill="white" opacity=".95"/><circle cx="135" cy="85" r="28" fill="white" opacity=".95"/><circle cx="100" cy="70" r="35" fill="white" opacity=".95"/><circle cx="78" cy="72" r="26" fill="white" opacity=".95"/><circle cx="122" cy="72" r="26" fill="white" opacity=".95"/><path d="M115 52 Q140 20 155 45 L135 60 Z" fill="#A8D8FF" stroke="#8EC5E8" stroke-width="1.5"/><circle cx="155" cy="43" r="6" fill="white" opacity=".9"/><path d="M78 90 Q82 86 86 90" stroke="#7B8FA6" stroke-width="2.2" fill="none" stroke-linecap="round"/><path d="M108 90 Q112 86 116 90" stroke="#7B8FA6" stroke-width="2.2" fill="none" stroke-linecap="round"/><circle cx="72" cy="96" r="6" fill="#FFB8C6" opacity=".4"/><circle cx="122" cy="96" r="6" fill="#FFB8C6" opacity=".4"/><path d="M90 100 Q97 108 106 100" stroke="#7B8FA6" stroke-width="1.8" fill="none" stroke-linecap="round"/><text x="148" y="55" font-size="14" fill="#A8D8FF" font-weight="bold" opacity=".7">z</text><text x="158" y="42" font-size="11" fill="#A8D8FF" font-weight="bold" opacity=".5">z</text></svg>'
    else:
        return f'<svg viewBox="0 0 200 160" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:{size};display:block"><ellipse cx="100" cy="100" rx="70" ry="40" fill="#E8EDF2" opacity=".95"/><circle cx="65" cy="85" r="32" fill="#E8EDF2" opacity=".95"/><circle cx="135" cy="85" r="28" fill="#E8EDF2" opacity=".95"/><circle cx="100" cy="70" r="35" fill="#E8EDF2" opacity=".95"/><circle cx="78" cy="72" r="26" fill="#E8EDF2" opacity=".95"/><circle cx="122" cy="72" r="26" fill="#E8EDF2" opacity=".95"/><circle cx="82" cy="88" r="3.5" fill="#6B7C93"/><circle cx="112" cy="88" r="3.5" fill="#6B7C93"/><path d="M88 104 Q97 96 108 104" stroke="#6B7C93" stroke-width="2" fill="none" stroke-linecap="round"/><line x1="75" y1="125" x2="73" y2="140" stroke="#A8D8FF" stroke-width="2" opacity=".5"/><line x1="95" y1="128" x2="93" y2="145" stroke="#A8D8FF" stroke-width="2" opacity=".4"/><line x1="115" y1="126" x2="113" y2="142" stroke="#A8D8FF" stroke-width="2" opacity=".5"/></svg>'

def mascot_msg(ctx="home"):
    s = calc_streak()
    m = {"home":[f"Привет! Я {st.session_state.cloud_name} ☁️ Давай улучшим сон!",f"Серия {s} дн! 💪","Хороший сон — суперсила! ✨","Ложись пораньше 🌙"],
         "breath":["Давай подышим! 💨","Вдох... выдох... Молодец! 🫁"],
         "journal":["Запись = +30 XP! 📔","Каждая запись помогает 💤"],
         "streak_lost":["Серия может прерваться! ❄️","Начнём заново 💙"],
         "shop":["Монеты с пользой! 💰","Заморозки спасают ❄️"]}
    return random.choice(m.get(ctx, m["home"]))

# ======================== MASSIVE CSS ========================
st.markdown(f"""
<style>
/* ===== NUCLEAR RESET - KILL ALL WHITE BACKGROUNDS ===== */
html, body {{ background: {T['bg']} !important; background-color: {T['bg']} !important; }}
.stApp {{ background: {T['bg']} !important; background-color: {T['bg']} !important; }}

/* Every single Streamlit container */
.stApp > div,
.stApp > div > div,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"],
[data-testid="stMain"],
[data-testid="stMainMenu"],
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stBottomBlockContainer"],
[data-testid="stStatusWidget"],
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
[data-testid="column"],
.main,
.appview-container,
.element-container,
.stMarkdown,
[data-testid="stMarkdownContainer"],
footer, header {{
    background: transparent !important;
    background-color: transparent !important;
    background-image: none !important;
}}

* {{ font-family: 'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; color: {T['text']}; }}
h1,h2,h3,h4,h5,h6,p,li,span,label,div {{ color: {T['text']} !important; }}

.main .block-container {{ max-width:100% !important; padding:1rem 2rem 3rem !important; }}
@media(min-width:768px) {{ .main .block-container {{ max-width:1320px !important; margin:0 auto; }} }}

/* ===== SIDEBAR ===== */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] > div > div,
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div {{
    background: {T['sidebar']} !important;
    background-color: {T['sidebar']} !important;
}}
section[data-testid="stSidebar"] {{ min-width:270px !important; max-width:270px !important; }}
[data-testid="stSidebarCollapsedControl"] {{ background: transparent !important; }}

/* ===== CARDS ===== */
.mc {{ background:linear-gradient(135deg,{T['card2']},{T['card']}); border:1px solid {T['border']};
    border-radius:20px; padding:20px; box-shadow:{T['shadow']}; }}
.hc {{ background:radial-gradient(ellipse at top right,rgba(120,201,255,.06),transparent 50%),
    linear-gradient(135deg,{T['card2']},{T['card']}); border:1px solid {T['border']};
    border-radius:24px; padding:26px; box-shadow:{T['shadow']}; }}
.sc {{ background:linear-gradient(135deg,{T['card2']},{T['card']}); border:1px solid {T['border']};
    border-radius:20px; padding:18px; box-shadow:{T['shadow']}; min-height:120px; }}

.st_ {{ font-size:1.1rem; font-weight:800; margin-bottom:.6rem; }}
.bt {{ font-size:1.9rem; font-weight:900; line-height:1.12; }}
.kpi {{ font-size:1.8rem; font-weight:900; margin-top:.2rem; }}
.ml {{ color:{T['subtext']} !important; margin-top:.3rem; font-size:.9rem; }}
.sm {{ color:{T['subtext']} !important; font-size:.95rem; line-height:1.55; }}

.bg1 {{ display:inline-flex; align-items:center; gap:6px; padding:.35rem .72rem; border-radius:999px;
    background:rgba(120,201,255,.12); color:{T['accent']} !important; border:1px solid rgba(120,201,255,.20);
    font-size:.82rem; font-weight:700; }}
.bg2 {{ display:inline-flex; align-items:center; gap:6px; padding:.35rem .72rem; border-radius:999px;
    background:rgba(255,215,109,.12); color:{T['gold']} !important; border:1px solid rgba(255,215,109,.20);
    font-size:.82rem; font-weight:700; }}
.bg3 {{ display:inline-flex; align-items:center; gap:6px; padding:.35rem .72rem; border-radius:999px;
    background:rgba(255,159,67,.12); color:{T['streak_fire']} !important; border:1px solid rgba(255,159,67,.20);
    font-size:.82rem; font-weight:700; }}

.ins {{ border-left:3px solid {T['accent']}; border-radius:14px; padding:.9rem 1rem; background:rgba(120,201,255,.06); }}
.dv {{ height:1px; background:{T['border']}; margin:.8rem 0; }}

.xpo {{ width:100%; height:12px; background:rgba(120,201,255,.15); border-radius:999px; overflow:hidden; margin:4px 0; }}
.xpi {{ height:100%; background:linear-gradient(90deg,{T['accent']},{T['accent2']}); border-radius:999px; }}

.sd {{ display:inline-flex; align-items:center; justify-content:center; width:34px; height:34px;
    border-radius:10px; font-size:.76rem; font-weight:700; margin:2px; }}
.sd-done {{ background:rgba(123,227,169,.20); color:{T['success']} !important; border:1.5px solid rgba(123,227,169,.35); }}
.sd-missed {{ background:rgba(255,154,174,.12); color:{T['danger']} !important; border:1.5px solid rgba(255,154,174,.25); }}
.sd-today {{ background:rgba(120,201,255,.18); color:{T['accent']} !important; border:2px solid {T['accent']}; }}
.sd-future {{ background:rgba(120,201,255,.05); color:{T['muted']} !important; border:1.5px solid {T['border']}; }}

/* ===== BUTTONS - transparent bg, themed border ===== */
div.stButton > button {{
    width:100%; min-height:44px; border-radius:14px;
    border:1px solid {T['border']} !important;
    background:linear-gradient(135deg,{T['card2']},{T['card']}) !important;
    color:{T['text']} !important; font-weight:700 !important; font-size:.92rem !important;
    box-shadow:none !important;
}}
div.stButton > button:hover {{
    border-color:{T['accent']} !important;
    background:linear-gradient(135deg,{T['card2']},{T['card']}) !important;
}}
div.stButton > button:active, div.stButton > button:focus {{
    background:linear-gradient(135deg,{T['card2']},{T['card']}) !important;
    color:{T['text']} !important;
    box-shadow:none !important; outline:none !important;
}}

/* ===== ALL INPUTS, SELECTS, DROPDOWNS ===== */
input, textarea {{
    background:{T['input_bg']} !important; color:{T['input_text']} !important;
    -webkit-text-fill-color:{T['input_text']} !important;
    border-color:{T['dd_border']} !important;
}}
input::placeholder, textarea::placeholder {{ color:{T['muted']} !important; opacity:1 !important; }}

.stTextInput input, .stTextArea textarea, .stNumberInput input,
.stNumberInput > div > div > input {{
    background:{T['input_bg']} !important; color:{T['input_text']} !important; border-radius:12px !important;
}}

/* Select trigger box */
div[data-baseweb="select"] > div {{
    background:{T['dd_bg']} !important; color:{T['dd_text']} !important;
    border:1px solid {T['dd_border']} !important; border-radius:12px !important;
}}
div[data-baseweb="select"] > div > div {{ color:{T['dd_text']} !important; }}
div[data-baseweb="select"] > div > div > div {{ color:{T['dd_text']} !important; }}
div[data-baseweb="select"] svg {{ fill:{T['dd_text']} !important; }}

/* ===== DROPDOWN POPOVER / MENU — THE KEY FIX ===== */
div[data-baseweb="popover"] {{
    background:{T['dd_bg']} !important; border:1px solid {T['dd_border']} !important;
    border-radius:12px !important;
}}
div[data-baseweb="popover"] > div {{
    background:{T['dd_bg']} !important;
}}
/* Menu list itself */
ul[role="listbox"] {{
    background:{T['dd_bg']} !important; background-color:{T['dd_bg']} !important;
}}
ul[role="listbox"] li {{
    background:{T['dd_bg']} !important; background-color:{T['dd_bg']} !important;
    color:{T['dd_text']} !important;
}}
ul[role="listbox"] li:hover {{
    background:{T['dd_hover']} !important; background-color:{T['dd_hover']} !important;
}}
ul[role="listbox"] li[aria-selected="true"] {{
    background:{T['dd_hover']} !important;
}}
/* Alternative menu structure */
div[role="listbox"] {{ background:{T['dd_bg']} !important; }}
div[role="listbox"] > div {{ background:{T['dd_bg']} !important; color:{T['dd_text']} !important; }}
div[role="option"] {{ background:{T['dd_bg']} !important; color:{T['dd_text']} !important; }}
div[role="option"]:hover {{ background:{T['dd_hover']} !important; }}

/* Baseweb menu */
[data-baseweb="menu"] {{ background:{T['dd_bg']} !important; }}
[data-baseweb="menu"] ul {{ background:{T['dd_bg']} !important; }}
[data-baseweb="menu"] li {{ background:{T['dd_bg']} !important; color:{T['dd_text']} !important; }}
[data-baseweb="menu"] li:hover {{ background:{T['dd_hover']} !important; }}

/* Multi-select tags */
[data-baseweb="tag"] {{ background:rgba(120,201,255,.15) !important; }}
[data-baseweb="tag"] span {{ color:{T['accent']} !important; }}
[data-baseweb="tag"] svg {{ fill:{T['accent']} !important; }}

/* Input containers */
div[data-baseweb="input"] > div {{ background:{T['input_bg']} !important; border:1px solid {T['dd_border']} !important; border-radius:12px !important; }}
div[data-baseweb="input"] {{ background:{T['input_bg']} !important; }}
div[data-baseweb="textarea"] > div {{ background:{T['input_bg']} !important; border:1px solid {T['dd_border']} !important; }}

/* Date input */
[data-testid="stDateInput"] > div {{ background:{T['input_bg']} !important; }}
[data-testid="stDateInput"] input {{ background:{T['input_bg']} !important; color:{T['input_text']} !important; }}
[data-baseweb="calendar"], [data-baseweb="calendar"] * {{
    background:{T['dd_bg']} !important; color:{T['dd_text']} !important;
}}

/* Slider */
.stSlider > div > div > div {{ color:{T['text']} !important; }}
[data-baseweb="slider"] {{ background:transparent !important; }}
[data-baseweb="slider"] div[role="slider"] {{ background:{T['accent']} !important; }}

/* Radio & Checkbox */
.stRadio label p, .stCheckbox label p {{ color:{T['text']} !important; }}
/* Toggle */
[data-testid="stToggle"] label span {{ color:{T['text']} !important; }}
/* Form */
[data-testid="stForm"] {{ background:transparent !important; border:1px solid {T['border']} !important; border-radius:16px !important; }}

/* Audio */
audio {{ border-radius:12px; filter: {'invert(0)' if st.session_state.theme == 'light' else 'invert(1) hue-rotate(180deg)'}; }}

/* Altair */
.vega-embed {{ background:transparent !important; }}
.vega-embed summary {{ color:{T['muted']} !important; }}

/* ===== SIDEBAR STYLES ===== */
.sh {{ background:linear-gradient(135deg,rgba(120,201,255,.10),rgba(154,184,255,.06));
    border-radius:16px; padding:16px 14px; margin-bottom:12px; border:1px solid {T['border']}; }}

/* Quest card */
.qc {{ background:linear-gradient(135deg,{T['card2']},{T['card']}); border:1px solid {T['border']};
    border-radius:14px; padding:12px 14px; margin-bottom:6px; display:flex; align-items:center; gap:12px; }}

/* Level ring */
.lr {{ display:inline-flex; align-items:center; justify-content:center; width:42px; height:42px;
    border-radius:999px; background:linear-gradient(135deg,rgba(120,201,255,.15),rgba(154,184,255,.10));
    border:2px solid {T['accent']}; font-size:1rem; font-weight:900; color:{T['accent']} !important; flex-shrink:0; }}

/* Mascot */
.mr {{ display:flex; align-items:flex-end; gap:12px; margin:8px 0; }}
.mb {{ background:linear-gradient(135deg,{T['card2']},{T['card']}); border:1px solid {T['border']};
    border-radius:16px; padding:12px 14px; font-size:.9rem; position:relative; flex:1; box-shadow:{T['shadow']}; }}
.mb::after {{ content:''; position:absolute; bottom:-7px; left:24px; width:14px; height:14px;
    background:{T['card']}; border:1px solid {T['border']}; border-top:none; border-left:none; transform:rotate(45deg); }}

/* Breath */
.bbg {{ background:#000; border-radius:24px; padding:30px; position:relative; overflow:hidden;
    min-height:400px; display:flex; flex-direction:column; align-items:center; justify-content:center; }}
.bst {{ position:absolute; inset:0; pointer-events:none; background:
    radial-gradient(1px 1px at 20% 30%,rgba(255,255,255,.4),transparent),
    radial-gradient(1px 1px at 80% 20%,rgba(255,255,255,.3),transparent),
    radial-gradient(1px 1px at 40% 60%,rgba(255,255,255,.2),transparent),
    radial-gradient(1px 1px at 60% 80%,rgba(255,255,255,.3),transparent),
    radial-gradient(1px 1px at 10% 90%,rgba(255,255,255,.2),transparent),
    radial-gradient(1px 1px at 90% 50%,rgba(255,255,255,.35),transparent); }}
.bmn {{ position:absolute; top:25px; right:35px; width:45px; height:45px; border-radius:999px;
    background:radial-gradient(circle at 35% 35%,#FFF8E7,#FFE4A0 60%,#F0C040);
    box-shadow:0 0 40px rgba(255,228,160,.3); }}
@keyframes ba {{ 0%{{transform:scale(.65);opacity:.5}} 50%{{transform:scale(1.15);opacity:1}} 100%{{transform:scale(.65);opacity:.5}} }}
.bc {{ width:200px; height:200px; border-radius:999px;
    background:radial-gradient(circle at 30% 30%,rgba(255,255,255,.22),rgba(120,201,255,.18) 40%,rgba(154,184,255,.08) 70%);
    box-shadow:0 0 0 20px rgba(120,201,255,.04),0 0 60px rgba(120,201,255,.12),inset 0 0 50px rgba(255,255,255,.05);
    position:relative; z-index:2; display:flex; align-items:center; justify-content:center; }}
.bc.an {{ animation:ba var(--cy) ease-in-out infinite; }}
.bl {{ font-size:1.15rem; font-weight:800; color:rgba(255,255,255,.85); text-shadow:0 2px 20px rgba(0,0,0,.5); }}

/* Feed, tree, shop */
.fi {{ padding:10px 12px; border-radius:12px; border:1px solid {T['border']}; margin-bottom:6px; }}
.tb {{ position:relative; height:200px; border-radius:20px; border:1px solid {T['border']};
    background:radial-gradient(ellipse at center 30%,rgba(130,226,219,.10),transparent 50%); overflow:hidden; }}
.tt {{ position:absolute; bottom:20px; left:50%; transform:translateX(-50%); width:18px;
    border-radius:9px; background:linear-gradient(180deg,#A0764A,#8B5E3C); }}
.tc {{ position:absolute; left:50%; transform:translateX(-50%); border-radius:999px;
    background:radial-gradient(circle at 30% 30%,#D0FFE8,#48C78E 70%); box-shadow:0 6px 20px rgba(72,199,142,.15); }}
.spc {{ background:linear-gradient(135deg,{T['card2']},{T['card']}); border:1px solid {T['border']};
    border-radius:18px; padding:20px; box-shadow:{T['shadow']}; text-align:center; }}
.spi {{ font-size:2.2rem; margin-bottom:8px; }}
.spp {{ font-size:1.1rem; font-weight:900; margin-top:8px; }}

@media(max-width:768px) {{ .bt{{font-size:1.4rem}} .kpi{{font-size:1.5rem}} }}
</style>
""", unsafe_allow_html=True)

# ======================== HELPERS ========================
def save_st():
    for k in ["theme","page","selected_sound","user_name","breath_cycle_seconds","breath_running","cloud_name"]:
        set_setting(k, st.session_state.get(k))

def go(p):
    st.session_state.page = p; save_st(); st.rerun()

def qdf(sql, p=()):
    c = get_conn(); df = pd.read_sql_query(sql, c, params=p); c.close(); return df

def xp_for_level(lvl): return int(80 * (1.25 ** (lvl - 1)))

def get_ul():
    c = get_conn(); r = c.cursor().execute("SELECT * FROM user_level WHERE id=1").fetchone(); c.close()
    return dict(r) if r else {"xp":0,"level":1,"coins":0,"freezes":2}

def add_xp(amt):
    c = get_conn(); cur = c.cursor(); r = cur.execute("SELECT * FROM user_level WHERE id=1").fetchone()
    xp, lvl, coins = r["xp"]+amt, r["level"], r["coins"]
    needed = xp_for_level(lvl)
    while xp >= needed: xp -= needed; lvl += 1; coins += 10+lvl*2; needed = xp_for_level(lvl)
    cur.execute("UPDATE user_level SET xp=?,level=?,coins=? WHERE id=1", (xp,lvl,coins)); c.commit(); c.close()
    if lvl >= 5: unlock_ach("level_5")
    if lvl >= 10: unlock_ach("level_10")
    if coins >= 100: unlock_ach("coins_100")

def add_coins(n):
    c = get_conn(); c.cursor().execute("UPDATE user_level SET coins=coins+? WHERE id=1",(n,)); c.commit(); c.close()

def use_freeze():
    c = get_conn(); cur = c.cursor(); r = cur.execute("SELECT freezes FROM user_level WHERE id=1").fetchone()
    if r and r["freezes"] > 0:
        cur.execute("UPDATE user_level SET freezes=freezes-1 WHERE id=1"); c.commit(); c.close(); return True
    c.close(); return False

def unlock_ach(code):
    c = get_conn(); cur = c.cursor()
    r = cur.execute("SELECT unlocked FROM achievements WHERE code=?",(code,)).fetchone()
    if r and not r["unlocked"]:
        cur.execute("UPDATE achievements SET unlocked=1,unlocked_at=? WHERE code=?",(datetime.now().isoformat(),code))
        c.commit()
    c.close()

def calc_streak():
    df = qdf("SELECT routine_date,total_points FROM routines ORDER BY routine_date DESC")
    if df.empty: return 0
    s, exp = 0, date.today()
    for _,r in df.iterrows():
        d = datetime.fromisoformat(r["routine_date"]).date()
        if d == exp and r["total_points"] > 0: s += 1; exp -= timedelta(days=1)
        else: break
    return s

def streak_freeze():
    df = qdf("SELECT routine_date,total_points FROM routines ORDER BY routine_date DESC")
    if df.empty: return 0, False
    s, exp, nf = 0, date.today(), False
    for _,r in df.iterrows():
        d = datetime.fromisoformat(r["routine_date"]).date()
        if d == exp:
            if r["total_points"] > 0: s += 1; exp -= timedelta(days=1)
            else: nf = True; break
        elif d < exp: nf = True; break
    return s, nf

def streak_cal(n=14):
    df = qdf("SELECT routine_date,total_points FROM routines ORDER BY routine_date DESC LIMIT ?",(n*2,))
    dp = {r["routine_date"]:r["total_points"] for _,r in df.iterrows()}
    res = []
    for i in range(n-1,-1,-1):
        d = date.today()-timedelta(days=i); ds = str(d); pts = dp.get(ds,0)
        if d == date.today(): st_ = "today"
        elif pts > 0: st_ = "done"
        else: st_ = "missed"
        res.append({"date":d,"status":st_})
    return res

def mark_rout(field, pts):
    today = str(date.today()); c = get_conn(); cur = c.cursor()
    r = cur.execute("SELECT * FROM routines WHERE routine_date=?",(today,)).fetchone()
    if r:
        if r[field] == 0:
            cur.execute(f"UPDATE routines SET {field}=1,total_points=? WHERE routine_date=?",(r["total_points"]+pts,today))
    else:
        vals = {"breath_done":0,"sound_done":0,"blocked_done":0,"journal_done":0}; vals[field] = 1
        cur.execute("INSERT OR IGNORE INTO routines(routine_date,breath_done,sound_done,blocked_done,journal_done,total_points) VALUES(?,?,?,?,?,?)",
                    (today,vals["breath_done"],vals["sound_done"],vals["blocked_done"],vals["journal_done"],pts))
    c.commit(); c.close(); add_xp(pts)

def avg_slp(d=7):
    df = qdf("SELECT sleep_hours FROM sleep_logs ORDER BY log_date DESC LIMIT ?",(d,))
    return round(df["sleep_hours"].mean(),1) if not df.empty else 0

def last_log():
    df = qdf("SELECT * FROM sleep_logs ORDER BY log_date DESC LIMIT 1")
    return df.iloc[0] if not df.empty else None

def smart_alarm(t, w):
    tgt = datetime.strptime(t,"%H:%M"); cand = tgt-timedelta(minutes=w)+timedelta(minutes=random.choice([8,14,18,24]))
    return min(cand,tgt).strftime("%H:%M")

def get_recs():
    df = qdf("SELECT * FROM sleep_logs ORDER BY log_date DESC LIMIT 14"); r = []
    if df.empty: return ["Начни дневник ☁️","Ложись в одно время 🕐","5 мин дыхания 💨"]
    if (df["screen_evening"]=="2+ часа").sum()>=2: r.append("📱 Сократи экран вечером")
    if (df["caffeine_evening"]=="Да").sum()>=2: r.append("☕ Кофеин после 18:00 мешает")
    if (df["stress_level"]=="Высокий").sum()>=2: r.append("😰 Стресс — попробуй дыхание")
    if df["sleep_hours"].mean()<7: r.append("⏰ Сон < 7 ч — ложись раньше")
    if not (df["daytime_activity"].isin(["Йога","Тренировка","Прогулка","Активный день"])).sum()>=4:
        r.append("🚶 Добавь прогулку днём")
    return r[:4]

def daily_quests():
    today = str(date.today()); c = get_conn(); cur = c.cursor()
    ex = cur.execute("SELECT * FROM daily_quests WHERE quest_date=?",(today,)).fetchall()
    if not ex:
        for qt,txt,xp in [("breath","💨 Дыхательная сессия",25),("journal","📔 Заполни дневник",30),
                           ("sound","🎵 Послушай звуки",15),("focus","🎯 Фокус-режим",20)]:
            cur.execute("INSERT INTO daily_quests(quest_date,quest_type,quest_text,completed,xp_reward) VALUES(?,?,?,0,?)",
                        (today,qt,txt,xp))
        c.commit(); ex = cur.execute("SELECT * FROM daily_quests WHERE quest_date=?",(today,)).fetchall()
    c.close(); return [dict(r) for r in ex]

def complete_quest(qt):
    today = str(date.today()); c = get_conn(); cur = c.cursor()
    r = cur.execute("SELECT * FROM daily_quests WHERE quest_date=? AND quest_type=? AND completed=0",(today,qt)).fetchone()
    if r: cur.execute("UPDATE daily_quests SET completed=1 WHERE id=?",(r["id"],)); c.commit(); add_xp(r["xp_reward"]); add_coins(5)
    c.close()

def stat_card(emoji, title, value, sub):
    st.markdown(f'<div class="sc"><div style="font-size:1.4rem;margin-bottom:4px">{emoji}</div>'
                f'<div style="font-size:.9rem;font-weight:700">{title}</div>'
                f'<div class="kpi">{value}</div><div class="ml">{sub}</div></div>', unsafe_allow_html=True)

def sec_intro(emoji, title, text):
    st.markdown(f'<div class="mc" style="margin-bottom:14px"><div style="display:flex;align-items:center;gap:10px">'
                f'<span style="font-size:1.4rem">{emoji}</span><div class="st_" style="margin-bottom:0">{title}</div>'
                f'</div><div class="sm" style="margin-top:8px">{text}</div></div>', unsafe_allow_html=True)

def xp_bar(ul):
    needed = xp_for_level(ul["level"]); pct = min(100, int(ul["xp"]/needed*100))
    st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin:6px 0">'
                f'<div class="lr">{ul["level"]}</div><div style="flex:1">'
                f'<div style="display:flex;justify-content:space-between;font-size:.78rem;font-weight:700;color:{T["subtext"]}">'
                f'<span>Уровень {ul["level"]}</span><span>{ul["xp"]}/{needed} XP</span></div>'
                f'<div class="xpo"><div class="xpi" style="width:{pct}%"></div></div></div></div>', unsafe_allow_html=True)

def streak_calendar():
    cal = streak_cal(14)
    h = '<div style="display:flex;flex-wrap:wrap;gap:2px;justify-content:center">'
    for i in cal: h += f'<div class="sd sd-{i["status"]}">{i["date"].day}</div>'
    st.markdown(h+'</div>', unsafe_allow_html=True)

def render_mascot(ctx="home"):
    s, nf = streak_freeze()
    mood = "sad" if nf and s==0 else ("sleeping" if nf else "happy")
    c = "streak_lost" if nf else ctx
    st.markdown(f'<div class="mr"><div style="flex-shrink:0;width:80px">{cloud_svg(mood,"80px")}</div>'
                f'<div class="mb">{mascot_msg(c)}</div></div>', unsafe_allow_html=True)

# ======================== SIDEBAR ========================
def sidebar_nav():
    with st.sidebar:
        ul = get_ul(); s = calc_streak()
        st.markdown(f'<div class="sh"><div style="display:flex;align-items:center;gap:8px">'
                    f'<div style="width:36px">{cloud_svg("happy","36px")}</div>'
                    f'<div><div style="font-size:1.25rem;font-weight:900">☁️ SleepFlow</div>'
                    f'<div style="font-size:.78rem;color:{T["muted"]}">Помощник для сна</div></div></div></div>',
                    unsafe_allow_html=True)
        xp_bar(ul)
        st.markdown(f'<div style="display:flex;justify-content:space-around;margin:8px 0 12px;text-align:center">'
                    f'<div><div>🔥</div><div style="font-size:.85rem;font-weight:800">{s}</div>'
                    f'<div style="font-size:.68rem;color:{T["muted"]}">серия</div></div>'
                    f'<div><div>💰</div><div style="font-size:.85rem;font-weight:800">{ul["coins"]}</div>'
                    f'<div style="font-size:.68rem;color:{T["muted"]}">монеты</div></div>'
                    f'<div><div>❄️</div><div style="font-size:.85rem;font-weight:800">{ul["freezes"]}</div>'
                    f'<div style="font-size:.68rem;color:{T["muted"]}">замор.</div></div></div>'
                    f'<div style="height:1px;background:{T["border"]};margin:4px 0 10px"></div>',
                    unsafe_allow_html=True)
        for label, icon in NAV_ITEMS:
            if st.button(f"{icon}  {label}", key=f"n_{label}", use_container_width=True):
                go(label)
        st.markdown(f'<div style="height:1px;background:{T["border"]};margin:10px 0 8px"></div>',unsafe_allow_html=True)
        ti = "☀️" if st.session_state.theme == "dark" else "🌙"
        tt = "Светлая тема" if st.session_state.theme == "dark" else "Тёмная тема"
        if st.button(f"{ti}  {tt}", key="stg", use_container_width=True):
            st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"; save_st(); st.rerun()

def top_header():
    st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">'
                f'<span style="font-size:1.5rem">☁️</span>'
                f'<span style="font-size:1.25rem;font-weight:900">SleepFlow</span>'
                f'<span style="font-size:.88rem;color:{T["muted"]};margin-left:8px">Спокойный сон</span></div>',
                unsafe_allow_html=True)

# ======================== PAGES ========================
def page_home():
    last = last_log(); a7,a14 = avg_slp(7),avg_slp(14); s,nf = streak_freeze(); ul = get_ul()
    lh = round(float(last["sleep_hours"]),1) if last is not None else 7.4
    lq = int(last["sleep_quality"]) if last is not None else 8
    lf = int(last["fall_asleep_minutes"]) if last is not None else 16
    if lh>=8: unlock_ach("sleep_8")
    if s>=5: unlock_ach("streak_5")
    if s>=10: unlock_ach("streak_10")
    render_mascot("home"); st.write("")
    st.markdown(f'<div class="hc"><div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap">'
                f'<span class="bg1">🌙 Обзор</span><span class="bg3">🔥 Серия {s} дн.</span></div>'
                f'<div class="bt">Ты спал {lh} ч, качество — {lq}/10</div>'
                f'<div class="sm" style="margin-top:8px">Засыпание ≈ {lf} мин · 7 дн — {a7} ч · 14 дн — {a14} ч</div>'
                f'<div class="dv"></div><div class="ins">💡 Убери экран за час до сна и ложись до 23:10</div></div>',
                unsafe_allow_html=True)
    st.write("")
    c1,c2,c3,c4 = st.columns(4)
    with c1: stat_card("🌙","Средний сон",f"{a7} ч","за 7 дней")
    with c2: stat_card("✨","Качество",f"{lq}/10","последняя")
    with c3: stat_card("💰","Монеты",ul["coins"],"заработано")
    with c4: stat_card("🔥","Серия",s,"дней подряд")
    st.write("")
    c1, c2 = st.columns([1.1,1])
    with c1:
        st.markdown(f'<div class="mc"><div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">'
                    f'<span style="font-size:1.2rem">📋</span><div class="st_" style="margin-bottom:0">Задания</div></div></div>',
                    unsafe_allow_html=True)
        quests = daily_quests()
        for q in quests:
            done = q["completed"]; si = "✅" if done else "⬜"; op = ".5" if done else "1"
            td = "line-through" if done else "none"
            st.markdown(f'<div class="qc" style="opacity:{op}"><div style="font-size:1.2rem">{si}</div>'
                        f'<div style="flex:1;text-decoration:{td}"><div style="font-weight:700;font-size:.9rem">'
                        f'{q["quest_text"]}</div></div><div class="bg2">+{q["xp_reward"]} XP</div></div>',
                        unsafe_allow_html=True)
            # Only show "Выполнить" button if quest is NOT done
            if not done:
                tp = QUEST_PAGE.get(q["quest_type"])
                if tp:
                    if st.button(f"▶️ Перейти к заданию", key=f"gq_{q['quest_type']}"):
                        go(tp)
        if nf:
            st.markdown(f'<div class="mc" style="border-color:rgba(84,160,255,.3);margin-top:8px">'
                        f'<div style="display:flex;align-items:center;gap:8px"><span style="font-size:1.2rem">❄️</span>'
                        f'<div><div style="font-weight:800">Серия может прерваться!</div>'
                        f'<div class="sm">Используй заморозку</div></div></div></div>',unsafe_allow_html=True)
            if st.button("❄️ Использовать заморозку",key="uf"):
                if use_freeze(): st.success("Серия сохранена! ❄️"); st.rerun()
                else: st.error("Нет заморозок! Купи в магазине 💰")
    with c2:
        st.markdown(f'<div class="mc"><div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">'
                    f'<span style="font-size:1.2rem">📅</span><div class="st_" style="margin-bottom:0">Календарь серии</div></div>',
                    unsafe_allow_html=True)
        streak_calendar()
        st.markdown(f'<div style="display:flex;gap:10px;justify-content:center;margin-top:10px;flex-wrap:wrap">'
                    f'<span style="font-size:.72rem;color:{T["muted"]}">✅ Сделано</span>'
                    f'<span style="font-size:.72rem;color:{T["muted"]}">❌ Пропуск</span>'
                    f'<span style="font-size:.72rem;color:{T["muted"]}">📍 Сегодня</span></div></div>',
                    unsafe_allow_html=True)
    st.write("")
    c1,c2 = st.columns([1.2,1])
    with c1:
        df = qdf("SELECT log_date,sleep_hours,sleep_quality FROM sleep_logs ORDER BY log_date ASC")
        if not df.empty:
            df["log_date"] = pd.to_datetime(df["log_date"])
            dm = df.melt(id_vars=["log_date"],value_vars=["sleep_hours","sleep_quality"],var_name="Метрика",value_name="Значение")
            dm["Метрика"] = dm["Метрика"].map({"sleep_hours":"Часы сна","sleep_quality":"Качество"})
            st.altair_chart(alt.Chart(dm).mark_line(point=True,strokeWidth=2.5).encode(
                x=alt.X("log_date:T",title="Дата",axis=alt.Axis(format="%d.%m",labelAngle=-45)),
                y=alt.Y("Значение:Q",title=""),
                color=alt.Color("Метрика:N",scale=alt.Scale(domain=["Часы сна","Качество"],range=[T["chart1"],T["chart2"]])),
                tooltip=[alt.Tooltip("log_date:T",title="Дата",format="%d.%m.%Y"),alt.Tooltip("Метрика:N"),alt.Tooltip("Значение:Q")]
            ).properties(height=300,title="📈 Сон и качество").configure_view(strokeWidth=0).configure(background="transparent"),
            use_container_width=True)
    with c2:
        recs = get_recs()
        rh = "".join(f"<li style='margin-bottom:5px'>{r}</li>" for r in recs)
        st.markdown(f'<div class="mc"><div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">'
                    f'<span style="font-size:1.2rem">🤖</span><div class="st_" style="margin-bottom:0">Советы ИИ</div></div>'
                    f'<ul class="sm" style="padding-left:16px">{rh}</ul></div>',unsafe_allow_html=True)

def page_breath():
    sec_intro("💨","Дыхательная практика","Расслабься перед сном. Настрой ритм и нажми «Начать».")
    render_mascot("breath"); st.write("")
    c1,c2 = st.columns([0.7,1.3])
    with c1:
        cycle = st.slider("💨 Ритм (секунды за цикл)", min_value=3, max_value=10,
                           value=st.session_state.breath_cycle_seconds, step=1)
        st.session_state.breath_cycle_seconds = cycle
        rounds = st.selectbox("⏱️ Длительность",["3 цикла","5 циклов","8 циклов","12 циклов","20 циклов"],index=2)
        rc = {"3 цикла":3,"5 циклов":5,"8 циклов":8,"12 циклов":12,"20 циклов":20}[rounds]
        st.markdown(f'<div style="padding:12px;border-radius:14px;background:rgba(120,201,255,.04);'
                    f'border:1px solid {T["border"]};margin:8px 0">'
                    f'<div style="font-weight:700;font-size:.9rem">⏱️ {cycle} сек/цикл</div>'
                    f'<div class="sm">≈ {round(cycle*rc/60,1)} мин</div></div>',unsafe_allow_html=True)
        ca,cb = st.columns(2)
        with ca:
            if st.button("▶️ Начать",key="bs"):
                st.session_state.breath_running = True; save_st(); st.rerun()
        with cb:
            if st.button("⏹️ Стоп",key="bsp"):
                st.session_state.breath_running = False; save_st(); st.rerun()
        if st.button("✅ Завершить (+20 XP)",key="bf"):
            st.session_state.breath_running = False; mark_rout("breath_done",20)
            complete_quest("breath"); unlock_ach("first_breath"); save_st()
            st.success("Завершено! +20 XP 🎉")
    with c2:
        cy = st.session_state.breath_cycle_seconds
        if st.session_state.breath_running:
            st.markdown(f'<div class="bbg" style="--cy:{cy}s"><div class="bst"></div><div class="bmn"></div>'
                        f'<div class="bc an" style="--cy:{cy}s"><div class="bl">Вдох · Выдох</div></div>'
                        f'<div style="color:rgba(255,255,255,.4);font-size:.85rem;margin-top:18px;text-align:center;z-index:2">'
                        f'Расширение — вдох, сужение — выдох</div></div>',unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="bbg"><div class="bst"></div><div class="bmn"></div>'
                        f'<div style="text-align:center;z-index:2"><div style="font-size:3rem;margin-bottom:14px">🌙</div>'
                        f'<div style="font-size:1.1rem;font-weight:700;color:rgba(255,255,255,.7)">Нажми ▶️ Начать</div>'
                        f'<div style="font-size:.85rem;color:rgba(255,255,255,.35);margin-top:8px">Анимация появится на ночном фоне</div>'
                        f'</div></div>',unsafe_allow_html=True)

def page_sounds():
    sec_intro("🎵","Звуки для сна","Природные звуки для расслабления"); st.write("")
    sn = list(SOUNDS.keys()); c1,c2 = st.columns([1,1])
    with c1:
        for name in sn:
            desc,url,emoji = SOUNDS[name]; sel = st.session_state.selected_sound == name
            bc = T["accent"] if sel else T["border"]; bg = "rgba(120,201,255,.06)" if sel else "transparent"
            sel_badge = '<span class="bg1">▶️</span>' if sel else ""
            st.markdown(f'<div style="padding:12px;border-radius:14px;border:1.5px solid {bc};background:{bg};margin-bottom:6px">'
                        f'<div style="display:flex;align-items:center;gap:10px"><span style="font-size:1.6rem">{emoji}</span>'
                        f'<div style="flex:1"><div style="font-weight:800;font-size:.92rem">{name}</div>'
                        f'<div style="font-size:.78rem;color:{T["muted"]}">{desc}</div></div>'
                        f'{sel_badge}</div></div>',unsafe_allow_html=True)
        selected = st.selectbox("Звук",sn,index=sn.index(st.session_state.selected_sound),label_visibility="collapsed")
        timer = st.selectbox("⏱️ Таймер",["15 мин","30 мин","45 мин","60 мин"],index=1)
        if st.button("▶️ Включить",key="ps"):
            st.session_state.selected_sound = selected; save_st()
            mark_rout("sound_done",15); complete_quest("sound")
            st.success(f"Играет: {selected} {SOUNDS[selected][2]}")
    with c2:
        desc,url,emoji = SOUNDS[st.session_state.selected_sound]
        st.markdown(f'<div class="hc" style="text-align:center"><div style="font-size:2.8rem;margin-bottom:8px">{emoji}</div>'
                    f'<div class="bt">{st.session_state.selected_sound}</div>'
                    f'<div class="sm" style="margin-top:6px">{desc}</div><div class="dv"></div>'
                    f'<div class="sm">Таймер: {timer}</div></div>',unsafe_allow_html=True)
        st.audio(url); render_mascot("home")

def page_alarm():
    sec_intro("⏰","Умный будильник","Просыпайся в лёгкой фазе"); st.write("")
    c1,c2 = st.columns([1,1])
    hrs = [f"{h:02d}" for h in range(24)]; mins = ["00","05","10","15","20","25","30","35","40","45","50","55"]
    with c1:
        h = st.selectbox("🕐 Час",hrs,index=7); m = st.selectbox("Мин",mins,index=0); at = f"{h}:{m}"
        w = st.selectbox("🪟 Окно",["10 мин","20 мин","30 мин","45 мин"],index=2)
        wm = {"10 мин":10,"20 мин":20,"30 мин":30,"45 мин":45}[w]
        dp = st.radio("📅 Повтор",["Будни","Каждый день","Выходные","Свой"])
        if dp=="Будни": days=["Пн","Вт","Ср","Чт","Пт"]
        elif dp=="Каждый день": days=DAY_NAMES
        elif dp=="Выходные": days=["Сб","Вс"]
        else: days = st.multiselect("Дни",DAY_NAMES,default=["Пн","Вт","Ср","Чт","Пт"])
        label = st.text_input("🏷️",value="Основной"); sm = st.toggle("🧠 Умное",value=True)
        if st.button("💾 Сохранить (+10 XP)"):
            c = get_conn(); c.cursor().execute("INSERT INTO alarms VALUES(NULL,?,?,?,?,?,?)",(at,wm,json.dumps(days),label,1 if sm else 0,1))
            c.commit(); c.close(); add_xp(10); st.success("Сохранён!"); st.rerun()
    with c2:
        sat = smart_alarm(at,wm)
        st.markdown(f'<div class="hc" style="text-align:center"><div style="font-size:2.2rem;margin-bottom:6px">⏰</div>'
                    f'<div class="bg2">🧠 Рекомендация</div><div class="bt" style="margin-top:10px">{sat}</div>'
                    f'<div class="sm">Цель: {at} · Окно: {w}</div></div>',unsafe_allow_html=True)
    st.write("")
    df = qdf("SELECT * FROM alarms ORDER BY id DESC")
    for _,r in df.iterrows():
        ds = ", ".join(json.loads(r["days_json"])) if r["days_json"] else ""
        ca,cb,cc = st.columns([2.5,.8,.7])
        with ca:
            ic = "🟢" if r["active"] else "⚫"
            st.markdown(f'<div class="mc" style="padding:12px"><div style="display:flex;align-items:center;gap:8px">'
                        f'<span>{ic}</span><div><div style="font-size:1.2rem;font-weight:900">{r["alarm_time"]}</div>'
                        f'<div style="font-size:.78rem;color:{T["muted"]}">{r["label"]} · {ds}</div></div></div></div>',
                        unsafe_allow_html=True)
        with cb:
            a = st.toggle("Вкл",value=bool(r["active"]),key=f"aa_{int(r['id'])}")
            c = get_conn(); c.cursor().execute("UPDATE alarms SET active=? WHERE id=?",(1 if a else 0,int(r["id"]))); c.commit(); c.close()
        with cc:
            if st.button("🗑️",key=f"da_{int(r['id'])}"):
                c = get_conn(); c.cursor().execute("DELETE FROM alarms WHERE id=?",(int(r["id"]),)); c.commit(); c.close(); st.rerun()

def page_focus():
    sec_intro("🎯","Фокус-режим","Ограничь приложения вечером"); st.write("")
    c1,c2 = st.columns([1,1])
    with c1:
        sh = st.selectbox("Начало ч",[f"{h:02d}" for h in range(24)],index=22)
        sm_ = st.selectbox("Начало мин",["00","15","30","45"],index=2)
        eh = st.selectbox("Конец ч",[f"{h:02d}" for h in range(24)],index=7)
        em = st.selectbox("Конец мин",["00","15","30","45"],index=0)
        apps = st.multiselect("📱 Ограничить",DISTRACT_APPS,default=["Instagram","TikTok","YouTube","Telegram"])
        if st.button("🎯 Активировать (+25 XP)"):
            c = get_conn(); c.cursor().execute("INSERT INTO focus_blocks VALUES(NULL,?,?,?,?)",(f"{sh}:{sm_}",f"{eh}:{em}",json.dumps(apps),1))
            c.commit(); c.close(); mark_rout("blocked_done",25); complete_quest("focus"); st.success("Фокус! +25 XP 🎯")
    with c2:
        st.markdown(f'<div class="hc" style="text-align:center"><div style="font-size:2.2rem;margin-bottom:6px">🎯</div>'
                    f'<div class="bg1">Вечерняя защита</div><div class="bt" style="margin-top:10px">{sh}:{sm_} → {eh}:{em}</div>'
                    f'<div class="dv"></div><div class="sm">Ограничены: {", ".join(apps[:4]) if apps else "—"}</div></div>',
                    unsafe_allow_html=True)
        render_mascot("home")

def page_journal():
    sec_intro("📔","Дневник сна","Быстрый опросник с эмодзи = +30 XP")
    render_mascot("journal"); st.write("")
    c1,c2 = st.columns([1.1,1])
    with c1:
        d = st.date_input("📅 Дата",value=date.today())
        st.markdown(f'<div style="font-weight:700;font-size:.9rem;margin:6px 0 2px">😴 Как спалось?</div>',unsafe_allow_html=True)
        qo = {"😫 Ужасно":2,"😕 Плохо":4,"😐 Норм":6,"😊 Хорошо":8,"🤩 Отлично":10}
        qc = st.radio("q",list(qo.keys()),index=3,horizontal=True,label_visibility="collapsed"); qv = qo[qc]
        st.markdown(f'<div style="font-weight:700;font-size:.9rem;margin:6px 0 2px">☀️ Утро</div>',unsafe_allow_html=True)
        eo = {"🥱 Сонно":"Сонно","😐 Норм":"Нормально","😊 Хорошо":"Хорошо","⚡ Отлично":"Отлично"}
        ec = st.radio("e",list(eo.keys()),index=2,horizontal=True,label_visibility="collapsed"); ev = eo[ec]
        sh_ = st.selectbox("🕐 Часы сна",[round(x*.5,1) for x in range(8,25)],index=7)
        ca_,cb_ = st.columns(2)
        with ca_: bh = st.selectbox("🛏️ Легли ч",[f"{h:02d}" for h in range(24)],index=23); bm = st.selectbox("мин",[f"{m:02d}" for m in range(0,60,5)],index=0,key="bm")
        with cb_: wh = st.selectbox("☀️ Встали ч",[f"{h:02d}" for h in range(24)],index=7); wm_ = st.selectbox("мин",[f"{m:02d}" for m in range(0,60,5)],index=0,key="wm")
        fa = st.selectbox("💤 Засыпание",[5,10,15,20,25,30,40,50,60],index=2)
        st.markdown(f'<div style="font-weight:700;font-size:.9rem;margin:6px 0 2px">😰 Стресс</div>',unsafe_allow_html=True)
        so = {"😌 Низкий":"Низкий","😐 Средний":"Средний","😰 Высокий":"Высокий"}
        sc_ = st.radio("s",list(so.keys()),index=1,horizontal=True,label_visibility="collapsed"); sv = so[sc_]
        act = st.selectbox("🏃 Активность",["Без активности","Прогулка","Йога","Тренировка","Активный день"])
        scr = st.selectbox("📱 Экран",["до 1 часа","1–2 часа","2+ часа"])
        caf = st.radio("☕ Кофеин 18:00+",["Нет","Да"],horizontal=True)
        note = st.text_area("📝 Заметка",placeholder="Что повлияло?")
        if st.button("💾 Сохранить (+30 XP)",key="sj"):
            c = get_conn(); c.cursor().execute("""INSERT INTO sleep_logs(log_date,sleep_hours,bedtime,wake_time,
                fall_asleep_minutes,daytime_activity,sleep_quality,energy_morning,stress_level,
                screen_evening,caffeine_evening,note,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (str(d),sh_,f"{bh}:{bm}",f"{wh}:{wm_}",fa,act,qv,ev,sv,scr,caf,note or "—",datetime.now().isoformat()))
            c.commit(); c.close(); mark_rout("journal_done",30); complete_quest("journal")
            if len(qdf("SELECT log_date FROM sleep_logs ORDER BY log_date DESC LIMIT 3"))>=3: unlock_ach("journal_3")
            st.success("Сохранено! +30 XP 📔"); st.rerun()
    with c2:
        recs = get_recs(); rh = "".join(f"<li style='margin-bottom:5px'>{r}</li>" for r in recs)
        st.markdown(f'<div class="hc"><div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">'
                    f'<span style="font-size:1.2rem">🤖</span><div class="st_" style="margin-bottom:0">Советы</div></div>'
                    f'<ul class="sm" style="padding-left:16px">{rh}</ul></div>',unsafe_allow_html=True)
        st.write("")
        df = qdf("SELECT * FROM sleep_logs ORDER BY log_date DESC LIMIT 5")
        for _,r in df.iterrows():
            q = int(r["sleep_quality"]); qe = "🤩" if q>=9 else "😊" if q>=7 else "😐" if q>=5 else "😕"
            st.markdown(f'<div class="mc" style="margin-bottom:6px;padding:12px">'
                        f'<div style="display:flex;justify-content:space-between;align-items:center">'
                        f'<div style="font-weight:800">{r["log_date"]}</div>'
                        f'<div class="bg1">{qe} {r["sleep_hours"]} ч · {q}/10</div></div>'
                        f'<div class="sm" style="margin-top:4px">🛏️ {r["bedtime"]} → ☀️ {r["wake_time"]} · 💤 {r["fall_asleep_minutes"]} мин</div></div>',
                        unsafe_allow_html=True)

def page_stats():
    sec_intro("📊","Статистика","Графики и достижения"); st.write("")
    df = qdf("SELECT * FROM sleep_logs ORDER BY log_date ASC")
    if df.empty: st.info("Нет данных"); return
    df["log_date"] = pd.to_datetime(df["log_date"])
    wm = {"Monday":"Пн","Tuesday":"Вт","Wednesday":"Ср","Thursday":"Чт","Friday":"Пт","Saturday":"Сб","Sunday":"Вс"}
    df["День"] = df["log_date"].dt.day_name().map(wm)
    ad,aq,af,bs = round(df["sleep_hours"].mean(),1),round(df["sleep_quality"].mean(),1),int(round(df["fall_asleep_minutes"].mean())),round(df["sleep_hours"].max(),1)
    c1,c2,c3,c4 = st.columns(4)
    with c1: stat_card("📈","Ср. сон",f"{ad} ч","всего")
    with c2: stat_card("✨","Качество",f"{aq}/10","всего")
    with c3: stat_card("💤","Засыпание",f"{af} мин","среднее")
    with c4: stat_card("🌟","Лучшая",f"{bs} ч","максимум")
    st.write("")
    def mch(ch): return ch.configure_view(strokeWidth=0).configure(background="transparent")
    c1,c2 = st.columns(2)
    with c1: st.altair_chart(mch(alt.Chart(df).mark_line(point=True,strokeWidth=2.5).encode(x=alt.X("log_date:T",title="Дата",axis=alt.Axis(format="%d.%m",labelAngle=-45)),y=alt.Y("sleep_hours:Q",title="Часы"),tooltip=[alt.Tooltip("log_date:T",title="Дата",format="%d.%m.%Y"),alt.Tooltip("sleep_hours:Q",title="Часы")]).properties(height=280,title="🌙 Длительность")),use_container_width=True)
    with c2: st.altair_chart(mch(alt.Chart(df).mark_area(opacity=.5,line=True).encode(x=alt.X("log_date:T",title="Дата",axis=alt.Axis(format="%d.%m",labelAngle=-45)),y=alt.Y("sleep_quality:Q",title="Качество"),tooltip=[alt.Tooltip("log_date:T",format="%d.%m.%Y"),alt.Tooltip("sleep_quality:Q")]).properties(height=280,title="✨ Качество")),use_container_width=True)
    st.write("")
    c1,c2 = st.columns(2)
    with c1: st.altair_chart(mch(alt.Chart(df).mark_bar(cornerRadiusTopLeft=8,cornerRadiusTopRight=8).encode(x=alt.X("День:N",sort=DAY_NAMES,title=""),y=alt.Y("mean(sleep_hours):Q",title="Ср. (ч)"),tooltip=[alt.Tooltip("mean(sleep_hours):Q",title="Ср.",format=".1f")]).properties(height=280,title="📅 По дням")),use_container_width=True)
    with c2: st.altair_chart(mch(alt.Chart(df).mark_line(point=True,strokeDash=[6,4]).encode(x=alt.X("log_date:T",title="Дата",axis=alt.Axis(format="%d.%m",labelAngle=-45)),y=alt.Y("fall_asleep_minutes:Q",title="Мин"),tooltip=[alt.Tooltip("log_date:T",format="%d.%m.%Y"),alt.Tooltip("fall_asleep_minutes:Q")]).properties(height=280,title="💤 Засыпание")),use_container_width=True)
    st.write("")
    st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px"><span style="font-size:1.2rem">🏆</span><span class="st_" style="margin-bottom:0">Достижения</span></div>',unsafe_allow_html=True)
    ach = qdf("SELECT * FROM achievements ORDER BY unlocked DESC, id ASC"); cols = st.columns(3)
    for i,(_,r) in enumerate(ach.iterrows()):
        with cols[i%3]:
            ic = r.get("icon","🏆") or "🏆"; u = r["unlocked"]; op = "1" if u else ".45"
            bc_ = "rgba(255,215,109,.30)" if u else T["border"]; bg_ = "rgba(255,215,109,.04)" if u else "transparent"
            st.markdown(f'<div class="mc" style="margin-bottom:8px;opacity:{op};border-color:{bc_};background:{bg_};padding:14px">'
                        f'<div style="display:flex;align-items:center;gap:8px"><span style="font-size:1.4rem">{ic}</span>'
                        f'<div><div style="font-weight:800;font-size:.88rem">{r["title"]}</div>'
                        f'<div style="font-size:.72rem;color:{T["muted"]}">{r["description"]}</div></div></div>'
                        f'<div style="margin-top:6px;font-size:.72rem;color:{T["muted"]}">{"✅" if u else "🔒"}</div></div>',unsafe_allow_html=True)

def page_shop():
    sec_intro("🛒","Магазин","Трать монеты на бонусы или оформи Pro")
    render_mascot("shop"); st.write("")
    ul = get_ul()
    st.markdown(f'<div class="hc" style="text-align:center;margin-bottom:16px"><div style="font-size:2.2rem;margin-bottom:6px">💰</div>'
                f'<div class="bt">{ul["coins"]} монет</div>'
                f'<div class="sm" style="margin-top:4px">Ур. {ul["level"]} · ❄️ {ul["freezes"]} замор. · Нужно {xp_for_level(ul["level"])} XP до след. ур.</div></div>',
                unsafe_allow_html=True)
    st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px"><span style="font-size:1.2rem">💰</span><span class="st_" style="margin-bottom:0">За монеты</span></div>',unsafe_allow_html=True)
    coin_items = [i for i in SHOP_ITEMS if i["currency"]=="coins"]; cols = st.columns(len(coin_items))
    for idx,item in enumerate(coin_items):
        with cols[idx]:
            st.markdown(f'<div class="spc"><div class="spi">{item["icon"]}</div>'
                        f'<div style="font-weight:800;font-size:.95rem">{item["name"]}</div>'
                        f'<div style="font-size:.78rem;color:{T["muted"]};margin-top:4px">{item["desc"]}</div>'
                        f'<div class="spp">💰 {item["price"]}</div></div>',unsafe_allow_html=True)
            if st.button(f"Купить",key=f"buy_{item['code']}"):
                if ul["coins"]>=item["price"]:
                    add_coins(-item["price"])
                    if item["code"]=="freeze":
                        c=get_conn();c.cursor().execute("UPDATE user_level SET freezes=freezes+1 WHERE id=1");c.commit();c.close()
                    st.success(f"{item['name']} куплен!"); st.rerun()
                else: st.warning(f"Нужно {item['price']} 💰")
    st.write("")
    st.markdown(f'<div style="height:1px;background:{T["border"]};margin:8px 0 16px"></div>',unsafe_allow_html=True)
    st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px"><span style="font-size:1.2rem">👑</span><span class="st_" style="margin-bottom:0">Подписка Pro</span></div>',unsafe_allow_html=True)
    sub_items = [i for i in SHOP_ITEMS if i["currency"]=="rub"]; cols = st.columns(len(sub_items))
    for idx,item in enumerate(sub_items):
        with cols[idx]:
            iy = "yearly" in item["code"]; hl = f"border:2px solid {T['gold']};" if iy else ""
            sb = f'<div class="bg2" style="margin-top:8px">💎 -40%</div>' if iy else ""
            st.markdown(f'<div class="spc" style="{hl}"><div class="spi">{item["icon"]}</div>'
                        f'<div style="font-weight:800;font-size:.95rem">{item["name"]}</div>'
                        f'<div style="font-size:.78rem;color:{T["muted"]};margin-top:4px">{item["desc"]}</div>{sb}'
                        f'<div class="spp">{item["price"]} ₽</div></div>',unsafe_allow_html=True)
            if st.button(f"Оформить",key=f"sub_{item['code']}"): st.info("Скоро! 🔜")
    st.write("")
    st.markdown(f'<div class="mc"><div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">'
                f'<span style="font-size:1.2rem">✨</span><div class="st_" style="margin-bottom:0">Что даёт Pro?</div></div>'
                f'<div class="sm"><ul style="padding-left:16px"><li>📊 ИИ-аналитика</li><li>🎶 12+ звуков</li>'
                f'<li>🎨 Темы</li><li>❄️ 5 замор./мес.</li><li>👨‍👩‍👧 Семья до 8 чел.</li><li>📱 Без рекламы</li></ul></div></div>',
                unsafe_allow_html=True)

def page_family():
    unlock_ach("family_join"); sec_intro("👨‍👩‍👧","Семья","Общий прогресс и мотивация"); st.write("")
    c1,c2 = st.columns([1,1])
    with c1:
        df = qdf("SELECT * FROM family_members ORDER BY points DESC"); medals = ["🥇","🥈","🥉"]
        for idx,(_,r) in enumerate(df.iterrows()):
            md = medals[idx] if idx<3 else "👤"
            st.markdown(f'<div class="mc" style="margin-bottom:6px;padding:12px"><div style="display:flex;align-items:center;gap:10px">'
                        f'<span style="font-size:1.3rem">{md}</span><div style="flex:1"><div style="font-weight:800">{r["name"]}</div>'
                        f'<div style="font-size:.78rem;color:{T["muted"]}">{r["role"]} · 🔥{r["streak"]} · 😴{r["sleep_avg"]}ч</div>'
                        f'</div><div class="bg2">💰{r["points"]}</div></div></div>',unsafe_allow_html=True)
        with st.form("fa"):
            nm = st.text_input("👤 Имя"); rl = st.selectbox("Роль",["Партнёр","Ребёнок","Родитель","Друг"])
            if st.form_submit_button("➕") and nm.strip():
                c=get_conn();c.cursor().execute("INSERT INTO family_members VALUES(NULL,?,?,0,0,0)",(nm.strip(),rl));c.commit();c.close();st.rerun()
    with c2:
        fam = qdf("SELECT * FROM family_members"); tot = int(fam["points"].sum()) if not fam.empty else 0
        st.markdown(f'<div class="hc" style="text-align:center"><div style="font-size:2.2rem;margin-bottom:6px">👨‍👩‍👧</div>'
                    f'<div class="bg2">🏆 Прогресс</div><div class="bt" style="margin-top:10px">{tot} очков</div>'
                    f'<div class="sm">{len(fam)} чел.</div></div>',unsafe_allow_html=True)
        st.write("")
        feed = qdf("SELECT * FROM family_feed ORDER BY id DESC LIMIT 6")
        for _,r in feed.iterrows():
            st.markdown(f'<div class="fi"><div style="font-weight:700;font-size:.88rem">{r["author"]}</div>'
                        f'<div style="font-size:.82rem;color:{T["muted"]};margin-top:3px">{r["message"]}</div></div>',unsafe_allow_html=True)
        msg = st.text_input("✉️",placeholder="Привет!")
        if st.button("📤",key="fs") and msg.strip():
            c=get_conn();c.cursor().execute("INSERT INTO family_feed VALUES(NULL,?,?,?)",(datetime.now().isoformat(),st.session_state.user_name,msg.strip()));c.commit();c.close();st.rerun()

def page_settings():
    sec_intro("⚙️","Настройки","Персонализация и цели"); st.write("")
    c1,c2 = st.columns(2)
    with c1:
        st.markdown(f'<div class="mc" style="margin-bottom:10px"><div style="display:flex;align-items:center;gap:6px">'
                    f'<span>🎨</span><div class="st_" style="margin-bottom:0">Интерфейс</div></div></div>',unsafe_allow_html=True)
        tm = st.radio("Тема",["🌙 Тёмная","☀️ Светлая"],horizontal=True,index=0 if st.session_state.theme=="dark" else 1)
        ss = st.selectbox("🎵 Звук",list(SOUNDS.keys()),index=list(SOUNDS.keys()).index(st.session_state.selected_sound))
        un = st.text_input("👤 Имя",value=st.session_state.user_name)
        cn = st.text_input("☁️ Маскот",value=st.session_state.cloud_name)
        if st.button("💾 Сохранить"):
            st.session_state.theme = "dark" if "Тёмная" in tm else "light"
            st.session_state.selected_sound = ss; st.session_state.user_name = un; st.session_state.cloud_name = cn
            save_st(); st.success("✅"); st.rerun()
    with c2:
        st.markdown(f'<div class="mc" style="margin-bottom:10px"><div style="display:flex;align-items:center;gap:6px">'
                    f'<span>🎯</span><div class="st_" style="margin-bottom:0">Цели</div></div></div>',unsafe_allow_html=True)
        tg = st.selectbox("😴 Цель",["6.5 ч","7 ч","7.5 ч","8 ч","8.5 ч"],index=3)
        bgh = st.selectbox("🛏️ Отбой ч",[f"{h:02d}" for h in range(24)],index=23)
        bgm = st.selectbox("мин",["00","15","30","45"],index=0,key="sgbm")
        if st.button("💾 Сохранить цели"): st.success(f"Цели: {tg}, отбой {bgh}:{bgm} ✅")
        st.write("")
        ul = get_ul()
        st.markdown(f'<div class="mc"><div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">'
                    f'<span>☁️</span><div class="st_" style="margin-bottom:0">Маскот {st.session_state.cloud_name}</div></div>'
                    f'<div style="display:flex;justify-content:space-around;align-items:flex-end">'
                    f'<div style="text-align:center"><div style="max-width:80px;margin:auto">{cloud_svg("happy","80px")}</div>'
                    f'<div style="font-size:.72rem;color:{T["muted"]}">Счастливый</div></div>'
                    f'<div style="text-align:center"><div style="max-width:80px;margin:auto">{cloud_svg("sleeping","80px")}</div>'
                    f'<div style="font-size:.72rem;color:{T["muted"]}">Сонный</div></div>'
                    f'<div style="text-align:center"><div style="max-width:80px;margin:auto">{cloud_svg("sad","80px")}</div>'
                    f'<div style="font-size:.72rem;color:{T["muted"]}">Грустный</div></div></div>'
                    f'<div class="dv"></div><div class="sm">📈 Ур. {ul["level"]}: нужно {xp_for_level(ul["level"])} XP · '
                    f'Ур. {ul["level"]+1}: {xp_for_level(ul["level"]+1)} XP</div></div>',unsafe_allow_html=True)

# ======================== RENDER ========================
sidebar_nav(); top_header(); st.write("")
pages = {"Главная":page_home,"Дыхание":page_breath,"Звуки":page_sounds,"Будильник":page_alarm,
         "Фокус":page_focus,"Дневник":page_journal,"Статистика":page_stats,"Магазин":page_shop,
         "Семья":page_family,"Настройки":page_settings}
pages.get(st.session_state.page, page_home)()
save_st()
