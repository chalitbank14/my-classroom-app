import streamlit as st
import pandas as pd
import altair as alt
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time
import json
import random

# ==============================================================================
# 1. SYSTEM CONFIGURATION & ADVANCED CSS FRAMEWORK
# ==============================================================================
st.set_page_config(
    page_title="Classroom OS: Ultimate",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ADVANCED STYLING ENGINE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&family=Prompt:wght@300;400;600&display=swap');
    
    :root {
        --primary: #4F46E5;
        --secondary: #10B981;
        --accent: #F59E0B;
        --danger: #EF4444;
        --bg-color: #F3F4F6;
        --glass: rgba(255, 255, 255, 0.90);
        --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }

    html, body, [class*="css"] {
        font-family: 'Sarabun', 'Prompt', sans-serif;
        background-color: var(--bg-color);
        color: #1F2937;
    }

    /* --- Custom Component: Hero Header --- */
    .hero-header {
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        padding: 1.5rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.4);
        position: relative;
        overflow: hidden;
    }
    .hero-pattern {
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        opacity: 0.1;
        background-image: radial-gradient(#fff 1px, transparent 1px);
        background-size: 20px 20px;
    }

    /* --- Custom Component: Glass Card --- */
    .glass-card {
        background: var(--glass);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255,255,255,0.6);
        border-radius: 16px;
        padding: 20px;
        box-shadow: var(--shadow);
        transition: all 0.3s ease;
        margin-bottom: 15px;
    }
    .glass-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    }

    /* --- UI Element: Rank Badge --- */
    .rank-badge-pill {
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* --- UI Element: Achievement Icon --- */
    .achievement-icon {
        font-size: 1.5rem;
        background: #FEF3C7;
        border-radius: 50%;
        width: 40px; height: 40px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin-right: 5px;
        border: 2px solid #FCD34D;
    }

    /* --- Mobile Optimization: Big Buttons --- */
    .stButton button {
        width: 100%;
        height: 55px;
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        border: none !important;
        transition: transform 0.1s !important;
    }
    .stButton button:active { transform: scale(0.96); }

    /* --- Tab Navigation Styling --- */
    .stTabs [data-baseweb="tab-list"] {
        background: white;
        padding: 5px;
        border-radius: 12px;
        box-shadow: var(--shadow);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #EEF2FF !important;
        color: #4F46E5 !important;
    }
    
    /* Progress Bar */
    div[data-testid="stProgressBar"] > div > div {
        background: linear-gradient(90deg, #4F46E5, #10B981);
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CORE BUSINESS LOGIC LAYERS (OOP)
# ==============================================================================

class GamificationEngine:
    """Core logic for Ranks and Achievements calculations."""
    
    def __init__(self):
        # Define Rank System
        self.ranks = [
            {"name": "PRESIDENT", "th": "👑 ประธานรุ่น", "min_xp": 1000, "color": "#F59E0B", "gradient": "linear-gradient(135deg, #F59E0B, #D97706)"},
            {"name": "DIRECTOR", "th": "💼 หัวหน้าฝ่าย", "min_xp": 600, "color": "#8B5CF6", "gradient": "linear-gradient(135deg, #8B5CF6, #6D28D9)"},
            {"name": "MANAGER", "th": "👔 หัวหน้าแผนก", "min_xp": 300, "color": "#3B82F6", "gradient": "linear-gradient(135deg, #3B82F6, #1D4ED8)"},
            {"name": "EMPLOYEE", "th": "👨‍💼 พนักงาน", "min_xp": 100, "color": "#10B981", "gradient": "linear-gradient(135deg, #10B981, #059669)"},
            {"name": "INTERN", "th": "👶 เด็กฝึกงาน", "min_xp": 0, "color": "#9CA3AF", "gradient": "linear-gradient(135deg, #9CA3AF, #4B5563)"}
        ]
        
        # Define Badges System
        self.badges_catalog = {
            "first_blood": {"icon": "🩸", "name": "First Blood", "desc": "คะแนนแรกของกลุ่ม"},
            "high_flyer":  {"icon": "🚀", "name": "High Flyer", "desc": "คะแนนรวมเกิน 500 XP"},
            "centurion":   {"icon": "💯", "name": "Perfect Score", "desc": "ได้คะแนน +100 ในครั้งเดียว"},
            "survivor":    {"icon": "🛡️", "name": "Survivor", "desc": "ถูกหักคะแนนแต่ยังรอดมาได้"},
            "legend":      {"icon": "👑", "name": "The Legend", "desc": "ถึงยศประธานรุ่น"}
        }

    def get_rank(self, xp):
        for rank in self.ranks:
            if xp >= rank['min_xp']: return rank
        return self.ranks[-1]

    def get_next_milestone(self, xp):
        """Calculate progress percentage to next rank."""
        for i, rank in enumerate(self.ranks):
            if xp >= rank['min_xp']:
                if i > 0: 
                    prev_rank = self.ranks[i-1]
                    total_needed = prev_rank['min_xp']
                    return prev_rank, min(1.0, xp / total_needed)
                return None, 1.0 # Max Rank
        return self.ranks[-2], xp/100.0

    def check_achievements(self, xp, history_log, current_badges):
        """Analyze history and XP to unlock new badges."""
        new_unlocks = []
        badges_list = json.loads(current_badges) if isinstance(current_badges, str) else []
        
        # 1. Check First Blood (History not empty)
        if len(history_log) > 0 and "first_blood" not in badges_list:
            new_unlocks.append("first_blood")
            
        # 2. Check High Flyer (XP > 500)
        if xp >= 500 and "high_flyer" not in badges_list:
            new_unlocks.append("high_flyer")
            
        # 3. Check Centurion (Any transaction >= 100)
        if "centurion" not in badges_list:
            for log in history_log:
                if log['amount'] >= 100:
                    new_unlocks.append("centurion")
                    break
        
        # 4. Check Legend (Rank Max)
        if xp >= 1000 and "legend" not in badges_list:
            new_unlocks.append("legend")

        return new_unlocks, badges_list + new_unlocks

class DataManager:
    """Handles Google Sheets Transactions with Robust Error Handling."""
    
    def __init__(self):
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
        except Exception as e:
            st.error(f"❌ Database Connection Failed: {e}")
            st.stop()

    def fetch_data(self):
        """Fetches and sanitizes data from Google Sheets."""
        try:
            # Read exact columns to prevent index errors
            df = self.conn.read(worksheet="Sheet1", usecols=list(range(7)), ttl=0)
            df = df.dropna(how='all')
            
            # Type Enforcement
            if 'XP' not in df.columns: df['XP'] = 0
            df['XP'] = pd.to_numeric(df['XP'], errors='coerce').fillna(0).astype(int)
            
            # Ensure JSON columns are strings
            for col in ['HistoryLog', 'Badges']:
                if col not in df.columns: df[col] = "[]"
                df[col] = df[col].fillna("[]").astype(str)
                
            return df
        except Exception:
            # Return skeleton DF if sheet is empty/broken
            cols = ['Room', 'GroupName', 'XP', 'Members', 'LastUpdated', 'HistoryLog', 'Badges']
            return pd.DataFrame(columns=cols)

    def commit_transaction(self, room, group_name, amount, reason, df, game_engine):
        """Executes a full transaction: Update XP, Log History, Check Badges."""
        idx = df[(df['Room'] == room) & (df['GroupName'] == group_name)].index
        
        if not idx.empty:
            i = idx[0]
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 1. Calculate new XP
            old_xp = df.at[i, 'XP']
            new_xp = max(0, old_xp + amount)
            
            # 2. Update History Log
            try:
                history = json.loads(df.at[i, 'HistoryLog'])
            except:
                history = []
            
            new_entry = {
                "ts": current_time,
                "reason": reason,
                "amount": amount,
                "balance": new_xp,
                "id": str(int(time.time()*1000)) # Unique Transaction ID
            }
            history.insert(0, new_entry) # Add to top
            
            # 3. Check Achievements
            new_badges, updated_badges_list = game_engine.check_achievements(
                new_xp, history, df.at[i, 'Badges']
            )
            
            # 4. Commit changes to DataFrame
            df.at[i, 'XP'] = new_xp
            df.at[i, 'LastUpdated'] = current_time
            df.at[i, 'HistoryLog'] = json.dumps(history, ensure_ascii=False)
            df.at[i, 'Badges'] = json.dumps(updated_badges_list, ensure_ascii=False)
            
            # 5. Push to Cloud
            self.conn.update(worksheet="Sheet1", data=df)
            st.cache_data.clear()
            
            return new_xp, old_xp, new_badges
        return None, None, []

    def create_group(self, room, name, members, df):
        if not ((df['Room'] == room) & (df['GroupName'] == name)).any():
            new_record = pd.DataFrame([{
                "Room": room,
                "GroupName": name,
                "XP": 0,
                "Members": members,
                "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "HistoryLog": "[]",
                "Badges": "[]"
            }])
            updated_df = pd.concat([df, new_record], ignore_index=True)
            self.conn.update(worksheet="Sheet1", data=updated_df)
            st.cache_data.clear()
            return True
        return False

    def remove_group(self, room, name, df):
        updated_df = df[~((df['Room'] == room) & (df['GroupName'] == name))]
        self.conn.update(worksheet="Sheet1", data=updated_df)
        st.cache_data.clear()

# Initialize Singletons
db = DataManager()
engine = GamificationEngine()

# ==============================================================================
# 3. UI RENDERERS (Modular UI Components)
# ==============================================================================

def render_hero_section(room_name):
    st.markdown(f"""
    <div class="hero-header">
        <div class="hero-pattern"></div>
        <div style="position:relative; z-index:1;">
            <h4 style="margin:0; opacity:0.8; text-transform:uppercase; letter-spacing:1px;">Classroom OS</h4>
            <h1 style="margin:5px 0 10px 0; font-size:2.2rem;">ห้องเรียน {room_name}</h1>
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="background:rgba(255,255,255,0.2); padding:2px 10px; border-radius:10px; font-size:0.8rem;">
                    🟢 Online
                </span>
                <span style="font-size:0.8rem; opacity:0.8;">
                    Sync: {datetime.now().strftime('%H:%M')}
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_group_card(rank, index, row, next_rank_info, progress_val):
    # Parse Badges
    try:
        badges = json.loads(row['Badges'])
    except:
        badges = []
        
    badge_html = ""
    for b in badges:
        if b in engine.badges_catalog:
            icon = engine.badges_catalog[b]['icon']
            badge_html += f"<span title='{engine.badges_catalog[b]['name']}'>{icon}</span> "

    st.markdown(f"""
    <div class="glass-card" style="border-left: 5px solid {rank['color']};">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
                <span style="font-size:0.8rem; font-weight:700; color:#9CA3AF; letter-spacing:1px;">RANK #{index}</span>
                <h3 style="margin:0; font-size:1.4rem; font-weight:700;">{row['GroupName']}</h3>
                <p style="margin:0; font-size:0.9rem; color:#6B7280;">👥 {row['Members']}</p>
                <div style="margin-top:8px;">{badge_html}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:1.8rem; font-weight:800; color:{rank['color']};">{row['XP']} <span style="font-size:1rem;">XP</span></div>
                <span class="rank-badge-pill" style="background:{rank['gradient']};">{rank['th']}</span>
            </div>
        </div>
        <div style="margin-top:15px;">
            <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#6B7280; margin-bottom:5px;">
                <span>Progress</span>
                <span>{next_rank_info['th'] if next_rank_info else 'MAX'}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(progress_val)

# ==============================================================================
# 4. MAIN APPLICATION FLOW
# ==============================================================================

# --- Sidebar Logic ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/9312/9312239.png", width=80)
    st.title("Admin Console")
    
    room_options = ["ม.1/1", "ม.1/2", "ม.1/10"]
    selected_room = st.selectbox("เลือกห้องเรียน", room_options)
    
    st.divider()
    
    # Export Data Feature
    df_raw = db.fetch_data()
    csv_data = df_raw.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Export CSV Report", csv_data, "classroom_data.csv", "text/csv")
    
    st.caption("v4.0.0 Ultra Enterprise")

# --- Main Logic ---
df = db.fetch_data()
room_df = df[df['Room'] == selected_room].copy()

render_hero_section(selected_room)

# Tabs Configuration
tabs = st.tabs(["⚡ Command Center", "🏆 Leaderboard", "📊 Analytics", "⚙️ Manage"])

# ------------------------------------------------------------------------------
# TAB 1: COMMAND CENTER (Mobile Optimized Actions)
# ------------------------------------------------------------------------------
with tabs[0]:
    if room_df.empty:
        st.info("💡 ห้องนี้ยังไม่มีกลุ่ม ไปที่แท็บ 'Manage' เพื่อสร้างกลุ่มก่อนครับ")
    else:
        # 1. Selector Section
        c_sel, c_info = st.columns([2, 1])
        with c_sel:
            target_group = st.selectbox("🎯 เลือกกลุ่มเป้าหมาย", room_df['GroupName'].unique())
        
        # Display Mini Info for Selected Group
        if target_group:
            g_data = room_df[room_df['GroupName'] == target_group].iloc[0]
            g_rank = engine.get_rank(g_data['XP'])
            with c_info:
                st.markdown(f"""
                <div style="background:white; padding:10px; border-radius:10px; border:1px solid #e5e7eb; text-align:center; margin-top:5px;">
                    <span style="font-size:0.8rem; color:grey;">Current XP</span>
                    <div style="font-weight:bold; color:{g_rank['color']}; font-size:1.2rem;">{g_data['XP']}</div>
                </div>
                """, unsafe_allow_html=True)

            st.write("") # Spacer

            # 2. Action Grid (Big Buttons)
            col_a, col_b = st.columns(2)
            
            def execute_xp(reason, amt):
                new_xp, old_xp, new_badges = db.commit_transaction(selected_room, target_group, amt, reason, df, engine)
                
                # Feedback System
                if amt > 0:
                    st.toast(f"✅ {target_group}: +{amt} XP ({reason})", icon="🔥")
                else:
                    st.toast(f"⚠️ {target_group}: {amt} XP ({reason})", icon="💢")
                
                # Check Level Up
                new_r = engine.get_rank(new_xp)
                old_r = engine.get_rank(old_xp)
                if new_r['min_xp'] > old_r['min_xp']:
                    st.balloons()
                    time.sleep(1)
                    st.success(f"🎉 **LEVEL UP!** กลุ่ม {target_group} เลื่อนยศเป็น {new_r['th']}!")
                
                # Check New Badges
                if new_badges:
                    for badge_id in new_badges:
                        b_info = engine.badges_catalog[badge_id]
                        st.success(f"🏆 **ACHIEVEMENT UNLOCKED:** {b_info['name']} {b_info['icon']}")
                        st.snow()
                
                time.sleep(0.5)
                st.rerun()

            with col_a:
                if st.button("📚 ส่งงานตรงเวลา (+50)", type="primary"): execute_xp("ส่งงานตรงเวลา", 50)
                if st.button("🙋 ตอบคำถาม (+20)"): execute_xp("ตอบคำถามในคาบ", 20)
                if st.button("💡 ไอเดียดีมาก (+30)"): execute_xp("เสนอไอเดียสร้างสรรค์", 30)
                if st.button("🏆 ชนะกิจกรรม (+100)"): execute_xp("ชนะกิจกรรมในห้อง", 100)

            with col_b:
                if st.button("🐢 ส่งงานช้า (-20)"): execute_xp("ส่งงานล่าช้า", -20)
                if st.button("📢 เสียงดัง (-10)"): execute_xp("คุยเสียงดัง/รบกวน", -10)
                if st.button("❌ ไม่ส่งงาน (-50)"): execute_xp("ไม่ส่งงานตามกำหนด", -50)
                if st.button("🗑️ ลืมอุปกรณ์ (-10)"): execute_xp("ไม่เตรียมอุปกรณ์", -10)

# ------------------------------------------------------------------------------
# TAB 2: LEADERBOARD & BADGES
# ------------------------------------------------------------------------------
with tabs[1]:
    if not room_df.empty:
        sorted_df = room_df.sort_values(by="XP", ascending=False).reset_index(drop=True)
        
        st.markdown("### 🏆 Hall of Fame")
        
        for i, row in sorted_df.iterrows():
            rank_data = engine.get_rank(row['XP'])
            next_r, progress = engine.get_next_milestone(row['XP'])
            render_group_card(rank_data, i+1, row, next_r, progress)

# ------------------------------------------------------------------------------
# TAB 3: ADVANCED ANALYTICS & HISTORY
# ------------------------------------------------------------------------------
with tabs[2]:
    if not room_df.empty:
        # A. Overview Metrics
        col_m1, col_m2, col_m3 = st.columns(3)
        top_grp = room_df.loc[room_df['XP'].idxmax()]
        col_m1.metric("🥇 Top Performer", top_grp['GroupName'], f"{top_grp['XP']} XP")
        col_m2.metric("📦 Active Groups", len(room_df))
        col_m3.metric("📊 Class Average", f"{int(room_df['XP'].mean())} XP")
        
        st.markdown("---")
        
        # B. Charts
        c_chart1, c_chart2 = st.columns([2, 1])
        
        with c_chart1:
            st.markdown("#### 📈 XP Distribution")
            bar = alt.Chart(room_df).mark_bar(cornerRadius=8).encode(
                x=alt.X('GroupName', sort='-y', title=None),
                y=alt.Y('XP'),
                color=alt.Color('XP', scale=alt.Scale(scheme='viridis'), legend=None),
                tooltip=['GroupName', 'XP', 'Members']
            ).properties(height=300)
            st.altair_chart(bar, use_container_width=True)
            
        with c_chart2:
            st.markdown("#### 🍰 Rank Composition")
            room_df['RankName'] = room_df['XP'].apply(lambda x: engine.get_rank(x)['th'])
            pie = alt.Chart(room_df).mark_arc(innerRadius=50).encode(
                theta="count()",
                color=alt.Color("RankName", title="Rank"),
                tooltip=["RankName", "count()"]
            ).properties(height=300)
            st.altair_chart(pie, use_container_width=True)

        # C. Detailed History Log
        st.markdown("### 📜 Audit Log (Transaction History)")
        group_filter = st.selectbox("Filter History by Group", ["All Groups"] + list(room_df['GroupName'].unique()))
        
        history_rows = []
        target_df = room_df if group_filter == "All Groups" else room_df[room_df['GroupName'] == group_filter]
        
        for _, r in target_df.iterrows():
            try:
                logs = json.loads(r['HistoryLog'])
                for log in logs:
                    log['GroupName'] = r['GroupName'] # Add group name to flat log
                    history_rows.append(log)
            except: pass
            
        if history_rows:
            hist_df = pd.DataFrame(history_rows)
            # Sort by timestamp (assuming 'ts' exists)
            hist_df = hist_df.sort_values(by="ts", ascending=False)
            
            st.dataframe(
                hist_df[['ts', 'GroupName', 'reason', 'amount', 'balance']],
                column_config={
                    "ts": "Timestamp",
                    "GroupName": "Group",
                    "reason": "Reason",
                    "amount": st.column_config.NumberColumn("Amount", format="%+d"),
                    "balance": "Balance"
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.caption("No transaction history found.")

# ------------------------------------------------------------------------------
# TAB 4: MANAGEMENT (CRUD)
# ------------------------------------------------------------------------------
with tabs[3]:
    st.markdown("### ⚙️ Group Management")
    
    col_new, col_del = st.columns(2)
    
    with col_new:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("#### ➕ Create New Group")
        with st.form("create_grp"):
            n_name = st.text_input("Group Name")
            n_mem = st.text_area("Members List")
            if st.form_submit_button("Create Group", type="primary"):
                if n_name:
                    if db.create_group(selected_room, n_name, n_mem, df):
                        st.success(f"Group '{n_name}' created!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Duplicate Group Name!")
                else:
                    st.warning("Please enter a name.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_del:
        st.markdown('<div class="glass-card" style="border:1px solid #FECACA;">', unsafe_allow_html=True)
        st.markdown("#### 🗑️ Delete Group")
        del_target = st.selectbox("Select Group", ["-"] + list(room_df['GroupName'].unique()))
        
        if del_target != "-":
            st.warning(f"⚠️ Warning: This will permanently delete '{del_target}' and all its history.")
            if st.button("Confirm Deletion", type="secondary"):
                db.remove_group(selected_room, del_target, df)
                st.success("Deleted successfully.")
                time.sleep(1)
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("<div style='text-align:center; color:grey; font-size:0.8rem;'>Classroom OS v4.0 Ultra | Powered by Streamlit</div>", unsafe_allow_html=True)
