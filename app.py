import streamlit as st
import pandas as pd
import altair as alt
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time
import json
import uuid
import io
from PIL import Image, ImageDraw, ImageFont

# ==============================================================================
# 1. SYSTEM CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="Classroom OS: Stable",
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
    
    .hero-container {
        background: linear-gradient(120deg, #4f46e5, #3b82f6);
        padding: 1.5rem; border-radius: 16px; color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        display: flex; justify-content: space-between; align-items: center;
    }
    .glass-card {
        background: #ffffff; border-radius: 16px; padding: 1.2rem;
        border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
    }
    .stat-box {
        text-align: center; padding: 15px; background: white;
        border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
    }
    .stButton button {
        width: 100%; height: 50px; border-radius: 12px !important;
        font-weight: 600 !important; font-size: 1rem !important;
    }
    .status-badge {
        padding: 4px 12px; border-radius: 20px; font-size: 0.75rem;
        font-weight: 800; text-transform: uppercase; color: white;
    }
    .score-positive { color: #10b981; font-weight: 800; }
    .score-negative { color: #ef4444; font-weight: 800; }
    
    .rank-detail-card {
        padding: 20px; border-radius: 15px; background: white;
        border-left: 8px solid #ddd; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .power-quote {
        background-color: #f1f5f9; padding: 10px; border-radius: 8px;
        font-weight: 600; color: #334155; margin-top: 10px;
        border-left: 4px solid #6366f1;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CORE LOGIC
# ==============================================================================
class RankSystem:
    def __init__(self):
        self.ranks = [
            # อัปเดตข้อมูลสิทธิ์ (desc) ให้ตรงกับที่แก้ใน Tab 4
            {"name": "PRESIDENT", "th": "👑 ประธานรุ่น", "min_xp": 1000, "color": "#f59e0b", "bg": "#fef3c7", "desc": "Immun. (ไม่ทำ 3 งาน) + โบนัส 1 ทุกงาน"},
            {"name": "DIRECTOR", "th": "💼 หัวหน้าฝ่าย", "min_xp": 600, "color": "#8b5cf6", "bg": "#f3e8ff", "desc": "Workload Cut (ลดงาน 50%)"},
            {"name": "MANAGER", "th": "👔 หัวหน้าแผนก", "min_xp": 300, "color": "#3b82f6", "bg": "#dbeafe", "desc": "Second Chance (แก้ตัวได้ 1 งาน/หน่วย)"},
            {"name": "EMPLOYEE", "th": "👨‍💼 พนักงาน", "min_xp": 100, "color": "#10b981", "bg": "#d1fae5", "desc": "Time Ext. (ส่งช้าได้ 2 สัปดาห์)"},
            {"name": "INTERN", "th": "👶 เด็กฝึกงาน", "min_xp": 0, "color": "#64748b", "bg": "#f1f5f9", "desc": "Check-up (ครูช่วยตรวจก่อนส่ง)"},
            {"name": "PROBATION", "th": "⚠️ ทัณฑ์บน", "min_xp": -999999, "color": "#ef4444", "bg": "#fee2e2", "desc": "รีบทำงานแก้คะแนนด่วน!"}
        ]
    def get_rank(self, xp):
        if xp < 0: return self.ranks[-1]
        for rank in self.ranks:
            if rank['name'] != "PROBATION" and xp >= rank['min_xp']: return rank
        return self.ranks[-2]
    def get_progress(self, xp):
        if xp < 0: return 0.0, "🔴 Warning"
        for i, rank in enumerate(self.ranks):
            if rank['name'] != "PROBATION" and xp >= rank['min_xp']:
                if i > 0:
                    prev = self.ranks[i-1]
                    pct = min(1.0, xp / prev['min_xp'])
                    return pct, f"{int(pct*100)}% to {prev['th']}"
                return 1.0, "MAX LEVEL"
        return 0.0, "0%"

class BadgeEngine:
    def __init__(self):
        self.catalog = {"wealthy": "💎", "sniper": "🎯", "debtor": "💸", "phoenix": "🔥", "first_blood": "🩸"}
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
            st.error(f"DB Error: {e}"); st.stop()
    def fetch(self):
        try:
            df = self.conn.read(worksheet="Sheet1", ttl=0)
            if df.empty or not set(self.cols).issubset(df.columns): return pd.DataFrame(columns=self.cols)
            df = df[self.cols].copy().dropna(how='all')
            df['XP'] = pd.to_numeric(df['XP'], errors='coerce').fillna(0).astype(int)
            for c in ['HistoryLog', 'Badges']: df[c] = df[c].fillna("[]").astype(str)
            return df
        except: return pd.DataFrame(columns=self.cols)
    def save(self, df):
        self.conn.update(worksheet="Sheet1", data=df); st.cache_data.clear()
    def update_score(self, room, groups, amount, reason, df, engine):
        if isinstance(groups, str): groups = [groups]
        c = 0
        for grp in groups:
            idx = df[(df['Room'] == room) & (df['GroupName'] == grp)].index
            if not idx.empty:
                i = idx[0]
                try: hist = json.loads(df.at[i, 'HistoryLog'])
                except: hist = []
                hist.insert(0, {"id":str(uuid.uuid4())[:8], "ts":datetime.now().strftime("%Y-%m-%d %H:%M"), "reason":reason, "amount":int(amount)})
                total = sum(x['amount'] for x in hist)
                hist[0]['balance'] = total
                df.at[i, 'XP'] = total
                df.at[i, 'HistoryLog'] = json.dumps(hist, ensure_ascii=False)
                df.at[i, 'Badges'] = json.dumps(engine.check(total, hist), ensure_ascii=False)
                df.at[i, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                c += 1
        if c > 0: self.save(df); return True, c
        return False, 0
    def create(self, room, name, mem, df):
        if not ((df['Room'] == room) & (df['GroupName'] == name)).any():
            self.save(pd.concat([df, pd.DataFrame([{"Room":room, "GroupName":name, "XP":0, "Members":mem, "LastUpdated":datetime.now().strftime("%Y-%m-%d %H:%M"), "HistoryLog":"[]", "Badges":"[]"}])], ignore_index=True))
            return True
        return False
    
    # --- ฟังก์ชันแก้ไขชื่อและสมาชิก ---
    def edit_group(self, room, old_name, new_name, new_members, df):
        if new_name != old_name and ((df['Room'] == room) & (df['GroupName'] == new_name)).any():
            return False 
        idx = df[(df['Room'] == room) & (df['GroupName'] == old_name)].index
        if not idx.empty:
            i = idx[0]
            df.at[i, 'GroupName'] = new_name
            df.at[i, 'Members'] = new_members
            self.save(df)
            return True
        return False
    # ------------------------------------

    def delete(self, room, name, df): self.save(df[~((df['Room'] == room) & (df['GroupName'] == name))])
    def power_edit(self, room, name, new_h, df, engine):
        idx = df[(df['Room'] == room) & (df['GroupName'] == name)].index
        if not idx.empty:
            i = idx[0]
            hl = new_h.to_dict('records')
            total = sum(int(x['amount']) for x in hl)
            for h in sorted(hl, key=lambda x: x['ts']): h['balance'] = sum(int(k['amount']) for k in hl if k['ts'] <= h['ts']) # Simple recalc
            final = sorted(hl, key=lambda x: x['ts'], reverse=True)
            df.at[i, 'XP'] = total
            df.at[i, 'HistoryLog'] = json.dumps(final, ensure_ascii=False)
            df.at[i, 'Badges'] = json.dumps(engine.check(total, final), ensure_ascii=False)
            self.save(df); return True
        return False

# ==============================================================================
# 3. IMAGE GENERATOR (WITH PRIVILEGES)
# ==============================================================================
def generate_image(room_name, df, rank_sys):
    # Cleaner Function
    def clean(text):
        for e in ["👑", "💼", "👔", "👨‍💼", "👶", "⚠️", "🩸", "💎", "💸", "🎯", "🔥", "🏆"]:
            text = text.replace(e, "")
        return text.strip()

    sorted_df = df.sort_values("XP", ascending=False).reset_index(drop=True)
    
    # Config
    W, ROW_H, HEADER_H, FOOTER_H = 1400, 320, 700, 150
    H = HEADER_H + (len(sorted_df) * ROW_H) + FOOTER_H
    
    img = Image.new('RGB', (W, H), color='#F8FAFC')
    draw = ImageDraw.Draw(img)
    
    # Load Fonts
    def load_font(name, size):
        try: return ImageFont.truetype(name, size)
        except: return ImageFont.load_default()
    
    f_header = load_font("Sarabun-Bold.ttf", 160)
    f_sub = load_font("Sarabun-Bold.ttf", 65)
    f_rank = load_font("Sarabun-Bold.ttf", 90)
    f_mem = load_font("Sarabun-Regular.ttf", 50)
    f_score = load_font("Sarabun-Bold.ttf", 110)
    f_badge = load_font("Sarabun-Bold.ttf", 55)
    f_privilege = load_font("Sarabun-Regular.ttf", 40) # Font สำหรับสิทธิพิเศษ

    # Draw Header
    draw.rectangle([(0, 0), (W, HEADER_H)], fill='#4338CA')
    draw.ellipse([(1000, -100), (1600, 500)], fill='#4F46E5')
    draw.ellipse([(-100, 300), (400, 800)], fill='#3730A3')
    
    draw.text((W//2, 250), "CLASSROOM LEADERBOARD", font=f_sub, fill='#A5B4FC', anchor="mm")
    draw.text((W//2, 450), f"{room_name}", font=f_header, fill='white', anchor="mm")

    # Draw Rows
    curr_y = HEADER_H + 50
    for i, row in sorted_df.iterrows():
        rank_info = rank_sys.get_rank(row['XP'])
        pct, _ = rank_sys.get_progress(row['XP'])
        
        if i==0: tc="#F59E0B"
        elif i==1: tc="#94A3B8"
        elif i==2: tc="#B45309"
        else: tc="#64748B"
        xc = "#EF4444" if row['XP']<0 else "#10B981"
        
        # Card
        draw.rounded_rectangle([(45, curr_y+10), (W-35, curr_y+ROW_H-15)], radius=35, fill='#CBD5E1')
        draw.rounded_rectangle([(40, curr_y), (W-40, curr_y+ROW_H-25)], radius=35, fill='white')
        
        # Rank Circle
        cx, cy = 150, curr_y+120
        draw.ellipse([(cx-80, cy-80), (cx+80, cy+80)], fill=tc)
        draw.text((cx, cy), str(i+1), font=f_rank, fill="white", anchor="mm")
        
        # Info Column
        tx = 280
        
        # 1. Group Name (Smart Resize)
        name = str(row['GroupName'])
        fz = 85
        while fz > 40:
            if load_font("Sarabun-Bold.ttf", fz).getlength(name) < 750: break
            fz -= 5
        draw.text((tx, curr_y+90), clean(name), font=load_font("Sarabun-Bold.ttf", fz), fill="#1E293B", anchor="ls")
        
        # 2. Members
        mem = str(row['Members'])
        if len(mem)>60: mem=mem[:58]+"..."
        draw.text((tx, curr_y+160), clean(mem), font=f_mem, fill="#64748B", anchor="ls")
        
        # 3. Progress Bar & Privileges (วาดชื่อยศและสิทธิพิเศษ)
        by = curr_y + 210
        bar_w = 600 # ลดความกว้างหลอดนิดนึงเพื่อให้มีที่ด้านขวา
        
        # หลอดพลัง
        draw.rounded_rectangle([(tx, by), (tx+bar_w, by+16)], radius=8, fill="#F1F5F9")
        if pct>0: draw.rounded_rectangle([(tx, by), (tx+int(bar_w*pct), by+16)], radius=8, fill=rank_info['color'])
        
        # วาดชื่อยศ (บน)
        text_start_x = tx + bar_w + 30
        draw.text((text_start_x, by-5), clean(rank_info['th']), font=f_badge, fill=rank_info['color'], anchor="lt")
        
        # วาดสิทธิพิเศษ (ล่าง) - ดึงจาก desc ที่เพิ่มใน RankSystem
        priv_text = rank_info.get('desc', '')
        # ถ้าข้อความยาวเกินไป ตัดให้สั้นหน่อย
        if len(priv_text) > 35: priv_text = priv_text[:33] + "..."
        draw.text((text_start_x, by+55), priv_text, font=f_privilege, fill="#64748B", anchor="ls")
        
        # Score Column
        draw.text((W-100, curr_y+110), f"{row['XP']}", font=f_score, fill=xc, anchor="rs")
        draw.text((W-100, curr_y+160), "XP", font=f_badge, fill="#94A3B8", anchor="rs")
        
        curr_y += ROW_H

    draw.text((W//2, H-70), f"Generated on {datetime.now().strftime('%d/%m/%Y')}", font=f_mem, fill="#94A3B8", anchor="mm")
    buf = io.BytesIO(); img.save(buf, format='PNG'); return buf.getvalue()

# ==============================================================================
# 4. MAIN APP
# ==============================================================================
db = DataManager(); rs = RankSystem(); be = BadgeEngine()

with st.sidebar:
    st.title("⚙️ Control Panel")
    selected_room = st.selectbox("เลือกห้องเรียน", ["ม.1/1", "ม.1/2", "ม.1/10"])
    st.divider()
    if st.button("⚠️ Repair Database"):
        try: db.conn.update(worksheet="Sheet1", data=pd.DataFrame(columns=db.cols)); st.success("Success")
        except: st.error("Failed")
    st.divider()
    st.download_button("📥 Export CSV", db.fetch().to_csv(index=False).encode('utf-8'), "data.csv")

df = db.fetch(); room_df = df[df['Room'] == selected_room].copy()

st.markdown(f"<div class='hero-container'><div><h4 style='margin:0; opacity:0.8;'>CLASSROOM OS</h4><h1 style='margin:0; font-size:2.2rem;'>{selected_room}</h1></div><div style='text-align:right;'><span style='font-size:2rem; font-weight:bold;'>{len(room_df)}</span> Groups</div></div>", unsafe_allow_html=True)

tabs = st.tabs(["⚡ Command", "🏆 Rankings", "📈 Analytics", "ℹ️ Privileges", "🛠️ Manage"])

# TAB 1
with tabs[0]:
    if room_df.empty: st.warning("No groups.")
    else:
        mode = st.radio("Mode:", ["Single", "Batch"], horizontal=True)
        tg = [st.selectbox("Target", room_df['GroupName'].unique())] if mode=="Single" else st.multiselect("Targets", room_df['GroupName'].unique())
        
        if len(tg)==1:
            g = room_df[room_df['GroupName']==tg[0]].iloc[0]
            r = rs.get_rank(g['XP'])
            st.markdown(f"<div style='text-align:center; padding:10px; border:1px solid #ddd; border-radius:10px; background:white;'><small>XP</small><div class='{'score-negative' if g['XP']<0 else 'score-positive'}' style='font-size:2rem; line-height:1;'>{g['XP']}</div><span class='status-badge' style='background:{r['bg']}; color:{r['color']}'>{r['th']}</span></div>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        def act(rn, am):
            if not tg: st.error("Select group"); return
            if db.update_score(selected_room, tg, am, rn, df, be)[0]: st.toast("Saved!", icon="✅"); time.sleep(1); st.rerun()
            
        with c1:
            if st.button("📚 ส่งงาน (+50)", type="primary"): act("ส่งงานตรงเวลา", 50)
            if st.button("🙋 ตอบคำถาม (+20)"): act("ตอบคำถาม", 20)
            if st.button("🏆 ชนะกิจกรรม (+100)"): act("ชนะกิจกรรม", 100)
            st.write("---")
            if st.button("🐢 ส่งช้า (-20)"): act("ส่งงานล่าช้า", -20)
        with c2:
            with st.form("m"):
                r = st.text_input("Reason"); a = st.number_input("Score", step=5)
                if st.form_submit_button("Save") and r and a!=0: act(r, a)

# TAB 2
with tabs[1]:
    if not room_df.empty:
        st.download_button("🖼️ Save Image", generate_image(selected_room, room_df, rs), f"Leaderboard_{selected_room}.png", "image/png", type="primary", use_container_width=True)
        st.write("---")
        for i, row in room_df.sort_values("XP", ascending=False).reset_index(drop=True).iterrows():
            r = rs.get_rank(row['XP']); pct, lbl = rs.get_progress(row['XP'])
            try: b=json.loads(row['Badges']); icons="".join([be.catalog[x] for x in b if x in be.catalog])
            except: icons=""
            col = "#ef4444" if row['XP']<0 else r['color']
            st.markdown(f"<div class='glass-card' style='border-left: 6px solid {col};'><div style='display:flex; justify-content:space-between;'><div><span style='font-weight:bold; color:#64748b;'>#{i+1}</span> <span style='font-size:1.2rem; font-weight:bold;'>{row['GroupName']}</span><div style='font-size:0.9rem; color:#64748b;'>{row['Members']}</div><div>{icons}</div></div><div style='text-align:right;'><div style='font-size:1.8rem; font-weight:800; color:{col};'>{row['XP']}</div><span class='status-badge' style='background:{r['bg']}; color:{r['color']}'>{r['th']}</span></div></div></div>", unsafe_allow_html=True); st.progress(pct)

# TAB 3
with tabs[2]:
    if not room_df.empty:
        total = room_df['XP'].sum(); avg = room_df['XP'].mean(); top = room_df.loc[room_df['XP'].idxmax()]['GroupName']
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='stat-box'><h3>🏆 Top</h3><div style='color:#6366f1; font-weight:bold;'>{top}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='stat-box'><h3>✨ Total</h3><div style='color:#10b981; font-weight:bold;'>{total:,}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='stat-box'><h3>📈 Avg</h3><div style='color:#f59e0b; font-weight:bold;'>{avg:.1f}</div></div>", unsafe_allow_html=True)
        st.write("---")
        h_data = []
        for _, row in room_df.iterrows():
            try:
                for log in json.loads(row['HistoryLog']): h_data.append({'Group':row['GroupName'], 'Time':pd.to_datetime(log['ts']), 'Score':log.get('balance',0)})
            except: pass
        if h_data:
            chart = alt.Chart(pd.DataFrame(h_data)).mark_line(point=True).encode(x='Time:T', y='Score:Q', color='Group:N', tooltip=['Group', 'Time', 'Score']).interactive()
            st.altair_chart(chart, use_container_width=True)

# TAB 4 (PRIVILEGES)
with tabs[3]:
    st.markdown("## 🏛️ ทำเนียบสิทธิพิเศษ")
    ranks_data = [
        ("👶 เด็กฝึกงาน", "0+ XP", "#64748b", "#f1f5f9", "🔍 สิทธิ์ Check-up", "ครูช่วยตรวจทานเบื้องต้นก่อนส่งจริง"),
        ("👨‍💼 พนักงาน", "100+ XP", "#10b981", "#d1fae5", "⏰ สิทธิ์ Time Extension", "ส่งช้าได้ 2 สัปดาห์ ไม่หักคะแนน"),
        ("👔 หัวหน้าแผนก", "300+ XP", "#3b82f6", "#dbeafe", "🔄 สิทธิ์ Second Chance", "สอบแก้ตัวหรือทำใบงานใหม่ได้ ้เลือกได้ 1 งานต่อ 1 หน่วยการเรียนรู้"),
        ("💼 หัวหน้าฝ่าย", "600+ XP", "#8b5cf6", "#f3e8ff", "✂️ สิทธิ์ Workload Cut", "ลดภาระงาน 50% แต่ได้คะแนนเต็ม"),
        ("👑 ประธาน", "1000+ XP", "#f59e0b", "#fef3c7", "🛡️ Immunity & Bonus", "ไม่ทำ 3 งานได้ + โบนัสฟรี 1 คะแนนทุกงานถ้าส่ง")
    ]
    for name, xp, col, bg, title, desc in ranks_data:
        st.markdown(f"<div class='rank-detail-card' style='border-left-color: {col};'><h3 style='color:{col}; margin:0;'>{name}</h3><span class='status-badge' style='background:{bg}; color:{col};'>{xp}</span><hr style='margin:10px 0;'><h4>{title}</h4><p>{desc}</p></div>", unsafe_allow_html=True)

# TAB 5 (MANAGEMENT)
with tabs[4]:
    st.markdown("### 🛠️ จัดการข้อมูลกลุ่ม")
    
    # 1. สร้างกลุ่มใหม่
    with st.expander("➕ สร้างกลุ่มใหม่ (Create Group)", expanded=False):
        with st.form("new_g"):
            n = st.text_input("ตั้งชื่อกลุ่ม")
            m = st.text_area("รายชื่อสมาชิก")
            if st.form_submit_button("สร้างกลุ่ม"): 
                if db.create(selected_room, n, m, df): st.success("สร้างสำเร็จ!"); time.sleep(1); st.rerun()
                else: st.error("ชื่อกลุ่มซ้ำกับที่มีอยู่แล้ว")

    st.markdown("---")
    
    # 2. แก้ไข / ย้ายสมาชิก
    st.markdown("#### ✏️ แก้ไข / ย้ายสมาชิก")
    col_edit, col_del = st.columns([2, 1])
    
    with col_edit:
        edit_target = st.selectbox("เลือกกลุ่มที่จะแก้ไข", ["-"] + list(room_df['GroupName'].unique()), key="edit_selector")
        
        if edit_target != "-":
            curr_row = room_df[room_df['GroupName'] == edit_target].iloc[0]
            with st.form("edit_form"):
                new_n = st.text_input("แก้ไขชื่อกลุ่ม", value=curr_row['GroupName'])
                new_m = st.text_area("แก้ไขรายชื่อสมาชิก (ย้ายเข้า-ออก)", value=curr_row['Members'], height=150)
                
                if st.form_submit_button("💾 บันทึกการแก้ไข"):
                    if db.edit_group(selected_room, edit_target, new_n, new_m, df):
                        st.success("บันทึกเรียบร้อย!"); time.sleep(1); st.rerun()
                    else:
                        st.error("ชื่อกลุ่มใหม่ซ้ำกับกลุ่มอื่น")

    # 3. ลบกลุ่ม
    with col_del:
        st.error("🗑️ โซนอันตราย")
        del_target = st.selectbox("เลือกกลุ่มที่จะลบ", ["-"] + list(room_df['GroupName'].unique()), key="del_selector")
        if del_target != "-" and st.button("ยืนยันการลบกลุ่ม", type="primary"):
            db.delete(selected_room, del_target, df)
            st.rerun()

    # 4. แก้ไขประวัติคะแนน
    st.markdown("---")
    with st.expander("⚡ แก้ไขประวัติคะแนน (Advanced)", expanded=False):
        pe = st.selectbox("เลือกกลุ่มเพื่อแก้ประวัติ", ["-"]+list(room_df['GroupName'].unique()), key="pe_selector")
        if pe!="-":
            r = room_df[room_df['GroupName']==pe].iloc[0]
            try: h = json.loads(r['HistoryLog'])
            except: h=[]
            ed = st.data_editor(pd.DataFrame(h), num_rows="dynamic", use_container_width=True)
            if st.button("บันทึกประวัติใหม่"):
                if db.power_edit(selected_room, pe, ed, df, be): st.success("Saved"); st.rerun()
