import streamlit as st
import pandas as pd
import altair as alt
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time
import json

# ==============================================================================
# 1. SYSTEM CONFIGURATION & ADVANCED CSS (การตั้งค่าระบบและดีไซน์)
# ==============================================================================
st.set_page_config(
    page_title="Classroom X - Ultimate",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- THEME & STYLE ENGINE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;800&family=Prompt:wght@300;400;600&display=swap');
    
    :root {
        --primary-color: #2563eb;
        --secondary-color: #3b82f6;
        --success-color: #10b981;
        --danger-color: #ef4444;
        --warning-color: #f59e0b;
        --bg-color: #f3f4f6;
        --card-bg: rgba(255, 255, 255, 0.95);
    }

    /* Global Typography */
    html, body, [class*="css"] {
        font-family: 'Sarabun', 'Prompt', sans-serif;
        background-color: var(--bg-color);
        color: #1f2937;
    }
    
    /* Header Styles */
    .header-container {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 1.5rem;
        border-radius: 16px;
        color: white;
        box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.5);
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }
    .header-container::before {
        content: "";
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%);
        animation: rotate 20s linear infinite;
    }
    @keyframes rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

    /* Card Design (Glassmorphism) */
    .glass-card {
        background: var(--card-bg);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.5);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: transform 0.2s ease-in-out;
        margin-bottom: 15px;
    }
    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }

    /* Mobile-First Buttons */
    .stButton button {
        width: 100%;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 0.75rem 1rem !important;
        transition: all 0.2s !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border: none !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Button Variants */
    .stButton button:hover { transform: scale(1.02); filter: brightness(110%); }
    .stButton button:active { transform: scale(0.98); }

    /* Rank Badge */
    .rank-badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* Tabs Navigation */
    .stTabs [data-baseweb="tab-list"] {
        background-color: white;
        padding: 8px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        font-weight: 600;
        color: #6b7280;
    }
    .stTabs [aria-selected="true"] {
        background-color: #eff6ff !important;
        color: #2563eb !important;
    }

    /* Progress Bar Customization */
    div[data-testid="stProgressBar"] > div {
        height: 10px;
        border-radius: 5px;
        background: #e5e7eb;
    }
    div[data-testid="stProgressBar"] > div > div {
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
    }

    /* Mobile Adjustments */
    @media (max-width: 640px) {
        .header-container { padding: 1rem; margin-bottom: 1rem; }
        .stMetric { background-color: white; padding: 10px; border-radius: 10px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
        h1 { font-size: 1.5rem !important; }
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. BUSINESS LOGIC LAYER (ระบบจัดการข้อมูลและคำนวณ)
# ==============================================================================

class RankSystem:
    """Class จัดการระบบยศและสิทธิพิเศษ"""
    def __init__(self):
        self.ranks = [
            {"name": "PRESIDENT", "th": "👑 ประธานรุ่น", "min_xp": 1000, "color": "#fbbf24", "bg": "linear-gradient(to right, #f59e0b, #d97706)", "perk": "🛡️ Immunity & Bonus"},
            {"name": "DIRECTOR", "th": "💼 หัวหน้าฝ่าย", "min_xp": 600, "color": "#a78bfa", "bg": "linear-gradient(to right, #8b5cf6, #7c3aed)", "perk": "✂️ Workload Cut 50%"},
            {"name": "MANAGER", "th": "👔 หัวหน้าแผนก", "min_xp": 300, "color": "#60a5fa", "bg": "linear-gradient(to right, #3b82f6, #2563eb)", "perk": "🔄 Second Chance"},
            {"name": "EMPLOYEE", "th": "👨‍💼 พนักงาน", "min_xp": 100, "color": "#34d399", "bg": "linear-gradient(to right, #10b981, #059669)", "perk": "⏰ Time Extension"},
            {"name": "INTERN", "th": "👶 เด็กฝึกงาน", "min_xp": 0, "color": "#9ca3af", "bg": "linear-gradient(to right, #9ca3af, #4b5563)", "perk": "🔍 Pre-Checkup"}
        ]

    def get_rank(self, xp):
        for rank in self.ranks:
            if xp >= rank['min_xp']: return rank
        return self.ranks[-1]

    def get_next_rank(self, xp):
        """หา Level ถัดไปเพื่อคำนวณ Progress Bar"""
        for i, rank in enumerate(self.ranks):
            if xp >= rank['min_xp']:
                if i > 0: return self.ranks[i-1] # Return rank ที่สูงกว่าปัจจุบัน
                else: return None # Max Level แล้ว
        return self.ranks[-2] # กรณีเป็น Intern ให้คืนค่า Employee

class DatabaseManager:
    """Class จัดการการเชื่อมต่อ Google Sheets และ Transaction"""
    def __init__(self):
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
        except Exception as e:
            st.error(f"🔥 Database Connection Error: {e}")
            st.stop()

    def load_data(self):
        """โหลดข้อมูลและแปลง Type ให้ถูกต้อง"""
        try:
            df = self.conn.read(worksheet="Sheet1", usecols=[0, 1, 2, 3, 4, 5], ttl=0)
            df = df.dropna(how='all')
            
            # Data Cleaning & Type Casting
            if 'XP' not in df.columns: df['XP'] = 0
            df['XP'] = pd.to_numeric(df['XP'], errors='coerce').fillna(0).astype(int)
            
            if 'HistoryLog' not in df.columns: df['HistoryLog'] = "[]"
            df['HistoryLog'] = df['HistoryLog'].fillna("[]").astype(str)
            
            return df
        except Exception as e:
            # Fallback กรณี sheet ว่าง
            return pd.DataFrame(columns=['Room', 'GroupName', 'XP', 'Members', 'LastUpdated', 'HistoryLog'])

    def save_data(self, df):
        """บันทึกข้อมูลกลับลง Sheet"""
        self.conn.update(worksheet="Sheet1", data=df)
        st.cache_data.clear()

    def update_xp(self, room, group_name, amount, reason, df):
        """อัปเดตคะแนนพร้อมบันทึกประวัติ (Log)"""
        idx = df[(df['Room'] == room) & (df['GroupName'] == group_name)].index
        
        if not idx.empty:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # 1. Update XP
            old_xp = df.loc[idx[0], 'XP']
            new_xp = max(0, old_xp + amount)
            df.loc[idx[0], 'XP'] = new_xp
            df.loc[idx[0], 'LastUpdated'] = current_time
            
            # 2. Update History Log (JSON format)
            try:
                history = json.loads(df.loc[idx[0], 'HistoryLog'])
            except:
                history = []
                
            new_log = {
                "date": current_time,
                "amount": amount,
                "reason": reason,
                "balance": new_xp
            }
            history.insert(0, new_log) # ใส่ข้อมูลใหม่ไว้หน้าสุด
            df.loc[idx[0], 'HistoryLog'] = json.dumps(history, ensure_ascii=False)
            
            self.save_data(df)
            return old_xp, new_xp
        return None, None

    def add_group(self, room, name, members, df):
        if not ((df['Room'] == room) & (df['GroupName'] == name)).any():
            new_row = pd.DataFrame([{
                "Room": room, 
                "GroupName": name, 
                "XP": 0, 
                "Members": members, 
                "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "HistoryLog": "[]"
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            self.save_data(df)
            return True
        return False

    def delete_group(self, room, name, df):
        df = df[~((df['Room'] == room) & (df['GroupName'] == name))]
        self.save_data(df)
        return True

# Initialize Systems
db = DatabaseManager()
rank_sys = RankSystem()

# ==============================================================================
# 3. USER INTERFACE COMPONENTS (ส่วนแสดงผล)
# ==============================================================================

def render_header(room):
    st.markdown(f"""
    <div class="header-container">
        <h1 style='margin:0; font-weight:800; font-size:2rem;'>🏛️ Classroom Command Center</h1>
        <div style='display:flex; justify-content:space-between; align-items:center; margin-top:10px;'>
            <span style='background:rgba(255,255,255,0.2); padding:5px 15px; border-radius:20px; font-weight:600;'>
                Room: {room}
            </span>
            <span style='font-size:0.9rem; opacity:0.9;'>Last Sync: {datetime.now().strftime('%H:%M')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_group_card(index, row, rank, next_rank):
    # Calculate Progress
    if next_rank:
        total_range = next_rank['min_xp']
        progress = min(1.0, max(0.0, row['XP'] / total_range))
        next_label = f"Next: {next_rank['th']} ({row['XP']}/{next_rank['min_xp']})"
    else:
        progress = 1.0
        next_label = "MAX LEVEL REACHED"

    st.markdown(f"""
    <div class="glass-card" style="border-left: 5px solid {rank['color']}; position: relative;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <div>
                <span style="font-size: 2rem; font-weight: 800; color: #cbd5e1; position: absolute; top: 10px; right: 20px; opacity: 0.2;">#{index}</span>
                <h3 style="margin: 0; font-weight: 700; font-size: 1.2rem;">{row['GroupName']}</h3>
                <p style="margin: 0; color: #64748b; font-size: 0.85rem;">👥 {row['Members']}</p>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 1.5rem; font-weight: 800; color: {rank['color']};">{row['XP']} XP</div>
                <span class="rank-badge" style="background: {rank['bg']}">{rank['th']}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(progress, text=next_label)

# ==============================================================================
# 4. MAIN APP EXECUTION (การทำงานหลัก)
# ==============================================================================

# --- Sidebar Configuration ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2997/2997322.png", width=80)
    st.title("Settings")
    
    # Room Selection
    all_rooms = ["ม.1/1", "ม.1/2", "ม.1/10"]
    selected_room = st.selectbox("🏫 Select Room", all_rooms)
    
    st.divider()
    st.info("💡 **Pro Tip:** กด 'Add to Home Screen' บนมือถือเพื่อใช้งานเต็มจอ")
    
    # Download Data Feature
    df_download = db.load_data()
    csv = df_download.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Export CSV",
        data=csv,
        file_name='classroom_data.csv',
        mime='text/csv',
        use_container_width=True
    )

# --- Load Data ---
df = db.load_data()
room_df = df[df['Room'] == selected_room].copy()

# --- Render Header ---
render_header(selected_room)

# --- Main Tabs ---
tabs = st.tabs(["⚡ Quick Actions", "📊 Dashboard", "📜 History & Details", "⚙️ Manage"])

# ------------------------------------------------------------------
# TAB 1: QUICK ACTIONS (Mobile Optimized)
# ------------------------------------------------------------------
with tabs[0]:
    if room_df.empty:
        st.warning("⚠️ No groups found. Please go to 'Manage' tab to create groups.")
    else:
        col_main, col_recent = st.columns([2, 1])
        
        with col_main:
            st.markdown("### 🎯 Score Control")
            
            # Smart Group Selector
            target_group = st.selectbox("Select Group", room_df['GroupName'].unique(), key="qa_select")
            
            # Show Current Status of Selected Group
            if target_group:
                curr_data = room_df[room_df['GroupName'] == target_group].iloc[0]
                curr_rank = rank_sys.get_rank(curr_data['XP'])
                st.info(f"📍 **Current Status:** {curr_rank['th']} ({curr_data['XP']} XP) | สิทธิ์: {curr_rank['perk']}")

            st.write("") # Spacer

            # Action Grid (Buttons)
            c1, c2 = st.columns(2)
            
            def process_action(reason, amount):
                old_xp, new_xp = db.update_xp(selected_room, target_group, amount, reason, df)
                
                # Notifications
                if amount > 0:
                    st.toast(f"✅ Added {amount} XP to {target_group}", icon="🎉")
                else:
                    st.toast(f"⚠️ Deducted {abs(amount)} XP from {target_group}", icon="📉")
                
                # Level Up Animation
                old_r = rank_sys.get_rank(old_xp)
                new_r = rank_sys.get_rank(new_xp)
                if new_r['min_xp'] > old_r['min_xp']:
                    st.balloons()
                    st.success(f"🌟 **LEVEL UP!** {target_group} is now {new_r['th']}!")
                    time.sleep(2)
                
                time.sleep(0.5)
                st.rerun()

            with c1:
                if st.button("📚 ส่งงาน (+50)", type="primary"): process_action("ส่งงานตรงเวลา", 50)
                if st.button("🙋 ตอบคำถาม (+20)"): process_action("ตอบคำถามในคาบ", 20)
                if st.button("🎨 งานกลุ่ม (+100)"): process_action("งานกลุ่ม/โปรเจกต์", 100)
            
            with c2:
                if st.button("🐢 ส่งช้า (-20)"): process_action("ส่งงานล่าช้า", -20)
                if st.button("📢 เสียงดัง (-10)"): process_action("คุยเสียงดัง/รบกวน", -10)
                if st.button("💀 ไม่ส่งงาน (-50)"): process_action("ไม่ส่งงาน", -50)

            # Manual Input
            with st.expander("✍️ Custom Input"):
                with st.form("custom_xp"):
                    custom_reason = st.text_input("Reason")
                    custom_val = st.number_input("Amount", step=5)
                    if st.form_submit_button("Submit"):
                        process_action(custom_reason if custom_reason else "Manual Adjustment", custom_val)

        # Recent Activity Feed (Mini)
        with col_recent:
            st.markdown("### 🕒 Recent Activity")
            if target_group:
                try:
                    logs = json.loads(room_df[room_df['GroupName'] == target_group]['HistoryLog'].values[0])
                    if not logs:
                        st.caption("No history yet.")
                    else:
                        for log in logs[:5]: # Show last 5
                            color = "green" if log['amount'] > 0 else "red"
                            icon = "chk" if log['amount'] > 0 else "cross"
                            st.markdown(f"""
                            <div style="background:white; padding:10px; border-radius:8px; margin-bottom:8px; border-left:4px solid {color}; font-size:0.85rem;">
                                <div style="display:flex; justify-content:space-between;">
                                    <strong>{log['reason']}</strong>
                                    <span style="color:{color}; font-weight:bold;">{log['amount']:+d}</span>
                                </div>
                                <div style="color:gray; font-size:0.75rem;">{log['date']} • Bal: {log['balance']}</div>
                            </div>
                            """, unsafe_allow_html=True)
                except:
                    st.error("Log format error")

# ------------------------------------------------------------------
# TAB 2: ANALYTICS DASHBOARD
# ------------------------------------------------------------------
with tabs[1]:
    if room_df.empty:
        st.info("No Data available for analytics.")
    else:
        # Top Metrics
        top_group = room_df.loc[room_df['XP'].idxmax()]
        total_xp_room = room_df['XP'].sum()
        avg_xp = room_df['XP'].mean()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("🏆 Top Performer", top_group['GroupName'], f"{top_group['XP']} XP")
        m2.metric("✨ Total Classroom XP", f"{total_xp_room:,.0f}")
        m3.metric("📈 Average XP", f"{avg_xp:.1f}")
        
        st.markdown("---")
        
        # Charts Section
        c_chart1, c_chart2 = st.columns([2, 1])
        
        with c_chart1:
            st.markdown("#### 📊 Score Comparison")
            chart_data = room_df[['GroupName', 'XP']].sort_values('XP', ascending=False)
            bar_chart = alt.Chart(chart_data).mark_bar(cornerRadius=10).encode(
                x=alt.X('GroupName', sort='-y', title=None),
                y=alt.Y('XP'),
                color=alt.Color('XP', scale=alt.Scale(scheme='plasma'), legend=None),
                tooltip=['GroupName', 'XP']
            ).properties(height=320)
            st.altair_chart(bar_chart, use_container_width=True)

        with c_chart2:
            st.markdown("#### 🍰 Rank Distribution")
            room_df['RankName'] = room_df['XP'].apply(lambda x: rank_sys.get_rank(x)['th'])
            pie = alt.Chart(room_df).mark_arc(innerRadius=60).encode(
                theta=alt.Theta("count()"),
                color=alt.Color("RankName", title="Rank"),
                tooltip=["RankName", "count()"]
            ).properties(height=320)
            st.altair_chart(pie, use_container_width=True)

        st.markdown("### 🏅 Live Leaderboard")
        sorted_df = room_df.sort_values(by="XP", ascending=False).reset_index(drop=True)
        for i, row in sorted_df.iterrows():
            r = rank_sys.get_rank(row['XP'])
            nr = rank_sys.get_next_rank(row['XP'])
            render_group_card(i+1, row, r, nr)

# ------------------------------------------------------------------
# TAB 3: HISTORY & DEEP DIVE
# ------------------------------------------------------------------
with tabs[2]:
    st.markdown("### 🔍 Group Inspection")
    view_group = st.selectbox("Select Group to View Details", room_df['GroupName'].unique())
    
    if view_group:
        g_data = room_df[room_df['GroupName'] == view_group].iloc[0]
        
        # Parse History
        try:
            logs = json.loads(g_data['HistoryLog'])
            history_df = pd.DataFrame(logs)
        except:
            history_df = pd.DataFrame()

        # Display Stats
        col_d1, col_d2 = st.columns([1, 2])
        
        with col_d1:
            st.markdown(f"""
            <div style="background:white; padding:20px; border-radius:15px; text-align:center;">
                <h2>{g_data['GroupName']}</h2>
                <h1 style="color:#2563eb; font-size:3rem;">{g_data['XP']}</h1>
                <p>Current XP</p>
                <hr>
                <div style="text-align:left;">
                    <p><b>👥 Members:</b><br>{g_data['Members']}</p>
                    <p><b>🕒 Last Update:</b><br>{g_data['LastUpdated']}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_d2:
            if not history_df.empty:
                st.markdown("#### 📈 XP Timeline")
                # Create Trend Line
                line = alt.Chart(history_df).mark_line(point=True).encode(
                    x=alt.X('date', title='Time'),
                    y=alt.Y('balance', title='XP Balance'),
                    tooltip=['date', 'reason', 'amount', 'balance']
                ).properties(height=250)
                st.altair_chart(line, use_container_width=True)
                
                st.markdown("#### 📜 Transaction Logs")
                st.dataframe(
                    history_df[['date', 'reason', 'amount', 'balance']], 
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No history logs available for this group.")

# ------------------------------------------------------------------
# TAB 4: MANAGEMENT (CRUD)
# ------------------------------------------------------------------
with tabs[3]:
    st.markdown("### 🛠️ Classroom Management")
    
    c_add, c_del = st.columns(2)
    
    with c_add:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("➕ Create New Group")
        with st.form("add_grp"):
            n_name = st.text_input("Group Name")
            n_mem = st.text_area("Members (e.g. No.1, No.5)")
            if st.form_submit_button("Create Group"):
                if n_name:
                    success = db.add_group(selected_room, n_name, n_mem, df)
                    if success:
                        st.success(f"Created {n_name} successfully!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Group name already exists in this room.")
                else:
                    st.warning("Please enter a group name.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with c_del:
        st.markdown('<div class="glass-card" style="border:1px solid #fee2e2;">', unsafe_allow_html=True)
        st.subheader("🗑️ Delete Group")
        d_name = st.selectbox("Select Group to Delete", ["-"] + list(room_df['GroupName'].unique()))
        
        if d_name != "-":
            st.warning(f"⚠️ Are you sure you want to delete **{d_name}**? This cannot be undone.")
            if st.button("Confirm Delete", type="primary"):
                db.delete_group(selected_room, d_name, df)
                st.success("Deleted successfully.")
                time.sleep(1)
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("Classroom X Ultimate Edition © 2025 | Developed for High-Performance Education")
