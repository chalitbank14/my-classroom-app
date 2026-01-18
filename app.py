"""
CLASSROOM OS: ENTERPRISE EDITION
Version: 4.0.0 (Thai Typography Fix)
Author: AI Assistant
Date: 2026-01-18

Description:
ระบบบริหารจัดการห้องเรียนแบบ Gamification ระดับองค์กร
รองรับการเชื่อมต่อ Google Sheets, การคำนวณคะแนนที่ซับซ้อน,
และระบบสร้างภาพกราฟิกที่มีความละเอียดสูง (High-Fidelity Rendering)
พร้อมระบบแก้ปัญหาสระลอยในภาษาไทย (Thai Vowel Adjustment Engine)
"""

import streamlit as st
import pandas as pd
import altair as alt
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import time
import json
import uuid
import io
import logging
from typing import List, Dict, Optional, Tuple, Any
from PIL import Image, ImageDraw, ImageFont

# ==============================================================================
# MODULE 1: LOGGING & DIAGNOSTICS
# ==============================================================================
# ตั้งค่าระบบ Log เพื่อติดตามการทำงานของระบบอย่างละเอียด
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("ClassroomOS")

# ==============================================================================
# MODULE 2: CONFIGURATION LAYER
# ==============================================================================
class AppConfig:
    """
    ศูนย์รวมการตั้งค่าทั้งหมดของระบบ (Single Source of Truth)
    """
    # Application Metadata
    APP_NAME = "Classroom OS"
    APP_VERSION = "4.0.0-Enterprise"
    
    # Graphic Rendering Config
    IMG_WIDTH = 1400
    IMG_HEADER_HEIGHT = 700
    IMG_ROW_HEIGHT = 450  # เพิ่มความสูงแถวเพื่อให้สระไม่ชนกัน
    IMG_FOOTER_HEIGHT = 150
    IMG_PADDING_X = 50
    
    # Typography Config (Thai Vowel Fix)
    FONT_MAIN = "Sarabun-Bold.ttf"
    FONT_SEC = "Sarabun-Regular.ttf"
    THAI_VOWEL_OFFSET = 20  # ค่าชดเชยแกน Y สำหรับสระบน
    
    # Color Palette (Theme: Corporate Indigo)
    COLOR_PRIMARY = "#4338CA"      # Header Background
    COLOR_SECONDARY = "#3730A3"    # Accent Elements
    COLOR_BG = "#F1F5F9"           # Global Background
    COLOR_CARD_BG = "#FFFFFF"      # Card Background
    COLOR_CARD_SHADOW = "#94A3B8"  # Card Shadow
    
    # Rank System Colors
    RANK_COLORS = {
        0: {"hex": "#F59E0B", "name": "Gold"},
        1: {"hex": "#94A3B8", "name": "Silver"},
        2: {"hex": "#B45309", "name": "Bronze"},
        "default": {"hex": "#64748B", "name": "Slate"}
    }

# ==============================================================================
# MODULE 3: DOMAIN MODELS & LOGIC
# ==============================================================================

class RankDefinition:
    """Model สำหรับนิยามยศและสิทธิพิเศษ"""
    def __init__(self, name: str, th_name: str, min_xp: int, color: str, bg_color: str, description: str):
        self.name = name
        self.th_name = th_name
        self.min_xp = min_xp
        self.color = color
        self.bg_color = bg_color
        self.description = description

class RankManager:
    """
    Business Logic สำหรับการคำนวณยศ (Rank)
    """
    def __init__(self):
        # นิยามยศทั้งหมดที่นี่
        self.ranks = [
            RankDefinition("PRESIDENT", "👑 ประธานรุ่น", 1000, "#F59E0B", "#FEF3C7", "Immunity (ไม่ทำ 3 งาน) + Bonus 1/งาน"),
            RankDefinition("DIRECTOR", "💼 หัวหน้าฝ่าย", 600, "#8B5CF6", "#F3E8FF", "Workload Cut (ลดภาระงาน 50%)"),
            RankDefinition("MANAGER", "👔 หัวหน้าแผนก", 300, "#3B82F6", "#DBEAFE", "Second Chance (แก้ตัวได้ 1 ครั้ง/หน่วย)"),
            RankDefinition("EMPLOYEE", "👨‍💼 พนักงาน", 100, "#10B981", "#D1FAE5", "Time Extension (ส่งช้าได้ 2 สัปดาห์)"),
            RankDefinition("INTERN", "👶 เด็กฝึกงาน", 0, "#64748B", "#F1F5F9", "Check-up (สิทธิ์ให้ครูตรวจงานก่อนส่ง)"),
            RankDefinition("PROBATION", "⚠️ ทัณฑ์บน", -999999, "#EF4444", "#FEE2E2", "สถานะวิกฤต! รีบซ่อมคะแนนด่วน")
        ]

    def get_rank(self, xp: int) -> RankDefinition:
        """คืนค่า Object ยศ ตาม XP ที่ได้รับ"""
        if xp < 0: return self.ranks[-1] # Probation
        for rank in self.ranks:
            if rank.name != "PROBATION" and xp >= rank.min_xp:
                return rank
        return self.ranks[-2] # Default Intearn

    def calculate_progress(self, xp: int) -> Tuple[float, str]:
        """คำนวณเปอร์เซ็นต์ความคืบหน้าสู่ยศถัดไป"""
        if xp < 0: return 0.0, "Critical Status"
        
        for i, rank in enumerate(self.ranks):
            if rank.name != "PROBATION" and xp >= rank.min_xp:
                if i > 0:
                    next_rank = self.ranks[i-1]
                    target = next_rank.min_xp
                    denominator = target if target > 0 else 100
                    pct = min(1.0, xp / denominator)
                    return pct, f"{int(pct*100)}% to {next_rank.th_name}"
                return 1.0, "MAX LEVEL"
        return 0.0, "0%"

class BadgeSystem:
    """ระบบคำนวณเหรียญตรา (Badges)"""
    def __init__(self):
        self.catalog = {
            "wealthy": "💎",    # 800+ XP
            "sniper": "🎯",     # Transaction > 100 XP
            "debtor": "💸",     # ติดลบ
            "phoenix": "🔥",    # เคยติดลบแล้วกลับมาบวก
            "first_blood": "🩸" # กิจกรรมแรก
        }

    def evaluate(self, current_xp: int, history: List[Dict]) -> List[str]:
        earned = []
        if current_xp >= 800: earned.append("wealthy")
        if current_xp < 0: earned.append("debtor")
        if any(h.get('amount', 0) >= 100 for h in history): earned.append("sniper")
        if len(history) > 0: earned.append("first_blood")
        # Logic for Phoenix could be added here
        return list(set(earned))

    def render(self, badge_keys: List[str]) -> str:
        return "".join([self.catalog.get(k, "") for k in badge_keys])

# ==============================================================================
# MODULE 4: DATA ACCESS LAYER (Repository Pattern)
# ==============================================================================

class GoogleSheetsRepository:
    """
    จัดการการเชื่อมต่อข้อมูลกับ Google Sheets อย่างปลอดภัย
    """
    REQUIRED_COLUMNS = ['Room', 'GroupName', 'XP', 'Members', 'LastUpdated', 'HistoryLog', 'Badges']

    def __init__(self):
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
            logger.info("Connected to Google Sheets service.")
        except Exception as e:
            logger.error(f"Failed to connect DB: {e}")
            st.error(f"🔴 Database Connection Error: {e}")
            st.stop()

    def _sanitize(self, df: pd.DataFrame) -> pd.DataFrame:
        """ทำความสะอาดข้อมูลดิบ"""
        if df.empty or not set(self.REQUIRED_COLUMNS).issubset(df.columns):
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS)
        
        df = df[self.REQUIRED_COLUMNS].copy().dropna(how='all')
        df['XP'] = pd.to_numeric(df['XP'], errors='coerce').fillna(0).astype(int)
        for col in ['HistoryLog', 'Badges']:
            df[col] = df[col].fillna("[]").astype(str)
        return df

    def get_data(self) -> pd.DataFrame:
        try:
            df = self.conn.read(worksheet="Sheet1", ttl=0)
            return self._sanitize(df)
        except Exception as e:
            logger.error(f"Read Error: {e}")
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS)

    def save_data(self, df: pd.DataFrame) -> bool:
        try:
            self.conn.update(worksheet="Sheet1", data=df)
            st.cache_data.clear()
            logger.info("Database updated successfully.")
            return True
        except Exception as e:
            logger.error(f"Write Error: {e}")
            st.error(f"Save Failed: {e}")
            return False

    # --- Domain Specific Operations ---

    def create_group(self, room: str, name: str, members: str, df: pd.DataFrame) -> bool:
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
        return self.save_data(pd.concat([df, new_row], ignore_index=True))

    def update_group(self, room: str, old_name: str, new_name: str, new_members: str, df: pd.DataFrame) -> bool:
        if new_name != old_name and ((df['Room'] == room) & (df['GroupName'] == new_name)).any():
            return False
            
        mask = (df['Room'] == room) & (df['GroupName'] == old_name)
        if mask.any():
            idx = df[mask].index[0]
            df.at[idx, 'GroupName'] = new_name
            df.at[idx, 'Members'] = new_members
            df.at[idx, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
            return self.save_data(df)
        return False

    def delete_group(self, room: str, name: str, df: pd.DataFrame) -> bool:
        mask = ~((df['Room'] == room) & (df['GroupName'] == name))
        return self.save_data(df[mask])

    def add_transaction(self, room: str, targets: List[str], amount: int, reason: str, df: pd.DataFrame, badge_sys: BadgeSystem) -> Tuple[bool, int]:
        count = 0
        for name in targets:
            mask = (df['Room'] == room) & (df['GroupName'] == name)
            if mask.any():
                idx = df[mask].index[0]
                try: hist = json.loads(df.at[idx, 'HistoryLog'])
                except: hist = []
                
                new_entry = {
                    "id": str(uuid.uuid4())[:8],
                    "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "reason": reason,
                    "amount": int(amount)
                }
                hist.insert(0, new_entry)
                new_total = sum(h['amount'] for h in hist)
                hist[0]['balance'] = new_total
                
                df.at[idx, 'XP'] = new_total
                df.at[idx, 'HistoryLog'] = json.dumps(hist, ensure_ascii=False)
                df.at[idx, 'Badges'] = json.dumps(badge_sys.evaluate(new_total, hist), ensure_ascii=False)
                df.at[idx, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                count += 1
        
        if count > 0:
            return self.save_data(df), count
        return False, 0

    def power_edit(self, room: str, target: str, new_hist_df: pd.DataFrame, df: pd.DataFrame, badge_sys: BadgeSystem) -> bool:
        mask = (df['Room'] == room) & (df['GroupName'] == target)
        if mask.any():
            idx = df[mask].index[0]
            hist_list = new_hist_df.to_dict('records')
            
            # Recalculate Balance strictly
            hist_sorted = sorted(hist_list, key=lambda x: x['ts'])
            running = 0
            for h in hist_sorted:
                running += int(h['amount'])
                h['balance'] = running
            
            final_hist = sorted(hist_sorted, key=lambda x: x['ts'], reverse=True)
            final_xp = running
            
            df.at[idx, 'XP'] = final_xp
            df.at[idx, 'HistoryLog'] = json.dumps(final_hist, ensure_ascii=False)
            df.at[idx, 'Badges'] = json.dumps(badge_sys.evaluate(final_xp, final_hist), ensure_ascii=False)
            return self.save_data(df)
        return False

# ==============================================================================
# MODULE 5: GRAPHICS ENGINE (THAI FONT FIX)
# ==============================================================================

class GraphicsEngine:
    """
    เครื่องมือสร้างภาพกราฟิกความละเอียดสูง พร้อมระบบจัดการฟอนต์ภาษาไทย
    """
    def __init__(self):
        self.cfg = AppConfig()

    def _get_font(self, name: str, size: int) -> ImageFont.FreeTypeFont:
        """โหลดฟอนต์อย่างปลอดภัย"""
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            logger.warning(f"Font {name} not found. Using default.")
            return ImageFont.load_default()

    def _remove_unsafe_chars(self, text: str) -> str:
        """ลบ Emoji ที่อาจทำให้ Pillow แครช"""
        unsafe = ["👑", "💼", "👔", "👨‍💼", "👶", "⚠️", "🩸", "💎", "💸", "🎯", "🔥", "🏆"]
        for u in unsafe:
            text = text.replace(u, "")
        return text.strip()

    def _draw_text_thai_safe(self, draw: ImageDraw.Draw, xy: Tuple[int, int], text: str, 
                             font: ImageFont.FreeTypeFont, fill: str, anchor: str = "ls", 
                             max_width: Optional[int] = None) -> int:
        """
        ฟังก์ชันวาดข้อความภาษาไทยแบบพิเศษ (Smart Draw)
        - คำนวณ Bounding Box จริง
        - ลดขนาดฟอนต์อัตโนมัติถ้าล้น (Auto-fit)
        - ชดเชยตำแหน่ง Y สำหรับสระบน (Vowel Compensation)
        """
        x, y = xy
        
        # 1. Auto-fit logic
        if max_width:
            current_size = font.size
            while font.getlength(text) > max_width and current_size > 30:
                current_size -= 2
                # โหลดฟอนต์ใหม่ด้วยขนาดที่เล็กลง
                try:
                    font = ImageFont.truetype(font.path, current_size)
                except:
                    break # ใช้ฟอนต์เดิมถ้าโหลดไม่ได้
        
        # 2. Thai Vowel Adjustment
        # เปลี่ยน Anchor จาก ls (Baseline) เป็น la (Left-Ascender) หรือ lt (Left-Top) 
        # เพื่อให้ควบคุมพื้นที่ด้านบนได้แม่นยำขึ้น
        
        # วิธีแก้ที่ดีที่สุด: วาดโดยใช้ Bounding Box จริง
        bbox = draw.textbbox((x, y), text, font=font, anchor=anchor)
        text_height = bbox[3] - bbox[1]
        
        # ถ้าเป็น anchor แบบ Baseline (ls, ms, rs) ให้ขยับลงมาหน่อยเผื่อสระบน
        # แต่เพื่อความชัวร์ เราจะวาดปกติแต่เผื่อพื้นที่ใน IMG_ROW_HEIGHT ไว้เยอะๆ แล้ว
        
        draw.text((x, y), text, font=font, fill=fill, anchor=anchor)
        
        return text_height

    def render(self, room_name: str, df: pd.DataFrame, rank_manager: RankManager) -> bytes:
        """สร้างภาพ Leaderboard"""
        
        # 1. Prepare Data
        data = df.sort_values("XP", ascending=False).reset_index(drop=True)
        total_height = (
            self.cfg.IMG_HEADER_HEIGHT + 
            (len(data) * self.cfg.IMG_ROW_HEIGHT) + 
            self.cfg.IMG_FOOTER_HEIGHT
        )
        
        # 2. Create Canvas
        img = Image.new('RGB', (self.cfg.IMG_WIDTH, total_height), color=self.cfg.COLOR_BG)
        draw = ImageDraw.Draw(img)
        
        # 3. Draw Header
        draw.rectangle([(0, 0), (self.cfg.IMG_WIDTH, self.cfg.IMG_HEADER_HEIGHT)], fill=self.cfg.COLOR_PRIMARY)
        # Decor
        draw.ellipse([(1000, -100), (1600, 500)], fill='#4F46E5')
        draw.ellipse([(-100, 300), (400, 800)], fill='#3730A3')
        
        # Header Typography
        f_super = self._get_font(self.cfg.FONT_MAIN, 200) # Icon fallback
        f_title = self._get_font(self.cfg.FONT_MAIN, 70)
        f_room = self._get_font(self.cfg.FONT_MAIN, 180)
        
        draw.text((self.cfg.IMG_WIDTH//2, 220), "🏆", font=f_super, fill="white", anchor="mm")
        draw.text((self.cfg.IMG_WIDTH//2, 400), "CLASSROOM LEADERBOARD", font=f_title, fill="#A5B4FC", anchor="mm")
        draw.text((self.cfg.IMG_WIDTH//2, 600), f"{room_name}", font=f_room, fill="white", anchor="mm")
        
        # 4. Draw Rows
        current_y = self.cfg.IMG_HEADER_HEIGHT + 50
        
        # Pre-load fonts
        f_rank = self._get_font(self.cfg.FONT_MAIN, 90)
        f_name = self._get_font(self.cfg.FONT_MAIN, 90) # ชื่อกลุ่ม
        f_score = self._get_font(self.cfg.FONT_MAIN, 110)
        f_label = self._get_font(self.cfg.FONT_MAIN, 50) # คำว่า XP
        f_members = self._get_font(self.cfg.FONT_SEC, 45)
        f_rank_name = self._get_font(self.cfg.FONT_MAIN, 50) # ชื่อยศ
        f_desc = self._get_font(self.cfg.FONT_SEC, 38) # สิทธิพิเศษ
        
        for i, row in data.iterrows():
            rank_def = rank_manager.get_rank(row['XP'])
            pct, _ = rank_manager.calculate_progress(row['XP'])
            
            # Theme Color
            rank_theme = self.cfg.RANK_COLORS.get(i, self.cfg.RANK_COLORS["default"])
            color_hex = rank_theme["hex"]
            score_color = "#EF4444" if row['XP'] < 0 else "#10B981"
            
            # Card Metrics
            card_x = self.cfg.IMG_PADDING_X
            card_w = self.cfg.IMG_WIDTH - (self.cfg.IMG_PADDING_X * 2)
            card_h = self.cfg.IMG_ROW_HEIGHT - 40
            
            # Shadow & Body
            draw.rounded_rectangle([(card_x+10, current_y+10), (card_x+card_w+10, current_y+card_h+10)], radius=30, fill=self.cfg.COLOR_CARD_SHADOW)
            draw.rounded_rectangle([(card_x, current_y), (card_x+card_w, current_y+card_h)], radius=30, fill=self.cfg.COLOR_CARD_BG)
            
            # --- ZONE 1: RANK CIRCLE ---
            cx, cy = 160, current_y + (card_h // 2)
            r = 80
            draw.ellipse([(cx-r, cy-r), (cx+r, cy+r)], fill=color_hex)
            draw.text((cx, cy), str(i+1), font=f_rank, fill="white", anchor="mm")
            
            # --- ZONE 2: INFO (Middle) ---
            info_x = 300
            info_w = 650
            
            # 2.1 Group Name (ใช้ฟังก์ชัน Safe Draw)
            # ปรับ Y ลงมาหน่อยเพื่อให้สระบนมีที่หายใจ
            name_y = current_y + 85 
            self._draw_text_thai_safe(draw, (info_x, name_y), self._remove_unsafe_chars(str(row['GroupName'])), f_name, "#1E293B", "ls", max_width=info_w)
            
            # 2.2 Members
            mem_y = name_y + 60
            mem_text = self._remove_unsafe_chars(str(row['Members']))
            if len(mem_text) > 60: mem_text = mem_text[:58] + "..."
            draw.text((info_x, mem_y), mem_text, font=f_members, fill="#64748B", anchor="ls")
            
            # 2.3 Progress Bar
            bar_y = mem_y + 40
            bar_w = 600
            bar_h = 14
            draw.rounded_rectangle([(info_x, bar_y), (info_x+bar_w, bar_y+bar_h)], radius=7, fill="#E2E8F0")
            if pct > 0:
                draw.rounded_rectangle([(info_x, bar_y), (info_x+int(bar_w*pct), bar_y+bar_h)], radius=7, fill=rank_def.color)
            
            # 2.4 Rank Info (Title & Desc) - แยกบรรทัดชัดเจน
            # Title
            title_y = bar_y + 45
            draw.text((info_x, title_y), rank_def.th_name, font=f_rank_name, fill=rank_def.color, anchor="ls")
            
            # Description (Privilege)
            desc_y = title_y + 45
            desc_text = self._remove_unsafe_chars(rank_def.description)
            self._draw_text_thai_safe(draw, (info_x, desc_y), desc_text, f_desc, "#64748B", "ls", max_width=info_w)
            
            # --- ZONE 3: SCORE (Right) ---
            score_x = self.cfg.IMG_WIDTH - 100
            score_y = current_y + (card_h // 2) - 20
            
            draw.text((score_x, score_y), f"{row['XP']}", font=f_score, fill=score_color, anchor="rs")
            draw.text((score_x, score_y + 60), "XP", font=f_label, fill="#94A3B8", anchor="rs")
            
            current_y += self.cfg.IMG_ROW_HEIGHT
            
        # 5. Footer
        foot_y = total_height - 70
        f_foot = self._get_font(self.cfg.FONT_SEC, 40)
        ts = datetime.now().strftime('%d/%m/%Y %H:%M')
        draw.text((self.cfg.IMG_WIDTH//2, foot_y), f"Generated by {self.cfg.APP_NAME} • {ts}", font=f_foot, fill="#94A3B8", anchor="mm")
        
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()

# ==============================================================================
# MODULE 6: MAIN APPLICATION CONTROLLER
# ==============================================================================

def main():
    st.set_page_config(
        page_title="Classroom OS: Enterprise",
        page_icon="🏛️",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Init Systems
    db = GoogleSheetsRepository()
    rank_sys = RankManager()
    badge_sys = BadgeSystem()
    gfx = GraphicsEngine()
    
    # Sidebar
    with st.sidebar:
        st.title("⚙️ System Control")
        selected_room = st.selectbox("Select Classroom", ["ม.1/1", "ม.1/2", "ม.1/10"])
        
        st.divider()
        if st.button("🔄 Reset Database Structure"):
            db.save_data(pd.DataFrame(columns=db.REQUIRED_COLUMNS))
            st.success("Database headers reset.")
            
        st.divider()
        csv = db.get_data().to_csv(index=False).encode('utf-8')
        st.download_button("📥 Backup CSV", csv, "classroom_backup.csv")

    # Load Context
    all_data = db.get_data()
    room_data = all_data[all_data['Room'] == selected_room].copy()
    
    # UI: Hero Section
    st.markdown(f"""
        <div style='background: linear-gradient(120deg, #4338CA, #3730A3); padding: 2rem; border-radius: 20px; color: white; margin-bottom: 2rem; display:flex; justify-content:space-between; align-items:center; box-shadow: 0 10px 20px rgba(0,0,0,0.1);'>
            <div>
                <div style='opacity:0.8; letter-spacing:2px; font-weight:600;'>CLASSROOM OS</div>
                <h1 style='margin:0; font-size:3.5rem; font-weight:800;'>{selected_room}</h1>
            </div>
            <div style='text-align:right;'>
                <div style='font-size:4rem; font-weight:800; line-height:1;'>{len(room_data)}</div>
                <div style='opacity:0.8;'>Active Groups</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # UI: Tabs
    tabs = st.tabs(["⚡ Command Center", "🏆 Leaderboard", "📈 Analytics", "ℹ️ Privileges", "🛠️ Management"])
    
    # --- TAB 1: COMMAND ---
    with tabs[0]:
        if room_data.empty:
            st.warning("⚠️ No groups found. Please create groups in 'Management' tab.")
        else:
            col_mode, col_sel = st.columns([1, 3])
            with col_mode:
                mode = st.radio("Selection Mode", ["Single Group", "Multiple Groups"])
            with col_sel:
                if mode == "Single Group":
                    target = [st.selectbox("Target Group", room_data['GroupName'].unique())]
                else:
                    target = st.multiselect("Target Groups", room_data['GroupName'].unique())
            
            # Single Group Stat
            if len(target) == 1:
                g = room_data[room_data['GroupName'] == target[0]].iloc[0]
                r = rank_sys.get_rank(g['XP'])
                st.markdown(f"""
                <div style='padding:20px; background:white; border-radius:15px; border:1px solid #E2E8F0; text-align:center; margin: 20px 0;'>
                    <div style='color:#64748B; font-size:0.9rem;'>CURRENT STATUS</div>
                    <div style='font-size:3rem; font-weight:800; color:{'#EF4444' if g['XP']<0 else '#10B981'};'>{g['XP']}</div>
                    <span style='background:{r.bg_color}; color:{r.color}; padding:5px 15px; border-radius:20px; font-weight:bold; font-size:0.9rem;'>{r.th_name}</span>
                </div>
                """, unsafe_allow_html=True)
            
            st.divider()
            
            # Action Buttons
            ac1, ac2 = st.columns(2)
            
            def execute(r_text, amt):
                if not target: st.error("Please select target."); return
                ok, n = db.add_transaction(selected_room, target, amt, r_text, all_data, badge_sys)
                if ok: st.toast(f"Updated {n} groups!", icon="✅"); time.sleep(1); st.rerun()

            with ac1:
                st.markdown("#### 🚀 Quick Actions")
                if st.button("📚 ส่งงานตรงเวลา (+50)", type="primary", use_container_width=True): execute("ส่งงานตรงเวลา", 50)
                if st.button("🙋 ตอบคำถาม (+20)", use_container_width=True): execute("ตอบคำถาม", 20)
                if st.button("🏆 ชนะกิจกรรม (+100)", use_container_width=True): execute("ชนะกิจกรรม", 100)
                st.markdown("---")
                if st.button("🐢 ส่งช้า (-20)", use_container_width=True): execute("ส่งงานล่าช้า", -20)
            
            with ac2:
                st.markdown("#### ✍️ Custom Input")
                with st.form("custom"):
                    reason = st.text_input("Reason")
                    score = st.number_input("Score (+/-)", step=5)
                    if st.form_submit_button("Submit Transaction", use_container_width=True):
                        if reason and score != 0: execute(reason, score)
                        else: st.warning("Invalid input")

    # --- TAB 2: LEADERBOARD ---
    with tabs[1]:
        if not room_data.empty:
            c_img, c_list = st.columns([1, 2])
            
            with c_img:
                st.markdown("### 🖼️ High-Fidelity Image")
                st.caption("Auto-generated with Thai typography support")
                img_data = gfx.render(selected_room, room_data, rank_sys)
                st.image(img_data, caption="Preview", use_container_width=True)
                st.download_button("Download HQ PNG", img_data, f"Leaderboard_{selected_room}.png", "image/png", type="primary", use_container_width=True)
            
            with c_list:
                st.markdown("### 📋 Live Data")
                sorted_df = room_data.sort_values("XP", ascending=False).reset_index(drop=True)
                for i, row in sorted_df.iterrows():
                    r = rank_sys.get_rank(row['XP'])
                    p, lbl = rank_sys.calculate_progress(row['XP'])
                    try: b = json.loads(row['Badges'])
                    except: b = []
                    
                    st.markdown(f"""
                    <div style='background:white; padding:15px; border-radius:15px; border-left:5px solid {r.color}; margin-bottom:10px; box-shadow:0 2px 4px rgba(0,0,0,0.05);'>
                        <div style='display:flex; justify-content:space-between; align-items:center;'>
                            <div>
                                <span style='font-weight:bold; color:#94A3B8; margin-right:10px;'>#{i+1}</span>
                                <span style='font-weight:bold; font-size:1.1rem;'>{row['GroupName']}</span>
                                <div style='font-size:0.9rem; color:#64748B;'>{row['Members']}</div>
                                <div>{badge_sys.render(b)}</div>
                            </div>
                            <div style='text-align:right;'>
                                <div style='font-size:1.8rem; font-weight:800; color:{'#EF4444' if row['XP']<0 else r.color}; line-height:1;'>{row['XP']}</div>
                                <div style='font-size:0.8rem; color:#94A3B8;'>XP</div>
                            </div>
                        </div>
                        <div style='margin-top:10px; display:flex; justify-content:space-between; align-items:center;'>
                            <span style='background:{r.bg_color}; color:{r.color}; padding:2px 10px; border-radius:10px; font-size:0.8rem; font-weight:bold;'>{r.th_name}</span>
                            <span style='font-size:0.8rem; color:#64748B;'>{lbl}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.progress(p)

    # --- TAB 3: ANALYTICS ---
    with tabs[2]:
        if not room_data.empty:
            tot = room_data['XP'].sum()
            avg = room_data['XP'].mean()
            top = room_data.loc[room_data['XP'].idxmax()]['GroupName']
            
            k1, k2, k3 = st.columns(3)
            k1.metric("🏆 Top Group", top)
            k2.metric("✨ Total XP", f"{tot:,}")
            k3.metric("📈 Average", f"{avg:.1f}")
            
            st.markdown("### 🏎️ Race Timeline")
            hist_data = []
            for _, row in room_data.iterrows():
                try:
                    logs = json.loads(row['HistoryLog'])
                    for l in logs:
                        hist_data.append({
                            "Group": row['GroupName'],
                            "Time": pd.to_datetime(l['ts']),
                            "XP": l.get('balance', 0)
                        })
                except: pass
            
            if hist_data:
                chart = alt.Chart(pd.DataFrame(hist_data)).mark_line(point=True).encode(
                    x='Time:T', y='XP:Q', color='Group:N', tooltip=['Group', 'Time', 'XP']
                ).interactive()
                st.altair_chart(chart, use_container_width=True)

    # --- TAB 4: PRIVILEGES ---
    with tabs[3]:
        st.markdown("## 🏛️ Privilege Hierarchy")
        for r in rank_sys.ranks:
            if r.name == "PROBATION": continue
            st.markdown(f"""
            <div style='padding:15px; background:white; border-radius:12px; border-left:4px solid {r.color}; margin-bottom:12px;'>
                <div style='display:flex; justify-content:space-between;'>
                    <h4 style='margin:0; color:{r.color};'>{r.th_name}</h4>
                    <span style='background:{r.bg_color}; color:{r.color}; padding:2px 8px; border-radius:10px; font-size:0.8rem; font-weight:bold;'>{r.min_xp}+ XP</span>
                </div>
                <hr style='margin:8px 0; border-color:#F1F5F9;'>
                <div style='color:#475569; font-size:0.95rem;'>🎁 {r.description}</div>
            </div>
            """, unsafe_allow_html=True)

    # --- TAB 5: MANAGEMENT ---
    with tabs[4]:
        st.header("🛠️ Group Management")
        
        with st.expander("➕ Create Group", expanded=True):
            with st.form("create"):
                n = st.text_input("Group Name")
                m = st.text_area("Members")
                if st.form_submit_button("Create Group"):
                    if db.create_group(selected_room, n, m, all_data):
                        st.success("Created!"); time.sleep(1); st.rerun()
                    else: st.error("Duplicate Name")
        
        st.divider()
        c_edit, c_del = st.columns([2, 1])
        
        with c_edit:
            st.subheader("✏️ Edit Group")
            target_e = st.selectbox("Select Group", ["-"] + list(room_data['GroupName'].unique()))
            if target_e != "-":
                curr = room_data[room_data['GroupName'] == target_e].iloc[0]
                with st.form("edit"):
                    nn = st.text_input("Name", value=curr['GroupName'])
                    nm = st.text_area("Members", value=curr['Members'])
                    if st.form_submit_button("Update Group"):
                        if db.update_group(selected_room, target_e, nn, nm, all_data):
                            st.success("Updated!"); time.sleep(1); st.rerun()
                        else: st.error("Failed (Duplicate?)")
                        
        with c_del:
            st.subheader("🗑️ Delete Group")
            target_d = st.selectbox("Delete Target", ["-"] + list(room_data['GroupName'].unique()))
            if target_d != "-" and st.button("Confirm Delete", type="primary"):
                db.delete_group(selected_room, target_d, all_data)
                st.rerun()
                
        st.markdown("---")
        with st.expander("⚡ Advanced: Edit History Log"):
            target_p = st.selectbox("Select for History Edit", ["-"] + list(room_data['GroupName'].unique()), key="pe")
            if target_p != "-":
                row_p = room_data[room_data['GroupName'] == target_p].iloc[0]
                try: h_dat = json.loads(row_p['HistoryLog'])
                except: h_dat = []
                
                edited_h = st.data_editor(pd.DataFrame(h_dat), num_rows="dynamic", use_container_width=True)
                if st.button("Save History Changes"):
                    if db.power_edit(selected_room, target_p, edited_h, all_data, badge_sys):
                        st.success("Saved!"); st.rerun()

if __name__ == "__main__":
    main()
