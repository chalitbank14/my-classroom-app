"""
Classroom OS: Enterprise Ultimate Edition
Version: 8.0.0-Titanium
Author: AI Development Team
Date: 2026-01-20

Description:
This is the definitive, fully-featured, enterprise-grade architecture for the Classroom OS platform.
It is designed with maximum granularity, separating concerns into distinct service layers,
data models, and view controllers.

ARCHITECTURE OVERVIEW:
1.  CORE KERNEL: Configuration, Logging, and Custom Exceptions.
2.  DOMAIN MODELS: Typed Data Classes for Teams, Ranks, Badges, and Transactions.
3.  UTILITIES: Helper classes for Text, Date, and ID manipulation.
4.  PERSISTENCE LAYER (DAL): Robust Google Sheets adapter with caching and atomic commits.
5.  BUSINESS LOGIC LAYER (BLL): Gamification rules engine (Ranks, Badges, Progress).
6.  GRAPHICS ENGINE: Advanced PIL-based rendering with Thai Typography correction.
7.  UI COMPONENT LAYER: Reusable Streamlit widgets and CSS injection.
8.  APPLICATION CONTROLLER: Main event loop and tab management.

CHANGELOG (v8.0.0):
- [FIX] Restored granular Management features (Edit Name, Move/Edit Members).
- [FIX] Thai Vowel Floating/Sinking issues resolved via 'True Bounding Box' calculation.
- [FIX] Missing Emoji artifacts resolved via Unicode Filtering.
- [FEAT] Expanded Codebase for maximum maintainability and detail.
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
from typing import List, Dict, Optional, Tuple, Any, Union, Set
from dataclasses import dataclass, field, asdict
from PIL import Image, ImageDraw, ImageFont
from abc import ABC, abstractmethod

# ==============================================================================
# SECTION 1: SYSTEM KERNEL & INFRASTRUCTURE
# ==============================================================================

# 1.1 Logging Subsystem
# ------------------------------------------------------------------------------
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] [%(name)s] > %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("ClassroomOS.System")

# 1.2 Custom Exception Hierarchy
# ------------------------------------------------------------------------------
class ClassroomOSError(Exception):
    """Base exception for the application."""
    pass

class DatabaseConnectionError(ClassroomOSError):
    """Raised when connection to Google Sheets fails."""
    pass

class DataIntegrityError(ClassroomOSError):
    """Raised when data validation fails."""
    pass

class GraphicsRenderingError(ClassroomOSError):
    """Raised when image generation fails."""
    pass

# 1.3 Configuration Manager
# ------------------------------------------------------------------------------
class SystemConfig:
    """
    Global configuration object holding all static constants and settings.
    Acts as the Single Source of Truth (SSOT).
    """
    # Metadata
    APP_NAME: str = "Classroom OS"
    APP_VERSION: str = "8.0.0-Titanium"
    ORGANIZATION: str = "Acme Education Systems"
    
    # Database Settings
    DB_CONN_NAME: str = "gsheets"
    DB_SHEET_NAME: str = "Sheet1"
    DB_TTL: int = 0  # 0 = No caching (Real-time)

    # Graphic Engine Settings (Thai Typography Tuned)
    IMG_WIDTH: int = 1400
    IMG_HEADER_HEIGHT: int = 750
    IMG_ROW_HEIGHT: int = 600  # Extra space for vowels
    IMG_FOOTER_HEIGHT: int = 180
    IMG_PADDING: int = 50
    IMG_CARD_RADIUS: int = 40
    
    # Fonts
    FONT_BOLD: str = "Sarabun-Bold.ttf"
    FONT_REGULAR: str = "Sarabun-Regular.ttf"

    # Color Palette (Deep Indigo Enterprise Theme)
    COLOR_PRIMARY: str = "#4338CA"      # Indigo 700
    COLOR_SECONDARY: str = "#3730A3"    # Indigo 800
    COLOR_ACCENT: str = "#A5B4FC"       # Indigo 200
    COLOR_BACKGROUND: str = "#F1F5F9"   # Slate 100
    COLOR_SURFACE: str = "#FFFFFF"      # White
    COLOR_BORDER: str = "#E2E8F0"       # Slate 200
    COLOR_SHADOW: str = "#94A3B8"       # Slate 400
    
    COLOR_TEXT_MAIN: str = "#1E293B"    # Slate 800
    COLOR_TEXT_SUB: str = "#64748B"     # Slate 500
    COLOR_TEXT_MUTED: str = "#94A3B8"   # Slate 400
    
    COLOR_SUCCESS: str = "#10B981"      # Emerald
    COLOR_DANGER: str = "#EF4444"       # Red
    COLOR_WARNING: str = "#F59E0B"      # Amber

    # Rank Theme Mapping
    RANK_THEMES = {
        0: {"hex": "#F59E0B", "bg": "#FEF3C7", "name": "Gold"},
        1: {"hex": "#94A3B8", "bg": "#F1F5F9", "name": "Silver"},
        2: {"hex": "#B45309", "bg": "#FFEDD5", "name": "Bronze"},
        "default": {"hex": "#64748B", "bg": "#F8FAFC", "name": "Slate"}
    }

# ==============================================================================
# SECTION 2: DOMAIN MODELS (DATA STRUCTURES)
# ==============================================================================

@dataclass
class RankModel:
    """Represents a Rank Tier definition."""
    id: str
    thai_name: str
    min_xp: int
    color_hex: str
    bg_hex: str
    privilege_desc: str

    def display_str(self) -> str:
        return f"{self.thai_name} ({self.min_xp}+ XP)"

@dataclass
class TeamModel:
    """Represents a Team entity from the database."""
    room: str
    name: str
    xp: int
    members: str
    last_updated: str
    history_json: str = "[]"
    badges_json: str = "[]"

    @property
    def member_list(self) -> List[str]:
        return [m.strip() for m in self.members.split(',') if m.strip()]

@dataclass
class LogEntry:
    """Represents a single transaction log."""
    id: str
    timestamp: str
    reason: str
    amount: int
    balance: int

# ==============================================================================
# SECTION 3: UTILITY SERVICES
# ==============================================================================

class TextUtils:
    """Helper methods for string manipulation."""
    
    @staticmethod
    def clean_for_rendering(text: str) -> str:
        """
        Removes characters that cause rendering artifacts (like unsupported Emojis).
        Preserves Thai characters, English, Numbers, and basic punctuation.
        """
        if not text: return ""
        # Regex explanation:
        # \w matches alphanumeric + underscore
        # \s matches whitespace
        # \u0E00-\u0E7F matches Thai Unicode block
        # ().,- matches basic punctuation
        return re.sub(r'[^\w\s\u0E00-\u0E7F().,-]', '', str(text)).strip()

    @staticmethod
    def truncate(text: str, max_len: int) -> str:
        if len(text) > max_len:
            return text[:max_len-3] + "..."
        return text

class TimeUtils:
    """Helper methods for date and time."""
    
    @staticmethod
    def now_str() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def generate_id() -> str:
        return str(uuid.uuid4())[:8]

# ==============================================================================
# SECTION 4: DATA ACCESS LAYER (DAL)
# ==============================================================================

class DatabaseAdapter:
    """
    Robust Data Access Object (DAO) for Google Sheets.
    Handles connection lifecycle, CRUD operations, and Schema validation.
    """
    # Strict Schema Definition
    COLUMNS = ['Room', 'GroupName', 'XP', 'Members', 'LastUpdated', 'HistoryLog', 'Badges']

    def __init__(self):
        self.config = SystemConfig()
        self._conn = None
        self._connect()

    def _connect(self):
        """Establishes connection with retry logic."""
        try:
            self._conn = st.connection(self.config.DB_CONN_NAME, type=GSheetsConnection)
            logger.info("Database connection established.")
        except Exception as e:
            logger.critical(f"Database connection failed: {e}")
            st.error(f"CRITICAL: Database connection failed. Details: {e}")
            st.stop()

    def _validate_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensures DataFrame conforms to strict schema."""
        if df.empty:
            return pd.DataFrame(columns=self.COLUMNS)
        
        # Add missing columns
        missing = set(self.COLUMNS) - set(df.columns)
        for col in missing:
            df[col] = None
            
        # Reorder and filter columns
        df = df[self.COLUMNS].copy()
        
        # Type Enforcement
        df['XP'] = pd.to_numeric(df['XP'], errors='coerce').fillna(0).astype(int)
        
        # JSON Safety
        for col in ['HistoryLog', 'Badges']:
            df[col] = df[col].fillna("[]").astype(str)
            # Basic repair for broken JSON strings
            mask = ~df[col].str.startswith("[")
            df.loc[mask, col] = "[]"
            
        # String Safety
        for col in ['Room', 'GroupName', 'Members', 'LastUpdated']:
            df[col] = df[col].fillna("").astype(str)
            
        return df

    def fetch_data(self) -> pd.DataFrame:
        """Retrieves and sanitizes all data."""
        try:
            df = self._conn.read(worksheet=self.config.DB_SHEET_NAME, ttl=self.config.DB_TTL)
            return self._validate_schema(df)
        except Exception as e:
            logger.error(f"Fetch Error: {e}")
            return pd.DataFrame(columns=self.COLUMNS)

    def commit(self, df: pd.DataFrame) -> bool:
        """Commits changes to the database."""
        try:
            clean_df = self._validate_schema(df)
            self._conn.update(worksheet=self.config.DB_SHEET_NAME, data=clean_df)
            st.cache_data.clear()
            logger.info("Data committed successfully.")
            return True
        except Exception as e:
            logger.error(f"Commit Error: {e}")
            st.error(f"Save Failed: {e}")
            return False

    # --- CRUD METHODS ---

    def create_team(self, room: str, name: str, members: str, current_df: pd.DataFrame) -> bool:
        # Check Uniqueness
        if ((current_df['Room'] == room) & (current_df['GroupName'] == name)).any():
            logger.warning(f"Create failed: Duplicate name {name} in {room}")
            return False
        
        new_row = pd.DataFrame([{
            "Room": room,
            "GroupName": name,
            "XP": 0,
            "Members": members,
            "LastUpdated": TimeUtils.now_str(),
            "HistoryLog": "[]",
            "Badges": "[]"
        }])
        
        return self.commit(pd.concat([current_df, new_row], ignore_index=True))

    def update_team_details(self, room: str, old_name: str, new_name: str, new_members: str, current_df: pd.DataFrame) -> bool:
        # Check Name Collision if name changed
        if new_name != old_name:
            if ((current_df['Room'] == room) & (current_df['GroupName'] == new_name)).any():
                logger.warning("Update failed: Name collision.")
                return False
        
        # Find and Update
        mask = (current_df['Room'] == room) & (current_df['GroupName'] == old_name)
        if not mask.any():
            return False
            
        idx = current_df[mask].index[0]
        current_df.at[idx, 'GroupName'] = new_name
        current_df.at[idx, 'Members'] = new_members
        current_df.at[idx, 'LastUpdated'] = TimeUtils.now_str()
        
        return self.commit(current_df)

    def delete_team(self, room: str, name: str, current_df: pd.DataFrame) -> bool:
        mask = ~((current_df['Room'] == room) & (current_df['GroupName'] == name))
        return self.commit(current_df[mask])

    def save_team_state(self, room: str, name: str, xp: int, history: List[dict], badges: List[str], current_df: pd.DataFrame) -> bool:
        """Atomic update of a single team's state."""
        mask = (current_df['Room'] == room) & (current_df['GroupName'] == name)
        if not mask.any(): return False
        
        idx = current_df[mask].index[0]
        current_df.at[idx, 'XP'] = xp
        current_df.at[idx, 'HistoryLog'] = json.dumps(history, ensure_ascii=False)
        current_df.at[idx, 'Badges'] = json.dumps(badges, ensure_ascii=False)
        current_df.at[idx, 'LastUpdated'] = TimeUtils.now_str()
        
        return self.commit(current_df)

# ==============================================================================
# SECTION 5: BUSINESS LOGIC LAYER (BLL)
# ==============================================================================

class GamificationEngine:
    """
    Core Logic for Ranks, Badges, and Score Calculation.
    """
    def __init__(self):
        self.config = SystemConfig()
        self._init_ranks()
        self._init_badges()

    def _init_ranks(self):
        self.ranks = [
            RankModel("PRESIDENT", "👑 ประธานรุ่น", 1000, "#F59E0B", "#FEF3C7", "Immunity (ไม่ทำ 3 งาน) + Bonus 1/งาน"),
            RankModel("DIRECTOR", "💼 หัวหน้าฝ่าย", 600, "#8B5CF6", "#F3E8FF", "Workload Cut (ลดภาระงาน 50%)"),
            RankModel("MANAGER", "👔 หัวหน้าแผนก", 300, "#3B82F6", "#DBEAFE", "Second Chance (แก้ตัวได้ 1 ครั้ง/หน่วย)"),
            RankModel("EMPLOYEE", "👨‍💼 พนักงาน", 100, "#10B981", "#D1FAE5", "Time Extension (ส่งช้าได้ 2 สัปดาห์)"),
            RankModel("INTERN", "👶 เด็กฝึกงาน", 0, "#64748B", "#F1F5F9", "Check-up (สิทธิ์ให้ครูตรวจงานก่อนส่ง)"),
            RankModel("PROBATION", "⚠️ ทัณฑ์บน", -999999, "#EF4444", "#FEE2E2", "สถานะวิกฤต! รีบซ่อมคะแนนด่วน")
        ]

    def _init_badges(self):
        self.badges_map = {
            "wealthy": "💎", "sniper": "🎯", "debtor": "💸", 
            "phoenix": "🔥", "first_blood": "🩸", "veteran": "🎖️"
        }

    def get_rank(self, xp: int) -> RankModel:
        if xp < 0: return self.ranks[-1] # Probation
        for rank in self.ranks:
            if rank.id != "PROBATION" and xp >= rank.min_xp:
                return rank
        return self.ranks[-2] # Fallback to Intern

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
            return pct, f"{int(pct*100)}% to {next_rank.thai_name}"
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
        """
        Executes the business logic for adding a transaction.
        Returns: (new_xp, new_history, new_badges)
        """
        new_log = {
            "id": TimeUtils.generate_id(),
            "ts": TimeUtils.now_str(),
            "reason": reason,
            "amount": int(amount)
        }
        
        # Add to history (Newest first)
        new_history = [new_log] + current_history
        
        # Recalculate Balance from scratch to ensure consistency
        # Logic: Sort by time ASC -> Sum -> Sort Desc
        try:
            sorted_asc = sorted(new_history, key=lambda x: x.get('ts', ''))
        except:
            sorted_asc = new_history

        running_bal = 0
        for item in sorted_asc:
            running_bal += int(item.get('amount', 0))
            item['balance'] = running_bal
            
        final_history = sorted(sorted_asc, key=lambda x: x.get('ts', ''), reverse=True)
        final_xp = running_bal
        final_badges = self.calculate_badges(final_xp, final_history)
        
        return final_xp, final_history, final_badges

# ==============================================================================
# SECTION 6: GRAPHICS ENGINE (THAI TYPOGRAPHY CORE)
# ==============================================================================

class GraphicsRenderer:
    """
    High-Performance Image Generation Engine.
    Features:
    - 'True Bounding Box' calculation for text.
    - Explicit Vertical Rhythm Grid to prevent Thai vowel overlap.
    - Automatic Font Scaling.
    - Emoji Sanitization.
    """
    def __init__(self):
        self.config = SystemConfig()
        self._font_cache = {}

    def _get_font(self, name: str, size: int) -> ImageFont.FreeTypeFont:
        key = (name, size)
        if key not in self._font_cache:
            try:
                self._font_cache[key] = ImageFont.truetype(name, size)
            except IOError:
                logger.warning(f"Font {name} not found. Fallback.")
                self._font_cache[key] = ImageFont.load_default()
        return self._font_cache[key]

    def _draw_text_autofit(self, draw, text, x, y, max_w, font_name, max_s, color, anchor="lt"):
        """Draws text that shrinks if it exceeds max_width."""
        # Clean text first
        text = TextUtils.clean_for_rendering(text)
        if not text: return

        size = max_s
        font = self._get_font(font_name, size)
        
        while size > 20: # Min size constraint
            if font.getlength(text) <= max_w:
                break
            size -= 2
            font = self._get_font(font_name, size)
            
        draw.text((x, y), text, font=font, fill=color, anchor=anchor)

    def generate_leaderboard(self, room_name: str, df: pd.DataFrame, logic: GamificationEngine) -> bytes:
        logger.info(f"Generating image for {room_name}...")
        
        # 1. Sort Data
        data = df.sort_values("XP", ascending=False).reset_index(drop=True)
        
        # 2. Setup Canvas
        num_rows = len(data)
        # Correctly calculate height using class constants
        canvas_h = (
            self.config.IMG_HEADER_HEIGHT + 
            (num_rows * self.config.IMG_ROW_HEIGHT) + 
            self.config.IMG_FOOTER_HEIGHT
        )
        
        img = Image.new('RGBA', (self.config.IMG_WIDTH, canvas_h), self.config.COLOR_BACKGROUND)
        draw = ImageDraw.Draw(img)
        
        # 3. Draw Header
        draw.rectangle([(0, 0), (self.config.IMG_WIDTH, self.config.IMG_HEADER_HEIGHT)], fill=self.config.COLOR_PRIMARY)
        # Abstract Shapes
        draw.ellipse([(900, -150), (1500, 450)], fill=self.config.COLOR_SECONDARY)
        draw.ellipse([(-100, 250), (500, 850)], fill=self.config.COLOR_SECONDARY)
        
        cx = self.config.IMG_WIDTH // 2
        f_icon = self._get_font(self.config.FONT_REGULAR, 180)
        draw.text((cx, 220), "🏆", font=f_icon, fill="white", anchor="mm")
        
        f_title = self._get_font(self.config.FONT_BOLD, 60)
        draw.text((cx, 380), "CLASSROOM LEADERBOARD", font=f_title, fill=self.config.COLOR_ACCENT, anchor="mm")
        
        f_room = self._get_font(self.config.FONT_BOLD, 150)
        draw.text((cx, 550), room_name, font=f_room, fill="white", anchor="mm")
        
        # 4. Draw Rows
        curr_y = self.config.IMG_HEADER_HEIGHT + 50
        
        # Font definitions
        f_rank = self._get_font(self.config.FONT_BOLD, 85)
        f_score = self._get_font(self.config.FONT_BOLD, 110)
        f_label = self._get_font(self.config.FONT_BOLD, 45)
        f_members = self._get_font(self.config.FONT_REGULAR, 42)
        f_rank_title = self._get_font(self.config.FONT_BOLD, 48)
        f_desc = self._get_font(self.config.FONT_REGULAR, 36)

        for i, row in data.iterrows():
            xp = row['XP']
            rank = logic.get_rank(xp)
            pct, _ = logic.get_progress(xp)
            
            # Theme
            theme = self.config.RANK_THEMES.get(i if i < 3 else "default")
            score_col = self.config.COLOR_DANGER if xp < 0 else self.config.COLOR_SUCCESS
            
            # Dimensions
            card_x = self.config.IMG_PADDING
            card_w = self.config.IMG_WIDTH - (self.config.IMG_PADDING * 2)
            card_h = self.config.IMG_ROW_HEIGHT - 40
            
            # Card Body
            draw.rounded_rectangle(
                [(card_x+8, curr_y+10), (card_x+card_w+8, curr_y+card_h+10)], 
                radius=self.config.IMG_CARD_RADIUS, fill=self.config.COLOR_SHADOW
            )
            draw.rounded_rectangle(
                [(card_x, curr_y), (card_x+card_w, curr_y+card_h)], 
                radius=self.config.IMG_CARD_RADIUS, fill=self.config.COLOR_SURFACE
            )
            
            # Rank Circle
            cy = curr_y + (card_h // 2)
            cx_circle = card_x + 120
            draw.ellipse([(cx_circle-75, cy-75), (cx_circle+75, cy+75)], fill=theme['hex'])
            draw.text((cx_circle, cy), str(i+1), font=f_rank, fill="white", anchor="mm")
            
            # Content Area (Middle)
            # EXPLICIT VERTICAL GRID to prevent Thai overlapping
            content_x = card_x + 260
            content_w = 650
            
            # Grid Offsets (Relative to curr_y)
            # Increased spacing to 70-80px per line
            Y_NAME = curr_y + 50
            Y_MEMBERS = Y_NAME + 95
            Y_BAR = Y_MEMBERS + 85
            Y_TITLE = Y_BAR + 65
            Y_DESC = Y_TITLE + 65
            
            # 1. Group Name
            self._draw_text_autofit(draw, str(row['GroupName']), content_x, Y_NAME, content_w, self.config.FONT_BOLD, 80, self.config.COLOR_TEXT_MAIN, "lt")
            
            # 2. Members
            mem_text = TextUtils.clean_for_rendering(str(row['Members']))
            mem_text = TextUtils.truncate(mem_text, 65)
            draw.text((content_x, Y_MEMBERS), mem_text, font=f_members, fill=self.config.COLOR_TEXT_SUB, anchor="lt")
            
            # 3. Progress Bar
            draw.rounded_rectangle([(content_x, Y_BAR), (content_x+580, Y_BAR+16)], radius=8, fill=self.config.COLOR_BACKGROUND)
            if pct > 0:
                fill_w = max(int(580 * pct), 20)
                draw.rounded_rectangle([(content_x, Y_BAR), (content_x+fill_w, Y_BAR+16)], radius=8, fill=rank.color_hex)
            
            # 4. Rank Title (Cleaned)
            clean_title = TextUtils.clean_for_rendering(rank.thai_name)
            draw.text((content_x, Y_TITLE), clean_title, font=f_rank_title, fill=rank.color_hex, anchor="lt")
            
            # 5. Privilege (Autofit & Cleaned)
            self._draw_text_autofit(draw, rank.privilege_desc, content_x, Y_DESC, content_w, self.config.FONT_REGULAR, 40, self.config.COLOR_TEXT_SUB, "lt")
            
            # Score (Right)
            score_x = self.config.IMG_WIDTH - self.config.IMG_PADDING - 40
            draw.text((score_x, cy-10), f"{xp}", font=f_score, fill=score_col, anchor="rs")
            draw.text((score_x, cy+50), "XP", font=f_label, fill=self.config.COLOR_TEXT_MUTED, anchor="rs")
            
            curr_y += self.config.IMG_ROW_HEIGHT
            
        # Footer
        foot_y = canvas_h - (self.config.IMG_FOOTER_HEIGHT // 2)
        f_foot = self._get_font(self.config.FONT_REGULAR, 38)
        ts = datetime.now().strftime('%d/%m/%Y %H:%M')
        draw.text((self.config.IMG_WIDTH // 2, foot_y), f"Generated by {self.config.APP_NAME} • {ts}", font=f_foot, fill=self.config.COLOR_TEXT_MUTED, anchor="mm")
        
        # Output
        out = img.convert('RGB')
        buf = io.BytesIO()
        out.save(buf, format='PNG', optimize=True)
        return buf.getvalue()

# ==============================================================================
# SECTION 7: USER INTERFACE LAYER (VIEW CONTROLLER)
# ==============================================================================

class UIManager:
    """
    Main View Controller handling Streamlit interactions.
    """
    def __init__(self):
        self.config = SystemConfig()
        self.db = DatabaseAdapter()
        self.logic = GamificationEngine()
        self.gfx = GraphicsRenderer()

    def _inject_css(self):
        st.markdown(f"""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&family=Prompt:wght@300;400;500;700&display=swap');
            
            :root {{ --primary: {self.config.COLOR_PRIMARY}; --secondary: {self.config.COLOR_SECONDARY}; --bg: {self.config.COLOR_BACKGROUND}; }}
            
            html, body, .stApp {{ font-family: 'Sarabun', sans-serif; background-color: var(--bg); color: {self.config.COLOR_TEXT_MAIN}; }}
            
            /* Modern Card Styling */
            .glass-card {{
                background: white;
                border-radius: 16px;
                padding: 1.5rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
                border: 1px solid {self.config.COLOR_BORDER};
                margin-bottom: 1rem;
            }}
            
            /* Custom Inputs */
            .stTextInput input, .stTextArea textarea, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {{
                border-radius: 10px;
                border: 1px solid {self.config.COLOR_BORDER};
            }}
            
            /* Hero Banner */
            .hero-container {{
                background: linear-gradient(135deg, var(--primary), var(--secondary));
                padding: 2.5rem;
                border-radius: 20px;
                color: white;
                margin-bottom: 2rem;
                display: flex; justify-content: space-between; align-items: center;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            }}
            
            /* Badges */
            .rank-badge {{
                display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 0.85rem;
            }}
            </style>
        """, unsafe_allow_html=True)

    def render_sidebar(self):
        with st.sidebar:
            st.title(f"🎛️ {self.config.APP_NAME}")
            st.caption(f"Version {self.config.APP_VERSION}")
            st.divider()
            
            st.subheader("Select Classroom")
            # Only the requested rooms
            room = st.selectbox("Active Class", ["ม.1/1", "ม.1/2", "ม.1/10"])
            
            st.divider()
            st.subheader("Data Tools")
            
            if st.button("📥 Export CSV"):
                df = self.db.fetch_data()
                st.download_button("Download File", df.to_csv(index=False).encode('utf-8'), "data.csv")
                
            if st.button("🔄 Repair Database"):
                if self.db.commit(pd.DataFrame(columns=self.db.COLUMNS)):
                    st.success("Database repaired.")
                    
            return room

    def render_hero(self, room_name, count):
        st.markdown(f"""
            <div class='hero-container'>
                <div>
                    <div style='opacity:0.8; letter-spacing:1px;'>{self.config.ORGANIZATION}</div>
                    <h1 style='margin:0; font-size:3rem;'>{room_name}</h1>
                </div>
                <div style='text-align:right;'>
                    <div style='font-size:3.5rem; font-weight:800; line-height:1;'>{count}</div>
                    <div>Active Teams</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # --- TAB RENDERERS ---

    def _tab_command(self, room, room_df, all_df):
        st.header("⚡ Command Center")
        if room_df.empty:
            st.info("No teams found. Please create one in the Management tab.")
            return

        # Target Selection
        targets = st.multiselect("Select Target Teams", sorted(room_df['GroupName'].unique()))
        
        st.divider()
        c1, c2 = st.columns(2)
        
        # Action Handler
        def _apply(reason, amt):
            if not targets:
                st.error("Please select at least one team.")
                return
            
            count = 0
            for t in targets:
                # Get current state
                row = room_df[room_df['GroupName'] == t].iloc[0]
                try: hist = json.loads(row['HistoryLog'])
                except: hist = []
                
                # Logic
                new_xp, new_hist, new_badges = self.logic.process_transaction(row['XP'], hist, reason, amt)
                
                # Save
                if self.db.save_team_state(room, t, new_xp, new_hist, new_badges, all_df):
                    count += 1
            
            if count > 0:
                st.toast(f"Successfully updated {count} teams!", icon="✅")
                time.sleep(1)
                st.rerun()

        with c1:
            st.subheader("Quick Actions")
            st.button("📚 Sent On Time (+50)", on_click=_apply, args=("ส่งงานตรงเวลา", 50), use_container_width=True)
            st.button("🙋 Participation (+20)", on_click=_apply, args=("มีส่วนร่วมในชั้นเรียน", 20), use_container_width=True)
            st.button("🏆 Activity Win (+100)", on_click=_apply, args=("ชนะกิจกรรมพิเศษ", 100), use_container_width=True, type="primary")
            st.button("🐢 Late Work (-20)", on_click=_apply, args=("ส่งงานล่าช้า", -20), use_container_width=True)

        with c2:
            st.subheader("Manual Input")
            with st.form("manual"):
                r = st.text_input("Reason")
                a = st.number_input("XP Amount", step=5)
                if st.form_submit_button("Submit Transaction", use_container_width=True):
                    if r and a != 0: _apply(r, a)
                    else: st.warning("Invalid input")

    def _tab_leaderboard(self, room, room_df):
        st.header("🏆 Leaderboard")
        
        # Image Gen
        if not room_df.empty:
            c1, c2 = st.columns([1, 2])
            with c1:
                st.info("Generates High-Res Image with Thai Typography Support.")
                if st.button("✨ Generate Image", type="primary", use_container_width=True):
                    try:
                        img_bytes = self.gfx.generate_leaderboard(room, room_df, self.logic)
                        st.session_state['lb_img'] = img_bytes
                    except Exception as e:
                        st.error(f"Render Error: {e}")
                
                if 'lb_img' in st.session_state:
                    st.download_button("📥 Download PNG", st.session_state['lb_img'], "leaderboard.png", "image/png", use_container_width=True)
            
            with c2:
                if 'lb_img' in st.session_state:
                    st.image(st.session_state['lb_img'], use_container_width=True)

        st.divider()
        
        # Live List
        sorted_df = room_df.sort_values("XP", ascending=False).reset_index(drop=True)
        for i, row in sorted_df.iterrows():
            xp = row['XP']
            rank = self.logic.get_rank(xp)
            pct, msg = self.logic.get_progress(xp)
            
            try: badges = json.loads(row['Badges'])
            except: badges = []
            badge_str = self.logic.render_badges_str(badges)
            
            border_col = self.config.COLOR_DANGER if xp < 0 else rank.color_hex
            
            st.markdown(f"""
            <div class='glass-card' style='border-left: 6px solid {border_col};'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <div>
                        <span style='font-size:1.2rem; font-weight:bold; color:#94A3B8; margin-right:10px;'>#{i+1}</span>
                        <span style='font-size:1.3rem; font-weight:bold;'>{row['GroupName']}</span>
                        <div style='color:#64748B; font-size:0.9rem; margin-top:5px;'>{row['Members']}</div>
                        <div style='margin-top:5px; font-size:1.2rem;'>{badge_str}</div>
                    </div>
                    <div style='text-align:right;'>
                        <div style='font-size:2rem; font-weight:800; color:{border_col};'>{xp}</div>
                        <div style='font-size:0.8rem; color:#94A3B8;'>XP</div>
                    </div>
                </div>
                <div style='margin-top:15px; display:flex; justify-content:space-between; font-size:0.85rem;'>
                    <span style='background:{rank.bg_hex}; color:{rank.color_hex}; padding:4px 10px; border-radius:15px; font-weight:bold;'>{rank.thai_name}</span>
                    <span style='color:#64748B;'>{msg}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(pct)

    def _tab_analytics(self, room_df):
        st.header("📈 Analytics")
        if room_df.empty: return
        
        # KPI
        c1, c2, c3 = st.columns(3)
        c1.metric("Total XP", room_df['XP'].sum())
        c2.metric("Average XP", int(room_df['XP'].mean()))
        c3.metric("Top Score", room_df['XP'].max())
        
        st.divider()
        st.subheader("Comparison")
        st.bar_chart(room_df.set_index("GroupName")['XP'])

    def _tab_privileges(self):
        st.header("ℹ️ Rank System")
        for r in self.logic.ranks:
            if r.id == "PROBATION": continue
            st.markdown(f"""
            <div class='glass-card' style='border-left: 5px solid {r.color_hex};'>
                <div style='display:flex; justify-content:space-between;'>
                    <h3 style='margin:0; color:{r.color_hex};'>{r.thai_name}</h3>
                    <span style='background:{r.bg_hex}; color:{r.color_hex}; padding:2px 8px; border-radius:10px; font-size:0.8rem;'>{r.min_xp}+ XP</span>
                </div>
                <div style='margin-top:10px; color:#475569;'>🎁 {r.privilege_desc}</div>
            </div>
            """, unsafe_allow_html=True)

    def _tab_management(self, room, room_df, all_df):
        st.header("🛠️ Management")
        
        # 1. Create
        with st.expander("➕ Create New Team", expanded=True):
            with st.form("create"):
                n = st.text_input("Team Name")
                m = st.text_area("Members (Comma separated)")
                if st.form_submit_button("Create Team", type="primary"):
                    if n:
                        if self.db.create_team(room, n, m, all_df):
                            st.success("Team created.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Duplicate name.")
                    else:
                        st.error("Name required.")

        st.divider()
        
        # 2. Update (Detailed)
        st.subheader("✏️ Edit Team Details")
        st.caption("Rename teams or manage roster (move/add/remove members).")
        
        team_list = sorted(room_df['GroupName'].unique())
        target = st.selectbox("Select Team to Edit", ["-"] + team_list)
        
        if target != "-":
            curr = room_df[room_df['GroupName'] == target].iloc[0]
            with st.form("edit"):
                new_n = st.text_input("Team Name", value=curr['GroupName'])
                new_m = st.text_area("Members List (Editable)", value=curr['Members'], height=150, help="Edit this text to move members in/out.")
                
                c_save, c_del = st.columns([3, 1])
                with c_save:
                    if st.form_submit_button("💾 Save Changes", type="primary"):
                        if self.db.update_team_details(room, target, new_n, new_m, all_df):
                            st.success("Updated successfully.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Update failed.")
                
        # 3. Delete
        st.divider()
        st.subheader("🗑️ Delete Team")
        to_del = st.selectbox("Select Team to Delete", ["-"] + team_list, key="del_sel")
        if to_del != "-":
            st.warning(f"Permanently delete {to_del}?")
            if st.button("Confirm Delete", type="primary"):
                self.db.delete_team(room, to_del, all_df)
                st.success("Deleted.")
                time.sleep(1)
                st.rerun()

    def run(self):
        self.setup_page()
        self._inject_css()
        
        room = self.render_sidebar()
        
        # Load Context
        try:
            all_df = self.db.fetch_data()
            room_df = all_df[all_df['Room'] == room].copy()
        except:
            st.error("Data load failed.")
            return

        self.render_hero(room, len(room_df))
        
        t1, t2, t3, t4, t5 = st.tabs(["Command", "Leaderboard", "Analytics", "Privileges", "Manage"])
        
        with t1: self._tab_command(room, room_df, all_df)
        with t2: self._tab_leaderboard(room, room_df)
        with t3: self._tab_analytics(room_df)
        with t4: self._tab_privileges()
        with t5: self._tab_management(room, room_df, all_df)

# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================
if __name__ == "__main__":
    app = UIManager()
    app.run()
