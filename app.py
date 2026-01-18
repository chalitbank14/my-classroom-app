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
# MODULE 1: CONFIGURATION & CONSTANTS
# ==============================================================================
class AppConfig:
    """
    เก็บค่าคงที่และการตั้งค่าทั้งหมดของระบบไว้ที่เดียว
    เพื่อให้แก้ไขง่ายและเป็นระเบียบ (Single Source of Truth)
    """
    # System Info
    APP_NAME = "Classroom OS: Enterprise"
    VERSION = "3.0.0 (Stable)"
    
    # Image Generation Config
    IMG_WIDTH = 1400
    IMG_HEADER_HEIGHT = 700
    IMG_ROW_HEIGHT = 420  # เพิ่มความสูงแถวเป็น 420px (จากเดิม 300-350) เพื่อกันทับ
    IMG_FOOTER_HEIGHT = 150
    
    # Colors Palette (Modern UI)
    COLOR_PRIMARY = "#4338CA"    # Indigo 700
    COLOR_SECONDARY = "#3730A3"  # Indigo 800
    COLOR_ACCENT = "#A5B4FC"     # Indigo 200
    COLOR_BG = "#F8FAFC"         # Slate 50
    COLOR_TEXT_MAIN = "#1E293B"  # Slate 800
    COLOR_TEXT_SUB = "#64748B"   # Slate 500
    
    # Card Colors
    COLOR_CARD_BG = "#FFFFFF"
    COLOR_CARD_SHADOW = "#CBD5E1"
    
    # Rank Colors System
    RANK_COLORS = {
        0: "#F59E0B",  # Gold (Rank 1)
        1: "#94A3B8",  # Silver (Rank 2)
        2: "#B45309",  # Bronze (Rank 3)
        "default": "#64748B" # Others
    }

# ==============================================================================
# MODULE 2: UI STYLING (CSS)
# ==============================================================================
def load_custom_css():
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&family=Prompt:wght@300;400;600&display=swap');
        
        :root {{
            --primary: {AppConfig.COLOR_PRIMARY};
            --bg: {AppConfig.COLOR_BG};
        }}

        html, body, [class*="css"] {{
            font-family: 'Sarabun', 'Prompt', sans-serif;
            background-color: var(--bg);
            color: #1E293B;
        }}
        
        /* Hero Section Styling */
        .hero-container {{
            background: linear-gradient(135deg, #4F46E5 0%, #3B82F6 100%);
            padding: 2.5rem;
            border-radius: 24px;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        /* Modern Glass Card */
        .glass-card {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 1.5rem;
            border: 1px solid #E2E8F0;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
            margin-bottom: 1.2rem;
        }}
        .glass-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        }}

        /* Rank Badge */
        .status-badge {{
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        /* Input Fields */
        .stTextInput input, .stTextArea textarea, .stNumberInput input {{
            border-radius: 12px;
            border: 1px solid #E2E8F0;
            padding: 10px 15px;
        }}
        .stTextInput input:focus, .stTextArea textarea:focus {{
            border-color: #4F46E5;
            box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.2);
        }}
        
        /* Custom Buttons */
        .stButton button {{
            border-radius: 12px !important;
            font-weight: 600 !important;
            height: 50px;
            transition: all 0.2s;
        }}
        </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# MODULE 3: DOMAIN LOGIC (BUSINESS RULES)
# ==============================================================================

class RankManager:
    """
    จัดการ Logic เกี่ยวกับยศและสิทธิพิเศษทั้งหมด
    """
    def __init__(self):
        # Configuration ของยศ (แก้ข้อความสิทธิ์ตรงนี้)
        self.ranks = [
            {
                "name": "PRESIDENT", 
                "th": "👑 ประธานรุ่น", 
                "min_xp": 1000, 
                "color": "#F59E0B", 
                "bg": "#FEF3C7", 
                "desc": "Immunity (ไม่ทำ 3 งาน) + Bonus 1/งาน"
            },
            {
                "name": "DIRECTOR", 
                "th": "💼 หัวหน้าฝ่าย", 
                "min_xp": 600, 
                "color": "#8B5CF6", 
                "bg": "#F3E8FF", 
                "desc": "Workload Cut (ลดภาระงาน 50%)"
            },
            {
                "name": "MANAGER", 
                "th": "👔 หัวหน้าแผนก", 
                "min_xp": 300, 
                "color": "#3B82F6", 
                "bg": "#DBEAFE", 
                "desc": "Second Chance (แก้ตัวได้ 1 ครั้ง/หน่วย)"
            },
            {
                "name": "EMPLOYEE", 
                "th": "👨‍💼 พนักงาน", 
                "min_xp": 100, 
                "color": "#10B981", 
                "bg": "#D1FAE5", 
                "desc": "Time Extension (ส่งช้าได้ 2 สัปดาห์)"
            },
            {
                "name": "INTERN", 
                "th": "👶 เด็กฝึกงาน", 
                "min_xp": 0, 
                "color": "#64748B", 
                "bg": "#F1F5F9", 
                "desc": "Check-up (สิทธิ์ให้ครูตรวจงานก่อนส่ง)"
            },
            {
                "name": "PROBATION", 
                "th": "⚠️ ทัณฑ์บน", 
                "min_xp": -999999, 
                "color": "#EF4444", 
                "bg": "#FEE2E2", 
                "desc": "ต้องรีบทำงานแก้คะแนนด่วนที่สุด!"
            }
        ]

    def get_rank_info(self, xp):
        """ค้นหายศที่เหมาะสมจาก XP"""
        if xp < 0: return self.ranks[-1] # Probation
        for rank in self.ranks:
            if rank['name'] != "PROBATION" and xp >= rank['min_xp']:
                return rank
        return self.ranks[-2] # Default to Intern

    def calculate_progress(self, xp):
        """คำนวณ % ความก้าวหน้าสู่ยศถัดไป"""
        if xp < 0: return 0.0, "Critical Status"
        
        for i, rank in enumerate(self.ranks):
            if rank['name'] != "PROBATION" and xp >= rank['min_xp']:
                if i > 0: # ยังไม่ตัน
                    next_rank = self.ranks[i-1]
                    target = next_rank['min_xp']
                    # Avoid division by zero
                    denominator = target if target > 0 else 100
                    pct = min(1.0, xp / denominator)
                    return pct, f"{int(pct*100)}% to {next_rank['th']}"
                return 1.0, "MAX LEVEL"
        return 0.0, "0%"

class BadgeSystem:
    """
    ระบบจัดการเหรียญตรา (Gamification Badges)
    """
    def __init__(self):
        self.badges_catalog = {
            "wealthy": "💎",    # 800+ XP
            "sniper": "🎯",     # Single transaction > 100
            "debtor": "💸",     # Negative XP
            "phoenix": "🔥",    # Recovery
            "first_blood": "🩸" # First activity
        }

    def evaluate(self, total_xp, history_log):
        """ประเมินว่าควรได้เหรียญอะไรบ้าง"""
        earned = []
        if total_xp >= 800: earned.append("wealthy")
        if total_xp < 0: earned.append("debtor")
        if any(h.get('amount', 0) >= 100 for h in history_log): earned.append("sniper")
        if len(history_log) > 0: earned.append("first_blood")
        return list(set(earned))

    def get_icons(self, badge_keys):
        """แปลง Key เป็น Emoji String"""
        return "".join([self.badges_catalog.get(k, "") for k in badge_keys])

# ==============================================================================
# MODULE 4: DATA ACCESS LAYER (DAL)
# ==============================================================================

class Database:
    """
    คลาสสำหรับจัดการการเชื่อมต่อ Google Sheets แบบ Robust
    """
    def __init__(self):
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
            self.REQUIRED_COLUMNS = ['Room', 'GroupName', 'XP', 'Members', 'LastUpdated', 'HistoryLog', 'Badges']
        except Exception as e:
            st.error(f"🔴 Database Connection Failed: {str(e)}")
            st.stop()

    def _clean_dataframe(self, df):
        """ทำความสะอาดข้อมูลดิบ ป้องกัน Error ค่า Null/NaN"""
        if df.empty or not set(self.REQUIRED_COLUMNS).issubset(df.columns):
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS)
        
        df = df[self.REQUIRED_COLUMNS].copy().dropna(how='all')
        # Convert XP to int safely
        df['XP'] = pd.to_numeric(df['XP'], errors='coerce').fillna(0).astype(int)
        # Ensure JSON columns are strings
        for col in ['HistoryLog', 'Badges']:
            df[col] = df[col].fillna("[]").astype(str)
        return df

    def get_all_data(self):
        try:
            df = self.conn.read(worksheet="Sheet1", ttl=0)
            return self._clean_dataframe(df)
        except Exception:
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS)

    def commit(self, df):
        """บันทึกข้อมูลและ Clear Cache"""
        try:
            self.conn.update(worksheet="Sheet1", data=df)
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Save Failed: {e}")
            return False

    # --- CRUD Operations ---
    
    def create_group(self, room, name, members, df):
        # Check Duplicate
        if ((df['Room'] == room) & (df['GroupName'] == name)).any():
            return False
        
        new_record = pd.DataFrame([{
            "Room": room,
            "GroupName": name,
            "XP": 0,
            "Members": members,
            "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "HistoryLog": "[]",
            "Badges": "[]"
        }])
        return self.commit(pd.concat([df, new_record], ignore_index=True))

    def update_group(self, room, old_name, new_name, new_members, df):
        # Check Duplicate if name changed
        if new_name != old_name and ((df['Room'] == room) & (df['GroupName'] == new_name)).any():
            return False
            
        mask = (df['Room'] == room) & (df['GroupName'] == old_name)
        if mask.any():
            idx = df[mask].index[0]
            df.at[idx, 'GroupName'] = new_name
            df.at[idx, 'Members'] = new_members
            df.at[idx, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
            return self.commit(df)
        return False

    def delete_group(self, room, name, df):
        mask = ~((df['Room'] == room) & (df['GroupName'] == name))
        return self.commit(df[mask])

    def add_score_transaction(self, room, group_names, amount, reason, df, badge_sys):
        if isinstance(group_names, str): group_names = [group_names]
        updated_count = 0
        
        for name in group_names:
            mask = (df['Room'] == room) & (df['GroupName'] == name)
            if mask.any():
                idx = df[mask].index[0]
                
                # Load History
                try: history = json.loads(df.at[idx, 'HistoryLog'])
                except: history = []
                
                # Create Log
                new_log = {
                    "id": str(uuid.uuid4())[:8],
                    "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "reason": reason,
                    "amount": int(amount)
                }
                history.insert(0, new_log)
                
                # Recalculate
                new_total = sum(x['amount'] for x in history)
                history[0]['balance'] = new_total
                
                # Update Rows
                df.at[idx, 'XP'] = new_total
                df.at[idx, 'HistoryLog'] = json.dumps(history, ensure_ascii=False)
                df.at[idx, 'Badges'] = json.dumps(badge_sys.evaluate(new_total, history), ensure_ascii=False)
                df.at[idx, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                updated_count += 1
                
        if updated_count > 0:
            return self.commit(df), updated_count
        return False, 0

    def power_edit_history(self, room, group_name, new_history_df, df, badge_sys):
        """แก้ไขประวัติย้อนหลังแบบ Advance"""
        mask = (df['Room'] == room) & (df['GroupName'] == group_name)
        if mask.any():
            idx = df[mask].index[0]
            
            # Reconstruct logic
            hist_list = new_history_df.to_dict('records')
            
            # Recalc balance strictly by time
            hist_sorted = sorted(hist_list, key=lambda x: x['ts'])
            running_bal = 0
            for item in hist_sorted:
                running_bal += int(item['amount'])
                item['balance'] = running_bal
                
            # Sort desc for storage
            final_hist = sorted(hist_sorted, key=lambda x: x['ts'], reverse=True)
            final_xp = running_bal
            
            df.at[idx, 'XP'] = final_xp
            df.at[idx, 'HistoryLog'] = json.dumps(final_hist, ensure_ascii=False)
            df.at[idx, 'Badges'] = json.dumps(badge_sys.evaluate(final_xp, final_hist), ensure_ascii=False)
            return self.commit(df)
        return False

# ==============================================================================
# MODULE 5: IMAGE RENDERING ENGINE (THE FIX)
# ==============================================================================

class GraphicsRenderer:
    """
    Engine สำหรับวาดภาพ Leaderboard ที่มีความละเอียดสูง
    แก้ปัญหาการทับซ้อนของตัวหนังสือโดยใช้ Bounding Box Calculation
    """
    def __init__(self):
        self.conf = AppConfig()
        
    def _clean_text(self, text):
        """ลบ Emoji ออกจาก String เพื่อป้องกัน PIL Error"""
        # Blocklist Emoji ที่มักทำให้ PIL พัง
        emojis = ["👑", "💼", "👔", "👨‍💼", "👶", "⚠️", "🩸", "💎", "💸", "🎯", "🔥", "🏆"]
        for e in emojis:
            text = text.replace(e, "")
        return text.strip()

    def _load_font(self, name, size):
        """โหลดฟอนต์พร้อม Fallback"""
        try:
            return ImageFont.truetype(name, size)
        except IOError:
            return ImageFont.load_default()

    def _draw_text_auto_fit(self, draw, text, max_width, x, y, font_name, max_size, color, anchor):
        """
        ฟังก์ชันอัจฉริยะ: ลดขนาดฟอนต์อัตโนมัติจนกว่าจะพอดีกับกรอบ
        """
        size = max_size
        min_size = 40
        font = self._load_font(font_name, size)
        
        while size > min_size:
            if font.getlength(text) <= max_width:
                break
            size -= 4
            font = self._load_font(font_name, size)
            
        draw.text((x, y), text, font=font, fill=color, anchor=anchor)
        # คืนค่าความสูงของ Text เพื่อใช้คำนวณบรรทัดถัดไป
        bbox = draw.textbbox((x, y), text, font=font, anchor=anchor)
        text_height = bbox[3] - bbox[1]
        return text_height

    def render_leaderboard(self, room_name, df, rank_sys):
        """
        Main Rendering Function
        """
        # Sort Data
        data = df.sort_values("XP", ascending=False).reset_index(drop=True)
        
        # Calculate Image Height
        total_height = (
            self.conf.IMG_HEADER_HEIGHT + 
            (len(data) * self.conf.IMG_ROW_HEIGHT) + 
            self.conf.IMG_FOOTER_HEIGHT
        )
        
        # Create Canvas
        img = Image.new('RGB', (self.conf.IMG_WIDTH, total_height), color=self.conf.COLOR_BG)
        draw = ImageDraw.Draw(img)
        
        # ---------------------------------------------------------
        # 1. DRAW HEADER
        # ---------------------------------------------------------
        draw.rectangle([(0, 0), (self.conf.IMG_WIDTH, self.conf.IMG_HEADER_HEIGHT)], fill=self.conf.COLOR_PRIMARY)
        # Decorative Elements
        draw.ellipse([(1000, -100), (1600, 500)], fill='#4F46E5')
        draw.ellipse([(-100, 300), (400, 800)], fill=self.conf.COLOR_SECONDARY)
        
        # Header Text
        f_header_title = self._load_font("Sarabun-Bold.ttf", 70)
        f_header_room = self._load_font("Sarabun-Bold.ttf", 180)
        
        # Draw Trophy Icon (Simple Text Fallback if image not present)
        draw.text((self.conf.IMG_WIDTH//2, 220), "🏆", font=self._load_font("Sarabun-Regular.ttf", 200), fill="white", anchor="mm")
        
        draw.text((self.conf.IMG_WIDTH//2, 400), "CLASSROOM LEADERBOARD", font=f_header_title, fill=self.conf.COLOR_ACCENT, anchor="mm")
        draw.text((self.conf.IMG_WIDTH//2, 600), f"{room_name}", font=f_header_room, fill="white", anchor="mm")
        
        # ---------------------------------------------------------
        # 2. DRAW ROWS (CARDS)
        # ---------------------------------------------------------
        current_y = self.conf.IMG_HEADER_HEIGHT + 40
        
        # Pre-load Fonts for efficiency
        f_rank_num = self._load_font("Sarabun-Bold.ttf", 90)
        f_score = self._load_font("Sarabun-Bold.ttf", 120)
        f_label = self._load_font("Sarabun-Bold.ttf", 55)
        f_members = self._load_font("Sarabun-Regular.ttf", 48)
        f_rank_title = self._load_font("Sarabun-Bold.ttf", 50)
        f_privilege = self._load_font("Sarabun-Regular.ttf", 38)

        for i, row in data.iterrows():
            # Get Rank Info
            rank_data = rank_sys.get_rank_info(row['XP'])
            progress, _ = rank_sys.calculate_progress(row['XP'])
            
            # Determine Colors
            theme_color = self.conf.RANK_COLORS.get(i, self.conf.RANK_COLORS["default"])
            score_color = "#EF4444" if row['XP'] < 0 else "#10B981"
            
            # Card Coordinates
            card_x = 40
            card_w = self.conf.IMG_WIDTH - 80
            card_h = self.conf.IMG_ROW_HEIGHT - 30 # เว้นช่องว่างระหว่างการ์ด
            
            # Draw Card Body (Shadow + White)
            draw.rounded_rectangle(
                [(card_x+8, current_y+10), (card_x+card_w+8, current_y+card_h+10)], 
                radius=40, fill=self.conf.COLOR_CARD_SHADOW
            )
            draw.rounded_rectangle(
                [(card_x, current_y), (card_x+card_w, current_y+card_h)], 
                radius=40, fill=self.conf.COLOR_CARD_BG
            )
            
            # --- COLUMN 1: RANK CIRCLE ---
            circle_cx = 160
            circle_cy = current_y + (card_h // 2) - 40 # ขยับขึ้นนิดหน่อย
            radius = 80
            draw.ellipse(
                [(circle_cx-radius, circle_cy-radius), (circle_cx+radius, circle_cy+radius)], 
                fill=theme_color
            )
            draw.text((circle_cx, circle_cy), str(i+1), font=f_rank_num, fill="white", anchor="mm")
            
            # --- COLUMN 2: GROUP INFO & PROGRESS ---
            content_x = 300
            content_w = 680 # Limit width to prevent collision with score
            
            # 2.1 Group Name (Top)
            name_y = current_y + 80
            self._draw_text_auto_fit(
                draw, self._clean_text(str(row['GroupName'])), 
                content_w, content_x, name_y, 
                "Sarabun-Bold.ttf", 90, self.conf.COLOR_TEXT_MAIN, "ls"
            )
            
            # 2.2 Members (Below Name)
            members_text = self._clean_text(str(row['Members']))
            if len(members_text) > 65: members_text = members_text[:62] + "..."
            draw.text((content_x, name_y + 70), members_text, font=f_members, fill=self.conf.COLOR_TEXT_SUB, anchor="ls")
            
            # 2.3 Progress Bar (Below Members)
            bar_y = name_y + 120
            bar_w = 600
            bar_h = 16
            draw.rounded_rectangle([(content_x, bar_y), (content_x+bar_w, bar_y+bar_h)], radius=8, fill="#F1F5F9")
            if progress > 0:
                fill_w = int(bar_w * progress)
                draw.rounded_rectangle([(content_x, bar_y), (content_x+fill_w, bar_y+bar_h)], radius=8, fill=rank_data['color'])
            
            # 2.4 RANK TITLE & PRIVILEGE (THE FIX for Overlap)
            # เราจะแยกตำแหน่งออกมาให้ชัดเจน ไม่ให้ชนกัน
            
            # Rank Title (วางไว้ท้าย Progress Bar เยื้องขวาบนนิดหน่อย หรือวางบรรทัดใหม่)
            # Strategy: วางบรรทัดใหม่ใต้ Progress bar เพื่อความชัวร์
            
            rank_title_y = bar_y + 50
            draw.text((content_x, rank_title_y), self._clean_text(rank_data['th']), font=f_rank_title, fill=rank_data['color'], anchor="ls")
            
            # Privilege Description (วางต่อจาก Rank Title โดยเว้นระยะห่างแน่นอน)
            priv_desc = self._clean_text(rank_data.get('desc', ''))
            # ตัดคำถ้าสิทธิ์ยาวเกินไป
            if len(priv_desc) > 50: priv_desc = priv_desc[:48] + "..."
            
            # คำนวณพิกัด Y ของสิทธิพิเศษ = Y ของชื่อยศ + ความสูงฟอนต์ + Padding
            priv_y = rank_title_y + 55 
            draw.text((content_x, priv_y), priv_desc, font=f_privilege, fill=self.conf.COLOR_TEXT_SUB, anchor="ls")
            
            # --- COLUMN 3: SCORE (RIGHT ALIGNED) ---
            score_x = self.conf.IMG_WIDTH - 100
            score_y_center = current_y + (card_h // 2) - 30
            
            draw.text((score_x, score_y_center), f"{row['XP']}", font=f_score, fill=score_color, anchor="rs")
            draw.text((score_x, score_y_center + 60), "XP", font=f_label, fill="#94A3B8", anchor="rs")
            
            # Next Row
            current_y += self.conf.IMG_ROW_HEIGHT
            
        # ---------------------------------------------------------
        # 3. DRAW FOOTER
        # ---------------------------------------------------------
        footer_y = total_height - 60
        f_footer = self._load_font("Sarabun-Regular.ttf", 40)
        ts = datetime.now().strftime('%d/%m/%Y %H:%M')
        draw.text(
            (self.conf.IMG_WIDTH//2, footer_y), 
            f"Generated by {self.conf.APP_NAME} • {ts}", 
            font=f_footer, fill="#94A3B8", anchor="mm"
        )
        
        # Export to Bytes
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()

# ==============================================================================
# MAIN APP COMPOSITION
# ==============================================================================

def main():
    st.set_page_config(
        page_title="Classroom OS: Enterprise",
        page_icon="🏛️",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    load_custom_css()
    
    # Initialize Dependencies
    db = Database()
    rank_sys = RankManager()
    badge_sys = BadgeSystem()
    renderer = GraphicsRenderer()
    
    # Sidebar Controls
    with st.sidebar:
        st.title("⚙️ Control Panel")
        selected_room = st.selectbox("เลือกห้องเรียน", ["ม.1/1", "ม.1/2", "ม.1/10"])
        
        st.divider()
        if st.button("⚠️ Repair Database"):
            db.commit(pd.DataFrame(columns=db.REQUIRED_COLUMNS))
            st.success("Database Repaired")
            
        st.divider()
        csv = db.get_all_data().to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export CSV", csv, "classroom_data.csv")
    
    # Load Data
    all_df = db.get_all_data()
    room_df = all_df[all_df['Room'] == selected_room].copy()
    
    # Hero Section
    st.markdown(f"""
    <div class='hero-container'>
        <div>
            <div style='opacity:0.8; letter-spacing:1px; font-weight:600;'>CLASSROOM OS : ENTERPRISE</div>
            <h1 style='margin:0; font-size:3.5rem; font-weight:800;'>{selected_room}</h1>
        </div>
        <div style='text-align:right;'>
            <div style='font-size:4rem; font-weight:800; line-height:1;'>{len(room_df)}</div>
            <div style='opacity:0.9;'>Active Groups</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs
    tabs = st.tabs(["⚡ Command Center", "🏆 Rankings & Image", "📈 Analytics", "ℹ️ Privileges Info", "🛠️ Management"])
    
    # --- TAB 1: COMMAND ---
    with tabs[0]:
        if room_df.empty:
            st.warning("⚠️ ยังไม่มีข้อมูลกลุ่ม กรุณาสร้างกลุ่มที่แท็บ Management")
        else:
            c1, c2 = st.columns([1, 3])
            with c1:
                mode = st.radio("Mode", ["Single Group", "Batch (Multiple)"])
            with c2:
                if mode == "Single Group":
                    target = [st.selectbox("Select Target", room_df['GroupName'].unique())]
                else:
                    target = st.multiselect("Select Targets", room_df['GroupName'].unique())
            
            # Show Stat Card for Single
            if len(target) == 1:
                grp = room_df[room_df['GroupName'] == target[0]].iloc[0]
                rank = rank_sys.get_rank_info(grp['XP'])
                st.markdown(f"""
                <div style='text-align:center; padding:20px; background:white; border-radius:15px; border:1px solid #e2e8f0; margin:20px 0;'>
                    <div style='color:#64748b; font-size:0.9rem;'>CURRENT XP</div>
                    <div class='{'score-negative' if grp['XP']<0 else 'score-positive'}' style='font-size:3rem; font-weight:800;'>{grp['XP']}</div>
                    <span class='status-badge' style='background:{rank['bg']}; color:{rank['color']}'>{rank['th']}</span>
                </div>
                """, unsafe_allow_html=True)
            
            st.divider()
            
            # Actions
            ac1, ac2 = st.columns(2)
            
            def execute_xp(reason, amount):
                if not target:
                    st.error("Please select a group first.")
                    return
                success, cnt = db.add_score_transaction(selected_room, target, amount, reason, all_df, badge_sys)
                if success:
                    st.toast(f"Updated {cnt} groups!", icon="✅")
                    time.sleep(1)
                    st.rerun()

            with ac1:
                st.subheader("🚀 Quick Actions")
                if st.button("📚 ส่งงานตรงเวลา (+50)", type="primary"): execute_xp("ส่งงานตรงเวลา", 50)
                if st.button("🙋 ตอบคำถาม (+20)"): execute_xp("ตอบคำถาม", 20)
                if st.button("🏆 ชนะกิจกรรม (+100)"): execute_xp("ชนะกิจกรรม", 100)
                st.markdown("---")
                if st.button("🐢 ส่งช้า (-20)"): execute_xp("ส่งงานล่าช้า", -20)
            
            with ac2:
                st.subheader("✍️ Manual Input")
                with st.form("manual"):
                    r = st.text_input("Reason")
                    s = st.number_input("Score", step=5)
                    if st.form_submit_button("Submit"):
                        if r and s != 0: execute_xp(r, s)
                        else: st.warning("Invalid Input")

    # --- TAB 2: RANKINGS (THE IMAGE) ---
    with tabs[1]:
        if room_df.empty: st.info("No Data")
        else:
            col_img, col_list = st.columns([1, 2])
            
            with col_img:
                st.markdown("### 🖼️ Leaderboard Image")
                st.caption("Auto-generated High Quality PNG")
                
                # Generate Image
                img_bytes = renderer.render_leaderboard(selected_room, room_df, rank_sys)
                
                st.download_button(
                    label="Download Image",
                    data=img_bytes,
                    file_name=f"Leaderboard_{selected_room}.png",
                    mime="image/png",
                    type="primary",
                    use_container_width=True
                )
                st.image(img_bytes, caption="Preview", use_container_width=True)

            with col_list:
                st.markdown("### 📋 Live Rankings")
                sorted_df = room_df.sort_values("XP", ascending=False).reset_index(drop=True)
                for i, row in sorted_df.iterrows():
                    r_info = rank_sys.get_rank_info(row['XP'])
                    pct, msg = rank_sys.calculate_progress(row['XP'])
                    try: badges = json.loads(row['Badges'])
                    except: badges = []
                    
                    card_c = "#EF4444" if row['XP'] < 0 else r_info['color']
                    
                    st.markdown(f"""
                    <div class='glass-card' style='border-left:5px solid {card_c};'>
                        <div style='display:flex; justify-content:space-between; align-items:center;'>
                            <div>
                                <span style='font-weight:bold; color:#94a3b8; font-size:1.2rem; margin-right:10px;'>#{i+1}</span>
                                <span style='font-weight:bold; font-size:1.2rem;'>{row['GroupName']}</span>
                                <div style='color:#64748b; font-size:0.9rem;'>{row['Members']}</div>
                                <div style='margin-top:5px;'>{badge_sys.get_icons(badges)}</div>
                            </div>
                            <div style='text-align:right;'>
                                <div style='font-size:2rem; font-weight:800; color:{card_c}; line-height:1;'>{row['XP']}</div>
                                <div style='font-size:0.8rem; color:#94a3b8;'>XP</div>
                            </div>
                        </div>
                        <div style='margin-top:10px; display:flex; justify-content:space-between; align-items:center;'>
                            <span class='status-badge' style='background:{r_info['bg']}; color:{r_info['color']}'>{r_info['th']}</span>
                            <span style='font-size:0.8rem; color:#64748b;'>{msg}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.progress(pct)

    # --- TAB 3: ANALYTICS ---
    with tabs[2]:
        if not room_df.empty:
            total = room_df['XP'].sum()
            avg = room_df['XP'].mean()
            top = room_df.loc[room_df['XP'].idxmax()]['GroupName']
            
            k1, k2, k3 = st.columns(3)
            k1.metric("🏆 Top Group", top)
            k2.metric("✨ Total Class XP", f"{total:,}")
            k3.metric("📈 Average XP", f"{avg:.1f}")
            
            st.markdown("### 🏎️ Race History")
            hist_data = []
            for _, r in room_df.iterrows():
                try:
                    logs = json.loads(r['HistoryLog'])
                    for l in logs:
                        hist_data.append({
                            "Group": r['GroupName'],
                            "Time": pd.to_datetime(l['ts']),
                            "Score": l.get('balance', 0)
                        })
                except: pass
            
            if hist_data:
                chart = alt.Chart(pd.DataFrame(hist_data)).mark_line(point=True).encode(
                    x='Time:T', y='Score:Q', color='Group:N', tooltip=['Group', 'Time', 'Score']
                ).interactive()
                st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No Data")

    # --- TAB 4: PRIVILEGES ---
    with tabs[3]:
        st.markdown("## 🏛️ Privilege System")
        for r in rank_sys.ranks:
            if r['name'] == "PROBATION": continue
            st.markdown(f"""
            <div style='padding:20px; background:white; border-radius:15px; border-left:5px solid {r['color']}; margin-bottom:15px; box-shadow:0 2px 4px rgba(0,0,0,0.05);'>
                <div style='display:flex; justify-content:space-between;'>
                    <h3 style='margin:0; color:{r['color']};'>{r['th']}</h3>
                    <span class='status-badge' style='background:{r['bg']}; color:{r['color']}'>{r['min_xp']}+ XP</span>
                </div>
                <hr style='margin:10px 0; border-color:#f1f5f9;'>
                <div style='color:#475569;'>🎁 {r['desc']}</div>
            </div>
            """, unsafe_allow_html=True)

    # --- TAB 5: MANAGEMENT ---
    with tabs[4]:
        st.header("🛠️ Group Management")
        
        with st.expander("➕ Create New Group", expanded=True):
            with st.form("create"):
                n = st.text_input("Group Name")
                m = st.text_area("Members")
                if st.form_submit_button("Create"):
                    if db.create_group(selected_room, n, m, all_df):
                        st.success("Created!"); time.sleep(1); st.rerun()
                    else: st.error("Duplicate Name")
        
        st.divider()
        
        col_m1, col_m2 = st.columns([2, 1])
        with col_m1:
            st.subheader("✏️ Edit Group")
            target_edit = st.selectbox("Select Group", ["-"] + list(room_df['GroupName'].unique()))
            if target_edit != "-":
                curr = room_df[room_df['GroupName'] == target_edit].iloc[0]
                with st.form("edit"):
                    nn = st.text_input("Name", value=curr['GroupName'])
                    nm = st.text_area("Members", value=curr['Members'])
                    if st.form_submit_button("Update"):
                        if db.update_group(selected_room, target_edit, nn, nm, all_df):
                            st.success("Updated!"); time.sleep(1); st.rerun()
                        else: st.error("Error updating")
        
        with col_m2:
            st.subheader("🗑️ Delete")
            target_del = st.selectbox("Delete Group", ["-"] + list(room_df['GroupName'].unique()))
            if target_del != "-" and st.button("Confirm Delete", type="primary"):
                db.delete_group(selected_room, target_del, all_df)
                st.rerun()
        
        st.divider()
        with st.expander("⚡ Power Edit (History Log)"):
            target_pe = st.selectbox("Select for History Edit", ["-"] + list(room_df['GroupName'].unique()), key="pe")
            if target_pe != "-":
                row_pe = room_df[room_df['GroupName'] == target_pe].iloc[0]
                try: h_data = json.loads(row_pe['HistoryLog'])
                except: h_data = []
                
                edited = st.data_editor(pd.DataFrame(h_data), num_rows="dynamic", use_container_width=True)
                if st.button("Save History Changes"):
                    if db.power_edit_history(selected_room, target_pe, edited, all_df, badge_sys):
                        st.success("Saved!"); st.rerun()

if __name__ == "__main__":
    main()
