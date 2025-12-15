import streamlit as st
import pandas as pd
import altair as alt
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time
import json
import uuid

# ==============================================================================
# 1. SYSTEM CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="Classroom OS: Architect",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&family=Prompt:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Sarabun', 'Prompt', sans-serif;
        background-color: #F8FAFC;
        color: #1E293B;
    }
    
    .hero-box {
        background: linear-gradient(135deg, #4338CA 0%, #3730A3 100%);
        padding: 2rem; border-radius: 16px; color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
    }
    .glass-card {
        background: white; border-radius: 16px; padding: 1.5rem;
        border: 1px solid #E2E8F0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }
    .stButton button { width: 100%; height: 50px; border-radius: 10px !important; font-weight: 600 !important; }
    
    /* Rank Colors */
    .status-normal { color: #059669; font-weight: 800; }
    .status-probation { color: #DC2626; font-weight: 800; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. LOGIC
# ==============================================================================

class RankSystem:
    def __init__(self):
        self.ranks = [
            {"name": "PRESIDENT", "th": "👑 ประธานรุ่น", "min_xp": 1000, "color": "#F59E0B", "bg": "#FEF3C7"},
            {"name": "DIRECTOR", "th": "💼 หัวหน้าฝ่าย", "min_xp": 600, "color": "#8B5CF6", "bg": "#F3E8FF"},
            {"name": "MANAGER", "th": "👔 หัวหน้าแผนก", "min_xp": 300, "color": "#3B82F6", "bg": "#DBEAFE"},
            {"name": "EMPLOYEE", "th": "👨‍💼 พนักงาน", "min_xp": 100, "color": "#10B981", "bg": "#D1FAE5"},
            {"name": "INTERN", "th": "👶 เด็กฝึกงาน", "min_xp": 0, "color": "#64748B", "bg": "#F1F5F9"},
            {"name": "PROBATION", "th": "⚠️ ทัณฑ์บน", "min_xp": -99999, "color": "#EF4444", "bg": "#FEE2E2"}
        ]
    
    def get_rank(self, xp):
        if xp < 0: return self.ranks[-1]
        for rank in self.ranks:
            if rank['name'] != "PROBATION" and xp >= rank['min_xp']: return rank
        return self.ranks[-2]
    
    def get_progress(self, xp):
        if xp < 0: return 0.0, "Need positive XP"
        for i, rank in enumerate(self.ranks):
            if rank['name'] != "PROBATION" and xp >= rank['min_xp']:
                if i > 0:
                    prev = self.ranks[i-1]
                    return min(1.0, xp/prev['min_xp']), f"Next: {prev['th']} ({xp}/{prev['min_xp']})"
                return 1.0, "MAX LEVEL"
        return 0.0, "0%"

class DataManager:
    def __init__(self):
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
            self.cols = ['Room', 'GroupName', 'XP', 'Members', 'LastUpdated', 'HistoryLog', 'Badges']
        except Exception as e:
            st.error(f"DB Error: {e}")
            st.stop()

    def reset_database_structure(self):
        """Emergency function to fix the sheet headers"""
        try:
            # Create a clean DataFrame with only headers
            empty_df = pd.DataFrame(columns=self.cols)
            # Clear everything and write headers
            self.conn.clear(worksheet="Sheet1")
            self.conn.update(worksheet="Sheet1", data=empty_df)
            st.cache_data.clear()
            return True, "✅ สร้างหัวตารางเรียบร้อย! ลองใช้งานได้เลย"
        except Exception as e:
            return False, f"❌ แก้ไขไม่สำเร็จ: {e}"

    def fetch_data(self):
        try:
            df = self.conn.read(worksheet="Sheet1", ttl=0)
            if df.empty or not set(self.cols).issubset(df.columns):
                return pd.DataFrame(columns=self.cols)
            
            df = df[self.cols].copy().dropna(how='all')
            df['XP'] = pd.to_numeric(df['XP'], errors='coerce').fillna(0).astype(int)
            for c in ['HistoryLog', 'Badges']:
                df[c] = df[c].fillna("[]").astype(str)
            return df
        except:
            return pd.DataFrame(columns=self.cols)

    def save(self, df):
        try:
            self.conn.update(worksheet="Sheet1", data=df)
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Save Error: {e}. กรุณากดปุ่ม 'ซ่อมแซมฐานข้อมูล' ในเมนูด้านซ้าย")

    def add_transaction(self, room, group, amount, reason, df):
        idx = df[(df['Room'] == room) & (df['GroupName'] == group)].index
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
            total_xp = sum(item['amount'] for item in hist)
            hist[0]['balance'] = total_xp
            
            # Badges Logic (Simplified for brevity)
            badges = []
            if total_xp >= 800: badges.append("wealthy")
            if total_xp < 0: badges.append("debtor")
            if len(hist)>0: badges.append("first_blood")
            
            df.at[i, 'XP'] = total_xp
            df.at[i, 'HistoryLog'] = json.dumps(hist, ensure_ascii=False)
            df.at[i, 'Badges'] = json.dumps(badges, ensure_ascii=False)
            df.at[i, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            self.save(df)
            return total_xp, badges
        return None, None

    def create_group(self, room, name, members, df):
        if not ((df['Room'] == room) & (df['GroupName'] == name)).any():
            new_row = pd.DataFrame([{
                "Room": room, "GroupName": name, "XP": 0, "Members": members,
                "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "HistoryLog": "[]", "Badges": "[]"
            }])
            self.save(pd.concat([df, new_row], ignore_index=True))
            return True
        return False

    def delete_group(self, room, name, df):
        self.save(df[~((df['Room'] == room) & (df['GroupName'] == name))])
        
    def power_edit(self, room, group, edited_df, df):
        idx = df[(df['Room'] == room) & (df['GroupName'] == group)].index
        if not idx.empty:
            i = idx[0]
            new_hist = edited_df.to_dict('records')
            total = sum(int(x['amount']) for x in new_hist)
            run_bal = 0
            for log in sorted(new_hist, key=lambda x: x['ts']):
                run_bal += int(log['amount'])
                log['balance'] = run_bal
            
            final_hist = sorted(new_hist, key=lambda x: x['ts'], reverse=True)
            df.at[i, 'XP'] = total
            df.at[i, 'HistoryLog'] = json.dumps(final_hist, ensure_ascii=False)
            self.save(df)
            return True
        return False

db = DataManager()
rs = RankSystem()

# ==============================================================================
# 3. UI
# ==============================================================================

with st.sidebar:
    st.title("Admin Panel")
    selected_room = st.selectbox("เลือกห้องเรียน", ["ม.1/1", "ม.1/2", "ม.1/10"])
    
    st.divider()
    st.markdown("### 🚑 โซนแก้ปัญหา")
    st.info("หากกดบันทึกไม่ได้ หรือขึ้น Error ให้กดปุ่มด้านล่างเพื่อล้างหัวตารางให้ถูกต้อง")
    if st.button("⚠️ ซ่อมแซม/สร้างหัวตารางใหม่", type="primary"):
        success, msg = db.reset_database_structure()
        if success: st.success(msg)
        else: st.error(msg)
    
    st.divider()
    if st.button("🔄 Refresh"): st.rerun()

df = db.fetch_data()
room_df = df[df['Room'] == selected_room].copy()

st.markdown(f"""
<div class="hero-box">
    <h1 style="margin:0;">{selected_room}</h1>
    <p style="margin:0;">Classroom Architect Edition</p>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["⚡ Command Center", "🏆 Rankings", "📈 Analytics", "🛠️ Settings"])

# TAB 1: COMMAND
with tabs[0]:
    if room_df.empty:
        st.warning("⚠️ ยังไม่มีกลุ่ม ไปที่แท็บ Settings เพื่อสร้าง")
    else:
        target = st.selectbox("🎯 เลือกกลุ่ม", room_df['GroupName'].unique())
        if target:
            dat = room_df[room_df['GroupName'] == target].iloc[0]
            rnk = rs.get_rank(dat['XP'])
            st.metric("คะแนนปัจจุบัน", f"{dat['XP']} XP", rnk['th'])
            
            c1, c2 = st.columns(2)
            def run(r, a):
                xp, b = db.add_transaction(selected_room, target, a, r, df)
                st.toast(f"{r}: {a:+d}", icon="✅")
                time.sleep(0.5); st.rerun()

            with c1:
                if st.button("📚 ส่งงาน (+50)", type="primary"): run("ส่งงานตรงเวลา", 50)
                if st.button("🙋 ตอบคำถาม (+20)"): run("ตอบคำถาม", 20)
                if st.button("💡 ไอเดียดี (+30)"): run("ความคิดสร้างสรรค์", 30)
                if st.button("🏆 ชนะเกม (+100)"): run("ชนะกิจกรรม", 100)
            with c2:
                if st.button("🐢 ส่งช้า (-20)"): run("ส่งงานล่าช้า", -20)
                if st.button("📢 เสียงดัง (-10)"): run("คุยเสียงดัง", -10)
                if st.button("❌ ไม่ส่ง (-50)"): run("ไม่ส่งงาน", -50)
                if st.button("🗑️ ลืมของ (-10)"): run("ลืมอุปกรณ์", -10)

# TAB 2: RANKINGS
with tabs[1]:
    if not room_df.empty:
        for i, row in room_df.sort_values("XP", ascending=False).reset_index(drop=True).iterrows():
            r = rs.get_rank(row['XP'])
            p, pl = rs.get_progress(row['XP'])
            st.markdown(f"""
            <div class="glass-card" style="border-left: 5px solid {r['color']}">
                <div style="display:flex; justify-content:space-between;">
                    <div><b>#{i+1} {row['GroupName']}</b><br><small>{row['Members']}</small></div>
                    <div style="text-align:right"><b style="color:{r['color']}">{row['XP']} XP</b><br><span style="font-size:0.8rem">{r['th']}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(p, pl)

# TAB 3: ANALYTICS
with tabs[2]:
    if not room_df.empty:
        ana_t = st.selectbox("เลือกกลุ่มดูกราฟ", room_df['GroupName'].unique())
        try:
            h = pd.DataFrame(json.loads(room_df[room_df['GroupName']==ana_t].iloc[0]['HistoryLog']))
            if not h.empty:
                h['ts'] = pd.to_datetime(h['ts'])
                st.altair_chart(alt.Chart(h).mark_line(point=True).encode(x='ts', y='balance').properties(height=300), use_container_width=True)
                st.dataframe(h[['ts', 'reason', 'amount', 'balance']], use_container_width=True)
        except: st.info("No Data")

# TAB 4: SETTINGS
with tabs[3]:
    c1, c2 = st.columns(2)
    with c1:
        with st.form("new"):
            n = st.text_input("ชื่อกลุ่มใหม่")
            m = st.text_area("สมาชิก")
            if st.form_submit_button("สร้างกลุ่ม"):
                if db.create_group(selected_room, n, m, df): st.success("Created"); st.rerun()
                else: st.error("ชื่อซ้ำ")
    with c2:
        d = st.selectbox("ลบกลุ่ม", ["-"]+list(room_df['GroupName'].unique()))
        if d != "-" and st.button("ยืนยันลบ"): db.delete_group(selected_room, d, df); st.rerun()
        
    st.markdown("---")
    pe = st.selectbox("แก้ไขประวัติย้อนหลัง", ["-"]+list(room_df['GroupName'].unique()))
    if pe != "-":
        row = room_df[room_df['GroupName']==pe].iloc[0]
        try: h_data = json.loads(row['HistoryLog'])
        except: h_data = []
        edited = st.data_editor(pd.DataFrame(h_data), num_rows="dynamic", use_container_width=True)
        if st.button("บันทึกการแก้ไข"):
            if db.power_edit(selected_room, pe, edited, df): st.success("Updated"); st.rerun()
