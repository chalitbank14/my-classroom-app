import streamlit as st
import pandas as pd
import altair as alt
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time
import json
import uuid

# ==============================================================================
# 1. SYSTEM CONFIGURATION & ADVANCED CSS
# ==============================================================================
st.set_page_config(
    page_title="Classroom OS: Architect",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- THEME ENGINE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&family=Prompt:wght@300;400;600&display=swap');
    
    :root {
        --primary: #4F46E5;
        --danger: #EF4444;
        --success: #10B981;
        --bg-color: #F8FAFC;
        --card-bg: #FFFFFF;
    }

    html, body, [class*="css"] {
        font-family: 'Sarabun', 'Prompt', sans-serif;
        background-color: var(--bg-color);
        color: #1E293B;
    }

    /* Hero Header */
    .hero-container {
        background: linear-gradient(135deg, #312E81 0%, #4338CA 100%);
        padding: 2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    
    /* Glass Cards */
    .glass-card {
        background: var(--card-bg);
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
        transition: transform 0.2s;
    }
    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }

    /* Mobile Buttons */
    .stButton button {
        width: 100%;
        height: 55px;
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
    }

    /* Status Colors */
    .status-probation { color: #DC2626; font-weight: 800; }
    .status-normal { color: #059669; font-weight: 800; }

    /* Badges */
    .badge-icon {
        font-size: 1.2rem;
        margin-right: 4px;
        cursor: help;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: white;
        padding: 8px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. BUSINESS LOGIC (OOP)
# ==============================================================================

class RankSystem:
    def __init__(self):
        self.ranks = [
            {"name": "PRESIDENT", "th": "👑 ประธานรุ่น", "min_xp": 1000, "color": "#F59E0B", "bg": "#FEF3C7"},
            {"name": "DIRECTOR", "th": "💼 หัวหน้าฝ่าย", "min_xp": 600, "color": "#8B5CF6", "bg": "#F3E8FF"},
            {"name": "MANAGER", "th": "👔 หัวหน้าแผนก", "min_xp": 300, "color": "#3B82F6", "bg": "#DBEAFE"},
            {"name": "EMPLOYEE", "th": "👨‍💼 พนักงาน", "min_xp": 100, "color": "#10B981", "bg": "#D1FAE5"},
            {"name": "INTERN", "th": "👶 เด็กฝึกงาน", "min_xp": 0, "color": "#64748B", "bg": "#F1F5F9"},
            {"name": "PROBATION", "th": "⚠️ ทัณฑ์บน (ติดลบ)", "min_xp": -99999, "color": "#EF4444", "bg": "#FEE2E2"}
        ]

    def get_rank(self, xp):
        # ถ้าติดลบ ให้คืนค่า Probation ทันที
        if xp < 0:
            return self.ranks[-1]
            
        for rank in self.ranks:
            if rank['name'] != "PROBATION" and xp >= rank['min_xp']:
                return rank
        return self.ranks[-2] # Default Intern

    def get_progress(self, xp):
        if xp < 0: return 0.0, "Need positive XP"
        
        for i, rank in enumerate(self.ranks):
            if rank['name'] != "PROBATION" and xp >= rank['min_xp']:
                if i > 0:
                    prev_rank = self.ranks[i-1]
                    target = prev_rank['min_xp']
                    return min(1.0, xp/target), f"Next: {prev_rank['th']} ({xp}/{target})"
                return 1.0, "MAX LEVEL"
        return 0.0, "0%"

class AchievementEngine:
    def __init__(self):
        self.badges = {
            "first_blood": {"icon": "🩸", "name": "First Blood", "desc": "คะแนนแรก"},
            "wealthy": {"icon": "💎", "name": "Wealthy", "desc": "800+ XP"},
            "debtor": {"icon": "💸", "name": "In Debt", "desc": "คะแนนติดลบ"},
            "sniper": {"icon": "🎯", "name": "Big Shot", "desc": "+100 ในครั้งเดียว"},
            "phoenix": {"icon": "🔥", "name": "Phoenix", "desc": "กลับมาจากติดลบ"}
        }

    def check(self, xp, history):
        unlocked = []
        if not history: return []
        
        if len(history) > 0: unlocked.append("first_blood")
        if xp >= 800: unlocked.append("wealthy")
        if xp < 0: unlocked.append("debtor")
        
        has_negative = False
        for log in history:
            if log['amount'] >= 100: unlocked.append("sniper")
            if log.get('balance', 0) < 0: has_negative = True
            
        if has_negative and xp > 0: unlocked.append("phoenix")
        return list(set(unlocked))

class DataManager:
    """Fixed Data Manager to prevent UnsupportedOperationError"""
    
    def __init__(self):
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
            self.cols = ['Room', 'GroupName', 'XP', 'Members', 'LastUpdated', 'HistoryLog', 'Badges']
        except Exception as e:
            st.error(f"DB Error: {e}")
            st.stop()

    def fetch_data(self):
        try:
            df = self.conn.read(worksheet="Sheet1", ttl=0)
            
            # ถ้า Sheet ว่าง หรือ column ไม่ครบ ให้คืน DataFrame เปล่าตามโครงสร้าง
            if df.empty or not set(self.cols).issubset(df.columns):
                return pd.DataFrame(columns=self.cols)
            
            # เลือกเฉพาะ Column ที่ใช้
            df = df[self.cols].copy()
            df = df.dropna(how='all')
            
            # แปลง Type
            df['XP'] = pd.to_numeric(df['XP'], errors='coerce').fillna(0).astype(int)
            for c in ['HistoryLog', 'Badges']:
                df[c] = df[c].fillna("[]").astype(str)
                
            return df
        except Exception:
            return pd.DataFrame(columns=self.cols)

    def save(self, df):
        self.conn.update(worksheet="Sheet1", data=df)
        st.cache_data.clear()

    def add_transaction(self, room, group, amount, reason, df, engine):
        idx = df[(df['Room'] == room) & (df['GroupName'] == group)].index
        if not idx.empty:
            i = idx[0]
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try: history = json.loads(df.at[i, 'HistoryLog'])
            except: history = []
            
            new_log = {
                "id": str(uuid.uuid4())[:8],
                "ts": current_time,
                "reason": reason,
                "amount": int(amount)
            }
            history.insert(0, new_log)
            
            # Recalc Balance (Allow Negative)
            total_xp = sum(item['amount'] for item in history)
            history[0]['balance'] = total_xp
            
            badges = engine.check(total_xp, history)
            
            df.at[i, 'XP'] = total_xp
            df.at[i, 'HistoryLog'] = json.dumps(history, ensure_ascii=False)
            df.at[i, 'Badges'] = json.dumps(badges, ensure_ascii=False)
            df.at[i, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            self.save(df)
            return total_xp, badges
        return None, None

    def create_group(self, room, name, members, df):
        if not ((df['Room'] == room) & (df['GroupName'] == name)).any():
            new_row = pd.DataFrame([{
                "Room": room,
                "GroupName": name,
                "XP": 0,
                "Members": members,
                "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "HistoryLog": "[]",
                "Badges": "[]"
            }])
            # Concat and Save
            updated_df = pd.concat([df, new_row], ignore_index=True)
            self.save(updated_df)
            return True
        return False

    def power_edit(self, room, group, edited_df, df, engine):
        idx = df[(df['Room'] == room) & (df['GroupName'] == group)].index
        if not idx.empty:
            i = idx[0]
            # Convert DF back to list
            new_hist = edited_df.to_dict('records')
            
            # Recalc Everything
            total_xp = sum(int(x['amount']) for x in new_hist)
            
            # Recalc running balance for chart correctness
            run_bal = 0
            sorted_hist = sorted(new_hist, key=lambda x: x['ts'])
            for log in sorted_hist:
                run_bal += int(log['amount'])
                log['balance'] = run_bal
            
            final_hist = sorted(sorted_hist, key=lambda x: x['ts'], reverse=True)
            badges = engine.check(total_xp, final_hist)
            
            df.at[i, 'XP'] = total_xp
            df.at[i, 'HistoryLog'] = json.dumps(final_hist, ensure_ascii=False)
            df.at[i, 'Badges'] = json.dumps(badges, ensure_ascii=False)
            
            self.save(df)
            return True
        return False

    def delete_group(self, room, name, df):
        updated = df[~((df['Room'] == room) & (df['GroupName'] == name))]
        self.save(updated)

# Initialize
db = DataManager()
rank_sys = RankSystem()
ach_sys = AchievementEngine()

# ==============================================================================
# 3. UI LAYER
# ==============================================================================

# Sidebar
with st.sidebar:
    st.title("Admin Panel")
    selected_room = st.selectbox("เลือกห้องเรียน", ["ม.1/1", "ม.1/2", "ม.1/10"])
    
    st.divider()
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    raw_df = db.fetch_data()
    st.download_button("📥 Export CSV", raw_df.to_csv(index=False).encode('utf-8'), "data.csv")

# Main Data Load
df = db.fetch_data()
room_df = df[df['Room'] == selected_room].copy()

# Hero
st.markdown(f"""
<div class="hero-container">
    <h4 style="margin:0; opacity:0.8;">CLASSROOM OS: ARCHITECT</h4>
    <h1 style="margin:0; font-size:2.5rem;">{selected_room}</h1>
    <p style="margin:5px 0 0 0; opacity:0.9;">Total Groups: {len(room_df)}</p>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["⚡ Command Center", "🏆 Rankings", "📈 Analytics", "🛠️ Settings"])

# --- TAB 1: COMMAND CENTER ---
with tabs[0]:
    if room_df.empty:
        st.warning("⚠️ No groups found. Go to 'Settings' to create groups.")
    else:
        c_sel, c_stat = st.columns([2, 1])
        with c_sel:
            target = st.selectbox("🎯 Select Target", room_df['GroupName'].unique())
            
        if target:
            g_dat = room_df[room_df['GroupName'] == target].iloc[0]
            g_rnk = rank_sys.get_rank(g_dat['XP'])
            xp_cls = "status-probation" if g_dat['XP'] < 0 else "status-normal"
            
            with c_stat:
                st.markdown(f"""
                <div style="background:white; padding:15px; border-radius:12px; border:1px solid #e2e8f0; text-align:center;">
                    <div style="font-size:0.8rem; color:grey;">CURRENT BALANCE</div>
                    <div class="{xp_cls}" style="font-size:2rem;">{g_dat['XP']} XP</div>
                    <span style="background:{g_rnk['bg']}; color:{g_rnk['color']}; padding:2px 8px; border-radius:10px; font-weight:bold; font-size:0.8rem;">{g_rnk['th']}</span>
                </div>
                """, unsafe_allow_html=True)
            
            st.write("")
            c1, c2 = st.columns(2)
            
            def run_tx(rsn, amt):
                nxp, bdg = db.add_transaction(selected_room, target, amt, rsn, df, ach_sys)
                st.toast(f"{target}: {amt:+d} ({rsn})", icon="✅")
                time.sleep(0.5)
                st.rerun()

            with c1:
                if st.button("📚 ส่งงาน (+50)", type="primary"): run_tx("ส่งงานตรงเวลา", 50)
                if st.button("🙋 ตอบคำถาม (+20)"): run_tx("ตอบคำถาม", 20)
                if st.button("💡 ไอเดียดี (+30)"): run_tx("ความคิดสร้างสรรค์", 30)
                if st.button("🏆 ชนะเกม (+100)"): run_tx("ชนะกิจกรรม", 100)
            with c2:
                if st.button("🐢 ส่งช้า (-20)"): run_tx("ส่งงานล่าช้า", -20)
                if st.button("📢 เสียงดัง (-10)"): run_tx("คุยเสียงดัง", -10)
                if st.button("❌ ไม่ส่งงาน (-50)"): run_tx("ไม่ส่งงาน", -50)
                if st.button("🗑️ ลืมของ (-10)"): run_tx("ลืมอุปกรณ์", -10)

# --- TAB 2: RANKINGS ---
with tabs[1]:
    if not room_df.empty:
        sorted_df = room_df.sort_values("XP", ascending=False).reset_index(drop=True)
        for i, row in sorted_df.iterrows():
            rnk = rank_sys.get_rank(row['XP'])
            prog, prog_lbl = rank_sys.get_progress(row['XP'])
            
            # Badges
            try: bdgs = json.loads(row['Badges'])
            except: bdgs = []
            icons = "".join([f"<span title='{ach_sys.badges[b]['name']}'>{ach_sys.badges[b]['icon']}</span>" for b in bdgs if b in ach_sys.badges])
            
            xp_color = "#DC2626" if row['XP'] < 0 else rnk['color']
            
            st.markdown(f"""
            <div class="glass-card" style="border-left: 5px solid {rnk['color']};">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                        <div style="font-size:0.8rem; font-weight:bold; color:#94A3B8;">RANK #{i+1}</div>
                        <h3 style="margin:0;">{row['GroupName']}</h3>
                        <small style="color:#64748B;">{row['Members']}</small>
                        <div style="margin-top:5px; font-size:1.2rem;">{icons}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:1.8rem; font-weight:800; color:{xp_color}">{row['XP']} XP</div>
                        <span style="background:{rnk['bg']}; color:{rnk['color']}; padding:2px 8px; border-radius:10px; font-weight:bold; font-size:0.75rem;">{rnk['th']}</span>
                    </div>
                </div>
                <div style="margin-top:10px; display:flex; justify-content:space-between; font-size:0.75rem; color:#64748B;">
                    <span>Progress</span><span>{prog_lbl}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(prog)

# --- TAB 3: ANALYTICS ---
with tabs[2]:
    if not room_df.empty:
        st.subheader("📈 Trend Analysis")
        ana_grp = st.selectbox("Select Group", room_df['GroupName'].unique())
        
        g_row = room_df[room_df['GroupName'] == ana_grp].iloc[0]
        try:
            h_data = json.loads(g_row['HistoryLog'])
            h_df = pd.DataFrame(h_data)
            if not h_df.empty:
                h_df['ts'] = pd.to_datetime(h_df['ts'])
                h_df = h_df.sort_values('ts')
                
                chart = alt.Chart(h_df).mark_line(point=True).encode(
                    x=alt.X('ts', title='Time', axis=alt.Axis(format='%H:%M')),
                    y=alt.Y('balance', title='XP Score'),
                    tooltip=['ts', 'reason', 'amount', 'balance']
                ).properties(height=300)
                st.altair_chart(chart, use_container_width=True)
                
                st.dataframe(h_df[['ts', 'reason', 'amount', 'balance']].sort_values('ts', ascending=False), use_container_width=True)
            else:
                st.info("No history yet.")
        except:
            st.error("Data Error")

# --- TAB 4: SETTINGS ---
with tabs[3]:
    st.subheader("🛠️ Management")
    
    with st.expander("📝 Create / Delete Groups", expanded=True):
        c_add, c_del = st.columns(2)
        with c_add:
            with st.form("new_grp"):
                n = st.text_input("Group Name")
                m = st.text_area("Members")
                if st.form_submit_button("Create"):
                    if db.create_group(selected_room, n, m, df):
                        st.success("Created!"); st.rerun()
                    else: st.error("Duplicate Name!")
        with c_del:
            d_t = st.selectbox("Delete Group", ["-"]+list(room_df['GroupName'].unique()))
            if d_t != "-" and st.button("Confirm Delete", type="primary"):
                db.delete_group(selected_room, d_t, df)
                st.rerun()

    st.markdown("#### ⚡ Power Editor (Edit Past Scores)")
    pe_grp = st.selectbox("Select Group to Edit", room_df['GroupName'].unique(), key="pe_k")
    
    if pe_grp:
        pe_row = room_df[room_df['GroupName'] == pe_grp].iloc[0]
        try: pe_hist = json.loads(pe_row['HistoryLog'])
        except: pe_hist = []
        
        pe_df = pd.DataFrame(pe_hist) if pe_hist else pd.DataFrame(columns=['ts', 'reason', 'amount'])
        
        edited = st.data_editor(
            pe_df,
            column_config={
                "ts": st.column_config.TextColumn("Timestamp", disabled=False),
                "reason": "Activity",
                "amount": st.column_config.NumberColumn("Score (+/-)", format="%d"),
                "id": None, "balance": None
            },
            num_rows="dynamic",
            use_container_width=True,
            key="editor_history"
        )
        
        if st.button("💾 Save & Recalculate"):
            if db.power_edit(selected_room, pe_grp, edited, df, ach_sys):
                st.success("Updated!"); time.sleep(1); st.rerun()
