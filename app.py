import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time

# ==========================================
# 1. ตั้งค่าหน้าเว็บ & CSS (ส่วนสำคัญของความสวยงาม)
# ==========================================
st.set_page_config(
    page_title="Classroom Gamification Pro",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS DESIGNS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;800&display=swap');
    
    /* Global Theme */
    html, body, [class*="css"] {
        font-family: 'Sarabun', sans-serif;
        background-color: #f4f6f9; /* สีพื้นหลังเทาอ่อน สบายตา */
        color: #333333;
    }

    /* Main Container Styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Header Banner */
    .header-banner {
        background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        text-align: center;
    }
    .header-banner h1 {
        color: white;
        font-weight: 800;
        margin: 0;
        font-size: 2.2rem;
    }
    .header-banner p {
        font-size: 1.1rem;
        opacity: 0.9;
        margin-top: 10px;
    }

    /* Card UI (กล่องต่างๆ) */
    .stCard, div[data-testid="stExpander"] {
        background-color: #ffffff;
        border-radius: 15px;
        padding: 1.5rem;
        box-shadow: 0 8px 20px rgba(0,0,0,0.06); /* เงาฟุ้งๆ ทันสมัย */
        border: none;
        margin-bottom: 1rem;
        transition: transform 0.2s;
    }
    div[data-testid="stExpander"]:hover {
        transform: translateY(-3px); /* ขยับขึ้นเล็กน้อยเมื่อเอาเมาส์ชี้ */
    }
    
    /* Metric Styling (Top 3 Cards) */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 8px 15px rgba(0,0,0,0.08);
        text-align: center;
        border-top: 5px solid #e0e0e0; /* Default top border */
    }
    [data-testid="stMetricLabel"] { font-weight: bold; color: #555; font-size: 1.1rem; }
    [data-testid="stMetricValue"] { font-size: 2.5rem; font-weight: 800; color: #2c3e50; }

    /* Custom Rank Colors for Borders */
    .rank-border-gold { border-left: 6px solid #FFD700 !important; }
    .rank-border-purple { border-left: 6px solid #9b59b6 !important; }
    .rank-border-blue { border-left: 6px solid #3498db !important; }
    .rank-border-green { border-left: 6px solid #2ecc71 !important; }
    .rank-border-gray { border-left: 6px solid #95a5a6 !important; }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
        padding: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        border-radius: 10px;
        background-color: #e9ecef;
        font-weight: 600;
        border: none;
        color: #6c757d;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4b6cb7 !important;
        color: white !important;
        box-shadow: 0 4px 10px rgba(75, 108, 183, 0.3);
    }

    /* Button Styling */
    .stButton button {
        border-radius: 10px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    /* Primary Button (บันทึก) */
    .stButton button[kind="primary"] {
        background: linear-gradient(90deg, #00b09b, #96c93d);
        border: none;
        box-shadow: 0 4px 15px rgba(0, 176, 155, 0.4);
    }
    .stButton button[kind="primary"]:hover {
        box-shadow: 0 6px 20px rgba(0, 176, 155, 0.6);
        transform: translateY(-2px);
    }
    /* Secondary Button (ธรรมดา) */
    .stButton button[kind="secondary"] {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        color: #333;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        box-shadow: 2px 0 10px rgba(0,0,0,0.05);
    }

    </style>
    """, unsafe_allow_html=True)

# เชื่อมต่อ Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"🔥 การเชื่อมต่อ Google Sheets ล้มเหลว: {e}")
    st.stop()

# ==========================================
# 2. ระบบยศ (Rank Logic) & Helper Functions
# ==========================================
RANKS = [
    {"name": "👑 ประธาน (President)", "min_xp": 1000, "perk": "🛡️ Immunity: ไม่ต้องทำงาน 3 ชิ้น + โบนัส", "color": "#FFD700", "css_class": "rank-border-gold"},
    {"name": "💼 หัวหน้าฝ่าย (Director)", "min_xp": 600, "perk": "✂️ Workload Cut: ลดงาน 50% ได้เต็ม", "color": "#9b59b6", "css_class": "rank-border-purple"},
    {"name": "👔 หัวหน้าแผนก (Manager)", "min_xp": 300, "perk": "🔄 Second Chance: สอบแก้ตัวได้", "color": "#3498db", "css_class": "rank-border-blue"},
    {"name": "👨‍💼 พนักงาน (Employee)", "min_xp": 100, "perk": "⏰ Time Extension: ส่งช้าได้ 1 สัปดาห์", "color": "#2ecc71", "css_class": "rank-border-green"},
    {"name": "👶 เด็กฝึกงาน (Intern)", "min_xp": 0, "perk": "🔍 Check-up: ครูตรวจก่อนส่งจริง", "color": "#95a5a6", "css_class": "rank-border-gray"}
]

def get_rank_info(xp):
    for rank in RANKS:
        if xp >= rank['min_xp']: return rank
    return RANKS[-1]

@st.cache_data(ttl=5)
def load_data():
    try:
        df = conn.read(worksheet="Sheet1", usecols=[0, 1, 2, 3, 4], ttl=0)
        df = df.dropna(how='all')
        if 'XP' not in df.columns: df['XP'] = 0
        df['XP'] = pd.to_numeric(df['XP'], errors='coerce').fillna(0).astype(int)
        return df
    except Exception:
        return pd.DataFrame(columns=['Room', 'GroupName', 'XP', 'Members', 'LastUpdated'])

def save_data(df):
    conn.update(worksheet="Sheet1", data=df)
    st.cache_data.clear()

# ==========================================
# 3. ส่วนแสดงผลหลัก (Main UI)
# ==========================================

# --- Sidebar ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3408/3408545.png", width=100)
    st.title("Control Center")
    st.write("แผงควบคุมสำหรับคุณครู")
    st.divider()
    all_rooms = ["ม.1/1", "ม.1/2", "ม.1/10"]
    selected_room = st.selectbox("🏫 เลือกห้องเรียน", all_rooms, index=0)
    st.info(f"กำลังใช้งาน: ห้อง {selected_room}")
    st.divider()
    st.caption("Gamification System v2.0 (Modern UI)")

# --- Main Content ---

# Header Banner
st.markdown(f"""
    <div class="header-banner">
        <h1>🎓 ห้องเรียน {selected_room}</h1>
        <p>ระบบสะสมคะแนนและจัดอันดับแบบ Gamification ออนไลน์</p>
    </div>
    """, unsafe_allow_html=True)

df = load_data()
room_df = df[df['Room'] == selected_room].copy()

# Tabs
tab1, tab2, tab3 = st.tabs(["🏆 จัดอันดับ (Leaderboard)", "⚡ ให้คะแนน (Action)", "⚙️ จัดการกลุ่ม (Manage)"])

# --- TAB 1: Leaderboard (หน้านี้เน้นสวยงาม) ---
with tab1:
    if room_df.empty:
        st.warning("⚠️ ยังไม่มีข้อมูลกลุ่มในห้องนี้ กรุณาไปที่แท็บ 'จัดการกลุ่ม' เพื่อสร้างกลุ่มแรก")
    else:
        leaderboard = room_df.sort_values(by="XP", ascending=False).reset_index(drop=True)
        
        st.subheader("🌟 Top 3 ผู้นำสูงสุด")
        
        # Top 3 Cards (Podium Style)
        cols = st.columns(3)
        for i in range(min(3, len(leaderboard))):
            row = leaderboard.iloc[i]
            rank_info = get_rank_info(row['XP'])
            
            # สร้าง CSS เฉพาะสำหรับ Top 3 เพื่อใส่สีขอบด้านบน
            top_card_css = f"""
                <style>
                    div[data-testid="column"]:nth-child({i+1}) div[data-testid="stMetric"] {{
                        border-top: 8px solid {rank_info['color']} !important;
                    }}
                </style>
            """
            st.markdown(top_card_css, unsafe_allow_html=True)
            
            medals = ["🥇", "🥈", "🥉"]
            with cols[i]:
                st.metric(
                    label=f"{medals[i]} อันดับ {i+1}: {row['GroupName']}", 
                    value=f"{row['XP']} XP", 
                    delta=rank_info['name']
                )

        st.divider()
        st.subheader("📋 ตารางอันดับทั้งหมด")

        # Full List with styled expanders
        for i, row in leaderboard.iterrows():
            rank_info = get_rank_info(row['XP'])
            
            # คำนวณ Progress Bar
            next_xp = 1000
            for r in reversed(RANKS):
                if r['min_xp'] > row['XP']:
                    next_xp = r['min_xp']
                    break
            progress = min(1.0, row['XP'] / next_xp if next_xp > 0 else 1.0)
            
            # ใช้ Container + CSS Class เพื่อทำขอบสี
            with st.container():
                # Inject CSS class ให้ container นี้
                st.markdown(f'<div class="{rank_info["css_class"]}"></div>', unsafe_allow_html=True)
                
                with st.expander(f"#{i+1} **{row['GroupName']}** ({rank_info['name']})"):
                    c1, c2 = st.columns([3, 1.5])
                    with c1:
                        st.caption("👥 สมาชิก:")
                        st.write(f"{row['Members']}")
                        st.caption(f"🎁 สิทธิพิเศษ ({rank_info['name']}):")
                        st.info(f"{rank_info['perk']}")
                    
                    with c2:
                        st.markdown(f"<h2 style='text-align:center; color:{rank_info['color']}; margin-bottom:0;'>{row['XP']} XP</h2>", unsafe_allow_html=True)
                        st.caption(f"<p style='text-align:center;'>เส้นทางสู่ยศถัดไป ({row['XP']}/{next_xp})</p>", unsafe_allow_html=True)
                        st.progress(progress)

# --- TAB 2: Give XP (หน้าให้คะแนน ใส่กล่องสวยๆ) ---
with tab2:
    if room_df.empty:
        st.warning("กรุณาสร้างกลุ่มก่อน")
    else:
        # ใช้ st.container เพื่อสร้างกล่อง Card รอบฟอร์ม
        with st.container():
            st.markdown('<div class="stCard">', unsafe_allow_html=True)
            st.subheader("✍️ ให้คะแนน/หักคะแนน")
            
            with st.form("xp_form", border=False): # border=False เพราะเรามี card ครอบแล้ว
                col_f1, col_f2 = st.columns([2, 1])
                with col_f1:
                    target_group = st.selectbox("🎯 เลือกกลุ่มเป้าหมาย", room_df['GroupName'].unique())
                    reason = st.text_input("📝 เหตุผล (เช่น ส่งงานครบ, จิตพิสัย)", "ส่งงานครบถ้วน")
                with col_f2:
                    xp_change = st.number_input("💎 จำนวน XP (ใส่ลบเพื่อหัก)", value=50, step=10, help="เช่น 50 หรือ -20")
                
                st.markdown("---")
                # ใช้ปุ่มแบบ primary สีสวยๆ
                submitted = st.form_submit_button("💾 บันทึกคะแนน", type="primary", use_container_width=True)
                
                if submitted:
                    idx = df[(df['Room'] == selected_room) & (df['GroupName'] == target_group)].index
                    if not idx.empty:
                        old_xp = df.loc[idx[0], 'XP']
                        new_xp = max(0, old_xp + xp_change)
                        df.loc[idx[0], 'XP'] = new_xp
                        df.loc[idx[0], 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        save_data(df)
                        
                        # Animation & Notification
                        old_rank = get_rank_info(old_xp)
                        new_rank = get_rank_info(new_xp)
                        
                        st.toast(f"บันทึกแล้ว! กลุ่ม {target_group} มี {new_xp} XP", icon="✅")
                        if new_rank['min_xp'] > old_rank['min_xp']:
                            st.balloons()
                            time.sleep(1)
                            st.success(f"🎉 สุดยอด! กลุ่ม {target_group} เลื่อนยศเป็น [{new_rank['name']}] แล้ว!")
                        
                        time.sleep(1)
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True) # ปิด div stCard

# --- TAB 3: Manage Groups (หน้าจัดการ ใส่กล่องเช่นกัน) ---
with tab3:
    col_m1, col_m2 = st.columns(2)
    
    # Card 1: เพิ่มกลุ่ม
    with col_m1:
        with st.container():
             st.markdown('<div class="stCard">', unsafe_allow_html=True)
             st.subheader("➕ สร้างกลุ่มใหม่")
             with st.form("add_group", border=False):
                new_name = st.text_input("ตั้งชื่อกลุ่ม")
                new_members = st.text_area("รายชื่อสมาชิก (คั่นด้วยคอมม่า)", placeholder="เช่น เลขที่ 1, เลขที่ 5, เลขที่ 12")
                add_btn = st.form_submit_button("สร้างกลุ่ม", type="primary")
                
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
                        st.success(f"✅ สร้างกลุ่ม {new_name} สำเร็จ!")
                        time.sleep(1)
                        st.rerun()
                    elif not new_name:
                        st.error("❌ กรุณาใส่ชื่อกลุ่ม")
                    else:
                        st.error("❌ ชื่อกลุ่มนี้มีอยู่แล้วในห้องนี้")
             st.markdown('</div>', unsafe_allow_html=True)

    # Card 2: ลบกลุ่ม
    with col_m2:
         with st.container():
             st.markdown('<div class="stCard" style="background-color: #fff5f5;">', unsafe_allow_html=True) # พื้นหลังแดงอ่อนๆ เตือนใจ
             st.subheader("🗑️ ลบกลุ่ม (อันตราย)")
             
             group_to_delete = st.selectbox("เลือกกลุ่มที่จะลบถาวร", ["(กรุณาเลือกกลุ่ม)"] + list(room_df['GroupName'].unique()))
             
             if group_to_delete != "(กรุณาเลือกกลุ่ม)":
                 st.write(f"⚠️ คุณกำลังจะลบกลุ่ม: **{group_to_delete}**")
                 if st.button("ยืนยันการลบกลุ่มนี้", type="primary"):
                     df = df[~((df['Room'] == selected_room) & (df['GroupName'] == group_to_delete))]
                     save_data(df)
                     st.toast(f"ลบกลุ่ม {group_to_delete} เรียบร้อย", icon="🗑️")
                     time.sleep(1)
                     st.rerun()
             st.markdown('</div>', unsafe_allow_html=True)

# Footer เล็กๆ
st.markdown("---")
st.caption("Developed for Gamified Classroom | ❤️ Educators")
