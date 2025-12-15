import streamlit as st
import pandas as pd
import altair as alt
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time

# ==========================================
# 1. SYSTEM CONFIG & DESIGN SYSTEM
# ==========================================
st.set_page_config(
    page_title="Classroom Master Pro",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed" # ซ่อนเมนูข้างเพื่อให้ดูเต็มตา
)

# --- MODERN CSS & THEME ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;600&display=swap');
    
    /* Global Font */
    html, body, [class*="css"] {
        font-family: 'Prompt', sans-serif;
        background-color: #F0F2F6;
    }
    
    /* Header Gradient */
    .stAppHeader {
        background-image: linear-gradient(to right, #4facfe 0%, #00f2fe 100%);
        color: white;
    }

    /* Custom Cards (Glassmorphism) */
    .custom-card {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid rgba(255, 255, 255, 0.3);
        margin-bottom: 15px;
        transition: transform 0.2s;
    }
    .custom-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }

    /* Rank Badges */
    .badge {
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        color: white;
        display: inline-block;
    }
    
    /* Quick Action Buttons Grid */
    .stButton button {
        border-radius: 12px;
        height: 3em;
        font-weight: 600;
        border: none;
        transition: all 0.3s;
    }
    .stButton button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }

    /* Progress Bar Customization */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #4facfe 0%, #00f2fe 100%);
    }
    
    </style>
""", unsafe_allow_html=True)

# Connection
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("❌ เชื่อมต่อ Google Sheets ไม่ได้ ตรวจสอบ Secrets อีกครั้ง")
    st.stop()

# ==========================================
# 2. LOGIC & DATA
# ==========================================
RANKS = [
    {"name": "President", "th": "👑 ประธานรุ่น", "xp": 1000, "color": "#FFD700", "bg": "linear-gradient(45deg, #FFD700, #FDB931)"},
    {"name": "Director", "th": "💼 หัวหน้าฝ่าย", "xp": 600, "color": "#9b59b6", "bg": "linear-gradient(45deg, #8E2DE2, #4A00E0)"},
    {"name": "Manager", "th": "👔 หัวหน้าแผนก", "xp": 300, "color": "#3498db", "bg": "linear-gradient(45deg, #2193b0, #6dd5ed)"},
    {"name": "Employee", "th": "👨‍💼 พนักงาน", "xp": 100, "color": "#2ecc71", "bg": "linear-gradient(45deg, #11998e, #38ef7d)"},
    {"name": "Intern", "th": "👶 เด็กฝึกงาน", "xp": 0, "color": "#95a5a6", "bg": "linear-gradient(45deg, #bdc3c7, #2c3e50)"}
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
# 3. INTERFACE
# ==========================================

# --- Header Area ---
c1, c2 = st.columns([3, 1])
with c1:
    st.title("🎓 Classroom Master")
    st.caption("ระบบบริหารจัดการชั้นเรียนยุคใหม่ (Gamification Dashboard)")
with c2:
    all_rooms = ["ม.1/1", "ม.1/2", "ม.1/10"]
    selected_room = st.selectbox("🏫 เลือกห้องเรียน", all_rooms)

df = load_data()
room_df = df[df['Room'] == selected_room].copy()

# --- Main Tabs ---
tabs = st.tabs(["📊 แดชบอร์ด (Overview)", "⚡ ให้คะแนนด่วน (Quick Action)", "⚙️ จัดการ (Settings)"])

# ----------------------------------------------------
# TAB 1: DASHBOARD (เน้นกราฟและข้อมูลสวยงาม)
# ----------------------------------------------------
with tabs[0]:
    if room_df.empty:
        st.info(f"ห้อง {selected_room} ยังไม่มีข้อมูลกลุ่ม เริ่มต้นที่แท็บ 'จัดการ' ได้เลยครับ")
    else:
        # 1. Top Stats Cards
        top_group = room_df.loc[room_df['XP'].idxmax()]
        total_xp = room_df['XP'].sum()
        
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("🏆 ผู้นำสูงสุด", top_group['GroupName'], f"{top_group['XP']} XP")
        col_s2.metric("✨ คะแนนรวมทั้งห้อง", f"{total_xp:,.0f}", "Active Point")
        col_s3.metric("👥 จำนวนกลุ่ม", f"{len(room_df)} กลุ่ม")
        
        st.markdown("---")
        
        # 2. Charts Area
        c_chart1, c_chart2 = st.columns([2, 1])
        
        with c_chart1:
            st.subheader("📈 เปรียบเทียบคะแนน (Competition)")
            # Bar Chart สวยๆ
            bar_chart = alt.Chart(room_df).mark_bar(cornerRadius=8).encode(
                x=alt.X('GroupName', sort='-y', title=None),
                y=alt.Y('XP', title='XP สะสม'),
                color=alt.Color('XP', scale=alt.Scale(scheme='viridis'), legend=None),
                tooltip=['GroupName', 'XP', 'Members']
            ).properties(height=300)
            st.altair_chart(bar_chart, use_container_width=True)
            
        with c_chart2:
            st.subheader("🍰 สัดส่วนยศ (Rank Dist.)")
            # เตรียมข้อมูล Pie Chart
            room_df['RankName'] = room_df['XP'].apply(lambda x: get_rank(x)['th'])
            rank_counts = room_df['RankName'].value_counts().reset_index()
            rank_counts.columns = ['Rank', 'Count']
            
            pie_chart = alt.Chart(rank_counts).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(field="Count", type="quantitative"),
                color=alt.Color(field="Rank", type="nominal"),
                tooltip=['Rank', 'Count']
            ).properties(height=300)
            st.altair_chart(pie_chart, use_container_width=True)

        # 3. Detailed List (Card Style)
        st.subheader("🏅 อันดับอย่างละเอียด")
        sorted_df = room_df.sort_values(by="XP", ascending=False).reset_index(drop=True)
        
        for i, row in sorted_df.iterrows():
            rank = get_rank(row['XP'])
            # Progress Logic
            next_xp = 1000
            for r in reversed(RANKS):
                if r['xp'] > row['XP']:
                    next_xp = r['xp']
                    break
            progress = min(1.0, row['XP'] / next_xp if next_xp > 0 else 1.0)
            
            # HTML Card Injection
            st.markdown(f"""
            <div class="custom-card" style="border-left: 5px solid {rank['color']};">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h3 style="margin:0; color:#2c3e50;">#{i+1} {row['GroupName']}</h3>
                        <p style="margin:0; font-size:0.9em; color:#7f8c8d;">{row['Members']}</p>
                    </div>
                    <div style="text-align:right;">
                        <span class="badge" style="background: {rank['bg']}">{rank['th']}</span>
                        <h2 style="margin:0; color:{rank['color']}">{row['XP']} XP</h2>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(progress, text=f"เส้นทางสู่ยศถัดไป ({row['XP']}/{next_xp})")

# ----------------------------------------------------
# TAB 2: QUICK ACTIONS (เน้นความเร็วในการใช้งาน)
# ----------------------------------------------------
with tabs[1]:
    if room_df.empty:
        st.warning("กรุณาสร้างกลุ่มก่อน")
    else:
        st.subheader("⚡ ให้คะแนนแบบด่วน (One-Click)")
        
        # เลือกกลุ่ม
        target_group = st.selectbox("🎯 เลือกกลุ่มที่จะให้คะแนน", room_df['GroupName'].unique(), key="quick_select")
        
        st.markdown("##### เลือกกิจกรรม:")
        
        # Grid ปุ่มกด (3 คอลัมน์)
        col_q1, col_q2, col_q3 = st.columns(3)
        
        # Action Logic Function
        def quick_update(reason, score):
            idx = df[(df['Room'] == selected_room) & (df['GroupName'] == target_group)].index
            if not idx.empty:
                old_xp = df.loc[idx[0], 'XP']
                new_xp = max(0, old_xp + score)
                df.loc[idx[0], 'XP'] = new_xp
                df.loc[idx[0], 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_data(df)
                
                # Feedback
                st.toast(f"บันทึกแล้ว: {target_group} ({score:+d})", icon="✅")
                new_rank = get_rank(new_xp)
                old_rank = get_rank(old_xp)
                if new_rank['xp'] > old_rank['xp']:
                    st.balloons()
                    st.success(f"🎉 เลื่อนยศเป็น {new_rank['th']}!")
                time.sleep(1)
                st.rerun()

        # ปุ่มต่างๆ
        with col_q1:
            if st.button("📚 ส่งงานตรงเวลา (+50)", use_container_width=True):
                quick_update("ส่งงานตรงเวลา", 50)
            if st.button("🙋 ตอบคำถาม (+20)", use_container_width=True):
                quick_update("ตอบคำถามในคาบ", 20)
                
        with col_q2:
            if st.button("🎨 งานสร้างสรรค์ (+100)", use_container_width=True):
                quick_update("งานสร้างสรรค์/โปรเจกต์", 100)
            if st.button("🧹 จิตพิสัย/ช่วยงาน (+30)", use_container_width=True):
                quick_update("จิตพิสัย", 30)

        with col_q3:
            if st.button("🐢 ส่งงานช้า (-20)", use_container_width=True):
                quick_update("ส่งงานช้า", -20)
            if st.button("📢 คุยเสียงดัง (-10)", use_container_width=True):
                quick_update("คุยเสียงดัง/รบกวน", -10)
        
        st.divider()
        st.subheader("✍️ กำหนดเอง (Manual Input)")
        with st.form("manual_xp"):
            c_m1, c_m2 = st.columns([3, 1])
            with c_m1:
                manual_reason = st.text_input("เหตุผลอื่นๆ")
            with c_m2:
                manual_score = st.number_input("คะแนน", step=10, value=10)
            
            if st.form_submit_button("บันทึกแบบกำหนดเอง"):
                quick_update(manual_reason if manual_reason else "กำหนดเอง", manual_score)

# ----------------------------------------------------
# TAB 3: SETTINGS
# ----------------------------------------------------
with tabs[2]:
    c_set1, c_set2 = st.columns(2)
    
    with c_set1:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.subheader("➕ เพิ่มกลุ่มใหม่")
        with st.form("add_group_form"):
            new_name = st.text_input("ชื่อกลุ่ม")
            new_members = st.text_area("รายชื่อสมาชิก")
            if st.form_submit_button("ยืนยันการสร้าง", type="primary"):
                if new_name and not ((df['Room'] == selected_room) & (df['GroupName'] == new_name)).any():
                    new_row = pd.DataFrame([{
                        "Room": selected_room, "GroupName": new_name, "XP": 0,
                        "Members": new_members, "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    df = pd.concat([df, new_row], ignore_index=True)
                    save_data(df)
                    st.success("สร้างกลุ่มสำเร็จ!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("ชื่อกลุ่มซ้ำหรือว่างเปล่า")
        st.markdown('</div>', unsafe_allow_html=True)

    with c_set2:
        st.markdown('<div class="custom-card" style="border:1px solid #ffcccc;">', unsafe_allow_html=True)
        st.subheader("⚠️ โซนอันตราย")
        del_target = st.selectbox("เลือกกลุ่มที่จะลบ", ["(เลือกกลุ่ม)"] + list(room_df['GroupName'].unique()))
        
        if del_target != "(เลือกกลุ่ม)":
            st.write(f"คุณกำลังจะลบ: **{del_target}**")
            if st.button("ยืนยันการลบ", type="primary"):
                df = df[~((df['Room'] == selected_room) & (df['GroupName'] == del_target))]
                save_data(df)
                st.toast("ลบข้อมูลเรียบร้อย")
                time.sleep(1)
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("Classroom Gamification System © 2024 | Created for Educational Purpose")
