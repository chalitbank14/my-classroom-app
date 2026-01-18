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
# SECTION 1: SYSTEM CONFIGURATION & STYLES
# ==============================================================================
st.set_page_config(
    page_title="Classroom OS: Ultimate",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Advanced CSS Styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&family=Prompt:wght@300;400;600&display=swap');
    
    :root {
        --primary-color: #4f46e5;
        --secondary-color: #3b82f6;
        --bg-color: #F8FAFC;
        --text-color: #1E293B;
    }

    html, body, [class*="css"] {
        font-family: 'Sarabun', 'Prompt', sans-serif;
        background-color: var(--bg-color);
        color: var(--text-color);
    }
    
    /* Hero Section */
    .hero-container {
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        padding: 2rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.3);
        display: flex;
        justify-content: space-between;
        align-items: center;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Modern Card */
    .glass-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 1rem;
    }
    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }

    /* Rank Detail Cards */
    .rank-detail-card {
        padding: 20px;
        border-radius: 15px;
        background: white;
        border-left: 8px solid #ddd;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }

    /* Custom Buttons */
    .stButton button {
        width: 100%;
        height: 55px;
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: 1.05rem !important;
        letter-spacing: 0.5px;
        transition: all 0.2s;
    }
    
    /* Status Badges */
    .status-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 50px;
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Typography Utilities */
    .text-huge { font-size: 2.5rem; font-weight: 800; line-height: 1.2; }
    .text-lg { font-size: 1.2rem; font-weight: 600; }
    .text-muted { color: #64748b; font-size: 0.9rem; }
    
    /* Score Colors */
    .score-positive { color: #10b981; font-weight: 800; }
    .score-negative { color: #ef4444; font-weight: 800; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# SECTION 2: BUSINESS LOGIC LAYERS
# ==============================================================================

class RankSystem:
    """
    ระบบจัดการยศและสิทธิพิเศษ (Rank & Privilege System)
    กำหนด Logic ของแต่ละยศ และสิทธิประโยชน์ที่จะได้รับ
    """
    def __init__(self):
        self.ranks = [
            {
                "name": "PRESIDENT", 
                "th": "👑 ประธานรุ่น", 
                "min_xp": 1000, 
                "color": "#f59e0b", 
                "bg": "#fef3c7", 
                "desc": "Immun. (ไม่ทำ 3 งาน) + โบนัส 1 ทุกงาน"
            },
            {
                "name": "DIRECTOR", 
                "th": "💼 หัวหน้าฝ่าย", 
                "min_xp": 600, 
                "color": "#8b5cf6", 
                "bg": "#f3e8ff", 
                "desc": "Workload Cut (ลดงาน 50%)"
            },
            {
                "name": "MANAGER", 
                "th": "👔 หัวหน้าแผนก", 
                "min_xp": 300, 
                "color": "#3b82f6", 
                "bg": "#dbeafe", 
                "desc": "Second Chance (แก้ตัวได้ 1 งาน/หน่วย)"
            },
            {
                "name": "EMPLOYEE", 
                "th": "👨‍💼 พนักงาน", 
                "min_xp": 100, 
                "color": "#10b981", 
                "bg": "#d1fae5", 
                "desc": "Time Ext. (ส่งช้าได้ 2 สัปดาห์)"
            },
            {
                "name": "INTERN", 
                "th": "👶 เด็กฝึกงาน", 
                "min_xp": 0, 
                "color": "#64748b", 
                "bg": "#f1f5f9", 
                "desc": "Check-up (ครูช่วยตรวจก่อนส่ง)"
            },
            {
                "name": "PROBATION", 
                "th": "⚠️ ทัณฑ์บน", 
                "min_xp": -999999, 
                "color": "#ef4444", 
                "bg": "#fee2e2", 
                "desc": "ต้องรีบทำงานแก้คะแนนด่วนที่สุด!"
            }
        ]

    def get_rank(self, xp):
        """ค้นหายศจาก XP ปัจจุบัน"""
        if xp < 0: return self.ranks[-1] # Probation
        for rank in self.ranks:
            if rank['name'] != "PROBATION" and xp >= rank['min_xp']:
                return rank
        return self.ranks[-2] # Default to Intern if something weird happens

    def get_progress(self, xp):
        """คำนวณ Progress Bar สู่ยศถัดไป"""
        if xp < 0: return 0.0, "🔴 Warning: ติดลบ"
        
        for i, rank in enumerate(self.ranks):
            if rank['name'] != "PROBATION" and xp >= rank['min_xp']:
                if i > 0: # ถ้ายังไม่ใชยศสูงสุด (President คือ index 0)
                    next_rank = self.ranks[i-1]
                    target = next_rank['min_xp']
                    # ป้องกันการหารด้วย 0
                    if target == 0: target = 100 
                    pct = min(1.0, xp / target)
                    return pct, f"{int(pct*100)}% to {next_rank['th']}"
                return 1.0, "MAX LEVEL"
        return 0.0, "0%"

class BadgeEngine:
    """
    ระบบจัดการเหรียญตรา (Gamification Badges)
    """
    def __init__(self):
        self.catalog = {
            "wealthy": "💎",    # รวย (800+ XP)
            "sniper": "🎯",     # แม่นยำ (เคยได้คะแนนก้อนใหญ่)
            "debtor": "💸",     # เป็นหนี้ (ติดลบ)
            "phoenix": "🔥",    # เคยกลับตัวได้
            "first_blood": "🩸" # เลือดแรก (มีประวัติแล้ว)
        }

    def check(self, xp, hist):
        """ตรวจสอบเงื่อนไขและคืนค่า List ของ Key เหรียญที่ได้รับ"""
        badges = []
        if xp >= 800: badges.append("wealthy")
        if xp < 0: badges.append("debtor")
        if any(h['amount'] >= 100 for h in hist): badges.append("sniper")
        if len(hist) > 0: badges.append("first_blood")
        return list(set(badges))

    def render_icons(self, badge_list):
        """แปลง List เหรียญเป็น String Emoji"""
        return "".join([self.catalog[b] for b in badge_list if b in self.catalog])

# ==============================================================================
# SECTION 3: DATA LAYER (Google Sheets Integration)
# ==============================================================================

class DataManager:
    """
    จัดการการเชื่อมต่อฐานข้อมูล Google Sheets และ CRUD Operations
    """
    def __init__(self):
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
            self.cols = ['Room', 'GroupName', 'XP', 'Members', 'LastUpdated', 'HistoryLog', 'Badges']
        except Exception as e:
            st.error(f"Critical DB Connection Error: {e}")
            st.stop()

    def _sanitize_df(self, df):
        """ทำความสะอาด Dataframe ป้องกัน Error ค่า Null"""
        if df.empty or not set(self.cols).issubset(df.columns):
            return pd.DataFrame(columns=self.cols)
        
        df = df[self.cols].copy().dropna(how='all')
        df['XP'] = pd.to_numeric(df['XP'], errors='coerce').fillna(0).astype(int)
        for c in ['HistoryLog', 'Badges']:
            df[c] = df[c].fillna("[]").astype(str)
        return df

    def fetch(self):
        """ดึงข้อมูลทั้งหมดจาก Sheet"""
        try:
            df = self.conn.read(worksheet="Sheet1", ttl=0)
            return self._sanitize_df(df)
        except Exception:
            return pd.DataFrame(columns=self.cols)

    def save(self, df):
        """บันทึกข้อมูลลง Sheet และเคลียร์ Cache"""
        try:
            self.conn.update(worksheet="Sheet1", data=df)
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Save Failed: {e}")
            return False

    def create_group(self, room, name, members, df):
        """สร้างกลุ่มใหม่"""
        # เช็คชื่อซ้ำในห้องเดียวกัน
        if ((df['Room'] == room) & (df['GroupName'] == name)).any():
            return False
        
        new_row = pd.DataFrame([{
            "Room": room,
            "GroupName": name,
            "XP": 0,
            "Members": members,
            "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "HistoryLog": "[]",
            "Badges": "[]"
        }])
        return self.save(pd.concat([df, new_row], ignore_index=True))

    def edit_group(self, room, old_name, new_name, new_members, df):
        """แก้ไขชื่อกลุ่มและสมาชิก"""
        # ถ้าเปลี่ยนชื่อ ต้องเช็คว่าชื่อใหม่ซ้ำไหม
        if new_name != old_name and ((df['Room'] == room) & (df['GroupName'] == new_name)).any():
            return False
            
        idx = df[(df['Room'] == room) & (df['GroupName'] == old_name)].index
        if not idx.empty:
            i = idx[0]
            df.at[i, 'GroupName'] = new_name
            df.at[i, 'Members'] = new_members
            df.at[i, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
            return self.save(df)
        return False

    def delete_group(self, room, name, df):
        """ลบกลุ่ม"""
        new_df = df[~((df['Room'] == room) & (df['GroupName'] == name))]
        return self.save(new_df)

    def update_xp(self, room, groups, amount, reason, df, badge_engine):
        """อัปเดตคะแนน (รองรับหลายกลุ่มพร้อมกัน)"""
        if isinstance(groups, str): groups = [groups]
        updated_count = 0
        
        for grp in groups:
            idx = df[(df['Room'] == room) & (df['GroupName'] == grp)].index
            if not idx.empty:
                i = idx[0]
                
                # Load History
                try: hist = json.loads(df.at[i, 'HistoryLog'])
                except: hist = []
                
                # Create Log Entry
                new_entry = {
                    "id": str(uuid.uuid4())[:8],
                    "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "reason": reason,
                    "amount": int(amount)
                }
                hist.insert(0, new_entry)
                
                # Recalculate Total
                total = sum(x['amount'] for x in hist)
                hist[0]['balance'] = total
                
                # Update DataFrame
                df.at[i, 'XP'] = total
                df.at[i, 'HistoryLog'] = json.dumps(hist, ensure_ascii=False)
                df.at[i, 'Badges'] = json.dumps(badge_engine.check(total, hist), ensure_ascii=False)
                df.at[i, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                updated_count += 1
                
        if updated_count > 0:
            return self.save(df), updated_count
        return False, 0

    def advanced_edit_history(self, room, name, new_history_df, df, badge_engine):
        """แก้ไขประวัติคะแนนแบบละเอียด (Power Edit)"""
        idx = df[(df['Room'] == room) & (df['GroupName'] == name)].index
        if not idx.empty:
            i = idx[0]
            
            # Convert DF back to List of Dicts
            hist_list = new_history_df.to_dict('records')
            
            # Recalculate Balance Logic
            # 1. Sort by Time Ascending to calc running balance
            hist_list_sorted = sorted(hist_list, key=lambda x: x['ts'])
            running_total = 0
            for h in hist_list_sorted:
                running_total += int(h['amount'])
                h['balance'] = running_total
                
            # 2. Sort back to Time Descending for storage
            final_hist = sorted(hist_list_sorted, key=lambda x: x['ts'], reverse=True)
            total_xp = running_total
            
            df.at[i, 'XP'] = total_xp
            df.at[i, 'HistoryLog'] = json.dumps(final_hist, ensure_ascii=False)
            df.at[i, 'Badges'] = json.dumps(badge_engine.check(total_xp, final_hist), ensure_ascii=False)
            return self.save(df)
        return False

# ==============================================================================
# SECTION 4: IMAGE GENERATION ENGINE (The Robust Fix)
# ==============================================================================

class LeaderboardGenerator:
    """
    คลาสสำหรับสร้างรูปภาพ Leaderboard โดยเฉพาะ
    แก้ปัญหา Text Overlapping และการจัดวาง Layout
    """
    def __init__(self, width=1400, header_height=700, row_height=350, footer_height=150):
        self.W = width
        self.H_HEADER = header_height
        self.H_ROW = row_height
        self.H_FOOTER = footer_height
        
        # Color Palette
        self.COLOR_BG = "#F8FAFC"
        self.COLOR_HEADER = "#4338CA"
        self.COLOR_CARD_BG = "#FFFFFF"
        self.COLOR_CARD_SHADOW = "#CBD5E1"
        self.COLOR_TEXT_MAIN = "#1E293B"
        self.COLOR_TEXT_SUB = "#64748B"

    def clean_text(self, text):
        """ลบ Emoji ออกเพื่อป้องกัน Error สี่เหลี่ยม"""
        blocklist = ["👑", "💼", "👔", "👨‍💼", "👶", "⚠️", "🩸", "💎", "💸", "🎯", "🔥", "🏆"]
        for char in blocklist:
            text = text.replace(char, "")
        return text.strip()

    def load_font(self, font_name, size):
        """โหลดฟอนต์พร้อมระบบ Fallback"""
        try:
            return ImageFont.truetype(font_name, size)
        except:
            return ImageFont.load_default()

    def draw_text_fit(self, draw, text, max_width, start_x, start_y, font_name, initial_size, color, anchor="ls"):
        """
        หัวใจสำคัญของการแก้ปัญหา Overlap:
        ฟังก์ชันนี้จะลดขนาดฟอนต์ลงเรื่อยๆ จนกว่าข้อความจะพอดีกับ max_width
        """
        font_size = initial_size
        min_size = 40 # ขนาดเล็กสุดที่ยอมรับได้
        
        current_font = self.load_font(font_name, font_size)
        
        # วนลูปตรวจสอบความกว้าง
        while font_size > min_size:
            text_width = current_font.getlength(text)
            if text_width <= max_width:
                break
            # ลดขนาดลง
            font_size -= 4
            current_font = self.load_font(font_name, font_size)
            
        # วาดข้อความลงไป
        draw.text((start_x, start_y), text, font=current_font, fill=color, anchor=anchor)
        return font_size # คืนค่าขนาดที่ใช้จริงเผื่อเอาไปใช้คำนวณต่อ

    def generate(self, room_name, df, rank_sys):
        """Main Function ในการวาดภาพ"""
        # เตรียมข้อมูล
        sorted_df = df.sort_values("XP", ascending=False).reset_index(drop=True)
        total_h = self.H_HEADER + (len(sorted_df) * self.H_ROW) + self.H_FOOTER
        
        # สร้าง Canvas
        img = Image.new('RGB', (self.W, total_h), color=self.COLOR_BG)
        draw = ImageDraw.Draw(img)
        
        # --- 1. Draw Header ---
        draw.rectangle([(0, 0), (self.W, self.H_HEADER)], fill=self.COLOR_HEADER)
        # Decorative Circles
        draw.ellipse([(1000, -100), (1600, 500)], fill='#4F46E5')
        draw.ellipse([(-100, 300), (400, 800)], fill='#3730A3')
        
        # Header Texts (ใช้ตำแหน่ง Y ที่ห่างกันชัดเจน)
        f_icon = self.load_font("Sarabun-Bold.ttf", 200)
        f_title = self.load_font("Sarabun-Bold.ttf", 65)
        f_room = self.load_font("Sarabun-Bold.ttf", 160)
        
        draw.text((self.W//2, 200), "🏆", font=self.load_font("Sarabun-Regular.ttf", 200), fill='white', anchor="mm") # Emoji font fallback issue handled by PIL usually if simple, else use clean text
        # หมายเหตุ: ถ้าใช้ PIL ธรรมดา emoji สีอาจไม่ขึ้น ให้ใช้ text "Award" แทน หรือทำใจเรื่องสี
        # เพื่อความชัวร์ ใช้ Code วาดถ้วยรางวัล หรือใช้ Emoji ธรรมดา
        
        draw.text((self.W//2, 380), "CLASSROOM LEADERBOARD", font=f_title, fill='#A5B4FC', anchor="mm")
        draw.text((self.W//2, 580), f"{room_name}", font=f_room, fill='white', anchor="mm")
        
        # --- 2. Draw Rows ---
        current_y = self.H_HEADER + 50
        
        f_rank_num = self.load_font("Sarabun-Bold.ttf", 90)
        f_score_num = self.load_font("Sarabun-Bold.ttf", 110)
        f_small_label = self.load_font("Sarabun-Bold.ttf", 55)
        f_privilege = self.load_font("Sarabun-Regular.ttf", 40)
        f_members = self.load_font("Sarabun-Regular.ttf", 48)

        for i, row in sorted_df.iterrows():
            rank_info = rank_sys.get_rank(row['XP'])
            pct, _ = rank_sys.get_progress(row['XP'])
            
            # Determine Rank Color
            if i == 0:   theme_col = "#F59E0B" # Gold
            elif i == 1: theme_col = "#94A3B8" # Silver
            elif i == 2: theme_col = "#B45309" # Bronze
            else:        theme_col = "#64748B" # Gray
            
            score_col = "#EF4444" if row['XP'] < 0 else "#10B981"
            
            # Card Background (Shadow + White Body)
            card_x_start = 40
            card_width = self.W - 80
            draw.rounded_rectangle(
                [(card_x_start+5, current_y+10), (card_x_start+card_width+5, current_y+self.H_ROW-15)], 
                radius=35, fill=self.COLOR_CARD_SHADOW
            )
            draw.rounded_rectangle(
                [(card_x_start, current_y), (card_x_start+card_width, current_y+self.H_ROW-25)], 
                radius=35, fill=self.COLOR_CARD_BG
            )
            
            # --- Column 1: Rank Circle (Left) ---
            circle_cx = 150
            circle_cy = current_y + 130
            r = 85
            draw.ellipse([(circle_cx-r, circle_cy-r), (circle_cx+r, circle_cy+r)], fill=theme_col)
            draw.text((circle_cx, circle_cy), str(i+1), font=f_rank_num, fill="white", anchor="mm")
            
            # --- Column 2: Group Info (Center) ---
            text_x_start = 280
            max_text_width = 700 # จำกัดความกว้างไม่ให้ชนคะแนน
            
            # 2.1 Group Name (Dynamic Fit)
            # ใช้พิกัด Y=90 (เทียบจาก Top ของ Card)
            # ใช้ anchor='ls' (Left-Baseline) เพื่อรองรับสระภาษาไทย
            group_name_y = current_y + 100 
            self.draw_text_fit(
                draw, self.clean(str(row['GroupName'])), 
                max_text_width, text_x_start, group_name_y, 
                "Sarabun-Bold.ttf", 90, self.COLOR_TEXT_MAIN, anchor="ls"
            )
            
            # 2.2 Members (Truncate & Draw)
            members_text = self.clean(str(row['Members']))
            if len(members_text) > 65: members_text = members_text[:62] + "..."
            members_y = current_y + 170
            draw.text((text_x_start, members_y), members_text, font=f_members, fill=self.COLOR_TEXT_SUB, anchor="ls")
            
            # 2.3 Progress Bar
            bar_y = current_y + 220
            bar_w = 600
            bar_h = 16
            draw.rounded_rectangle([(text_x_start, bar_y), (text_x_start+bar_w, bar_y+bar_h)], radius=8, fill="#F1F5F9")
            if pct > 0:
                draw.rounded_rectangle([(text_x_start, bar_y), (text_x_start+int(bar_w*pct), bar_y+bar_h)], radius=8, fill=rank_info['color'])
            
            # 2.4 Rank Name & Privilege (Prevent Overlap)
            rank_text_x = text_x_start + bar_w + 30
            
            # Rank Title
            draw.text((rank_text_x, bar_y-5), self.clean(rank_info['th']), font=f_small_label, fill=rank_info['color'], anchor="lt")
            
            # Privilege Description (Dynamic Fit)
            priv_desc = self.clean(rank_info.get('desc', ''))
            priv_y = bar_y + 60
            self.draw_text_fit(
                draw, priv_desc, 
                450, # Max width สำหรับคำอธิบาย
                rank_text_x, priv_y, 
                "Sarabun-Regular.ttf", 40, self.COLOR_TEXT_SUB, anchor="ls"
            )

            # --- Column 3: Score (Right) ---
            score_x_end = self.W - 100
            
            # Score Number
            draw.text((score_x_end, current_y+110), f"{row['XP']}", font=f_score_num, fill=score_col, anchor="rs")
            # "XP" Label
            draw.text((score_x_end, current_y+160), "XP", font=f_small_label, fill="#94A3B8", anchor="rs")
            
            # Next Loop
            current_y += self.H_ROW
            
        # --- 3. Footer ---
        footer_y = total_h - 70
        f_footer = self.load_font("Sarabun-Regular.ttf", 45)
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M')
        draw.text((self.W//2, footer_y), f"Generated by Classroom OS • {timestamp}", font=f_footer, fill="#94A3B8", anchor="mm")
        
        # Export
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()

# ==============================================================================
# SECTION 5: INITIALIZATION & MAIN UI
# ==============================================================================

# Init Objects
db = DataManager()
rs = RankSystem()
be = BadgeEngine()
img_gen = LeaderboardGenerator()

# Sidebar
with st.sidebar:
    st.title("⚙️ Control Panel")
    selected_room = st.selectbox("เลือกห้องเรียน", ["ม.1/1", "ม.1/2", "ม.1/10"])
    
    st.divider()
    if st.button("⚠️ Repair Database (Reset Headers)"):
        try: 
            db.conn.update(worksheet="Sheet1", data=pd.DataFrame(columns=db.cols))
            st.success("Database Repaired!")
        except Exception as e: 
            st.error(f"Failed: {e}")
            
    st.divider()
    csv_data = db.fetch().to_csv(index=False).encode('utf-8')
    st.download_button("📥 Export CSV", csv_data, "classroom_data.csv")

# Fetch Data
all_df = db.fetch()
room_df = all_df[all_df['Room'] == selected_room].copy()

# Hero Section
st.markdown(f"""
<div class='hero-container'>
    <div>
        <h4 style='margin:0; opacity:0.9; letter-spacing:1px;'>CLASSROOM OS : ULTIMATE</h4>
        <h1 style='margin:0; font-size:3rem; font-weight:800;'>{selected_room}</h1>
    </div>
    <div style='text-align:right;'>
        <div style='font-size:3.5rem; font-weight:800;'>{len(room_df)}</div>
        <div style='opacity:0.8;'>Active Groups</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Main Tabs
tabs = st.tabs([
    "⚡ Command Center", 
    "🏆 Rankings & Image", 
    "📈 Analytics", 
    "ℹ️ Privileges Info", 
    "🛠️ Group Management"
])

# --- TAB 1: COMMAND CENTER ---
with tabs[0]:
    if room_df.empty:
        st.warning("⚠️ ยังไม่มีกลุ่มในห้องนี้ กรุณาไปที่แท็บ 'Group Management' เพื่อสร้างกลุ่มก่อนครับ")
    else:
        # Selection Mode
        col_mode, col_select = st.columns([1, 3])
        with col_mode:
            mode = st.radio("รูปแบบการให้คะแนน:", ["รายกลุ่ม (Single)", "หลายกลุ่ม (Batch)"])
        with col_select:
            if mode == "รายกลุ่ม (Single)":
                target_groups = [st.selectbox("🎯 เลือกกลุ่มเป้าหมาย", room_df['GroupName'].unique())]
            else:
                target_groups = st.multiselect("🎯 เลือกกลุ่มเป้าหมาย (หลายกลุ่ม)", room_df['GroupName'].unique())
        
        # Display Single Group Stats
        if len(target_groups) == 1:
            g_data = room_df[room_df['GroupName'] == target_groups[0]].iloc[0]
            rank_info = rs.get_rank(g_data['XP'])
            st.markdown(f"""
            <div style='text-align:center; padding:20px; border:2px solid #e2e8f0; border-radius:15px; background:white; margin: 20px 0;'>
                <div style='color:#64748b; font-size:0.9rem; margin-bottom:5px;'>CURRENT XP</div>
                <div class='{'score-negative' if g_data['XP'] < 0 else 'score-positive'}' style='font-size:3rem; line-height:1; margin-bottom:10px;'>
                    {g_data['XP']}
                </div>
                <span class='status-badge' style='background:{rank_info['bg']}; color:{rank_info['color']}'>
                    {rank_info['th']}
                </span>
            </div>
            """, unsafe_allow_html=True)

        st.divider()
        
        # Actions
        c1, c2 = st.columns(2)
        
        # Helper Function to Process Action
        def process_action(reason, amount):
            if not target_groups:
                st.error("กรุณาเลือกกลุ่มก่อนครับ")
                return
            success, count = db.update_xp(selected_room, target_groups, amount, reason, all_df, be)
            if success:
                st.toast(f"บันทึกสำเร็จ! ({count} กลุ่ม)", icon="✅")
                time.sleep(1)
                st.rerun()

        with c1:
            st.markdown("##### 🚀 ปุ่มด่วน (Quick Actions)")
            if st.button("📚 ส่งงานตรงเวลา (+50)", type="primary"): process_action("ส่งงานตรงเวลา", 50)
            if st.button("🙋 ตอบคำถามในคาบ (+20)"): process_action("ตอบคำถาม", 20)
            if st.button("🏆 ชนะกิจกรรมพิเศษ (+100)"): process_action("ชนะกิจกรรม", 100)
            st.markdown("---")
            if st.button("🐢 ส่งงานล่าช้า (-20)"): process_action("ส่งงานล่าช้า", -20)
            
        with c2:
            st.markdown("##### ✍️ กำหนดเอง (Custom)")
            with st.form("manual_xp"):
                reason = st.text_input("ระบุเหตุผล", placeholder="เช่น จิตพิสัย, ทำเวร")
                score = st.number_input("คะแนน (+/-)", step=5, value=0)
                if st.form_submit_button("💾 บันทึกรายการ"):
                    if reason and score != 0:
                        process_action(reason, score)
                    else:
                        st.warning("ระบุข้อมูลให้ครบถ้วน")

# --- TAB 2: RANKINGS & IMAGE ---
with tabs[1]:
    if room_df.empty:
        st.info("No Data available.")
    else:
        c_btn, c_view = st.columns([1, 2])
        with c_btn:
            st.markdown("### 🖼️ Leaderboard Image")
            st.caption("ระบบจะสร้างภาพความละเอียดสูง พร้อมจัดระเบียบตัวหนังสือให้อัตโนมัติ")
            
            # Generate Image using the new robust engine
            img_bytes = img_gen.generate(selected_room, room_df, rs)
            
            st.download_button(
                label="ดาวน์โหลดรูปภาพ (HQ PNG)",
                data=img_bytes,
                file_name=f"Leaderboard_{selected_room}.png",
                mime="image/png",
                type="primary",
                use_container_width=True
            )
            
        st.markdown("---")
        
        # Web View Leaderboard
        sorted_rows = room_df.sort_values("XP", ascending=False).reset_index(drop=True)
        for i, row in sorted_rows.iterrows():
            r = rs.get_rank(row['XP'])
            pct, lbl = rs.get_progress(row['XP'])
            
            # Badges
            try: badges = json.loads(row['Badges'])
            except: badges = []
            icon_str = be.render_icons(badges)
            
            card_col = "#ef4444" if row['XP'] < 0 else r['color']
            
            st.markdown(f"""
            <div class='glass-card' style='border-left: 6px solid {card_col};'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <div style='flex-grow:1;'>
                        <span style='font-size:1.5rem; font-weight:bold; color:#94a3b8; margin-right:15px;'>#{i+1}</span>
                        <span style='font-size:1.3rem; font-weight:bold;'>{row['GroupName']}</span>
                        <div style='font-size:0.9rem; color:#64748b; margin-top:5px;'>{row['Members']}</div>
                        <div style='margin-top:5px;'>{icon_str}</div>
                    </div>
                    <div style='text-align:right; min-width:120px;'>
                        <div style='font-size:2rem; font-weight:800; color:{card_col}; line-height:1;'>{row['XP']}</div>
                        <div style='font-size:0.8rem; color:#94a3b8;'>XP</div>
                    </div>
                </div>
                <div style='margin-top:15px; display:flex; justify-content:space-between; align-items:center;'>
                    <span class='status-badge' style='background:{r['bg']}; color:{r['color']}'>{r['th']}</span>
                    <span style='font-size:0.8rem; color:#64748b;'>{lbl}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(pct)

# --- TAB 3: ANALYTICS ---
with tabs[2]:
    if room_df.empty:
        st.info("No Data.")
    else:
        total_xp = room_df['XP'].sum()
        avg_xp = room_df['XP'].mean()
        top_grp = room_df.loc[room_df['XP'].idxmax()]['GroupName']
        
        m1, m2, m3 = st.columns(3)
        m1.markdown(f"<div class='stat-box'><h3>🏆 Top Group</h3><div style='color:#6366f1; font-size:1.5rem; font-weight:bold;'>{top_grp}</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='stat-box'><h3>✨ Class Total XP</h3><div style='color:#10b981; font-size:1.5rem; font-weight:bold;'>{total_xp:,}</div></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='stat-box'><h3>📈 Average XP</h3><div style='color:#f59e0b; font-size:1.5rem; font-weight:bold;'>{avg_xp:.1f}</div></div>", unsafe_allow_html=True)
        
        st.markdown("### 🏎️ XP Race History")
        history_data = []
        for _, row in room_df.iterrows():
            try:
                logs = json.loads(row['HistoryLog'])
                for log in logs:
                    history_data.append({
                        'Group': row['GroupName'],
                        'Time': pd.to_datetime(log['ts']),
                        'Score': log.get('balance', 0)
                    })
            except: pass
            
        if history_data:
            chart_df = pd.DataFrame(history_data)
            chart = alt.Chart(chart_df).mark_line(point=True).encode(
                x=alt.X('Time:T', title='Timeline', axis=alt.Axis(format='%d/%m %H:%M')),
                y=alt.Y('Score:Q', title='XP Balance'),
                color='Group:N',
                tooltip=['Group', 'Time', 'Score']
            ).properties(height=400).interactive()
            st.altair_chart(chart, use_container_width=True)

# --- TAB 4: PRIVILEGES INFO ---
with tabs[3]:
    st.markdown("## 🏛️ ทำเนียบสิทธิพิเศษ (Privilege Hierarchy)")
    
    # ดึงข้อมูลจาก RankSystem มาแสดงเลย เพื่อความถูกต้อง 100%
    for rank in rs.ranks:
        # ข้าม Probation
        if rank['name'] == "PROBATION": continue
        
        st.markdown(f"""
        <div class='rank-detail-card' style='border-left-color: {rank['color']};'>
            <div style='display:flex; justify-content:space-between; align-items:center;'>
                <h3 style='color:{rank['color']}; margin:0;'>{rank['th']}</h3>
                <span class='status-badge' style='background:{rank['bg']}; color:{rank['color']};'>{rank['min_xp']}+ XP</span>
            </div>
            <hr style='margin:10px 0; border-color:#f1f5f9;'>
            <h4 style='margin:0; font-size:1rem;'>🎁 สิทธิพิเศษ:</h4>
            <p style='margin-top:5px; color:#334155;'>{rank['desc']}</p>
        </div>
        """, unsafe_allow_html=True)

    # Probation แยกต่างหาก
    prob = rs.ranks[-1]
    st.markdown(f"""
    <div class='rank-detail-card' style='border-left-color: {prob['color']}; background:#fff1f2;'>
        <h3 style='color:{prob['color']}; margin:0;'>{prob['th']}</h3>
        <p style='margin-top:10px; font-weight:bold;'>{prob['desc']}</p>
    </div>
    """, unsafe_allow_html=True)

# --- TAB 5: MANAGEMENT ---
with tabs[4]:
    st.markdown("### 🛠️ Group Management System")
    
    # 1. Create
    with st.expander("➕ สร้างกลุ่มใหม่ (Create Group)", expanded=False):
        with st.form("create_grp"):
            n = st.text_input("ชื่อกลุ่ม")
            m = st.text_area("รายชื่อสมาชิก")
            if st.form_submit_button("ยืนยันสร้างกลุ่ม"):
                if db.create_group(selected_room, n, m, all_df):
                    st.success("สร้างกลุ่มสำเร็จ!"); time.sleep(1); st.rerun()
                else:
                    st.error("ชื่อกลุ่มซ้ำ! กรุณาใช้ชื่ออื่น")
                    
    st.markdown("---")
    
    # 2. Edit / Move
    st.markdown("#### ✏️ แก้ไขข้อมูล / ย้ายสมาชิก")
    col_e1, col_e2 = st.columns([2, 1])
    with col_e1:
        edit_target = st.selectbox("เลือกกลุ่มที่ต้องการแก้ไข", ["-"] + list(room_df['GroupName'].unique()))
        if edit_target != "-":
            curr = room_df[room_df['GroupName'] == edit_target].iloc[0]
            with st.form("edit_grp"):
                new_n = st.text_input("ชื่อกลุ่ม", value=curr['GroupName'])
                new_m = st.text_area("รายชื่อสมาชิก", value=curr['Members'], height=150)
                if st.form_submit_button("บันทึกการแก้ไข"):
                    if db.edit_group(selected_room, edit_target, new_n, new_m, all_df):
                        st.success("บันทึกแล้ว!"); time.sleep(1); st.rerun()
                    else:
                        st.error("บันทึกไม่ผ่าน (ชื่ออาจซ้ำ)")
                        
    # 3. Delete
    with col_e2:
        st.markdown("#### 🗑️ ลบกลุ่ม")
        st.warning("ลบแล้วกู้คืนไม่ได้")
        del_target = st.selectbox("เลือกกลุ่มที่จะลบ", ["-"] + list(room_df['GroupName'].unique()))
        if del_target != "-" and st.button("ยืนยันการลบ", type="primary"):
            db.delete_group(selected_room, del_target, all_df)
            st.rerun()
            
    st.markdown("---")
    
    # 4. Power Edit
    with st.expander("⚡ แก้ไขประวัติคะแนนย้อนหลัง (Power Edit)", expanded=False):
        pe_target = st.selectbox("เลือกกลุ่ม", ["-"] + list(room_df['GroupName'].unique()), key="pe")
        if pe_target != "-":
            r = room_df[room_df['GroupName'] == pe_target].iloc[0]
            try: h = json.loads(r['HistoryLog'])
            except: h = []
            
            edited_h = st.data_editor(pd.DataFrame(h), num_rows="dynamic", use_container_width=True)
            if st.button("บันทึกประวัติใหม่ทั้งหมด"):
                if db.advanced_edit_history(selected_room, pe_target, edited_h, all_df, be):
                    st.success("Saved!"); st.rerun()
