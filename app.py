import streamlit as st
import pandas as pd
import altair as alt
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time

# ==========================================
# 1. Configuration & Modern Design System
# ==========================================
st.set_page_config(
    page_title="Classroom Command Center",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Professional Look
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
    
    /* General Theme */
    html, body, [class*="css"] {
        font-family: 'Sarabun', sans-serif;
        background-color: #f8f9fa;
        color: #2c3e50;
    }
    
    /* Header Style */
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    .main-header h1 { color: white; margin: 0; font-weight: 700; font-size: 2rem; }
    .main-header p { color: #e0e0e0; margin-top: 5px; font-size: 1rem; }

    /* Cards */
    .stCard {
        background-color: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
        margin-bottom: 1rem;
    }
    
    /* Rank Badges */
    .rank-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        color: white;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    /* Progress Bar Label */
    .progress-label {
        font-size: 0.8rem;
        color: #6c757d;
        margin-top: 5px;
        display: flex;
        justify-content: space-between;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        background-color: #fff;
        border: 1px solid #e9ecef;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2a5298 !important;
        color: white !important;
        border: none;
    }
    
    /* Metrics */
    div[data-testid="stMetric"] {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #2a5298;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# Google Sheets Connection
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Connection Error: {e}")
    st.stop()

# ==========================================
# 2. Logic & Rank System
# ==========================================
RANKS = [
    {"name": "👑 President", "th_name": "ประธาน", "min_xp": 1000, "perk": "🛡️ Immunity & Bonus", "color": "#FFD700", "bg": "#FFF9C4"},
    {"name": "💼 Director", "th_name": "หัวหน้าฝ่าย", "min_xp": 600, "perk": "✂️ Workload Cut (50%)", "color": "#9b59b6", "bg": "#F3E5F5"},
    {"name": "👔 Manager", "th_name": "หัวหน้าแผนก", "min_xp": 300, "perk": "🔄 Second Chance", "color": "#3498db", "bg": "#E3F2FD"},
    {"name": "👨‍💼 Employee", "th_name": "พนักงาน", "min_xp": 100, "perk": "⏰ Time Extension", "color": "#2ecc71", "bg": "#E8F5E9"},
    {"name": "👶 Intern", "th_name": "เด็กฝึกงาน", "min_xp": 0, "perk": "🔍 Check-up", "color": "#95a5a6", "bg": "#F5F5F5"}
]

def get_rank_details(xp):
    current_rank = RANKS[-1]
    next_rank = None
    
    for i, rank in enumerate(RANKS):
        if xp >= rank['min_xp']:
            current_rank = rank
            if i > 0: next_rank = RANKS[i-1]
            break
            
    return current_rank, next_rank

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
# 3. Sidebar (Rank Legend & Navigation)
# ==========================================
with st.sidebar:
    st.title("🏫 Control Panel")
    
    # Room Selector
    all_rooms = ["ม.1/1", "ม.1/2", "ม.1/10"]
    selected_room = st.selectbox("เลือกห้องเรียน", all_rooms)
    
    st.divider()
    
    # Rank Legend (คู่มือยศ)
    st.subheader("ℹ️ ระบบยศและสิทธิพิเศษ")
    for r in RANKS:
        with st.expander(f"{r['name']} ({r['min_xp']}+ XP)"):
            st.markdown(f"**ยศ:** {r['th_name']}")
            st.info(f"{r['perk']}")
            
    st.divider()
    st.caption(f"Last Login: {datetime.now().strftime('%H:%M')}")

# ==========================================
# 4. Main Interface
# ==========================================

# 4.1 Header Banner
st.markdown(f"""
<div class="main-header">
    <h1>🏛️ Classroom Gamification: {selected_room}</h1>
    <p>ระบบบริหารจัดการคะแนนและจัดอันดับชั้นเรียนอย่างละเอียด</p>
</div>
""", unsafe_allow_html=True)

# Load Data
df = load_data()
room_df = df[df['Room'] == selected_room].copy()

# Tabs for Organization
tab_dash, tab_action, tab_manage = st.tabs(["📊 ภาพรวม & สถิติ (Dashboard)", "⚡ จัดการคะแนน (Actions)", "⚙️ ข้อมูลกลุ่ม (Settings)"])

# ------------------------------------------
# TAB 1: Dashboard Analytics
# ------------------------------------------
with tab_dash:
    if room_df.empty:
        st.info("💡 ยังไม่มีข้อมูลกลุ่ม กรุณาไปที่แท็บ 'ข้อมูลกลุ่ม' เพื่อเริ่มสร้าง")
    else:
        # A. Summary Metrics
        total_xp = room_df['XP'].sum()
        avg_xp = room_df['XP'].mean()
        top_group = room_df.loc[room_df['XP'].idxmax()]['GroupName']
        
        c1, c2, c3 = st.columns(3)
        c1.metric("🏆 ผู้นำสูงสุด", top_group)
        c2.metric("💎 XP รวมทั้งห้อง", f"{total_xp:,.0f}")
        c3.metric("📈 XP เฉลี่ย", f"{avg_xp:.1f}")
        
        st.markdown("---")
        
        # B. Charts & Visuals
        col_chart, col_list = st.columns([1.5, 1])
        
        with col_chart:
            st.subheader("📊 เปรียบเทียบคะแนนแต่ละกลุ่ม")
            # Create colorful bar chart
            chart = alt.Chart(room_df).mark_bar(cornerRadiusTopLeft=10, cornerRadiusTopRight=10).encode(
                x=alt.X('GroupName', sort='-y', title='กลุ่ม'),
                y=alt.Y('XP', title='XP สะสม'),
                color=alt.Color('XP', scale=alt.Scale(scheme='blues'), legend=None),
                tooltip=['GroupName', 'XP', 'Members']
            ).properties(height=350)
            st.altair_chart(chart, use_container_width=True)

        with col_list:
            st.subheader("🏆 อันดับปัจจุบัน (Leaderboard)")
            leaderboard = room_df.sort_values(by="XP", ascending=False).reset_index(drop=True)
            
            for i, row in leaderboard.iterrows():
                rank, next_rank = get_rank_details(row['XP'])
                
                # Detailed Card Logic
                with st.container():
                    st.markdown(f"""
                    <div style="background:{rank['bg']}; padding:15px; border-radius:10px; margin-bottom:10px; border-left: 5px solid {rank['color']};">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <strong>#{i+1} {row['GroupName']}</strong>
                            <span class="rank-badge" style="background-color:{rank['color']}">{rank['name']}</span>
                        </div>
                        <div style="margin-top:5px; font-size:0.9rem;">⭐ {row['XP']} XP</div>
                    </div>
                    """, unsafe_allow_html=True)

# ------------------------------------------
# TAB 2: Actions (Give XP)
# ------------------------------------------
with tab_action:
    if room_df.empty:
        st.warning("กรุณาสร้างกลุ่มก่อน")
    else:
        st.subheader("✍️ บันทึกคะแนน / เหตุการณ์")
        
        with st.container():
            st.markdown('<div class="stCard">', unsafe_allow_html=True)
            with st.form("action_form", border=False):
                c_sel, c_reason, c_val = st.columns([2, 2, 1])
                
                with c_sel:
                    target = st.selectbox("เลือกกลุ่ม", room_df['GroupName'].unique())
                with c_reason:
                    reason = st.text_input("เหตุผล / กิจกรรม", placeholder="เช่น ส่งงานตรงเวลา, ตอบคำถาม")
                with c_val:
                    val = st.number_input("คะแนน (+/-)", value=50, step=10)
                
                submitted = st.form_submit_button("✅ บันทึกรายการ", type="primary", use_container_width=True)
                
                if submitted:
                    idx = df[(df['Room'] == selected_room) & (df['GroupName'] == target)].index
                    if not idx.empty:
                        # Calculation
                        old_xp = df.loc[idx[0], 'XP']
                        new_xp = max(0, old_xp + val)
                        
                        # Update Data
                        df.loc[idx[0], 'XP'] = new_xp
                        df.loc[idx[0], 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        save_data(df)
                        
                        # Feedback
                        rank, _ = get_rank_details(new_xp)
                        st.success(f"บันทึกสำเร็จ! กลุ่ม {target} คะแนนใหม่: {new_xp} XP")
                        st.info(f"สถานะล่าสุด: {rank['name']} - {rank['perk']}")
                        time.sleep(1.5)
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
        # Show Detailed Progress for Selected Group
        if not room_df.empty:
            st.subheader("🔍 ตรวจสอบความก้าวหน้า (Detail View)")
            view_target = st.selectbox("ดูกลุ่มไหนดี?", room_df['GroupName'].unique())
            
            g_data = room_df[room_df['GroupName'] == view_target].iloc[0]
            curr_rank, next_rank = get_rank_details(g_data['XP'])
            
            st.markdown(f"**สมาชิก:** {g_data['Members']}")
            st.markdown(f"**อัปเดตล่าสุด:** {g_data.get('LastUpdated', '-')}")
            
            if next_rank:
                needed = next_rank['min_xp'] - g_data['XP']
                pct = g_data['XP'] / next_rank['min_xp']
                st.progress(min(1.0, pct))
                st.caption(f"🚀 อีก {needed} XP เพื่อเลื่อนเป็น **{next_rank['name']}**")
            else:
                st.progress(1.0)
                st.balloons()
                st.caption("🏆 สูงสุดในสายงานแล้ว!")

# ------------------------------------------
# TAB 3: Management
# ------------------------------------------
with tab_manage:
    c_add, c_del = st.columns(2)
    
    with c_add:
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        st.subheader("➕ เพิ่มกลุ่มใหม่")
        with st.form("add_group"):
            n_name = st.text_input("ชื่อกลุ่ม")
            n_mem = st.text_area("รายชื่อสมาชิก (เช่น เลขที่ 1, 2, 3)")
            if st.form_submit_button("สร้างกลุ่ม", type="primary"):
                if n_name and not ((df['Room'] == selected_room) & (df['GroupName'] == n_name)).any():
                    new_row = pd.DataFrame([{
                        "Room": selected_room, "GroupName": n_name, "XP": 0,
                        "Members": n_mem, "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    df = pd.concat([df, new_row], ignore_index=True)
                    save_data(df)
                    st.success("สร้างเสร็จสิ้น")
                    st.rerun()
                else:
                    st.error("ชื่อซ้ำหรือว่างเปล่า")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with c_del:
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        st.subheader("🗑️ ลบข้อมูล")
        d_name = st.selectbox("เลือกกลุ่มที่จะลบ", ["-"] + list(room_df['GroupName'].unique()))
        if d_name != "-":
            if st.button("ยืนยันการลบ", type="primary"):
                df = df[~((df['Room'] == selected_room) & (df['GroupName'] == d_name))]
                save_data(df)
                st.warning("ลบแล้ว")
                time.sleep(1)
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
