import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time

# ==========================================
# 1. ตั้งค่าหน้าเว็บ & เชื่อมต่อ Google Sheets
# ==========================================
st.set_page_config(page_title="Classroom Gamification", page_icon="🎓", layout="wide")

# CSS ปรับแต่งความสวยงาม (Minimalist & Clean)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    .stApp { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    div[data-testid="stExpander"] { background-color: #ffffff; border-radius: 10px; border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .big-font { font-size: 20px !important; font-weight: bold; color: #2c3e50; }
    </style>
    """, unsafe_allow_html=True)

# เชื่อมต่อกับ Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 2. ระบบคำนวณยศ (Rank Logic)
# ==========================================
RANKS = [
    {"name": "👑 ประธาน (President)", "min_xp": 1000, "perk": "🛡️ Immunity: ไม่ต้องทำงาน 3 ชิ้น + โบนัส", "color": "#FFD700"},
    {"name": "💼 หัวหน้าฝ่าย (Director)", "min_xp": 600, "perk": "✂️ Workload Cut: ลดงาน 50% ได้เต็ม", "color": "#9b59b6"},
    {"name": "👔 หัวหน้าแผนก (Manager)", "min_xp": 300, "perk": "🔄 Second Chance: สอบแก้ตัวได้", "color": "#3498db"},
    {"name": "👨‍💼 พนักงาน (Employee)", "min_xp": 100, "perk": "⏰ Time Extension: ส่งช้าได้ 1 สัปดาห์", "color": "#2ecc71"},
    {"name": "👶 เด็กฝึกงาน (Intern)", "min_xp": 0, "perk": "🔍 Check-up: ครูตรวจก่อนส่งจริง", "color": "#95a5a6"}
]

def get_rank_info(xp):
    for rank in RANKS:
        if xp >= rank['min_xp']: return rank
    return RANKS[-1]

# ==========================================
# 3. โหลดและบันทึกข้อมูล
# ==========================================
@st.cache_data(ttl=5) # Cache ข้อมูล 5 วินาที เพื่อความเร็ว
def load_data():
    try:
        df = conn.read(worksheet="Sheet1", usecols=[0, 1, 2, 3, 4], ttl=0)
        # แปลงให้แน่ใจว่าเป็น format ที่ถูกต้อง
        df = df.dropna(how='all')
        if 'XP' not in df.columns: df['XP'] = 0
        df['XP'] = pd.to_numeric(df['XP'], errors='coerce').fillna(0).astype(int)
        return df
    except Exception:
        # กรณี Sheet ว่างเปล่าให้สร้าง DataFrame เปล่า
        return pd.DataFrame(columns=['Room', 'GroupName', 'XP', 'Members', 'LastUpdated'])

def save_data(df):
    conn.update(worksheet="Sheet1", data=df)
    st.cache_data.clear() # ล้าง Cache เพื่อให้โหลดใหม่

# ==========================================
# 4. ส่วนแสดงผล (Main UI)
# ==========================================
st.sidebar.title("🏫 Classroom Control")
df = load_data()

# เลือกห้องเรียน
all_rooms = ["ม.1/1", "ม.1/2", "ม.1/10"]
selected_room = st.sidebar.selectbox("เลือกห้องเรียน", all_rooms)

st.title(f"🎓 ห้องเรียน {selected_room}")
st.caption("ระบบ Gamification ออนไลน์ | ข้อมูลเชื่อมต่อกับ Google Sheets ☁️")

# Filter ข้อมูลเฉพาะห้องที่เลือก
room_df = df[df['Room'] == selected_room].copy()

tab1, tab2, tab3 = st.tabs(["🏆 จัดอันดับ", "⚡ ให้คะแนน", "⚙️ จัดการกลุ่ม"])

# --- TAB 1: Dashboard ---
with tab1:
    if room_df.empty:
        st.info("ยังไม่มีข้อมูลกลุ่มในห้องนี้ ไปที่แท็บ 'จัดการกลุ่ม' เพื่อสร้าง")
    else:
        # Sort คะแนน
        leaderboard = room_df.sort_values(by="XP", ascending=False).reset_index(drop=True)
        
        # Top 3 Cards
        cols = st.columns(3)
        for i in range(min(3, len(leaderboard))):
            row = leaderboard.iloc[i]
            rank_info = get_rank_info(row['XP'])
            with cols[i]:
                st.metric(label=f"อันดับ {i+1}: {row['GroupName']}", value=f"{row['XP']} XP", delta=rank_info['name'])

        st.divider()
        
        # Detailed List
        for i, row in leaderboard.iterrows():
            rank_info = get_rank_info(row['XP'])
            # คำนวณหลอดพลัง
            next_xp = 1000
            for r in reversed(RANKS):
                if r['min_xp'] > row['XP']:
                    next_xp = r['min_xp']
                    break
            progress = min(1.0, row['XP'] / next_xp if next_xp > 0 else 1.0)
            
            with st.expander(f"#{i+1} **{row['GroupName']}** ({rank_info['name']})"):
                c1, c2 = st.columns([3, 1])
                c1.write(f"👥 **สมาชิก:** {row['Members']}")
                c1.write(f"🎁 **สิทธิ์:** {rank_info['perk']}")
                c1.progress(progress, text=f"เส้นทางสู่ยศถัดไป ({row['XP']}/{next_xp})")
                c2.markdown(f"<h2 style='text-align:center; color:{rank_info['color']}'>{row['XP']} XP</h2>", unsafe_allow_html=True)

# --- TAB 2: Give XP ---
with tab2:
    if room_df.empty:
        st.warning("กรุณาสร้างกลุ่มก่อน")
    else:
        st.subheader("✍️ ให้คะแนน/หักคะแนน")
        with st.form("xp_form"):
            target_group = st.selectbox("เลือกกลุ่ม", room_df['GroupName'].unique())
            reason = st.text_input("เหตุผล", "ส่งงานครบถ้วน")
            xp_change = st.number_input("คะแนน (ติดลบเพื่อหัก)", value=50, step=10)
            submitted = st.form_submit_button("บันทึกคะแนน", use_container_width=True)
            
            if submitted:
                # อัปเดตข้อมูลใน DataFrame หลัก
                idx = df[(df['Room'] == selected_room) & (df['GroupName'] == target_group)].index
                if not idx.empty:
                    old_xp = df.loc[idx[0], 'XP']
                    new_xp = max(0, old_xp + xp_change)
                    df.loc[idx[0], 'XP'] = new_xp
                    df.loc[idx[0], 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    save_data(df) # บันทึกลง Google Sheets
                    
                    # Animation Check
                    old_rank = get_rank_info(old_xp)
                    new_rank = get_rank_info(new_xp)
                    
                    st.toast(f"บันทึกแล้ว! กลุ่ม {target_group} มี {new_xp} XP", icon="✅")
                    if new_rank['min_xp'] > old_rank['min_xp']:
                        st.balloons()
                        st.success(f"🎉 LEVEL UP! เลื่อนยศเป็น {new_rank['name']}")
                    time.sleep(1)
                    st.rerun()

# --- TAB 3: Manage Groups ---
with tab3:
    st.subheader("➕ เพิ่มกลุ่มใหม่")
    with st.form("add_group"):
        new_name = st.text_input("ชื่อกลุ่ม")
        new_members = st.text_area("รายชื่อสมาชิก (เช่น เลขที่ 1, เลขที่ 5)")
        add_btn = st.form_submit_button("สร้างกลุ่ม")
        
        if add_btn:
            if new_name and not ((df['Room'] == selected_room) & (df['GroupName'] == new_name)).any():
                new_row = pd.DataFrame([{
                    "Room": selected_room,
                    "GroupName": new_name,
                    "XP": 0,
                    "Members": new_members,
                    "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df)
                st.success(f"สร้างกลุ่ม {new_name} สำเร็จ!")
                time.sleep(1)
                st.rerun()
            elif not new_name:
                st.error("กรุณาใส่ชื่อกลุ่ม")
            else:
                st.error("ชื่อกลุ่มนี้มีอยู่แล้ว")
                
    st.divider()
    st.subheader("🗑️ ลบกลุ่ม")
    group_to_delete = st.selectbox("เลือกกลุ่มที่จะลบ", ["(เลือกกลุ่ม)"] + list(room_df['GroupName'].unique()))
    if group_to_delete != "(เลือกกลุ่ม)":
        if st.button(f"ยืนยันลบกลุ่ม {group_to_delete}", type="primary"):
            df = df[~((df['Room'] == selected_room) & (df['GroupName'] == group_to_delete))]
            save_data(df)
            st.success("ลบเรียบร้อย")
            time.sleep(1)
            st.rerun()
