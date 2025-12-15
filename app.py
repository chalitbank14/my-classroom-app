import streamlit as st
import pandas as pd
import altair as alt
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time
import json
import uuid

# ==============================================================================
# 1. SYSTEM CONFIGURATION & ULTRA UI
# ==============================================================================
st.set_page_config(
    page_title="Classroom OS: God Mode",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- THEME ENGINE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&family=Prompt:wght@300;400;600&display=swap');
    
    :root {
        --primary: #6366f1;
        --success: #10b981;
        --danger: #ef4444;
        --bg-color: #f1f5f9;
        --card-bg: #ffffff;
    }

    html, body, [class*="css"] {
        font-family: 'Sarabun', 'Prompt', sans-serif;
        background-color: var(--bg-color);
        color: #0f172a;
    }

    /* Hero Header */
    .hero-container {
        background: linear-gradient(120deg, #4f46e5, #3b82f6);
        padding: 1.5rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Glass Cards */
    .glass-card {
        background: var(--card-bg);
        border-radius: 16px;
        padding: 1.2rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
        transition: transform 0.2s;
    }
    
    /* Input & Select Styling */
    .stSelectbox div[data-baseweb="select"] {
        border-radius: 10px;
        border: 2px solid #e2e8f0;
    }
    .stTextInput input, .stNumberInput input {
        border-radius: 10px;
        border: 2px solid #e2e8f0;
        padding: 10px;
    }

    /* Big Action Buttons */
    .stButton button {
        width: 100%;
        height: 50px;
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.2s;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    /* Status Indicators */
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 800;
        text-transform: uppercase;
        color: white;
    }
    .score-positive { color: #10b981; font-weight: 800; }
    .score-negative { color: #ef4444; font-weight: 800; }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: white;
        padding: 8px;
        border-radius: 12px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. LOGIC CORE (OOP)
# ==============================================================================

class RankSystem:
    def __init__(self):
        self.ranks = [
            {"name": "PRESIDENT", "th": "👑 ประธานรุ่น", "min_xp": 1000, "color": "#f59e0b", "bg": "#fef3c7"},
            {"name": "DIRECTOR", "th": "💼 หัวหน้าฝ่าย", "min_xp": 600, "color": "#8b5cf6", "bg": "#f3e8ff"},
            {"name": "MANAGER", "th": "👔 หัวหน้าแผนก", "min_xp": 300, "color": "#3b82f6", "bg": "#dbeafe"},
            {"name": "EMPLOYEE", "th": "👨‍💼 พนักงาน", "min_xp": 100, "color": "#10b981", "bg": "#d1fae5"},
            {"name": "INTERN", "th": "👶 เด็กฝึกงาน", "min_xp": 0, "color": "#64748b", "bg": "#f1f5f9"},
            {"name": "PROBATION", "th": "⚠️ ทัณฑ์บน", "min_xp": -999999, "color": "#ef4444", "bg": "#fee2e2"}
        ]

    def get_rank(self, xp):
        if xp < 0: return self.ranks[-1]
        for rank in self.ranks:
            if rank['name'] != "PROBATION" and xp >= rank['min_xp']:
                return rank
        return self.ranks[-2]

    def get_progress(self, xp):
        if xp < 0: return 0.0, "🔴 Warning: Negative Score"
        for i, rank in enumerate(self.ranks):
            if rank['name'] != "PROBATION" and xp >= rank['min_xp']:
                if i > 0:
                    prev = self.ranks[i-1]
                    target = prev['min_xp']
                    pct = min(1.0, xp / target)
                    return pct, f"{int(pct*100)}% to {prev['th']}"
                return 1.0, "MAX LEVEL"
        return 0.0, "0%"

class BadgeEngine:
    def __init__(self):
        self.catalog = {
            "wealthy": "💎", "sniper": "🎯", "debtor": "💸", 
            "phoenix": "🔥", "first_blood": "🩸"
        }
    def check(self, xp, hist):
        b = []
        if xp >= 800: b.append("wealthy")
        if xp < 0: b.append("debtor")
        if any(h['amount'] >= 100 for h in hist): b.append("sniper")
        if len(hist) > 0: b.append("first_blood")
        return list(set(b))

class DataManager:
    def __init__(self):
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
            self.cols = ['Room', 'GroupName', 'XP', 'Members', 'LastUpdated', 'HistoryLog', 'Badges']
        except Exception as e:
            st.error(f"DB Connect Error: {e}")
            st.stop()

    def fetch(self):
        try:
            df = self.conn.read(worksheet="Sheet1", ttl=0)
            if df.empty or not set(self.cols).issubset(df.columns):
                return pd.DataFrame(columns=self.cols)
            df = df[self.cols].copy().dropna(how='all')
            df['XP'] = pd.to_numeric(df['XP'], errors='coerce').fillna(0).astype(int)
            for c in ['HistoryLog', 'Badges']: df[c] = df[c].fillna("[]").astype(str)
            return df
        except: return pd.DataFrame(columns=self.cols)

    def save(self, df):
        self.conn.update(worksheet="Sheet1", data=df)
        st.cache_data.clear()

    def update_score(self, room, groups, amount, reason, df, engine):
        """Batch Update: Handle multiple groups at once"""
        if isinstance(groups, str): groups = [groups] # Convert single to list
        
        updated_count = 0
        
        for grp in groups:
            idx = df[(df['Room'] == room) & (df['GroupName'] == grp)].index
            if not idx.empty:
                i = idx[0]
                try: hist = json.loads(df.at[i, 'HistoryLog'])
                except: hist = []
                
                new_log = {
                    "id": str(uuid.uuid4())[:8],
                    "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "reason": reason, "amount": int(amount)
                }
                hist.insert(0, new_log)
                
                # Recalc
                total = sum(x['amount'] for x in hist)
                hist[0]['balance'] = total
                badges = engine.check(total, hist)
                
                df.at[i, 'XP'] = total
                df.at[i, 'HistoryLog'] = json.dumps(hist, ensure_ascii=False)
                df.at[i, 'Badges'] = json.dumps(badges, ensure_ascii=False)
                df.at[i, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                updated_count += 1
        
        if updated_count > 0:
            self.save(df)
            return True, updated_count
        return False, 0

    def create(self, room, name, mem, df):
        if not ((df['Room'] == room) & (df['GroupName'] == name)).any():
            new = pd.DataFrame([{
                "Room": room, "GroupName": name, "XP": 0, "Members": mem,
                "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "HistoryLog": "[]", "Badges": "[]"
            }])
            self.save(pd.concat([df, new], ignore_index=True))
            return True
        return False

    def delete(self, room, name, df):
        self.save(df[~((df['Room'] == room) & (df['GroupName'] == name))])

    def power_edit(self, room, name, new_hist_df, df, engine):
        idx = df[(df['Room'] == room) & (df['GroupName'] == name)].index
        if not idx.empty:
            i = idx[0]
            # Convert DF back to list
            hist_list = new_hist_df.to_dict('records')
            
            # Recalc total
            total = sum(int(x['amount']) for x in hist_list)
            
            # Recalc running balance
            run = 0
            sorted_h = sorted(hist_list, key=lambda x: x['ts'])
            for h in sorted_h:
                run += int(h['amount'])
                h['balance'] = run
            
            final = sorted(sorted_h, key=lambda x: x['ts'], reverse=True)
            badges = engine.check(total, final)
            
            df.at[i, 'XP'] = total
            df.at[i, 'HistoryLog'] = json.dumps(final, ensure_ascii=False)
            df.at[i, 'Badges'] = json.dumps(badges, ensure_ascii=False)
            
            self.save(df)
            return True
        return False

db = DataManager()
rs = RankSystem()
be = BadgeEngine()

# ==============================================================================
# 3. UI LAYOUT
# ==============================================================================

with st.sidebar:
    st.title("⚙️ Control Panel")
    selected_room = st.selectbox("เลือกห้องเรียน", ["ม.1/1", "ม.1/2", "ม.1/10"])
    
    st.divider()
    # Repair Button
    if st.button("⚠️ ซ่อมแซมฐานข้อมูล (Repair)"):
        try:
            db.conn.update(worksheet="Sheet1", data=pd.DataFrame(columns=db.cols))
            st.success("Reset Headers Success")
        except: st.error("Failed")
        
    st.divider()
    raw = db.fetch()
    st.download_button("📥 Export CSV", raw.to_csv(index=False).encode('utf-8'), "data.csv")

# Main Load
df = db.fetch()
room_df = df[df['Room'] == selected_room].copy()

# Header
st.markdown(f"""
<div class="hero-container">
    <div>
        <h4 style="margin:0; opacity:0.8;">CLASSROOM OS: GOD MODE</h4>
        <h1 style="margin:0; font-size:2.2rem;">{selected_room}</h1>
    </div>
    <div style="text-align:right;">
        <span style="font-size:2rem; font-weight:bold;">{len(room_df)}</span> Groups
    </div>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["⚡ Command Center", "🏆 Rankings", "📈 Analytics", "🛠️ Management"])

# --- TAB 1: HYBRID COMMAND CENTER ---
with tabs[0]:
    if room_df.empty:
        st.warning("⚠️ No groups found. Create one in 'Management' tab.")
    else:
        # 1. Mode Selection
        mode = st.radio("รูปแบบการให้คะแนน:", ["รายกลุ่ม (Single)", "ทีละหลายกลุ่ม (Batch)"], horizontal=True)
        
        target_groups = []
        if mode == "รายกลุ่ม (Single)":
            tg = st.selectbox("🎯 เลือกกลุ่ม", room_df['GroupName'].unique())
            if tg: target_groups = [tg]
        else:
            target_groups = st.multiselect("🎯 เลือกหลายกลุ่ม (ให้คะแนนพร้อมกัน)", room_df['GroupName'].unique())
            st.caption(f"กำลังเลือก: {len(target_groups)} กลุ่ม")

        st.divider()

        # 2. Status Monitor (Show only if Single)
        if len(target_groups) == 1:
            g_data = room_df[room_df['GroupName'] == target_groups[0]].iloc[0]
            rnk = rs.get_rank(g_data['XP'])
            xp_cls = "score-negative" if g_data['XP'] < 0 else "score-positive"
            
            c_mon, c_badge = st.columns([1, 2])
            with c_mon:
                st.markdown(f"""
                <div style="text-align:center; padding:10px; border:1px solid #ddd; border-radius:10px;">
                    <small>CURRENT XP</small>
                    <div class="{xp_cls}" style="font-size:2rem; line-height:1;">{g_data['XP']}</div>
                    <span class="status-badge" style="background:{rnk['bg']}; color:{rnk['color']}">{rnk['th']}</span>
                </div>
                """, unsafe_allow_html=True)
        
        # 3. Hybrid Input (Buttons + Manual)
        col_left, col_right = st.columns([1, 1])
        
        def process_xp(r, a):
            if not target_groups:
                st.error("กรุณาเลือกกลุ่มก่อน")
                return
            success, count = db.update_score(selected_room, target_groups, a, r, df, be)
            if success:
                st.toast(f"บันทึกสำเร็จ! ({count} กลุ่ม): {r} {a:+d}", icon="✅")
                if a > 0: st.balloons()
                time.sleep(1)
                st.rerun()

        with col_left:
            st.markdown("##### 🚀 ปุ่มด่วน (Quick)")
            if st.button("📚 ส่งงานตรงเวลา (+50)", type="primary"): process_xp("ส่งงานตรงเวลา", 50)
            if st.button("🙋 ตอบคำถาม (+20)"): process_xp("ตอบคำถาม", 20)
            if st.button("🏆 ชนะกิจกรรม (+100)"): process_xp("ชนะกิจกรรม", 100)
            st.markdown("---")
            if st.button("🐢 ส่งช้า (-20)"): process_xp("ส่งงานล่าช้า", -20)
            if st.button("❌ ไม่ส่งงาน (-50)"): process_xp("ไม่ส่งงาน", -50)

        with col_right:
            st.markdown("##### ✍️ กำหนดเอง (Manual)")
            with st.form("manual_frm"):
                m_reason = st.text_input("ระบุเหตุผล", placeholder="เช่น จิตพิสัย, ทำเวร")
                m_score = st.number_input("คะแนน (+/-)", value=0, step=5)
                if st.form_submit_button("💾 บันทึกรายการ"):
                    if m_reason and m_score != 0: process_xp(m_reason, m_score)
                    else: st.error("ระบุข้อมูลให้ครบ")

        # 4. Recent Logs (Mini)
        if len(target_groups) == 1:
            st.markdown("##### 🕒 ประวัติล่าสุด (Recent)")
            try: 
                logs = json.loads(g_data['HistoryLog'])[:3]
                for l in logs:
                    st.markdown(f"- **{l['reason']}** ({l['amount']:+d}) <span style='color:grey; font-size:0.8rem'>{l['ts']}</span>", unsafe_allow_html=True)
            except: pass

# --- TAB 2: LEADERBOARD ---
with tabs[1]:
    if not room_df.empty:
        sorted_df = room_df.sort_values("XP", ascending=False).reset_index(drop=True)
        for i, row in sorted_df.iterrows():
            r = rs.get_rank(row['XP'])
            pct, lbl = rs.get_progress(row['XP'])
            
            # Badges
            try: bdgs = json.loads(row['Badges'])
            except: bdgs = []
            icons = "".join([be.catalog[b] for b in bdgs if b in be.catalog])
            
            border_col = "#ef4444" if row['XP'] < 0 else r['color']
            
            st.markdown(f"""
            <div class="glass-card" style="border-left: 6px solid {border_col};">
                <div style="display:flex; justify-content:space-between;">
                    <div>
                        <span style="font-weight:bold; color:#64748b;">#{i+1}</span>
                        <span style="font-size:1.2rem; font-weight:bold; margin-left:10px;">{row['GroupName']}</span>
                        <div style="font-size:0.9rem; color:#64748b; margin-top:4px;">{row['Members']}</div>
                        <div style="margin-top:5px; font-size:1.2rem;">{icons}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:1.8rem; font-weight:800; color:{border_col};">{row['XP']}</div>
                        <span class="status-badge" style="background:{r['bg']}; color:{r['color']}">{r['th']}</span>
                    </div>
                </div>
                <div style="margin-top:10px; font-size:0.8rem; color:grey; display:flex; justify-content:space-between;">
                    <span>Next Level</span><span>{lbl}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(pct)

# --- TAB 3: ANALYTICS ---
with tabs[2]:
    if not room_df.empty:
        ana_t = st.selectbox("เลือกกลุ่มเพื่อวิเคราะห์", room_df['GroupName'].unique())
        try:
            row = room_df[room_df['GroupName']==ana_t].iloc[0]
            h = pd.DataFrame(json.loads(row['HistoryLog']))
            if not h.empty:
                h['ts'] = pd.to_datetime(h['ts'])
                st.altair_chart(alt.Chart(h).mark_line(point=True, color='#6366f1').encode(x='ts', y='balance').properties(height=300), use_container_width=True)
                st.dataframe(h, use_container_width=True)
        except: st.info("No data")

# --- TAB 4: MANAGEMENT ---
with tabs[3]:
    c1, c2 = st.columns(2)
    with c1:
        with st.form("new_grp"):
            st.markdown("#### ➕ สร้างกลุ่ม")
            n = st.text_input("ชื่อกลุ่ม")
            m = st.text_area("สมาชิก")
            if st.form_submit_button("สร้าง"):
                if db.create(selected_room, n, m, df): st.success("Created"); st.rerun()
                else: st.error("ซ้ำ")
    with c2:
        st.markdown("#### 🗑️ ลบกลุ่ม")
        d = st.selectbox("เลือกกลุ่ม", ["-"]+list(room_df['GroupName'].unique()))
        if d != "-" and st.button("ยืนยันลบ"): db.delete(selected_room, d, df); st.rerun()

    st.markdown("---")
    st.markdown("#### ⚡ Power Editor (แก้ไขประวัติ)")
    pe_g = st.selectbox("เลือกกลุ่มแก้ไข", ["-"]+list(room_df['GroupName'].unique()), key="pe")
    if pe_g != "-":
        r = room_df[room_df['GroupName']==pe_g].iloc[0]
        try: h_data = json.loads(r['HistoryLog'])
        except: h_data = []
        
        edited = st.data_editor(pd.DataFrame(h_data), num_rows="dynamic", use_container_width=True)
        if st.button("💾 บันทึกและคำนวณใหม่"):
            if db.power_edit(selected_room, pe_g, edited, df, be):
                st.success("Updated"); st.rerun()
