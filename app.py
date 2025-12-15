import streamlit as st
import pandas as pd
import altair as alt
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time
import json
import uuid
import random

# ==============================================================================
# 1. CORE SYSTEM CONFIGURATION (การตั้งค่าระบบขั้นสูง)
# ==============================================================================
st.set_page_config(
    page_title="Classroom OS: Architect",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed" # ซ่อนเมนูข้างเพื่อความสะอาดตา
)

# --- ADVANCED CSS & THEME ENGINE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&family=Prompt:wght@300;400;600&family=JetBrains+Mono:wght@400&display=swap');
    
    :root {
        --primary: #4338ca;
        --secondary: #059669;
        --danger: #dc2626;
        --bg-color: #f8fafc;
        --card-bg: rgba(255, 255, 255, 0.95);
        --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
        --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
    }

    html, body, [class*="css"] {
        font-family: 'Sarabun', 'Prompt', sans-serif;
        background-color: var(--bg-color);
        color: #1e293b;
    }

    /* --- HERO HEADER --- */
    .hero-container {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: var(--shadow-lg);
        position: relative;
        overflow: hidden;
    }
    .hero-stat {
        background: rgba(255,255,255,0.1);
        padding: 10px 20px;
        border-radius: 12px;
        backdrop-filter: blur(5px);
        border: 1px solid rgba(255,255,255,0.2);
    }

    /* --- GLASS CARD SYSTEM --- */
    .glass-card {
        background: var(--card-bg);
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid #e2e8f0;
        box-shadow: var(--shadow-md);
        margin-bottom: 1rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-lg);
    }

    /* --- NEGATIVE SCORE ALERT --- */
    .negative-score {
        color: #dc2626;
        font-weight: 800;
        text-shadow: 0 0 10px rgba(220, 38, 38, 0.2);
    }
    .positive-score {
        color: #16a34a;
        font-weight: 800;
    }

    /* --- RANK BADGES --- */
    .rank-pill {
        display: inline-flex;
        align-items: center;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: white;
    }

    /* --- MOBILE OPTIMIZATION --- */
    .stButton button {
        width: 100%;
        height: 56px;
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        border: none !important;
        box-shadow: var(--shadow-sm);
        transition: all 0.2s;
    }
    .stButton button:hover {
        transform: scale(1.02);
        box-shadow: var(--shadow-md);
    }
    
    /* --- TABS --- */
    .stTabs [data-baseweb="tab-list"] {
        background: white;
        padding: 8px;
        border-radius: 16px;
        box-shadow: var(--shadow-sm);
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        font-weight: 600;
        color: #64748b;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e0e7ff !important;
        color: #4338ca !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. BUSINESS LOGIC ENGINE (OOP)
# ==============================================================================

class RankSystem:
    """Manages Ranks, Negative Scores Logic, and Progress Calculations."""
    def __init__(self):
        self.ranks = [
            {"name": "PRESIDENT", "th": "👑 ประธานรุ่น", "min_xp": 1000, "color": "#F59E0B", "bg": "linear-gradient(to right, #F59E0B, #B45309)"},
            {"name": "DIRECTOR", "th": "💼 หัวหน้าฝ่าย", "min_xp": 600, "color": "#8B5CF6", "bg": "linear-gradient(to right, #8B5CF6, #6D28D9)"},
            {"name": "MANAGER", "th": "👔 หัวหน้าแผนก", "min_xp": 300, "color": "#3B82F6", "bg": "linear-gradient(to right, #3B82F6, #1E40AF)"},
            {"name": "EMPLOYEE", "th": "👨‍💼 พนักงาน", "min_xp": 100, "color": "#10B981", "bg": "linear-gradient(to right, #10B981, #047857)"},
            {"name": "INTERN", "th": "👶 เด็กฝึกงาน", "min_xp": 0, "color": "#64748B", "bg": "linear-gradient(to right, #94A3B8, #475569)"},
            # Special Rank for Negative Scores
            {"name": "PROBATION", "th": "⚠️ ทัณฑ์บน (ติดลบ)", "min_xp": -999999, "color": "#DC2626", "bg": "linear-gradient(to right, #EF4444, #991B1B)"}
        ]

    def get_rank(self, xp):
        """Returns rank object based on XP."""
        # Check normal ranks
        for rank in self.ranks:
            if xp >= rank['min_xp'] and rank['name'] != "PROBATION":
                return rank
        # Fallback for negative scores
        return self.ranks[-1]

    def get_progress_stats(self, xp):
        """Calculates progress to next level."""
        # Handle Negative XP
        if xp < 0:
            return 0.0, "Need positive XP to rank up"
        
        for i, rank in enumerate(self.ranks):
            if xp >= rank['min_xp'] and rank['name'] != "PROBATION":
                if i > 0: # Not max rank
                    prev_rank = self.ranks[i-1]
                    target = prev_rank['min_xp']
                    progress = min(1.0, xp / target)
                    return progress, f"Next: {prev_rank['th']} ({xp}/{target})"
                else: # Max Rank
                    return 1.0, "MAX LEVEL REACHED"
        return 0.0, "System Error"

class AchievementEngine:
    """Manages Badges and Special Unlocks."""
    def __init__(self):
        self.badges_db = {
            "first_blood": {"icon": "🩸", "name": "First Blood", "desc": "รายการคะแนนแรก"},
            "wealthy": {"icon": "💰", "name": "Wealthy", "desc": "คะแนนรวมเกิน 800 XP"},
            "debtor": {"icon": "💸", "name": "In Debt", "desc": "คะแนนติดลบ"},
            "sniper": {"icon": "🎯", "name": "Big Shot", "desc": "ได้คะแนน +100 ในครั้งเดียว"},
            "phoenix": {"icon": "🔥", "name": "Phoenix", "desc": "กลับมาจากติดลบจนเป็นบวก"}
        }

    def check_unlocks(self, xp, history):
        unlocked = []
        if not history: return []
        
        # 1. First Blood
        if len(history) > 0: unlocked.append("first_blood")
        # 2. Wealthy
        if xp >= 800: unlocked.append("wealthy")
        # 3. Debtor
        if xp < 0: unlocked.append("debtor")
        # 4. Big Shot
        for log in history:
            if log.get('amount', 0) >= 100: unlocked.append("sniper")
        # 5. Phoenix (Check history trend)
        has_been_negative = any(log.get('balance', 0) < 0 for log in history)
        if has_been_negative and xp > 0: unlocked.append("phoenix")
            
        return list(set(unlocked))

class DatabaseController:
    """Handles Google Sheets with Transaction Logs & Re-balancing."""
    
    def __init__(self):
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
        except Exception as e:
            st.error(f"❌ Database Error: {e}")
            st.stop()

    def fetch_data(self):
        """Reads and cleans data."""
        try:
            df = self.conn.read(worksheet="Sheet1", usecols=list(range(7)), ttl=0)
            df = df.dropna(how='all')
            # Data Type Enforcement
            if 'XP' not in df.columns: df['XP'] = 0
            df['XP'] = pd.to_numeric(df['XP'], errors='coerce').fillna(0).astype(int)
            for col in ['HistoryLog', 'Badges']:
                if col not in df.columns: df[col] = "[]"
                df[col] = df[col].fillna("[]").astype(str)
            return df
        except:
            return pd.DataFrame(columns=['Room', 'GroupName', 'XP', 'Members', 'LastUpdated', 'HistoryLog', 'Badges'])

    def commit_update(self, df):
        self.conn.update(worksheet="Sheet1", data=df)
        st.cache_data.clear()

    def add_transaction(self, room, group_name, amount, reason, df, engine):
        """Adds a log and updates balance (Allowing Negatives)."""
        idx = df[(df['Room'] == room) & (df['GroupName'] == group_name)].index
        if not idx.empty:
            i = idx[0]
            # Load History
            try: history = json.loads(df.at[i, 'HistoryLog'])
            except: history = []
            
            # Create Transaction Object
            tx_id = str(uuid.uuid4())[:8]
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Recalculate Balance
            # Note: We append new log, then recalc sum from scratch for accuracy
            new_log = {
                "id": tx_id,
                "ts": current_time,
                "reason": reason,
                "amount": int(amount)
                # 'balance' will be calculated dynamically for display
            }
            history.insert(0, new_log)
            
            # Calculate Total XP (Sum of all amounts)
            total_xp = sum(item['amount'] for item in history)
            # IMPORTANT: NO max(0, ...) here. Allows negative scores.
            
            # Check Badges
            badges = engine.check_unlocks(total_xp, history)
            
            # Update Log with current running balance (for analytics)
            history[0]['balance'] = total_xp 
            
            # Save to DF
            df.at[i, 'XP'] = total_xp
            df.at[i, 'HistoryLog'] = json.dumps(history, ensure_ascii=False)
            df.at[i, 'Badges'] = json.dumps(badges, ensure_ascii=False)
            df.at[i, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            self.commit_update(df)
            return total_xp, badges
        return None, None

    def power_edit_history(self, room, group_name, edited_df, df, engine):
        """Replaces history with edited version and re-balances."""
        idx = df[(df['Room'] == room) & (df['GroupName'] == group_name)].index
        if not idx.empty:
            i = idx[0]
            # Convert DF back to JSON structure
            new_history = edited_df.to_dict('records')
            
            # Recalculate Total
            total_xp = sum(int(item['amount']) for item in new_history)
            
            # Recalculate Running Balances for Charts
            running_bal = 0
            # Sort by time asc for calculation, then desc for storage
            sorted_hist = sorted(new_history, key=lambda x: x['ts'])
            for log in sorted_hist:
                running_bal += int(log['amount'])
                log['balance'] = running_bal
            
            final_history = sorted(sorted_hist, key=lambda x: x['ts'], reverse=True)
            
            badges = engine.check_unlocks(total_xp, final_history)
            
            df.at[i, 'XP'] = total_xp
            df.at[i, 'HistoryLog'] = json.dumps(final_history, ensure_ascii=False)
            df.at[i, 'Badges'] = json.dumps(badges, ensure_ascii=False)
            
            self.commit_update(df)
            return True
        return False

    def create_group(self, room, name, members, df):
        if not ((df['Room'] == room) & (df['GroupName'] == name)).any():
            new_row = pd.DataFrame([{
                "Room": room, "GroupName": name, "XP": 0, "Members": members,
                "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "HistoryLog": "[]", "Badges": "[]"
            }])
            self.commit_update(pd.concat([df, new_row], ignore_index=True))
            return True
        return False

    def delete_group(self, room, name, df):
        self.commit_update(df[~((df['Room'] == room) & (df['GroupName'] == name))])

# Initialize
db = DatabaseController()
rank_engine = RankSystem()
badge_engine = AchievementEngine()

# ==============================================================================
# 3. UI RENDERING & PAGE LOGIC
# ==============================================================================

# --- Sidebar ---
with st.sidebar:
    st.title("Admin Panel")
    all_rooms = ["ม.1/1", "ม.1/2", "ม.1/10"]
    selected_room = st.selectbox("เลือกห้องเรียน", all_rooms)
    
    st.divider()
    df_raw = db.fetch_data()
    st.download_button("📥 Export CSV", df_raw.to_csv(index=False).encode('utf-8'), "data.csv", "text/csv")

# --- Load Data ---
df = db.fetch_data()
room_df = df[df['Room'] == selected_room].copy()

# --- Header ---
st.markdown(f"""
<div class="hero-container">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <h4 style="margin:0; opacity:0.8; letter-spacing:1px;">CLASSROOM OS: ARCHITECT</h4>
            <h1 style="margin:0; font-size:2.5rem; font-weight:800;">{selected_room}</h1>
        </div>
        <div style="text-align:right;">
             <div class="hero-stat">
                <span style="font-size:0.8rem;">TOTAL GROUPS</span><br>
                <span style="font-size:1.5rem; font-weight:bold;">{len(room_df)}</span>
             </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Tabs ---
tabs = st.tabs(["⚡ Command Center", "🏆 Rankings", "📈 Analytics", "🛠️ Editor & Settings"])

# ------------------------------------------------------------------------------
# TAB 1: COMMAND CENTER (GIVE POINTS)
# ------------------------------------------------------------------------------
with tabs[0]:
    if room_df.empty:
        st.warning("⚠️ No groups found. Go to 'Settings' to create one.")
    else:
        # Selector
        c_sel, c_stat = st.columns([2, 1])
        with c_sel:
            target = st.selectbox("🎯 Target Group", room_df['GroupName'].unique())
        
        # Display Current Status
        if target:
            g_data = room_df[room_df['GroupName'] == target].iloc[0]
            g_rank = rank_engine.get_rank(g_data['XP'])
            xp_class = "negative-score" if g_data['XP'] < 0 else "positive-score"
            
            with c_stat:
                st.markdown(f"""
                <div style="background:white; padding:10px; border-radius:10px; text-align:center; border:1px solid #e2e8f0; margin-top:5px;">
                    <div style="font-size:0.8rem; color:gray;">Current Balance</div>
                    <div class="{xp_class}" style="font-size:1.8rem;">{g_data['XP']} XP</div>
                    <span class="rank-pill" style="background:{g_rank['bg']}">{g_rank['th']}</span>
                </div>
                """, unsafe_allow_html=True)

            st.write("") # Spacer

            # Action Grid
            c1, c2 = st.columns(2)
            
            def execute(reason, amount):
                xp, b = db.add_transaction(selected_room, target, amount, reason, df, badge_engine)
                
                # Dynamic Feedback
                if amount > 0:
                    st.toast(f"✅ Added {amount} XP to {target}", icon="💰")
                else:
                    st.toast(f"💢 Deducted {abs(amount)} XP from {target}", icon="📉")
                
                # Check Badges
                if b:
                    st.success(f"🏅 Badges Updated: {len(b)} total")
                
                time.sleep(0.5)
                st.rerun()

            with c1:
                if st.button("📚 ส่งงานตรงเวลา (+50)", type="primary"): execute("ส่งงานตรงเวลา", 50)
                if st.button("🙋 ตอบคำถาม (+20)"): execute("ตอบคำถามในคาบ", 20)
                if st.button("💡 ความคิดสร้างสรรค์ (+30)"): execute("ไอเดียสร้างสรรค์", 30)
                if st.button("🏆 ชนะกิจกรรม (+100)"): execute("ชนะกิจกรรม", 100)
            
            with c2:
                if st.button("🐢 ส่งงานช้า (-20)"): execute("ส่งงานล่าช้า", -20)
                if st.button("📢 คุยเสียงดัง (-10)"): execute("คุยเสียงดัง/รบกวน", -10)
                if st.button("❌ ไม่ส่งงาน (-50)"): execute("ไม่ส่งงาน", -50)
                if st.button("🗑️ ลืมอุปกรณ์ (-10)"): execute("ไม่เตรียมอุปกรณ์", -10)

# ------------------------------------------------------------------------------
# TAB 2: LEADERBOARDS
# ------------------------------------------------------------------------------
with tabs[1]:
    if not room_df.empty:
        # Sort by XP descending
        sorted_df = room_df.sort_values(by="XP", ascending=False).reset_index(drop=True)
        
        for i, row in sorted_df.iterrows():
            rank = rank_engine.get_rank(row['XP'])
            progress, prog_label = rank_engine.get_progress_stats(row['XP'])
            xp_style = "color:#dc2626;" if row['XP'] < 0 else f"color:{rank['color']};"
            
            # Badges HTML
            try: bdgs = json.loads(row['Badges'])
            except: bdgs = []
            badge_html = "".join([f"<span title='{badge_engine.badges_db[b]['name']}'>{badge_engine.badges_db[b]['icon']}</span> " for b in bdgs if b in badge_engine.badges_db])
            
            st.markdown(f"""
            <div class="glass-card" style="border-left: 5px solid {rank['color']};">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                        <div style="font-size:0.8rem; font-weight:700; color:#94a3b8;">RANK #{i+1}</div>
                        <h3 style="margin:0; font-size:1.4rem;">{row['GroupName']}</h3>
                        <div style="color:#64748b; font-size:0.9rem;">👥 {row['Members']}</div>
                        <div style="margin-top:5px; font-size:1.2rem;">{badge_html}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:1.8rem; font-weight:800; {xp_style}">{row['XP']} XP</div>
                        <span class="rank-pill" style="background:{rank['bg']}">{rank['th']}</span>
                    </div>
                </div>
                <div style="margin-top:10px; font-size:0.8rem; color:#64748b; display:flex; justify-content:space-between;">
                    <span>Progress</span><span>{prog_label}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(progress)

# ------------------------------------------------------------------------------
# TAB 3: ANALYTICS (TRENDS)
# ------------------------------------------------------------------------------
with tabs[2]:
    if not room_df.empty:
        st.subheader("📈 Performance Analytics")
        
        # Select Group for Deep Dive
        ana_target = st.selectbox("Select Group to Analyze", room_df['GroupName'].unique())
        
        # Process History for Chart
        g_data = room_df[room_df['GroupName'] == ana_target].iloc[0]
        try:
            history = json.loads(g_data['HistoryLog'])
            hist_df = pd.DataFrame(history)
            if not hist_df.empty:
                # Ensure datetime format
                hist_df['ts'] = pd.to_datetime(hist_df['ts'])
                hist_df = hist_df.sort_values('ts')
                
                # Create Line Chart
                chart = alt.Chart(hist_df).mark_line(point=True, interpolate='step-after').encode(
                    x=alt.X('ts', title='Time', axis=alt.Axis(format='%H:%M')),
                    y=alt.Y('balance', title='XP Balance'),
                    tooltip=['ts', 'reason', 'amount', 'balance'],
                    color=alt.value('#4338ca')
                ).properties(height=300)
                
                st.altair_chart(chart, use_container_width=True)
                
                # Transaction Table
                st.markdown("##### 📜 Transaction History")
                st.dataframe(
                    hist_df[['ts', 'reason', 'amount', 'balance']].sort_values('ts', ascending=False),
                    column_config={
                        "ts": "Timestamp",
                        "reason": "Activity",
                        "amount": st.column_config.NumberColumn("Change", format="%+d"),
                        "balance": "Total"
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No transaction history available.")
        except Exception as e:
            st.error(f"Error parsing history: {e}")

# ------------------------------------------------------------------------------
# TAB 4: ADVANCED EDITOR (CRUD + RE-BALANCE)
# ------------------------------------------------------------------------------
with tabs[3]:
    st.subheader("🛠️ Management Console")
    
    with st.expander("📝 Create / Delete Groups", expanded=True):
        c_add, c_del = st.columns(2)
        with c_add:
            with st.form("create_grp"):
                n = st.text_input("New Group Name")
                m = st.text_area("Members")
                if st.form_submit_button("Create Group"):
                    if db.create_group(selected_room, n, m, df):
                        st.success("Created!"); st.rerun()
                    else: st.error("Name exists!")
        with c_del:
            d_t = st.selectbox("Select Group to Delete", ["-"]+list(room_df['GroupName'].unique()))
            if d_t != "-" and st.button("Confirm Delete", type="primary"):
                db.delete_group(selected_room, d_t, df)
                st.rerun()

    st.markdown("---")
    st.markdown("#### ⚡ Power Editor (Edit Scores & History)")
    st.info("💡 You can edit past transactions here. The system will automatically recalculate the total score.")
    
    edit_grp = st.selectbox("Select Group to Edit", room_df['GroupName'].unique(), key="pe_sel")
    
    if edit_grp:
        grp_row = room_df[room_df['GroupName'] == edit_grp].iloc[0]
        try:
            h_data = json.loads(grp_row['HistoryLog'])
            h_df = pd.DataFrame(h_data) if h_data else pd.DataFrame(columns=['ts', 'reason', 'amount'])
        except:
            h_df = pd.DataFrame(columns=['ts', 'reason', 'amount'])
            
        # DATA EDITOR
        edited_h = st.data_editor(
            h_df,
            column_config={
                "ts": st.column_config.TextColumn("Timestamp (YYYY-MM-DD HH:MM:SS)"),
                "reason": "Reason",
                "amount": st.column_config.NumberColumn("XP Amount", format="%d"),
                "id": None, "balance": None
            },
            num_rows="dynamic",
            use_container_width=True,
            key="data_editor_history"
        )
        
        if st.button("💾 Save & Recalculate Balance"):
            if db.power_edit_history(selected_room, edit_grp, edited_h, df, badge_engine):
                st.success("✅ History updated & Balance recalculated successfully!")
                time.sleep(1)
                st.rerun()
