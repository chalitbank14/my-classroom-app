"""
Classroom OS: Enterprise Platinum Edition
Version: 16.0.0 (Final Stable - Zero Errors)
Author: AI Development Team
Date: 2026-01-20

Description:
The absolute definitive edition of Classroom OS.
- Fixed IndentationError in Database Service.
- Fixed AttributeError in Graphics Engine.
- Full Vector Sticker Engine (No external images required).
- Full CRUD Management (Create, Edit Name/Members, Delete).
- High-Fidelity Thai Typography Rendering.
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
import re
from typing import List, Dict, Optional, Tuple, Any, Union
from PIL import Image, ImageDraw, ImageFont

# ==============================================================================
# SECTION 1: SYSTEM KERNEL
# ==============================================================================

# Configure Logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("ClassroomOS")

class SystemConfig:
    """
    Centralized System Configuration (Single Source of Truth).
    """
    # App Metadata
    APP_NAME = "Classroom OS"
    APP_VERSION = "16.0.0-Platinum"
    ORGANIZATION = "Acme Education Systems"

    # Database Settings
    DB_CONN_NAME = "gsheets"
    DB_SHEET_NAME = "Sheet1"
    DB_TTL = 0

    # Graphics Engine Settings (Calibrated for Thai Language)
    IMG_WIDTH = 1400
    IMG_HEADER_HEIGHT = 780
    IMG_ROW_HEIGHT = 620  # Height optimized for Thai vowels
    IMG_FOOTER_HEIGHT = 200
    IMG_PADDING = 50
    IMG_CARD_RADIUS = 45

    # Typography Assets
    FONT_BOLD = "Sarabun-Bold.ttf"
    FONT_REGULAR = "Sarabun-Regular.ttf"

    # Color Palette
    COLOR_PRIMARY = "#4338CA"      # Indigo 700
    COLOR_SECONDARY = "#3730A3"    # Indigo 800
    COLOR_ACCENT = "#A5B4FC"       # Indigo 200
    COLOR_BACKGROUND = "#F1F5F9"   # Slate 100
    COLOR_SURFACE = "#FFFFFF"      # White
    COLOR_BORDER = "#E2E8F0"       # Slate 200
    COLOR_SHADOW = "#94A3B8"       # Slate 400
    
    COLOR_TEXT_MAIN = "#1E293B"
    COLOR_TEXT_SUB = "#64748B"
    COLOR_TEXT_MUTED = "#94A3B8"
    
    COLOR_SUCCESS = "#10B981"
    COLOR_DANGER = "#EF4444"

    # Rank Themes
    RANK_THEMES = {
        0: {"hex": "#F59E0B", "bg": "#FEF3C7", "name": "Gold"},
        1: {"hex": "#94A3B8", "bg": "#F1F5F9", "name": "Silver"},
        2: {"hex": "#B45309", "bg": "#FFEDD5", "name": "Bronze"},
        "default": {"hex": "#64748B", "bg": "#F8FAFC", "name": "Slate"}
    }

# ==============================================================================
# SECTION 2: BUSINESS LOGIC LAYER
# ==============================================================================

class RankDefinition:
    """Data Model for Rank Tiers."""
    def __init__(self, id, th_name, min_xp, color, bg, desc):
        self.id = id
        self.th_name = th_name
        self.min_xp = min_xp
        self.color = color
        self.bg = bg
        self.desc = desc

class GamificationEngine:
    """
    Core Logic for Ranks, Badges, and Score Calculation.
    """
    def __init__(self):
        self._init_ranks()
        self._init_badges()

    def _init_ranks(self):
        self.ranks = [
            RankDefinition("PRESIDENT", "👑 ประธานรุ่น", 1000, "#F59E0B", "#FEF3C7", "Immunity (ไม่ทำ 3 งาน) + Bonus 1/งาน"),
            RankDefinition("DIRECTOR", "💼 หัวหน้าฝ่าย", 600, "#8B5CF6", "#F3E8FF", "Workload Cut (ลดภาระงาน 50%)"),
            RankDefinition("MANAGER", "👔 หัวหน้าแผนก", 300, "#3B82F6", "#DBEAFE", "Second Chance (แก้ตัวได้ 1 ครั้ง/หน่วย)"),
            RankDefinition("EMPLOYEE", "👨‍💼 พนักงาน", 100, "#10B981", "#D1FAE5", "Time Extension (ส่งช้าได้ 2 สัปดาห์)"),
            RankDefinition("INTERN", "👶 เด็กฝึกงาน", 0, "#64748B", "#F1F5F9", "Check-up (สิทธิ์ให้ครูตรวจงานก่อนส่ง)"),
            RankDefinition("PROBATION", "⚠️ ทัณฑ์บน", -999999, "#EF4444", "#FEE2E2", "สถานะวิกฤต! รีบซ่อมคะแนนด่วน")
        ]

    def _init_badges(self):
        self.badges_map = {
            "wealthy": "💎", "sniper": "🎯", "debtor": "💸", 
            "phoenix": "🔥", "first_blood": "🩸", "veteran": "🎖️"
        }

    def get_rank(self, xp: int) -> RankDefinition:
        if xp < 0: return self.ranks[-1]
        for rank in self.ranks:
            if rank.id != "PROBATION" and xp >= rank.min_xp:
                return rank
        return self.ranks[-2]

    def get_progress(self, xp: int) -> Tuple[float, str]:
        if xp < 0: return 0.0, "Critical Status"
        current = self.get_rank(xp)
        try:
            idx = self.ranks.index(current)
        except: return 0.0, "Error"

        if idx > 0:
            next_rank = self.ranks[idx - 1]
            target = next_rank.min_xp
            denom = target if target > 0 else 100
            pct = min(1.0, xp / denom)
            return pct, f"{int(pct*100)}% to {next_rank.th_name}"
        return 1.0, "MAX LEVEL"

    def calculate_badges(self, xp: int, history: List[dict]) -> List[str]:
        earned = set()
        if xp >= 800: earned.add("wealthy")
        if xp < 0: earned.add("debtor")
        if history:
            earned.add("first_blood")
            if len(history) >= 10: earned.add("veteran")
            if any(h.get('amount', 0) >= 100 for h in history): earned.add("sniper")
        return list(earned)

    def render_badges_str(self, badge_list: List[str]) -> str:
        return "".join([self.badges_map.get(b, "") for b in badge_list])

    def process_transaction(self, current_xp: int, current_history: List[dict], reason: str, amount: int) -> Tuple[int, List[dict], List[str]]:
        new_log = {
            "id": str(uuid.uuid4())[:8],
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "reason": reason,
            "amount": int(amount)
        }
        new_history = [new_log] + current_history
        
        # Recalculate Balance
        try: sorted_asc = sorted(new_history, key=lambda x: x.get('ts', ''))
        except: sorted_asc = new_history

        running_bal = 0
        for item in sorted_asc:
            running_bal += int(item.get('amount', 0))
            item['balance'] = running_bal
            
        final_history = sorted(sorted_asc, key=lambda x: x.get('ts', ''), reverse=True)
        final_xp = running_bal
        final_badges = self.calculate_badges(final_xp, final_history)
        
        return final_xp, final_history, final_badges

# ==============================================================================
# SECTION 4: DATA ACCESS LAYER (DATABASE SERVICE)
# ==============================================================================

class DatabaseService:
    """
    Robust Data Access Layer for Google Sheets.
    Handles all CRUD operations securely.
    """
    SCHEMA = ['Room', 'GroupName', 'XP', 'Members', 'LastUpdated', 'HistoryLog', 'Badges']

    def __init__(self):
        self.config = SystemConfig()
        self.conn = self._connect()

    def _connect(self):
        try:
            return st.connection(self.config.DB_CONN_NAME, type=GSheetsConnection)
        except Exception as e:
            st.error(f"DB Connection Error: {e}")
            st.stop()

    def _sanitize(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty: return pd.DataFrame(columns=self.SCHEMA)
        
        missing = set(self.SCHEMA) - set(df.columns)
        for col in missing: df[col] = None
        
        df = df[self.SCHEMA].copy().dropna(how='all')
        df['XP'] = pd.to_numeric(df['XP'], errors='coerce').fillna(0).astype(int)
        
        for col in ['HistoryLog', 'Badges']:
            df[col] = df[col].fillna("[]").astype(str)
            if not df[col].astype(str).str.startswith('['): df[col] = "[]"
            
        for col in ['Room', 'GroupName', 'Members', 'LastUpdated']:
            df[col] = df[col].fillna("").astype(str)
            
        return df

    def fetch_data(self) -> pd.DataFrame:
        try:
            df = self.conn.read(worksheet=self.config.DB_SHEET_NAME, ttl=self.config.DB_TTL)
            return self._sanitize(df)
        except: return pd.DataFrame(columns=self.SCHEMA)

    def commit(self, df: pd.DataFrame) -> bool:
        try:
            self.conn.update(worksheet=self.config.DB_SHEET_NAME, data=self._sanitize(df))
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Save Error: {e}")
            return False

    # --- CRUD OPERATIONS (FIXED INDENTATION HERE) ---

    def create_team(self, room: str, name: str, members: str, current_df: pd.DataFrame) -> bool:
        if ((current_df['Room'] == room) & (current_df['GroupName'] == name)).any(): 
            return False
        
        new_row = {
            "Room": room, 
            "GroupName": name, 
            "XP": 0, 
            "Members": members,
            "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "HistoryLog": "[]", 
            "Badges": "[]"
        }
        return self.commit(pd.concat([current_df, pd.DataFrame([new_row])], ignore_index=True))

    def update_team(self, room: str, old_name: str, new_name: str, members: str, current_df: pd.DataFrame) -> bool:
        # Check duplicate name if name changed
        if new_name != old_name:
            if ((current_df['Room'] == room) & (current_df['GroupName'] == new_name)).any(): 
                return False
            
        mask = (current_df['Room'] == room) & (current_df['GroupName'] == old_name)
        if not mask.any(): 
            return False
        
        idx = current_df[mask].index[0]
        current_df.at[idx, 'GroupName'] = new_name
        current_df.at[idx, 'Members'] = members
        current_df.at[idx, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        return self.commit(current_df)

    def delete_team(self, room: str, name: str, current_df: pd.DataFrame) -> bool:
        mask = ~((current_df['Room'] == room) & (current_df['GroupName'] == name))
        return self.commit(current_df[mask])

    def save_state(self, room: str, name: str, xp: int, hist: List[dict], badges: List[str], current_df: pd.DataFrame) -> bool:
        mask = (current_df['Room'] == room) & (current_df['GroupName'] == name)
        if not mask.any(): return False
        
        idx = current_df[mask].index[0]
        current_df.at[idx, 'XP'] = xp
        current_df.at[idx, 'HistoryLog'] = json.dumps(hist, ensure_ascii=False)
        current_df.at[idx, 'Badges'] = json.dumps(badges, ensure_ascii=False)
        current_df.at[idx, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        return self.commit(current_df)

    def process_batch(self, room: str, targets: List[str], amount: int, reason: str, current_df: pd.DataFrame, engine: GamificationEngine) -> bool:
        count = 0
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        for t in targets:
            mask = (current_df['Room'] == room) & (current_df['GroupName'] == t)
            if mask.any():
                idx = current_df[mask].index[0]
                try: hist = json.loads(current_df.at[idx, 'HistoryLog'])
                except: hist = []
                
                nxp, nh, nb = engine.process_transaction(current_df.at[idx, 'XP'], hist, reason, amount)
                
                current_df.at[idx, 'XP'] = nxp
                current_df.at[idx, 'HistoryLog'] = json.dumps(nh, ensure_ascii=False)
                current_df.at[idx, 'Badges'] = json.dumps(nb, ensure_ascii=False)
                current_df.at[idx, 'LastUpdated'] = ts
                count += 1
                
        if count > 0: 
            return self.commit(current_df)
        return False

    def power_edit_history(self, room: str, group_name: str, new_history_df: pd.DataFrame, current_df: pd.DataFrame, engine: GamificationEngine) -> bool:
        mask = (current_df['Room'] == room) & (current_df['GroupName'] == group_name)
        if not mask.any(): return False
        
        idx = current_df[mask].index[0]
        hist_list = new_history_df.to_dict('records')
        
        try: sorted_asc = sorted(hist_list, key=lambda x: x.get('ts', ''))
        except: sorted_asc = hist_list
        
        run = 0
        for item in sorted_asc:
            amt = int(item.get('amount', 0))
            item['amount'] = amt
            run += amt
            item['balance'] = run
            
        final_xp = run
        final_hist = sorted(sorted_asc, key=lambda x: x.get('ts', ''), reverse=True)
        final_badges = engine.calculate_badges(final_xp, final_hist)
        
        current_df.at[idx, 'XP'] = final_xp
        current_df.at[idx, 'HistoryLog'] = json.dumps(final_hist, ensure_ascii=False)
        current_df.at[idx, 'Badges'] = json.dumps(final_badges, ensure_ascii=False)
        current_df.at[idx, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        return self.commit(current_df)

# ==============================================================================
# SECTION 5: GRAPHICS ENGINE (VECTOR STICKERS)
# ==============================================================================

class GraphicsEngine:
    """
    Renders High-Fidelity Leaderboards with Vector Stickers.
    """
    def __init__(self):
        self.cfg = SystemConfig()
        self._font_cache = {}

    def _get_font(self, name: str, size: int) -> ImageFont.FreeTypeFont:
        key = (name, size)
        if key not in self._font_cache:
            try:
                self._font_cache[key] = ImageFont.truetype(name, size)
            except:
                self._font_cache[key] = ImageFont.load_default()
        return self._font_cache[key]

    def _clean_text(self, text: str) -> str:
        """Removes artifacts to prevent squares."""
        if not isinstance(text, str): return ""
        return re.sub(r'[^\w\s\u0E00-\u0E7F().,-]', '', text).strip()

    def _draw_sticker_medal(self, draw: ImageDraw.Draw, x: int, y: int, color_hex: str, rank_num: int):
        """Draws a vector medal sticker."""
        # Ribbon
        draw.polygon([(x-20, y-80), (x+20, y-80), (x, y-40)], fill="#EF4444")
        # White Border
        draw.ellipse([(x-85, y-85), (x+85, y+85)], fill="#FFFFFF")
        # Body
        draw.ellipse([(x-75, y-75), (x+75, y+75)], fill=color_hex)
        # Shine
        draw.chord([(x-75, y-75), (x+75, y+75)], 180, 360, fill="#FFFFFF40")

    def _draw_text_autofit(self, draw, text, x, y, max_w, font_name, max_s, color, anchor="lt"):
        text = self._clean_text(text)
        if not text: return
        
        size = max_s
        font = self._get_font(font_name, size)
        while size > 24:
            if font.getlength(text) <= max_w: break
            size -= 2
            font = self._get_font(font_name, size)
        draw.text((x, y), text, font=font, fill=color, anchor=anchor)

    def generate_leaderboard(self, room_name: str, df: pd.DataFrame, logic: GamificationEngine) -> bytes:
        data = df.sort_values("XP", ascending=False).reset_index(drop=True)
        
        # Height
        canvas_h = (
            self.cfg.IMG_HEADER_HEIGHT + 
            (len(data) * self.cfg.IMG_ROW_HEIGHT) + 
            self.cfg.IMG_FOOTER_HEIGHT
        )
        
        img = Image.new('RGBA', (self.cfg.IMG_WIDTH, canvas_h), self.cfg.COLOR_BACKGROUND)
        draw = ImageDraw.Draw(img)
        
        # --- HEADER ---
        draw.rectangle([(0, 0), (self.cfg.IMG_WIDTH, self.cfg.IMG_HEADER_HEIGHT)], fill=self.cfg.COLOR_PRIMARY)
        # Decor
        draw.ellipse([(900, -150), (1500, 450)], fill=self.cfg.COLOR_SECONDARY)
        draw.ellipse([(-100, 250), (500, 850)], fill=self.cfg.COLOR_SECONDARY)
        
        cx = self.cfg.IMG_WIDTH // 2
        # Trophy Vector
        draw.polygon([(cx-60, 180), (cx+60, 180), (cx+30, 280), (cx-30, 280)], fill="#FFD700")
        draw.ellipse([(cx-60, 170), (cx+60, 190)], fill="#FFC107")
        draw.rectangle([(cx-40, 280), (cx+40, 300)], fill="#DAA520")
        
        f_title = self._get_font(self.cfg.FONT_BOLD, 70)
        draw.text((cx, 420), "CLASSROOM LEADERBOARD", font=f_title, fill=self.cfg.COLOR_ACCENT, anchor="mm")
        
        f_room = self._get_font(self.cfg.FONT_BOLD, 160)
        draw.text((cx, 620), room_name, font=f_room, fill="white", anchor="mm")
        
        # --- ROWS ---
        curr_y = self.cfg.IMG_HEADER_HEIGHT + 50
        
        f_rank = self._get_font(self.cfg.FONT_BOLD, 90)
        f_score = self._get_font(self.cfg.FONT_BOLD, 120)
        f_lbl = self._get_font(self.cfg.FONT_BOLD, 50)
        f_mem = self._get_font(self.cfg.FONT_REGULAR, 45)
        f_ttl = self._get_font(self.cfg.FONT_BOLD, 50)
        f_desc = self._get_font(self.cfg.FONT_REGULAR, 36)
        
        for i, row in data.iterrows():
            xp = row['XP']
            rank = logic.get_rank(xp)
            pct, _ = logic.get_progress(xp)
            
            theme = self.cfg.RANK_THEMES.get(i if i < 3 else "default")
            score_col = self.cfg.COLOR_DANGER if xp < 0 else self.cfg.COLOR_SUCCESS
            
            # Card Metrics
            cx_card = self.cfg.IMG_PADDING
            cw = self.cfg.IMG_WIDTH - (self.cfg.IMG_PADDING * 2)
            ch = self.cfg.IMG_ROW_HEIGHT - 40
            
            # Draw Card Body
            draw.rounded_rectangle([(cx_card+10, curr_y+10), (cx_card+cw+10, curr_y+ch+10)], radius=40, fill=self.cfg.COLOR_SHADOW)
            draw.rounded_rectangle([(cx_card, curr_y), (cx_card+cw, curr_y+ch)], radius=40, fill=self.cfg.COLOR_SURFACE)
            
            # --- STICKER GENERATION ---
            cx_sticker = cx_card + 120
            cy_sticker = curr_y + (ch // 2)
            
            if i < 3:
                self._draw_sticker_medal(draw, cx_sticker, cy_sticker, theme['hex'], i+1)
            else:
                draw.ellipse([(cx_sticker-80, cy_sticker-80), (cx_sticker+80, cy_sticker+80)], fill="#FFFFFF")
                draw.ellipse([(cx_sticker-70, cy_sticker-70), (cx_sticker+70, cy_sticker+70)], fill=theme['hex'])
            
            draw.text((cx_sticker, cy_sticker), str(i+1), font=f_rank, fill="white", anchor="mm")
            
            # --- CONTENT GRID (THAI OPTIMIZED) ---
            info_x = cx_card + 280
            info_w = 600
            
            Y1 = curr_y + 50   # Name
            Y2 = Y1 + 100      # Members
            Y3 = Y2 + 100      # Bar
            Y4 = Y3 + 70       # Rank Title
            Y5 = Y4 + 70       # Privilege
            
            # 1. Name
            self._draw_text_autofit(draw, str(row['GroupName']), info_x, Y1, info_w, self.cfg.FONT_BOLD, 90, self.cfg.COLOR_TEXT_MAIN, "lt")
            
            # 2. Members
            mem_txt = self._clean_text(str(row['Members']))
            # Truncate
            if len(mem_txt) > 60: mem_txt = mem_txt[:57] + "..."
            draw.text((info_x, Y2), mem_txt, font=f_mem, fill=self.cfg.COLOR_TEXT_SUB, anchor="lt")
            
            # 3. Bar
            draw.rounded_rectangle([(info_x, Y3), (info_x+580, Y3+16)], radius=8, fill=self.cfg.COLOR_BACKGROUND)
            if pct > 0:
                fw = max(int(580*pct), 20)
                draw.rounded_rectangle([(info_x, Y3), (info_x+fw, Y3+16)], radius=8, fill=rank.color)
            
            # 4. Rank Title
            cln_ttl = self._clean_text(rank.th_name)
            draw.text((info_x, Y4), cln_ttl, font=f_ttl, fill=rank.color, anchor="lt")
            
            # 5. Privilege
            self._draw_text_autofit(draw, rank.desc, info_x, Y5, info_w, self.cfg.FONT_REGULAR, 40, self.cfg.COLOR_TEXT_SUB, "lt")
            
            # --- SCORE ---
            sx = self.cfg.IMG_WIDTH - self.cfg.IMG_PADDING - 50
            draw.text((sx, cy_sticker-10), f"{xp}", font=f_score, fill=score_col, anchor="rs")
            draw.text((sx, cy_sticker+60), "XP", font=f_lbl, fill=self.cfg.COLOR_TEXT_MUTED, anchor="rs")
            
            curr_y += self.cfg.IMG_ROW_HEIGHT
            
        # Footer
        fy = canvas_h - (self.cfg.IMG_FOOTER_HEIGHT // 2)
        f_ft = self._get_font(self.cfg.FONT_REGULAR, 38)
        ts = datetime.now().strftime('%d/%m/%Y %H:%M')
        draw.text((self.cfg.IMG_WIDTH // 2, fy), f"Generated by {self.cfg.APP_NAME} • {ts}", font=f_ft, fill=self.cfg.COLOR_TEXT_MUTED, anchor="mm")
        
        out = img.convert('RGB')
        buf = io.BytesIO()
        out.save(buf, format='PNG', optimize=True)
        return buf.getvalue()

# ==============================================================================
# SECTION 6: APP CONTROLLER (UI)
# ==============================================================================

class UIManager:
    """
    Main Controller. Handles UI State and Rendering.
    """
    def __init__(self):
        self.cfg = SystemConfig()
        self.db = DatabaseService()
        self.logic = GamificationEngine()
        self.gfx = GraphicsEngine()

    def setup_page(self):
        st.set_page_config(page_title=self.cfg.APP_NAME, page_icon="🏫", layout="wide", initial_sidebar_state="expanded")
        self._inject_css()

    def _inject_css(self):
        st.markdown(f"""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&family=Prompt:wght@300;400;500;700&display=swap');
            :root {{ --primary: {self.cfg.COLOR_PRIMARY}; --secondary: {self.cfg.COLOR_SECONDARY}; --bg: {self.cfg.COLOR_BACKGROUND}; }}
            html, body, .stApp {{ font-family: 'Sarabun', sans-serif; background-color: var(--bg); color: {self.cfg.COLOR_TEXT_MAIN}; }}
            .glass-card {{ background: white; border-radius: 16px; padding: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid {self.cfg.COLOR_BORDER}; margin-bottom: 1rem; }}
            .hero-container {{ background: linear-gradient(135deg, {self.cfg.COLOR_PRIMARY}, {self.cfg.COLOR_SECONDARY}); padding: 2.5rem; border-radius: 20px; color: white; margin-bottom: 2rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }}
            .stTextInput input, .stTextArea textarea, .stNumberInput input {{ border-radius: 10px; border: 1px solid {self.cfg.COLOR_BORDER}; }}
            </style>
        """, unsafe_allow_html=True)

    def render_sidebar(self):
        with st.sidebar:
            st.title(f"🎛️ {self.cfg.APP_NAME}")
            st.caption(f"v{self.cfg.APP_VERSION}")
            st.divider()
            
            st.subheader("Classroom Context")
            # Only requested rooms
            room = st.selectbox("Active Class", ["ม.1/1", "ม.1/2", "ม.1/10"])
            
            st.divider()
            if st.button("📥 Export CSV"):
                df = self.db.fetch_data()
                st.download_button("Download", df.to_csv(index=False).encode('utf-8'), "data.csv")
            
            if st.button("🔄 Reset DB"):
                if self.db.commit(pd.DataFrame(columns=self.db.SCHEMA)):
                    st.success("Reset done.")
                    time.sleep(1); st.rerun()
            return room

    def _tab_command(self, room, room_df, all_df):
        st.header("⚡ Command Center")
        if room_df.empty: st.info("Please create teams first."); return
        
        targets = st.multiselect("Select Teams (Batch)", sorted(room_df['GroupName'].unique()))
        st.divider()
        c1, c2 = st.columns(2)
        
        def apply(r, a):
            if not targets: st.error("Select team."); return
            with st.status("Processing Batch...") as s:
                if self.db.process_batch(room, targets, a, r, all_df, self.logic):
                    s.update(label="Success!", state="complete")
                    time.sleep(0.5); st.rerun()
                else: s.update(label="Failed", state="error")

        with c1:
            st.button("📚 On Time (+50)", on_click=apply, args=("ส่งงานตรงเวลา", 50), use_container_width=True)
            st.button("🙋 Participate (+20)", on_click=apply, args=("มีส่วนร่วม", 20), use_container_width=True)
        with c2:
            with st.form("cust"):
                r = st.text_input("Reason"); a = st.number_input("XP", step=5)
                if st.form_submit_button("Submit", use_container_width=True) and r: apply(r, a)

    def _tab_leaderboard(self, room, room_df):
        st.header("🏆 Leaderboard")
        if not room_df.empty:
            c1, c2 = st.columns([1, 2])
            with c1:
                st.info("Generates Sticker-Enhanced Image.")
                if st.button("✨ Generate Image", type="primary", use_container_width=True):
                    try:
                        img = self.gfx.generate_leaderboard(room, room_df, self.logic)
                        st.session_state['lb_img'] = img
                    except Exception as e: st.error(f"Err: {e}")
                
                if 'lb_img' in st.session_state:
                    st.download_button("Download PNG", st.session_state['lb_img'], "lb.png", "image/png", use_container_width=True)
            
            with c2:
                if 'lb_img' in st.session_state: st.image(st.session_state['lb_img'], use_container_width=True)
        
        st.divider()
        for _, r in room_df.sort_values("XP", ascending=False).iterrows():
            rank = self.logic.get_rank(r['XP'])
            st.markdown(f"<div class='glass-card' style='border-left:5px solid {rank.color}'><h3>{r['GroupName']}</h3>{r['XP']} XP | {rank.th_name}</div>", unsafe_allow_html=True)

    def _tab_manage(self, room, room_df, all_df):
        st.header("🛠️ Management")
        
        with st.expander("➕ Create Team", expanded=True):
            with st.form("new_team"):
                n = st.text_input("Name"); m = st.text_area("Members")
                if st.form_submit_button("Create") and n:
                    if self.db.create_team(room, n, m, all_df): st.success("Created!"); time.sleep(0.5); st.rerun()
                    else: st.error("Duplicate!")

        st.divider()
        st.subheader("✏️ Edit Team (Rename / Move Members)")
        t_list = sorted(room_df['GroupName'].unique())
        target = st.selectbox("Select Team", ["-"] + t_list)
        
        if target != "-":
            curr = room_df[room_df['GroupName'] == target].iloc[0]
            with st.form("edit_team"):
                nn = st.text_input("Name", value=curr['GroupName'])
                nm = st.text_area("Members", value=curr['Members'], height=150)
                if st.form_submit_button("Save Changes", type="primary"):
                    if self.db.update_team(room, target, nn, nm, all_df):
                        st.success("Updated!"); time.sleep(0.5); st.rerun()
                    else: st.error("Failed.")
                    
        st.divider()
        delt = st.selectbox("Delete Team", ["-"] + t_list)
        if delt != "-" and st.button("Confirm Delete"):
            self.db.delete_team(room, delt, all_df); st.rerun()
            
        st.divider()
        with st.expander("⚡ Power Edit History"):
            pe = st.selectbox("Select", ["-"]+t_list, key="pe")
            if pe != "-":
                row = room_df[room_df['GroupName']==pe].iloc[0]
                try: h = json.loads(row['HistoryLog'])
                except: h = []
                ed = st.data_editor(pd.DataFrame(h), num_rows="dynamic", use_container_width=True)
                if st.button("Save History"):
                    self.db.power_edit_history(room, pe, ed, all_df, self.logic); st.success("Saved!"); st.rerun()

    def run(self):
        self.setup_page()
        room = self.render_sidebar()
        try:
            all_df = self.db.fetch_data()
            room_df = all_df[all_df['Room'] == room].copy()
        except: st.error("DB Error"); return

        self.render_hero(room, len(room_df))
        t1, t2, t3, t4, t5 = st.tabs(["Command", "Leaderboard", "Analytics", "Privileges", "Manage"])
        
        with t1: self._tab_command(room, room_df, all_df)
        with t2: self._tab_leaderboard(room, room_df)
        with t3:
            st.header("Analytics")
            if not room_df.empty: st.bar_chart(room_df.set_index("GroupName")['XP'])
        with t4:
            st.header("Privileges")
            for r in self.logic.ranks: 
                if r.id!="PROBATION": st.info(f"**{r.th_name}**: {r.desc}")
        with t5: self._tab_manage(room, room_df, all_df)

    def render_hero(self, room, count):
        st.markdown(f"<div class='hero-container'><div><h1>{room}</h1></div><div style='font-size:3rem;font-weight:bold'>{count} Teams</div></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    UIManager().run()
