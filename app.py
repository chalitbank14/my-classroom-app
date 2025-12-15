import streamlit as st
import pandas as pd
import altair as alt
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time
import json
import uuid
# --- ส่วน Import ที่ต้องเพิ่ม ---
from PIL import Image, ImageDraw, ImageFont
import io

# ==============================================================================
# ฟังก์ชันสร้างรูปภาพจัดอันดับ (Image Generator Engine)
# ==============================================================================
def generate_image(room_name, df, rank_sys):
    # 1. ตั้งค่าหน้ากระดาษ (แนวตั้งมือถือ Width 1080px คมชัด)
    W, ROW_H = 1080, 180
    HEADER_H = 400
    # คำนวณความสูงตามจำนวนกลุ่มที่มี
    H = HEADER_H + (len(df) * ROW_H) + 100 
    
    # สร้างกระดาษเปล่าสีพื้นหลัง
    img = Image.new('RGB', (W, H), color='#F8FAFC')
    draw = ImageDraw.Draw(img)
    
    # 2. โหลดฟอนต์ (ถ้าไม่มีไฟล์ จะพยายามใช้ค่า Default)
    try:
        # ใช้ขนาดใหญ่เพื่อให้ภาพคมชัด
        font_title = ImageFont.truetype("Sarabun-Bold.ttf", 120)
        font_sub = ImageFont.truetype("Sarabun-Bold.ttf", 60)
        font_name = ImageFont.truetype("Sarabun-Bold.ttf", 70)
        font_detail = ImageFont.truetype("Sarabun-Regular.ttf", 40)
        font_score = ImageFont.truetype("Sarabun-Bold.ttf", 90)
        font_rank = ImageFont.truetype("Sarabun-Bold.ttf", 50)
    except:
        # กรณีฉุกเฉินหาไฟล์ไม่เจอ
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_name = ImageFont.load_default()
        font_detail = ImageFont.load_default()
        font_score = ImageFont.load_default()
        font_rank = ImageFont.load_default()

    # 3. วาดส่วนหัว (Header) สไตล์ Hero Gradient
    # วาดสี่เหลี่ยมสีน้ำเงินไล่โทน (จำลองด้วยการวาดสีพื้น)
    draw.rectangle([(0, 0), (W, HEADER_H)], fill='#4338CA')
    
    # วาดวงกลมตกแต่งให้ดูโมเดิร์น
    draw.ellipse([(800, -100), (1200, 300)], fill='#4F46E5')
    draw.ellipse([(-100, 200), (200, 500)], fill='#3730A3')
    
    # เขียนข้อความหัวกระดาษ
    draw.text((W/2, 120), f"LEADERBOARD", font=font_sub, fill='#A5B4FC', anchor="mm")
    draw.text((W/2, 230), f"{room_name}", font=font_title, fill='white', anchor="mm")
    
    # 4. วนลูปวาดรายชื่อกลุ่ม (Loop Drawing)
    sorted_df = df.sort_values("XP", ascending=False).reset_index(drop=True)
    current_y = HEADER_H + 40
    
    for i, row in sorted_df.iterrows():
        # กำหนดสีตามอันดับ
        if i == 0:   badge_col = "#F59E0B" # ทอง
        elif i == 1: badge_col = "#94A3B8" # เงิน
        elif i == 2: badge_col = "#B45309" # ทองแดง
        else:        badge_col = "#64748B" # ทั่วไป
        
        # สีคะแนน (แดงถ้าติดลบ / เขียวถ้าบวก)
        score_col = "#EF4444" if row['XP'] < 0 else "#10B981"
        
        # วาดกล่องการ์ด (Card Background)
        # เงา
        draw.rounded_rectangle([(45, current_y+5), (W-45, current_y+165)], radius=30, fill='#E2E8F0')
        # พื้นขาว
        draw.rounded_rectangle([(40, current_y), (W-40, current_y+160)], radius=30, fill='white')
        # แถบสีด้านซ้าย
        draw.rounded_rectangle([(40, current_y), (70, current_y+160)], radius=30, fill=badge_col, corners=(True, False, False, True))
        
        # เขียนอันดับ (#1, #2...)
        draw.text((130, current_y+80), f"#{i+1}", font=font_name, fill=badge_col, anchor="mm")
        
        # เขียนชื่อกลุ่ม
        draw.text((220, current_y+60), str(row['GroupName']), font=font_name, fill='#1E293B', anchor="lm")
        
        # เขียนสมาชิก (ตัดคำถ้าเว้นวรรคยาว)
        mem_txt = str(row['Members'])
        if len(mem_txt) > 50: mem_txt = mem_txt[:50] + "..."
        draw.text((220, current_y+115), mem_txt, font=font_detail, fill='#64748B', anchor="lm")
        
        # เขียนคะแนน
        draw.text((W-80, current_y+80), f"{row['XP']}", font=font_score, fill=score_col, anchor="rm")
        
        # ขยับแกน Y ลงมาเพื่อวาดแถวถัดไป
        current_y += ROW_H + 20
        
    # ใส่ Footer เครดิตเล็กๆ
    draw.text((W/2, H-50), "Generated by Classroom OS", font=font_detail, fill='#94A3B8', anchor="mm")

    # แปลงข้อมูลเป็น Bytes เพื่อส่งให้ปุ่ม Download
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()
# ==============================================================================
# 1. SYSTEM CONFIGURATION & ULTRA UI
# ==============================================================================
st.set_page_config(
    page_title="Classroom OS: Gamification",
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
        <h4 style="margin:0; opacity:0.8;">CLASSROOM OS: Gamification </h4>
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
            if st.button("📚 ส่งงานตรงเวลา (+100)", type="primary"): process_xp("ส่งงานตรงเวลา", 100)
            if st.button("🙋 ตอบคำถาม (+20)"): process_xp("ตอบคำถาม", 20)
            if st.button("🏆 ชนะกิจกรรม (+100)"): process_xp("ชนะกิจกรรม", 100)
            st.markdown("---")
            if st.button("🐢 ส่งช้า (-100)"): process_xp("ส่งงานล่าช้า", -100)

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
    if room_df.empty:
        st.info("ยังไม่มีข้อมูลกลุ่ม")
    else:
        # 1. ส่วนปุ่มดาวน์โหลด (วางไว้บนสุด)
        col_btn, col_blank = st.columns([1, 2])
        with col_btn:
            # สร้างรูปภาพเตรียมไว้
            img_data = generate_image(selected_room, room_df, rs)
            
            st.download_button(
                label="🖼️ บันทึกรูปจัดอันดับ (Save Image)",
                data=img_data,
                file_name=f"Leaderboard_{selected_room}.png",
                mime="image/png",
                use_container_width=True,
                type="primary" # ปุ่มสีเด่น
            )
        
        st.markdown("---")

        # 2. ส่วนแสดงผลบนหน้าเว็บ (เหมือนเดิม)
        sorted_df = room_df.sort_values("XP", ascending=False).reset_index(drop=True)
        for i, row in sorted_df.iterrows():
            r = rs.get_rank(row['XP'])
            pct, lbl = rs.get_progress(row['XP'])
            
            # แปลง Badges
            try: bdgs = json.loads(row['Badges'])
            except: bdgs = []
            icons = "".join([be.catalog[b] for b in bdgs if b in be.catalog])
            
            col = "#ef4444" if row['XP'] < 0 else r['color']
            
            st.markdown(f"""
            <div class="glass-card" style="border-left: 6px solid {col};">
                <div style="display:flex; justify-content:space-between;">
                    <div>
                        <span style="font-weight:bold; color:#64748b;">#{i+1}</span>
                        <span style="font-size:1.2rem; font-weight:bold; margin-left:10px;">{row['GroupName']}</span>
                        <div style="font-size:0.9rem; color:#64748b; margin-top:4px;">{row['Members']}</div>
                        <div style="margin-top:5px; font-size:1.2rem;">{icons}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:1.8rem; font-weight:800; color:{col};">{row['XP']}</div>
                        <span class="status-badge" style="background:{r['bg']}; color:{r['color']}">{r['th']}</span>
                    </div>
                </div>
                <div style="margin-top:10px; font-size:0.8rem; color:grey; display:flex; justify-content:space-between;">
                    <span>Next Level</span><span>{lbl}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(pct)

# --- TAB 3: EVOLUTION ANALYTICS ---
with tabs[2]:
    if room_df.empty:
        st.info("ยังไม่มีข้อมูลกลุ่มในห้องนี้")
    else:
        # =========================================================
        # PART 1: ROOM OVERVIEW (สถิติรวมของห้อง)
        # =========================================================
        st.markdown("#### 📊 ภาพรวมห้องเรียน (Room Overview)")
        
        # คำนวณสถิติ
        total_xp = room_df['XP'].sum()
        avg_xp = room_df['XP'].mean()
        # หากลุ่มที่มีคะแนนสูงสุด
        top_group_row = room_df.loc[room_df['XP'].idxmax()]
        top_group_name = top_group_row['GroupName']
        top_group_xp = top_group_row['XP']
        
        # แสดงผลเป็นกล่อง 3 กล่อง
        m1, m2, m3 = st.columns(3)
        
        # กล่องที่ 1: Top Group
        m1.markdown(f"""
        <div class='stat-box'>
            <h3 style='margin:0; font-size:1rem; color:grey;'>🏆 Top Group</h3>
            <div style='color:#6366f1; font-weight:bold; font-size:1.5rem;'>{top_group_name}</div>
            <small>({top_group_xp} XP)</small>
        </div>
        """, unsafe_allow_html=True)
        
        # กล่องที่ 2: Total XP
        m2.markdown(f"""
        <div class='stat-box'>
            <h3 style='margin:0; font-size:1rem; color:grey;'>✨ Total XP (Class)</h3>
            <div style='color:#10b981; font-weight:bold; font-size:1.5rem;'>{total_xp:,}</div>
            <small>คะแนนรวมทั้งห้อง</small>
        </div>
        """, unsafe_allow_html=True)
        
        # กล่องที่ 3: Average XP
        m3.markdown(f"""
        <div class='stat-box'>
            <h3 style='margin:0; font-size:1rem; color:grey;'>📈 Average XP</h3>
            <div style='color:#f59e0b; font-weight:bold; font-size:1.5rem;'>{avg_xp:.1f}</div>
            <small>คะแนนเฉลี่ยต่อกลุ่ม</small>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # =========================================================
        # PART 2: EVOLUTION RACE CHART (กราฟเส้นรวมทุกกลุ่ม)
        # =========================================================
        st.markdown("#### 🏎️ เส้นทางวิวัฒนาการ (XP Evolution Race)")
        st.caption("กราฟเปรียบเทียบการเติบโตของคะแนนแต่ละกลุ่มตามช่วงเวลา")
        
        # ดึงประวัติของ "ทุกกลุ่ม" มารวมกัน
        all_history = []
        for _, row in room_df.iterrows():
            try:
                logs = json.loads(row['HistoryLog'])
                for log in logs:
                    all_history.append({
                        'Group': row['GroupName'],
                        'Timestamp': pd.to_datetime(log['ts']),
                        'Score': log.get('balance', 0), # ใช้ balance ณ ตอนนั้น
                        'Reason': log['reason'],
                        'Change': log['amount']
                    })
            except:
                pass
            
        if all_history:
            hist_df = pd.DataFrame(all_history)
            
            # สร้างกราฟเส้น Multi-line Chart
            chart = alt.Chart(hist_df).mark_line(point=True).encode(
                # แกน X เป็นเวลา
                x=alt.X('Timestamp', title='เวลาที่บันทึก', axis=alt.Axis(format='%d/%m %H:%M')),
                # แกน Y เป็นคะแนนสะสม
                y=alt.Y('Score', title='คะแนนสะสม (XP)'),
                # สีเส้นแบ่งตามชื่อกลุ่ม
                color=alt.Color('Group', scale=alt.Scale(scheme='category20'), title='ชื่อกลุ่ม'),
                # Tooltip เวลาเอาเมาส์ชี้
                tooltip=[
                    alt.Tooltip('Group', title='กลุ่ม'),
                    alt.Tooltip('Timestamp', title='เวลา', format='%d/%m %H:%M'),
                    alt.Tooltip('Score', title='คะแนนรวม'),
                    alt.Tooltip('Change', title='ล่าสุด (+/-)'),
                    alt.Tooltip('Reason', title='เหตุผล')
                ]
            ).properties(
                height=450, # ความสูงกราฟ
                width='container'
            ).interactive() # ทำให้ซูมเข้าออก/เลื่อนได้
            
            st.altair_chart(chart, use_container_width=True)
            
            # =========================================================
            # PART 3: COMBINED RECENT ACTIVITY (ตารางประวัติรวม)
            # =========================================================
            st.markdown("#### 🕒 ความเคลื่อนไหวล่าสุด (All Activity)")
            
            # เรียงลำดับตามเวลาล่าสุด
            recent_df = hist_df.sort_values('Timestamp', ascending=False).head(50)
            
            # จัด Format ตารางให้สวยงาม
            st.dataframe(
                recent_df[['Timestamp', 'Group', 'Reason', 'Change', 'Score']],
                column_config={
                    "Timestamp": st.column_config.DatetimeColumn("เวลา", format="D MMM, HH:mm"),
                    "Group": "กลุ่ม",
                    "Reason": "รายการกิจกรรม",
                    "Change": st.column_config.NumberColumn("เปลี่ยนแปลง", format="%+d XP"),
                    "Score": st.column_config.NumberColumn("ยอดคงเหลือ", format="%d XP")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("ยังไม่มีประวัติการให้คะแนนในห้องนี้ กราฟจะแสดงเมื่อมีการบันทึกคะแนนแรก")

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
