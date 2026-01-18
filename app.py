"""
Classroom OS: Enterprise Edition
Version: 7.0.0-Ultimate (Stable Release)
Author: AI Development Team
Date: 2026-01-20

Description:
The definitive edition of the Classroom OS platform. This system is architected
using strict Object-Oriented Programming (OOP) principles, ensuring modularity,
scalability, and robustness.

Key Features:
- Robust Google Sheets Integration with caching and error handling.
- Advanced Typography Engine specifically tuned for Thai glyphs (vowels/tone marks).
- Gamification Logic with Ranks, Badges, and Dynamic Progress Calculation.
- High-Fidelity Image Generation for social sharing.
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
# MODULE 1: SYSTEM KERNEL & DIAGNOSTICS
# ==============================================================================

# Configure application-wide structured logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] [%(name)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("ClassroomOS.Kernel")

class AppConfig:
    """
    Centralized Configuration Manager.
    Serves as the Single Source of Truth (SSOT) for all application constants.
    """
    # --- Application Metadata ---
    APP_NAME: str = "Classroom OS"
    APP_VERSION: str = "7.0.0-Ultimate"
    ORG_NAME: str = "Acme Education Systems"

    # --- Database Configuration ---
    DB_CONNECTION_NAME: str = "gsheets"
    DB_MAIN_WORKSHEET: str = "Sheet1"
    DB_CACHE_TTL: int = 0  # Zero for real-time consistency

    # --- Graphic Engine Configuration (Calibrated for Thai) ---
    IMG_WIDTH: int = 1400
    IMG_HEADER_HEIGHT: int = 750
    # Increased row height to 600px to absolutely prevent vowel overlapping
    IMG_ROW_HEIGHT: int = 600
    IMG_FOOTER_HEIGHT: int = 180
    IMG_PADDING_X: int = 50
    IMG_CARD_RADIUS: int = 40

    # --- Typography Assets ---
    FONT_PRIMARY_BOLD: str = "Sarabun-Bold.ttf"
    FONT_PRIMARY_REG: str = "Sarabun-Regular.ttf"

    # --- Theme & Color Palette ---
    COLOR_BRAND_PRIMARY: str = "#4338CA"    # Indigo 700
    COLOR_BRAND_SECONDARY: str = "#3730A3"  # Indigo 800
    COLOR_BRAND_ACCENT: str = "#A5B4FC"     # Indigo 200
    
    COLOR_BG_MAIN: str = "#F1F5F9"          # Slate 100
    COLOR_CARD_SURFACE: str = "#FFFFFF"     # White
    COLOR_CARD_SHADOW: str = "#94A3B8"      # Slate 400
    
    COLOR_TEXT_PRIMARY: str = "#1E293B"     # Slate 800
    COLOR_TEXT_SECONDARY: str = "#64748B"   # Slate 500
    COLOR_TEXT_MUTED: str = "#94A3B8"       # Slate 400

    COLOR_SCORE_POSITIVE: str = "#10B981"   # Emerald
    COLOR_SCORE_NEGATIVE: str = "#EF4444"   # Red

    # --- Rank Styling Map ---
    RANK_THEMES: Dict[Union[int, str], Dict[str, str]] = {
        0: {"hex": "#F59E0B", "bg": "#FEF3C7", "name": "Gold"},   # Rank 1
        1: {"hex": "#94A3B8", "bg": "#F1F5F9", "name": "Silver"}, # Rank 2
        2: {"hex": "#B45309", "bg": "#FFEDD5", "name": "Bronze"}, # Rank 3
        "default": {"hex": "#64748B", "bg": "#F8FAFC", "name": "Slate"} # Others
    }

# ==============================================================================
# MODULE 2: DOMAIN MODELS
# ==============================================================================

class RankDefinition:
    """
    Immutable Value Object representing a Rank Tier.
    """
    def __init__(self, id: str, th_name: str, min_xp: int, color: str, bg_color: str, description: str):
        self.id = id
        self.th_name = th_name
        self.min_xp = min_xp
        self.color = color
        self.bg_color = bg_color
        self.description = description

    def __repr__(self):
        return f"<Rank: {self.th_name} ({self.min_xp}+ XP)>"

# ==============================================================================
# MODULE 3: BUSINESS LOGIC LAYER
# ==============================================================================

class RankManager:
    """
    Business Logic Component for Rank Evaluation and Progress Calculation.
    """
    def __init__(self):
        # Initialize Rank Hierarchy (Highest to Lowest)
        self._ranks: List[RankDefinition] = [
            RankDefinition("PRESIDENT", "👑 ประธานรุ่น", 1000, "#F59E0B", "#FEF3C7", "Immunity (ไม่ทำ 3 งาน) + Bonus 1/งาน"),
            RankDefinition("DIRECTOR", "💼 หัวหน้าฝ่าย", 600, "#8B5CF6", "#F3E8FF", "Workload Cut (ลดภาระงาน 50%)"),
            RankDefinition("MANAGER", "👔 หัวหน้าแผนก", 300, "#3B82F6", "#DBEAFE", "Second Chance (แก้ตัวได้ 1 ครั้ง/หน่วย)"),
            RankDefinition("EMPLOYEE", "👨‍💼 พนักงาน", 100, "#10B981", "#D1FAE5", "Time Extension (ส่งช้าได้ 2 สัปดาห์)"),
            RankDefinition("INTERN", "👶 เด็กฝึกงาน", 0, "#64748B", "#F1F5F9", "Check-up (สิทธิ์ให้ครูตรวจงานก่อนส่ง)"),
            RankDefinition("PROBATION", "⚠️ ทัณฑ์บน", -999999, "#EF4444", "#FEE2E2", "สถานะวิกฤต! รีบซ่อมคะแนนด่วน")
        ]
        self._probation_rank = self._ranks[-1]
        self._default_rank = self._ranks[-2] # Intern

    @property
    def all_ranks(self) -> List[RankDefinition]:
        return self._ranks

    def get_rank_by_xp(self, xp: int) -> RankDefinition:
        """Determines rank based on XP value."""
        if xp < 0:
            return self._probation_rank
        
        for rank in self._ranks:
            if rank.id != "PROBATION" and xp >= rank.min_xp:
                return rank
        return self._default_rank

    def calculate_progress_to_next(self, xp: int) -> Tuple[float, str]:
        """Calculates percentage progress to the next tier."""
        if xp < 0:
            return 0.0, "Critical Status"
        
        current_rank = self.get_rank_by_xp(xp)
        try:
            idx = self._ranks.index(current_rank)
        except ValueError:
             return 0.0, "Error"

        if idx > 0:
            next_rank = self._ranks[idx - 1]
            target_xp = next_rank.min_xp
            denominator = target_xp if target_xp > 0 else 100 
            progress_pct = min(1.0, xp / denominator)
            return progress_pct, f"{int(progress_pct * 100)}% to {next_rank.th_name}"
            
        return 1.0, "MAX LEVEL REACHED"

class BadgeSystem:
    """
    Gamification Logic for Badge Awards.
    """
    def __init__(self):
        self._badge_catalog: Dict[str, str] = {
            "wealthy": "💎",    "sniper": "🎯",     "debtor": "💸", 
            "phoenix": "🔥",    "first_blood": "🩸", "veteran": "🎖️"
        }

    def evaluate_badges(self, current_xp: int, history: List[Dict[str, Any]]) -> List[str]:
        earned_badges = set()
        if current_xp >= 800: earned_badges.add("wealthy")
        if current_xp < 0: earned_badges.add("debtor")
        
        if history:
            earned_badges.add("first_blood")
            if len(history) >= 10: earned_badges.add("veteran")
            if any(h.get('amount', 0) >= 100 for h in history): earned_badges.add("sniper")
            
        return list(earned_badges)

    def render_badges(self, badge_ids: List[str]) -> str:
        return "".join([self._badge_catalog.get(bid, "") for bid in badge_ids])

# ==============================================================================
# MODULE 4: DATA ACCESS LAYER (DAL)
# ==============================================================================

class GoogleSheetsRepository:
    """
    Persistence Layer handling Google Sheets operations.
    Implements Data Mapper pattern for sanitization.
    """
    SCHEMA = ['Room', 'GroupName', 'XP', 'Members', 'LastUpdated', 'HistoryLog', 'Badges']

    def __init__(self):
        self.cfg = AppConfig()
        self.conn = self._establish_connection()

    def _establish_connection(self) -> GSheetsConnection:
        try:
            conn = st.connection(self.cfg.DB_CONNECTION_NAME, type=GSheetsConnection)
            return conn
        except Exception as e:
            logger.critical(f"DB Connect Failed: {e}")
            st.error(f"System Error: Database connection failed. {e}")
            st.stop()

    def _sanitize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=self.SCHEMA)
        
        missing = set(self.SCHEMA) - set(df.columns)
        for col in missing:
            df[col] = None

        df = df[self.SCHEMA].copy().dropna(how='all')
        df['XP'] = pd.to_numeric(df['XP'], errors='coerce').fillna(0).astype(int)
        
        for col in ['HistoryLog', 'Badges']:
            df[col] = df[col].fillna("[]").astype(str)
            mask = ~df[col].str.startswith("[") | ~df[col].str.endswith("]")
            df.loc[mask, col] = "[]"

        for col in ['Room', 'GroupName', 'Members', 'LastUpdated']:
            df[col] = df[col].fillna("").astype(str)

        return df

    def fetch_all_data(self) -> pd.DataFrame:
        try:
            df = self.conn.read(worksheet=self.cfg.DB_MAIN_WORKSHEET, ttl=self.cfg.DB_CACHE_TTL)
            return self._sanitize_dataframe(df)
        except Exception as e:
            logger.error(f"Fetch Error: {e}")
            return pd.DataFrame(columns=self.SCHEMA)

    def commit_data(self, df: pd.DataFrame) -> bool:
        try:
            df_write = self._sanitize_dataframe(df)
            self.conn.update(worksheet=self.cfg.DB_MAIN_WORKSHEET, data=df_write)
            st.cache_data.clear()
            return True
        except Exception as e:
            logger.error(f"Commit Error: {e}")
            st.error(f"Save failed: {e}")
            return False

    # --- Transactions ---

    def create_group_record(self, room: str, name: str, members: str, current_df: pd.DataFrame) -> bool:
        dup = (current_df['Room'] == room) & (current_df['GroupName'] == name)
        if dup.any(): return False
        
        new_row = {
            "Room": room, "GroupName": name, "XP": 0, "Members": members,
            "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "HistoryLog": "[]", "Badges": "[]"
        }
        return self.commit_data(pd.concat([current_df, pd.DataFrame([new_row])], ignore_index=True))

    def update_group_record(self, room: str, old: str, new: str, mem: str, current_df: pd.DataFrame) -> bool:
        if new != old:
             if ((current_df['Room'] == room) & (current_df['GroupName'] == new)).any(): return False

        mask = (current_df['Room'] == room) & (current_df['GroupName'] == old)
        if not mask.any(): return False
             
        idx = current_df[mask].index[0]
        current_df.at[idx, 'GroupName'] = new
        current_df.at[idx, 'Members'] = mem
        current_df.at[idx, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        return self.commit_data(current_df)

    def delete_group_record(self, room: str, name: str, current_df: pd.DataFrame) -> bool:
        mask = ~((current_df['Room'] == room) & (current_df['GroupName'] == name))
        return self.commit_data(current_df[mask])

    def process_xp_transaction(self, room: str, targets: List[str], amount: int, reason: str, 
                               current_df: pd.DataFrame, badge_sys: BadgeSystem) -> Tuple[bool, int]:
        cnt = 0
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        for t in targets:
            mask = (current_df['Room'] == room) & (current_df['GroupName'] == t)
            if mask.any():
                idx = current_df[mask].index[0]
                try: hist = json.loads(current_df.at[idx, 'HistoryLog'])
                except: hist = []
                
                new_log = {"id": str(uuid.uuid4())[:8], "ts": ts, "reason": reason, "amount": int(amount)}
                hist.insert(0, new_log)
                bal = sum(x['amount'] for x in hist)
                hist[0]['balance'] = bal
                badges = badge_sys.evaluate_badges(bal, hist)
                
                current_df.at[idx, 'XP'] = bal
                current_df.at[idx, 'HistoryLog'] = json.dumps(hist, ensure_ascii=False)
                current_df.at[idx, 'Badges'] = json.dumps(badges, ensure_ascii=False)
                current_df.at[idx, 'LastUpdated'] = ts
                cnt += 1
        
        if cnt > 0: return self.commit_data(current_df), cnt
        return False, 0

    def apply_history_override(self, room: str, target: str, new_hist_df: pd.DataFrame, 
                               current_df: pd.DataFrame, badge_sys: BadgeSystem) -> bool:
        mask = (current_df['Room'] == room) & (current_df['GroupName'] == target)
        if not mask.any(): return False
            
        idx = current_df[mask].index[0]
        hist_list = new_hist_df.to_dict('records')
        
        # Logic: Sort asc -> calc balance -> sort desc -> save
        try: hist_asc = sorted(hist_list, key=lambda x: x.get('ts', ''))
        except: hist_asc = hist_list

        run = 0
        for item in hist_asc:
            amt = int(item.get('amount', 0))
            item['amount'] = amt
            run += amt
            item['balance'] = run
            
        hist_desc = sorted(hist_asc, key=lambda x: x.get('ts', ''), reverse=True)
        badges = badge_sys.evaluate_badges(run, hist_desc)
        
        current_df.at[idx, 'XP'] = run
        current_df.at[idx, 'HistoryLog'] = json.dumps(hist_desc, ensure_ascii=False)
        current_df.at[idx, 'Badges'] = json.dumps(badges, ensure_ascii=False)
        return self.commit_data(current_df)

# ==============================================================================
# MODULE 5: GRAPHICS ENGINE (THAI TYPOGRAPHY OPTIMIZED)
# ==============================================================================

class GraphicsEngine:
    """
    Renders High-Fidelity Leaderboard Images.
    Includes advanced text cleaning and explicit positioning to prevent
    Thai vowel overlaps.
    """
    def __init__(self):
        self.cfg = AppConfig()
        self._font_cache = {}

    def _get_font(self, name: str, size: int) -> ImageFont.FreeTypeFont:
        key = (name, size)
        if key not in self._font_cache:
            try:
                self._font_cache[key] = ImageFont.truetype(name, size)
            except IOError:
                logger.warning(f"Font {name} not found. Using default.")
                self._font_cache[key] = ImageFont.load_default()
        return self._font_cache[key]

    def _clean_text_for_render(self, text: str) -> str:
        """
        Sanitizes text to remove Emoji/Special Chars that cause rendering artifacts (Squares).
        Keeps Thai, English, Numbers, and punctuation.
        """
        if not isinstance(text, str): return ""
        # Regex to keep Thai Range (u0E00-u0E7F) + ASCII
        return re.sub(r'[^\w\s\u0E00-\u0E7F().,-]', '', text).strip()

    def _draw_text_with_autofit(self, draw: ImageDraw.Draw, text: str, 
                                x: int, y: int, max_width: int,
                                font_name: str, max_size: int, 
                                color: str, anchor: str = "lt") -> None:
        """Draws text with automatic font size reduction."""
        text = self._clean_text_for_render(text)
        if not text: return

        current_size = max_size
        min_size = 30
        font = self._get_font(font_name, current_size)
        
        while current_size > min_size:
            if font.getlength(text) <= max_width: break
            current_size -= 4
            font = self._get_font(font_name, current_size)
            
        draw.text((x, y), text, font=font, fill=color, anchor=anchor)

    def render_leaderboard_image(self, room_name: str, df: pd.DataFrame, rank_manager: RankManager) -> bytes:
        """
        Generates the leaderboard image.
        Uses a strict Y-Coordinate Grid to prevent overlaps.
        """
        logger.info(f"Rendering image for {room_name}")
        data = df.sort_values("XP", ascending=False).reset_index(drop=True)
        
        # 1. Calculate Dynamic Height
        total_rows = len(data)
        # FIX: Define canvas_height properly
        canvas_height = (
            self.cfg.IMG_HEADER_HEIGHT + 
            (total_rows * self.cfg.IMG_ROW_HEIGHT) + 
            self.cfg.IMG_FOOTER_HEIGHT
        )
        
        # 2. Init Canvas
        img = Image.new('RGBA', (self.cfg.IMG_WIDTH, canvas_height), color=self.cfg.COLOR_BG_MAIN)
        draw = ImageDraw.Draw(img)
        
        # --- HEADER ---
        draw.rectangle([(0, 0), (self.cfg.IMG_WIDTH, self.cfg.IMG_HEADER_HEIGHT)], fill=self.cfg.COLOR_BRAND_PRIMARY)
        draw.ellipse([(900, -150), (1500, 450)], fill=self.cfg.COLOR_BRAND_SECONDARY)
        draw.ellipse([(-100, 250), (500, 850)], fill=self.cfg.COLOR_BRAND_SECONDARY)
        
        cx = self.cfg.IMG_WIDTH // 2
        f_icon = self._get_font(self.cfg.FONT_PRIMARY_REG, 180)
        draw.text((cx, 220), "🏆", font=f_icon, fill="white", anchor="mm")
        
        f_title = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 60)
        draw.text((cx, 380), "CLASSROOM LEADERBOARD", font=f_title, fill=self.cfg.COLOR_BRAND_ACCENT, anchor="mm")
        
        f_room = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 150)
        draw.text((cx, 550), room_name, font=f_room, fill="white", anchor="mm")

        # --- ROWS ---
        current_y = self.cfg.IMG_HEADER_HEIGHT + 50
        
        f_rank_num = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 85)
        f_score_val = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 110)
        f_score_lbl = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 45)
        f_members = self._get_font(self.cfg.FONT_PRIMARY_REG, 42)
        f_rank_title = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 48)
        f_privilege = self._get_font(self.cfg.FONT_PRIMARY_REG, 36)

        for i, row in data.iterrows():
            xp = row['XP']
            rank_def = rank_manager.get_rank_by_xp(xp)
            pct, _ = rank_manager.calculate_progress_to_next(xp)
            
            theme = self.cfg.RANK_THEMES.get(i if i < 3 else "default")
            score_col = self.cfg.COLOR_SCORE_NEGATIVE if xp < 0 else self.cfg.COLOR_SCORE_POSITIVE

            # Card Metrics
            card_x = self.cfg.IMG_PADDING_X
            card_w = self.cfg.IMG_WIDTH - (self.cfg.IMG_PADDING_X * 2)
            card_h = self.cfg.IMG_ROW_HEIGHT - 40 
            
            # Card Body
            draw.rounded_rectangle([(card_x+8, current_y+10), (card_x+card_w+8, current_y+card_h+10)], radius=self.cfg.IMG_CARD_RADIUS, fill=self.cfg.COLOR_CARD_SHADOW)
            draw.rounded_rectangle([(card_x, current_y), (card_x+card_w, current_y+card_h)], radius=self.cfg.IMG_CARD_RADIUS, fill=self.cfg.COLOR_CARD_SURFACE)

            # 1. Rank Circle
            circle_cx = card_x + 120
            circle_cy = current_y + (card_h // 2)
            draw.ellipse([(circle_cx-75, circle_cy-75), (circle_cx+75, circle_cy+75)], fill=theme['hex'])
            draw.text((circle_cx, circle_cy), str(i+1), font=f_rank_num, fill="white", anchor="mm")

            # 2. Content Zone (Updated Y-Grid for Thai Vowels)
            info_x = card_x + 260
            info_w = 650
            
            # Expanded Y-Grid Spacing
            Y_POS_NAME = current_y + 50
            Y_POS_MEMBERS = Y_POS_NAME + 95   # Gap for Group Name Vowels
            Y_POS_PROGRESS_BAR = Y_POS_MEMBERS + 85 # Gap for Member Vowels
            Y_POS_RANK_TITLE = Y_POS_PROGRESS_BAR + 65
            Y_POS_PRIVILEGE = Y_POS_RANK_TITLE + 65 # Gap for Rank Title Vowels

            # Name
            self._draw_text_with_autofit(draw, str(row['GroupName']), info_x, Y_POS_NAME, info_w, self.cfg.FONT_PRIMARY_BOLD, 80, self.cfg.COLOR_TEXT_PRIMARY, anchor="lt")
            
            # Members
            mem_txt = self._clean_text_for_render(str(row['Members']))
            if len(mem_txt) > 65: mem_txt = mem_txt[:62] + "..."
            draw.text((info_x, Y_POS_MEMBERS), mem_txt, font=f_members, fill=self.cfg.COLOR_TEXT_SECONDARY, anchor="lt")

            # Bar
            draw.rounded_rectangle([(info_x, Y_POS_PROGRESS_BAR), (info_x+580, Y_POS_PROGRESS_BAR+16)], radius=8, fill=self.cfg.COLOR_BG_MAIN)
            if pct > 0:
                fw = max(int(580*pct), 20)
                draw.rounded_rectangle([(info_x, Y_POS_PROGRESS_BAR), (info_x+fw, Y_POS_PROGRESS_BAR+16)], radius=8, fill=rank_def.color)

            # Rank & Privilege
            clean_rank_title = self._clean_text_for_render(rank_def.th_name)
            draw.text((info_x, Y_POS_RANK_TITLE), clean_rank_title, font=f_rank_title, fill=rank_def.color, anchor="lt")
            
            self._draw_text_with_autofit(draw, rank_def.description, info_x, Y_POS_PRIVILEGE, info_w, self.cfg.FONT_PRIMARY_REG, 40, self.cfg.COLOR_TEXT_SECONDARY, anchor="lt")

            # 3. Score
            score_x = self.cfg.IMG_WIDTH - self.cfg.IMG_PADDING_X - 40
            score_cy = current_y + (card_h // 2)
            draw.text((score_x, score_cy-10), f"{xp}", font=f_score_val, fill=score_col, anchor="rs")
            draw.text((score_x, score_cy+50), "XP", font=f_score_lbl, fill=self.cfg.COLOR_TEXT_MUTED, anchor="rs")

            current_y += self.cfg.IMG_ROW_HEIGHT

        # --- FOOTER ---
        footer_cy = canvas_height - (self.cfg.IMG_FOOTER_HEIGHT // 2)
        f_foot = self._get_font(self.cfg.FONT_PRIMARY_REG, 38)
        ts = datetime.now().strftime('%d/%m/%Y %H:%M')
        draw.text((self.cfg.IMG_WIDTH // 2, footer_cy), f"Generated by {self.cfg.APP_NAME} • {ts}", font=f_foot, fill=self.cfg.COLOR_TEXT_MUTED, anchor="mm")

        # Output
        img_final = img.convert('RGB')
        buf = io.BytesIO()
        img_final.save(buf, format='PNG', optimize=True)
        buf.seek(0)
        return buf.getvalue()

# ==============================================================================
# MODULE 6: PRESENTATION LAYER (STREAMLIT UI)
# ==============================================================================

class UIManager:
    """
    Manages the Streamlit interface, layout, and user interaction flow.
    """
    def __init__(self):
        self.cfg = AppConfig()
        self.db = GoogleSheetsRepository()
        self.rank_mgr = RankManager()
        self.badge_sys = BadgeSystem()
        self.gfx = GraphicsEngine()

    def setup_page(self):
        st.set_page_config(page_title=f"{self.cfg.APP_NAME}", page_icon="🏫", layout="wide", initial_sidebar_state="expanded")
        self._inject_custom_css()

    def _inject_custom_css(self):
        st.markdown(f"""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&family=Prompt:wght@300;400;500;700&display=swap');
            :root {{ --primary: {self.cfg.COLOR_BRAND_PRIMARY}; --secondary: {self.cfg.COLOR_BRAND_SECONDARY}; --bg-body: {self.cfg.COLOR_BG_MAIN}; }}
            html, body, [class*="css"] {{ font-family: 'Sarabun', 'Prompt', sans-serif; color: #1E293B; background-color: var(--bg-body); }}
            .stApp {{ background-color: var(--bg-body); }}
            div[data-testid="stExpander"] {{ border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-radius: 12px; background: white; }}
            .stButton>button {{ border-radius: 10px; font-weight: 600; padding: 0.5rem 1rem; }}
            .stTextInput>div>div>input {{ border-radius: 10px; border: 1px solid #E2E8F0; }}
            .hero-banner {{ background: linear-gradient(120deg, var(--primary), var(--secondary)); padding: 2.5rem; border-radius: 20px; color: white; margin-bottom: 2rem; display: flex; align-items: center; justify-content: space-between; }}
            .glass-card {{ background: rgba(255, 255, 255, 0.9); border-radius: 16px; border: 1px solid #E2E8F0; padding: 1.5rem; margin-bottom: 1rem; }}
            .badge {{ display: inline-block; padding: 0.3em 0.8em; font-size: 80%; font-weight: 700; border-radius: 0.5rem; }}
            </style>
        """, unsafe_allow_html=True)

    def render_sidebar(self) -> str:
        with st.sidebar:
            st.image("https://cdn-icons-png.flaticon.com/512/4738/4738983.png", width=60)
            st.title("Control Panel")
            st.markdown(f"v{self.cfg.APP_VERSION}")
            st.divider()
            
            # FIX: Updated Classroom List
            selected_room = st.selectbox(
                "Select Active Class",
                ["ม.1/1", "ม.1/2", "ม.1/10"],
                index=0
            )
            
            st.divider()
            if st.button("📥 Export CSV"):
                df = self.db.fetch_all_data()
                st.download_button("Download", df.to_csv(index=False).encode('utf-8'), "data.csv")
            
            if st.button("🔄 Reset DB"):
                self.db.commit_data(pd.DataFrame(columns=self.db.SCHEMA))
                st.rerun()
            
            return selected_room

    def render_hero_section(self, room_name: str, group_count: int):
        st.markdown(f"""
            <div class="hero-banner">
                <div class="hero-title">
                    <div class="hero-subtitle">{self.cfg.ORG_NAME} • {self.cfg.APP_NAME}</div>
                    <h1>{room_name}</h1>
                </div>
                <div class="hero-stat">
                    <div class="hero-stat-number">{group_count}</div>
                    <div>Active Teams</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    def _render_command_center_tab(self, room_name: str, room_df: pd.DataFrame, all_df: pd.DataFrame):
        st.header("⚡ Command Center")
        if room_df.empty:
            st.info("Create groups in Management tab first.")
            return

        targets = st.multiselect("Select Teams", sorted(room_df['GroupName'].unique()))
        st.divider()
        
        c1, c2 = st.columns(2)
        def act(r, a):
            if targets: 
                self.db.process_xp_transaction(room_name, targets, a, r, all_df, self.badge_sys)
                st.success("Done!"); time.sleep(0.5); st.rerun()
                
        with c1:
            st.button("📚 On-Time (+50)", on_click=act, args=("ส่งงานตรงเวลา", 50), use_container_width=True)
            st.button("🙋 Participate (+20)", on_click=act, args=("มีส่วนร่วม", 20), use_container_width=True)
        with c2:
            with st.form("custom"):
                r = st.text_input("Reason")
                a = st.number_input("XP", step=5)
                if st.form_submit_button("Submit") and r and a: act(r, a)

    def _render_leaderboard_tab(self, room_name: str, room_df: pd.DataFrame):
        st.header("🏆 Leaderboard")
        if st.button("✨ Generate Image", type="primary"):
            try:
                img = self.gfx.render_leaderboard_image(room_name, room_df, self.rank_mgr)
                st.image(img, caption="Preview")
                st.download_button("Download PNG", img, "lb.png", "image/png")
            except Exception as e:
                st.error(f"Render Error: {e}")
            
        for _, row in room_df.sort_values("XP", ascending=False).iterrows():
            r = self.rank_mgr.get_rank_by_xp(row['XP'])
            st.markdown(f"""<div class="glass-card" style="border-left:5px solid {r.color}"><h3>{row['GroupName']}</h3>{row['XP']} XP | {r.th_name}</div>""", unsafe_allow_html=True)

    def _render_analytics_tab(self, room_df: pd.DataFrame):
        st.header("📈 Analytics")
        if not room_df.empty:
            st.bar_chart(room_df.set_index("GroupName")['XP'])

    def _render_privileges_tab(self):
        st.header("ℹ️ Privileges")
        for r in self.rank_mgr.all_ranks:
            st.info(f"**{r.th_name}**: {r.description}")

    def _render_management_tab(self, room_name: str, room_df: pd.DataFrame, all_df: pd.DataFrame):
        st.header("🛠️ Management")
        with st.form("new"):
            n = st.text_input("Name"); m = st.text_area("Members")
            if st.form_submit_button("Create") and n:
                self.db.create_group_record(room_name, n, m, all_df)
                st.rerun()
        
        d = st.selectbox("Delete", ["-"]+list(room_df['GroupName'].unique()))
        if d != "-" and st.button("Confirm Delete"):
            self.db.delete_group_record(room_name, d, all_df)
            st.rerun()

    def run(self):
        self.setup_page()
        selected_room = self.render_sidebar()
        try:
            all_df = self.db.fetch_all_data()
            room_df = all_df[all_df['Room'] == selected_room].copy()
        except: return
        
        self.render_hero_section(selected_room, len(room_df))
        t1, t2, t3, t4, t5 = st.tabs(["Command", "Leaderboard", "Analytics", "Privileges", "Manage"])
        
        with t1: self._render_command_center_tab(selected_room, room_df, all_df)
        with t2: self._render_leaderboard_tab(selected_room, room_df)
        with t3: self._render_analytics_tab(room_df)
        with t4: self._render_privileges_tab()
        with t5: self._render_management_tab(selected_room, room_df, all_df)

# ==============================================================================
# EXECUTION ENTRY POINT
# ==============================================================================
if __name__ == "__main__":
    app = UIManager()
    app.run()
