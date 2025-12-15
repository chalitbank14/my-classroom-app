import streamlit as st
import pandas as pd
import altair as alt
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time

# ==========================================
# 1. MOBILE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Classroom Mobile",
    page_icon="📱",
    layout="centered", # ใช้ centered เพื่อให้โฟกัสตรงกลางบนมือถือ
    initial_sidebar_state="collapsed" # ซ่อนเมนูข้างเพื่อประหยัดพื้นที่
)

# --- CSS FOR MOBILE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Prompt', sans-serif;
        background-color: #f0f2f5; /* สีเทาอ่อนเหมือน Facebook/Line */
    }

    /* ซ่อน Decoration ด้านบนของ Streamlit เพื่อประหยัดที่ */
    header {visibility: hidden;}
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 5rem !important;
    }

    /* Mobile Cards */
    .mobile-card {
        background: white;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 10px;
        border: 1px solid #e0e0e0;
    }

    /* Big Buttons for Touch (ปุ่มใหญ่กดง่าย) */
    .stButton button {
        width: 100%;
        height: 60px !important; /* ปุ่มสูงขึ้น */
        border-radius: 12px !important;
        font-size: 18px !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 5px;
    }
    
    /* Tabs styling for mobile */
    .stTabs [data-baseweb="tab-list"] {
        justify-content: center;
        background-color: white;
        padding: 5px;
        border-radius: 15px;
        margin-bottom: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab"] {
        flex-grow: 1; /* ขยายเต็มความกว้าง */
        text-align: center;
    }

    /* Floating Room Badge */
    .room-badge {
        background-color: #2c3e50;
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.8rem;
        display: inline-block;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# Connection
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("Connection Error")
    st.stop()

# ==========================================
# 2. LOGIC
# ==========================================
RANKS = [
    {"name": "President", "th": "👑 ประธาน", "xp": 1000, "color": "#FFD700", "bg": "#FFF9C4"},
    {"name": "Director", "th": "💼 หน.ฝ่าย", "xp": 600, "color": "#9b59b6", "bg": "#F3E5F5"},
    {"name": "Manager", "th": "👔 หน.แผนก", "xp": 300, "color": "#3498db", "bg": "#E3F2FD"},
    {"name": "Employee", "th": "👨‍💼 พนักงาน", "xp": 100, "color": "#2ecc71", "bg": "#E8F5E9"},
    {"name": "Intern", "th": "👶 ฝึกงาน", "xp": 0, "color": "#95a5a6", "bg": "#FAFAFA"}
]

def get_rank(xp):
    for r in RANKS:
        if xp >= r['xp']: return r
    return RANKS[-1]

@st.cache_data(ttl=5)
def load_data():
    try:
        df = conn.read(worksheet="Sheet1", usecols=[0, 1, 2, 3, 4], ttl=0)
        df = df.dropna(how='all')
        if 'XP' not in df.columns: df['XP'] = 0
        df['XP'] = pd.to_numeric(df['XP'], errors='coerce').fillna(0).astype(int)
        return df
    except:
        return pd.DataFrame(columns=['Room', 'GroupName', 'XP', 'Members', 'LastUpdated'])

def save_data(df):
    conn.update(worksheet="Sheet1", data=df)
    st.cache_data.clear()

# ==========================================
# 3. MOBILE UI
# ==========================================

# --- Top Navigation (แทน Sidebar เดิม) ---
# ใช้ Sidebar เฉพาะเลือกห้อง เพื่อไม่ให้เกะกะ
with st.sidebar:
    st.title("Settings")
    all_rooms = ["ม.1/1", "ม.1/2", "ม.1/10"]
    selected_room = st.selectbox("เลือกห้องเรียน", all_rooms)
    st.info("💡 เคล็ดลับ: เพิ่มหน้าเว็บนี้ลงในหน้าจอโฮมเพื่อใช้งานเหมือนแอป")

# Header
st.markdown(f"<div class='room-badge'>ห้องเรียน: {selected_room}</div>", unsafe_allow_html=True)
st.markdown("<h2 style='margin-top:-10px;'>📱 Classroom Mobile</h2>", unsafe_allow_html=True)

df = load_data()
room_df = df[df['Room'] == selected_room].copy()

# Tabs (Action มาก่อนเพื่อน เพื่อความไว)
tab_action, tab_leader, tab_manage = st.tabs(["⚡ ให้คะแนน", "🏆 อันดับ", "⚙️ จัดการ"])

# ----------------------------------------------------
# TAB 1: QUICK ACTION (เน้นปุ่มใหญ่)
# ----------------------------------------------------
with tab_action:
    if room_df.empty:
        st.warning("⚠️ ยังไม่มีกลุ่ม (ไปที่เมนู 'จัดการ')")
    else:
        # Selector ใหญ่ๆ
        target_group = st.selectbox("🎯 เลือกกลุ่ม", room_df['GroupName'].unique(), key="mob_select")
        
        # แสดงสถานะปัจจุบันของกลุ่มที่เลือก
        if target_group:
            curr_xp = room_df[room_df['GroupName'] == target_group]['XP'].values[0]
            curr_rank = get_rank(curr_xp)
            st.caption(f"สถานะ: {curr_rank['th']} ({curr_xp} XP)")

        st.write("---")
        
        # ปุ่มกดคะแนน (2 คอลัมน์พอบนมือถือ)
        c1, c2 = st.columns(2)
        
        def push_xp(reason, score):
            idx = df[(df['Room'] == selected_room) & (df['GroupName'] == target_group)].index
            if not idx.empty:
                old_xp = df.loc[idx[0], 'XP']
                new_xp = max(0, old_xp + score)
                df.loc[idx[0], 'XP'] = new_xp
                df.loc[idx[0], 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_data(df)
                
                # Feedback แบบ Mobile Toast
                st.toast(f"{target_group}: {score:+d} ({reason})", icon="✅")
                
                # Check Level Up
                if get_rank(new_xp)['xp'] > get_rank(old_xp)['xp']:
                    st.balloons()
                    time.sleep(1)
                else:
                    time.sleep(0.5)
                st.rerun()

        with c1:
            if st.button("👍 ส่งงาน (+50)", type="primary"): push_xp("ส่งงาน", 50)
            if st.button("🙋 ตอบคำถาม (+20)"): push_xp("ตอบคำถาม", 20)
            if st.button("🧹 จิตพิสัย (+10)"): push_xp("จิตพิสัย", 10)
            
        with c2:
            if st.button("🐢 ส่งช้า (-20)"): push_xp("ส่งช้า", -20)
            if st.button("📢 เสียงดัง (-10)"): push_xp("เสียงดัง", -10)
            if st.button("❌ ไม่ส่งงาน (-50)"): push_xp("ไม่ส่งงาน", -50)

# ----------------------------------------------------
# TAB 2: LEADERBOARD (Feed Style)
# ----------------------------------------------------
with tab_leader:
    if room_df.empty:
        st.info("ว่างเปล่า...")
    else:
        # Sort
        leaders = room_df.sort_values(by="XP", ascending=False).reset_index(drop=True)
        
        # แสดงผลแบบ Mobile Cards (เหมือน Feed)
        for i, row in leaders.iterrows():
            rank = get_rank(row['XP'])
            
            # คำนวณ Progress
            next_xp = 1000
            for r in reversed(RANKS):
                if r['xp'] > row['XP']:
                    next_xp = r['xp']
                    break
            pct = min(1.0, row['XP'] / next_xp if next_xp > 0 else 1.0)

            # HTML Card
            st.markdown(f"""
            <div class="mobile-card" style="border-left: 6px solid {rank['color']};">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                        <span style="font-size:1.1rem; font-weight:bold;">#{i+1} {row['GroupName']}</span>
                        <div style="font-size:0.8rem; color:grey; margin-top:2px;">{row['Members']}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:1.2rem; font-weight:bold; color:{rank['color']}">{row['XP']}</div>
                        <span style="background:{rank['bg']}; padding:2px 8px; border-radius:10px; font-size:0.7rem;">{rank['th']}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            # Progress bar เล็กๆ ใต้การ์ด
            st.progress(pct)

# ----------------------------------------------------
# TAB 3: MANAGE (Simple Form)
# ----------------------------------------------------
with tab_manage:
    st.markdown("#### ➕ เพิ่มกลุ่ม")
    with st.form("mobile_add"):
        n = st.text_input("ชื่อกลุ่ม")
        m = st.text_area("สมาชิก", height=70) # ลดความสูง
        if st.form_submit_button("สร้างกลุ่ม", use_container_width=True):
            if n and not ((df['Room'] == selected_room) & (df['GroupName'] == n)).any():
                new_row = pd.DataFrame([{"Room": selected_room, "GroupName": n, "XP": 0, "Members": m}])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df)
                st.success("เสร็จสิ้น")
                st.rerun()
            else:
                st.error("ซ้ำหรือว่าง")

    st.markdown("---")
    st.markdown("#### 🗑️ ลบกลุ่ม")
    d_target = st.selectbox("เลือกกลุ่มลบ", ["-"] + list(room_df['GroupName'].unique()))
    if d_target != "-":
        if st.button(f"ยืนยันลบ {d_target}", type="primary", use_container_width=True):
            df = df[~((df['Room'] == selected_room) & (df['GroupName'] == d_target))]
            save_data(df)
            st.success("ลบแล้ว")
            time.sleep(0.5)
            st.rerun()
