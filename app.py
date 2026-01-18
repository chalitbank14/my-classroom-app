"""
Classroom OS: Enterprise Architect Edition
Version: 31.0.0-Titanium-Fixed
Author: AI Architecture Team
Date: 2026-01-20

[SYSTEM MANIFEST]
This software is a comprehensive Classroom Gamification Operating System.
It is architected as a monolithic application to ensure zero-dependency issues during runtime.

[FIX LOG v31.0.0]
- [CRITICAL FIX] Altair SchemaValidationError: Added strict type casting (int/str) 
  for Analytics data to prevent graph rendering crashes.
- [FEATURE] Vector Sticker Engine: Generates medals/trophies procedurally.
- [FEATURE] Atomic Batch Processing: Reliable multi-team scoring.
- [FEATURE] Full CRUD Management: Create, Edit, Delete teams.
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
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from PIL import Image, ImageDraw, ImageFont

# ==============================================================================
# SECTION 1: CORE KERNEL & CONFIGURATION
# ==============================================================================

# 1.1 Logging Setup
logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("ClassroomOS.Kernel")

# 1.2 Enumerations
class RankID(Enum):
    PRESIDENT = "PRES"
    DIRECTOR = "DIR"
    MANAGER = "MGR"
    EMPLOYEE = "EMP"
    INTERN = "INT"
    PROBATION = "PROB"

class BadgeType(Enum):
    WEALTHY = "wealthy"
    SNIPER = "sniper"
    DEBTOR = "debtor"
    PHOENIX = "phoenix"
    FIRST_BLOOD = "first_blood"
    VETERAN = "veteran"

# 1.3 System Configuration
class SystemConfig:
    """Global immutable configuration."""
    APP_NAME: str = "Classroom OS"
    APP_VERSION: str = "31.0.0-Titanium"
    ORGANIZATION: str = "Acme Education Systems"
    
    # Database
    DB_CONNECTION: str = "gsheets"
    DB_WORKSHEET: str = "Sheet1"
    DB_CACHE_TTL: int = 0
    
    # Graphics - Layout
    IMG_WIDTH: int = 1400
    IMG_HEADER_H: int = 780
    IMG_ROW_H: int = 650
    IMG_FOOTER_H: int = 220
    IMG_PADDING: int = 60
    IMG_RADIUS: int = 45
    
    # Graphics - Typography
    FONT_BOLD: str = "Sarabun-Bold.ttf"
    FONT_REGULAR: str = "Sarabun-Regular.ttf"
    
    # Graphics - Colors
    COLOR_PRIMARY: str = "#4338CA"      # Indigo 700
    COLOR_SECONDARY: str = "#3730A3"    # Indigo 800
    COLOR_ACCENT: str = "#A5B4FC"       # Indigo 200
    COLOR_BG: str = "#F8FAFC"           # Slate 50
    COLOR_SURFACE: str = "#FFFFFF"      # White
    COLOR_BORDER: str = "#E2E8F0"       # Slate 200
    COLOR_SHADOW: str = "#94A3B8"       # Slate 400
    
    COLOR_TEXT: str = "#1E293B"         # Slate 800
    COLOR_TEXT_MUTED: str = "#64748B"   # Slate 500
    
    COLOR_SUCCESS: str = "#10B981"      # Emerald
    COLOR_DANGER: str = "#EF4444"       # Red
    COLOR_WARNING: str = "#F59E0B"      # Amber

    # Rank Configuration
    RANK_METADATA = {
        RankID.PRESIDENT: {"th": "👑 ประธานรุ่น", "min": 1000, "col": "#F59E0B", "bg": "#FEF3C7", "desc": "Immunity (ไม่ทำ 3 งาน) + Bonus"},
        RankID.DIRECTOR:  {"th": "💼 หัวหน้าฝ่าย", "min": 600,  "col": "#8B5CF6", "bg": "#F3E8FF", "desc": "Workload Cut (ลดงาน 50%)"},
        RankID.MANAGER:   {"th": "👔 หัวหน้าแผนก", "min": 300,  "col": "#3B82F6", "bg": "#DBEAFE", "desc": "Second Chance (แก้ตัวได้ 1 ครั้ง)"},
        RankID.EMPLOYEE:  {"th": "👨‍💼 พนักงาน",   "min": 100,  "col": "#10B981", "bg": "#D1FAE5", "desc": "Time Extension (ส่งช้าได้)"},
        RankID.INTERN:    {"th": "👶 เด็กฝึกงาน",  "min": 0,    "col": "#64748B", "bg": "#F1F5F9", "desc": "Check-up (ครูตรวจก่อนส่ง)"},
        RankID.PROBATION: {"th": "⚠️ ทัณฑ์บน",    "min": -9999, "col": "#EF4444", "bg": "#FEE2E2", "desc": "สถานะวิกฤต! รีบซ่อมคะแนน"}
    }

# ==============================================================================
# SECTION 2: DOMAIN MODELS
# ==============================================================================

@dataclass
class RankModel:
    """Represents a Rank Definition."""
    id: RankID
    name_th: str
    min_xp: int
    color_hex: str
    bg_hex: str
    privilege: str

@dataclass
class TeamModel:
    """Represents a Team entity."""
    room: str
    name: str
    xp: int
    members: str
    last_updated: str
    history: List[Dict] = field(default_factory=list)
    badges: List[str] = field(default_factory=list)

# ==============================================================================
# SECTION 3: UTILITY LAYER
# ==============================================================================

class TextUtils:
    """Advanced Text Processing Utilities."""
    
    @staticmethod
    def sanitize_for_render(text: str) -> str:
        """Removes Emojis and non-renderable glyphs."""
        if not text: return ""
        text = str(text)
        return re.sub(r'[^\w\s\u0E00-\u0E7F().,\-!]', '', text).strip()

    @staticmethod
    def truncate(text: str, limit: int) -> str:
        if len(text) > limit:
            return text[:limit-3] + "..."
        return text

class TimeUtils:
    """Time synchronization utilities."""
    
    @staticmethod
    def now_short() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def gen_uuid() -> str:
        return str(uuid.uuid4())[:8]

# ==============================================================================
# SECTION 4: DATA ACCESS LAYER (DAL)
# ==============================================================================

class DatabaseSchema:
    """Defines the rigid schema for the database."""
    COL_ROOM = "Room"
    COL_NAME = "GroupName"
    COL_XP = "XP"
    COL_MEMBERS = "Members"
    COL_UPDATED = "LastUpdated"
    COL_HISTORY = "HistoryLog"
    COL_BADGES = "Badges"
    
    ALL_COLUMNS = [COL_ROOM, COL_NAME, COL_XP, COL_MEMBERS, COL_UPDATED, COL_HISTORY, COL_BADGES]

class GoogleSheetsRepository:
    """
    High-level Data Access Object for Google Sheets.
    """
    def __init__(self):
        self.config = SystemConfig()
        self._conn = self._init_connection()

    def _init_connection(self) -> GSheetsConnection:
        try:
            return st.connection(self.config.DB_CONNECTION, type=GSheetsConnection)
        except Exception as e:
            st.error(f"CRITICAL: Database Connection Failed. {e}")
            st.stop()

    def _validate_and_clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensures DataFrame conforms to the schema."""
        if df.empty:
            return pd.DataFrame(columns=DatabaseSchema.ALL_COLUMNS)
        
        # 1. Ensure Columns Exist
        existing_cols = set(df.columns)
        required_cols = set(DatabaseSchema.ALL_COLUMNS)
        missing = required_cols - existing_cols
        
        for c in missing:
            df[c] = None
            
        # 2. Select and Reorder
        df = df[DatabaseSchema.ALL_COLUMNS].copy()
        
        # 3. Type Enforcement
        df = df.dropna(subset=[DatabaseSchema.COL_NAME], how='all')
        df[DatabaseSchema.COL_XP] = pd.to_numeric(df[DatabaseSchema.COL_XP], errors='coerce').fillna(0).astype(int)
        
        # JSON Columns
        for col in [DatabaseSchema.COL_HISTORY, DatabaseSchema.COL_BADGES]:
            df[col] = df[col].fillna("[]").astype(str)
            df[col] = df[col].apply(lambda x: x if x.strip().startswith("[") and x.strip().endswith("]") else "[]")
            
        # String Columns
        for col in [DatabaseSchema.COL_ROOM, DatabaseSchema.COL_NAME, DatabaseSchema.COL_MEMBERS, DatabaseSchema.COL_UPDATED]:
            df[col] = df[col].fillna("").astype(str)
            
        return df

    def fetch_all(self) -> pd.DataFrame:
        try:
            df = self._conn.read(worksheet=self.config.DB_WORKSHEET, ttl=self.config.DB_CACHE_TTL)
            return self._validate_and_clean(df)
        except Exception as e:
            return pd.DataFrame(columns=DatabaseSchema.ALL_COLUMNS)

    def _commit(self, df: pd.DataFrame) -> bool:
        try:
            clean_df = self._validate_and_clean(df)
            self._conn.update(worksheet=self.config.DB_WORKSHEET, data=clean_df)
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Database Write Error: {e}")
            return False

    # --- ATOMIC TRANSACTIONS ---

    def create_team(self, room: str, name: str, members: str, current_df: pd.DataFrame) -> bool:
        if ((current_df[DatabaseSchema.COL_ROOM] == room) & 
            (current_df[DatabaseSchema.COL_NAME] == name)).any():
            return False
            
        new_record = {
            DatabaseSchema.COL_ROOM: room,
            DatabaseSchema.COL_NAME: name,
            DatabaseSchema.COL_XP: 0,
            DatabaseSchema.COL_MEMBERS: members,
            DatabaseSchema.COL_UPDATED: TimeUtils.now_short(),
            DatabaseSchema.COL_HISTORY: "[]",
            DatabaseSchema.COL_BADGES: "[]"
        }
        
        updated_df = pd.concat([current_df, pd.DataFrame([new_record])], ignore_index=True)
        return self._commit(updated_df)

    def update_team_details(self, room: str, old_name: str, new_name: str, new_members: str, current_df: pd.DataFrame) -> bool:
        # Check Collision
        if new_name != old_name:
            conflict = ((current_df[DatabaseSchema.COL_ROOM] == room) & 
                        (current_df[DatabaseSchema.COL_NAME] == new_name)).any()
            if conflict:
                return False
        
        mask = (current_df[DatabaseSchema.COL_ROOM] == room) & (current_df[DatabaseSchema.COL_NAME] == old_name)
        if not mask.any():
            return False
            
        idx = current_df[mask].index[0]
        current_df.at[idx, DatabaseSchema.COL_NAME] = new_name
        current_df.at[idx, DatabaseSchema.COL_MEMBERS] = new_members
        current_df.at[idx, DatabaseSchema.COL_UPDATED] = TimeUtils.now_short()
        
        return self._commit(current_df)

    def delete_team(self, room: str, name: str, current_df: pd.DataFrame) -> bool:
        mask = ~((current_df[DatabaseSchema.COL_ROOM] == room) & 
                 (current_df[DatabaseSchema.COL_NAME] == name))
        updated_df = current_df[mask]
        return self._commit(updated_df)

    def batch_update_state(self, updates_map: Dict[str, Dict], current_df: pd.DataFrame) -> int:
        updates_count = 0
        timestamp = TimeUtils.now_short()
        
        for name, data in updates_map.items():
            mask = (current_df[DatabaseSchema.COL_NAME] == name)
            if mask.any():
                idx = current_df[mask].index[0]
                current_df.at[idx, DatabaseSchema.COL_XP] = data['xp']
                current_df.at[idx, DatabaseSchema.COL_HISTORY] = json.dumps(data['history'], ensure_ascii=False)
                current_df.at[idx, DatabaseSchema.COL_BADGES] = json.dumps(data['badges'], ensure_ascii=False)
                current_df.at[idx, DatabaseSchema.COL_UPDATED] = timestamp
                updates_count += 1
                
        if updates_count > 0:
            if self._commit(current_df):
                return updates_count
        return 0

# ==============================================================================
# SECTION 5: BUSINESS LOGIC LAYER
# ==============================================================================

class GamificationService:
    """
    Orchestrates business logic for XP, Ranks, and Badges.
    """
    def __init__(self):
        self.config = SystemConfig()

    def get_rank_definition(self, xp: int) -> Dict[str, Any]:
        if xp < 0: return self.config.RANK_METADATA[RankID.PROBATION]
        
        for rank_id in [RankID.PRESIDENT, RankID.DIRECTOR, RankID.MANAGER, RankID.EMPLOYEE, RankID.INTERN]:
            meta = self.config.RANK_METADATA[rank_id]
            if xp >= meta['min']:
                return meta
                
        return self.config.RANK_METADATA[RankID.INTERN]

    def calculate_progress(self, xp: int) -> Tuple[float, str]:
        if xp < 0: return 0.0, "CRITICAL STATUS"
            
        current_rank_def = self.get_rank_definition(xp)
        rank_keys = [r for r in self.config.RANK_METADATA.keys() if r != RankID.PROBATION]
        
        try:
            current_idx = -1
            for i, r_id in enumerate(rank_keys):
                if self.config.RANK_METADATA[r_id]['min'] == current_rank_def['min']:
                    current_idx = i
                    break
        except: return 0.0, "Error"
            
        if current_idx == 0: return 1.0, "MAX RANK REACHED"
            
        next_rank_id = rank_keys[current_idx - 1]
        next_rank_def = self.config.RANK_METADATA[next_rank_id]
        
        target = next_rank_def['min']
        denominator = target if target > 0 else 100
        percentage = min(1.0, xp / denominator)
        return percentage, f"{int(percentage * 100)}% to {next_rank_def['th']}"

    def calculate_new_state(self, current_xp: int, current_history: List[dict], reason: str, amount: int) -> Tuple[int, List[dict], List[str]]:
        new_log = {
            "id": TimeUtils.gen_uuid(),
            "ts": TimeUtils.now_short(),
            "reason": reason,
            "amount": int(amount)
        }
        
        temp_history = [new_log] + current_history
        
        # Replay for Balance
        try: events_chronological = sorted(temp_history, key=lambda x: x.get('ts', ''))
        except: events_chronological = temp_history

        running_balance = 0
        for event in events_chronological:
            amt = int(event.get('amount', 0))
            running_balance += amt
            event['balance'] = running_balance
            
        final_xp = running_balance
        final_history = sorted(events_chronological, key=lambda x: x.get('ts', ''), reverse=True)
        
        # Badges
        earned_badges = set()
        if final_xp >= 800: earned_badges.add("wealthy")
        if final_xp < 0: earned_badges.add("debtor")
        if any(e.get('amount', 0) >= 100 for e in final_history): earned_badges.add("sniper")
        if len(final_history) > 0: earned_badges.add("first_blood")
        
        return final_xp, final_history, list(earned_badges)

# ==============================================================================
# SECTION 6: GRAPHICS ENGINE (VECTOR STICKER TECHNOLOGY)
# ==============================================================================

class GraphicsEngine:
    """
    Renders high-fidelity leaderboard images using pure vector logic via PIL.
    """
    def __init__(self):
        self.config = SystemConfig()
        self._font_cache = {}

    def _load_font(self, font_type: str, size: int) -> ImageFont.FreeTypeFont:
        key = (font_type, size)
        if key not in self._font_cache:
            try:
                font_file = self.config.FONT_BOLD if font_type == "bold" else self.config.FONT_REGULAR
                self._font_cache[key] = ImageFont.truetype(font_file, size)
            except IOError:
                self._font_cache[key] = ImageFont.load_default()
        return self._font_cache[key]

    def _draw_vector_medal(self, draw: ImageDraw.Draw, x: int, y: int, color_hex: str, rank_idx: int):
        """Draws a procedural vector sticker."""
        if rank_idx < 3: # Medal for Top 3
            draw.polygon([(x-25, y-95), (x-25, y-50), (x, y-20), (x+25, y-50), (x+25, y-95)], fill="#EF4444")
            draw.ellipse([(x-85, y-85), (x+85, y+85)], fill="#FFFFFF")
            draw.ellipse([(x-75, y-75), (x+75, y+75)], fill=color_hex)
            draw.chord([(x-75, y-75), (x+75, y+75)], 180, 360, fill="#FFFFFF40")
        else: # Badge for others
            draw.ellipse([(x-80, y-80), (x+80, y+80)], fill="#FFFFFF")
            draw.ellipse([(x-70, y-70), (x+70, y+70)], fill=color_hex)

    def _draw_text_block(self, draw: ImageDraw.Draw, text: str, x: int, y: int, max_w: int, 
                         font_style: str, max_size: int, color: str, anchor: str = "lt"):
        clean_text = TextUtils.sanitize_for_render(text)
        if not clean_text: return
        
        size = max_size
        font = self._load_font(font_style, size)
        while size > 24:
            if font.getlength(clean_text) <= max_w: break
            size -= 4
            font = self._load_font(font_style, size)
            
        draw.text((x, y), clean_text, font=font, fill=color, anchor=anchor)

    def render_leaderboard(self, room_name: str, df: pd.DataFrame, logic: GamificationService) -> bytes:
        data = df.sort_values("XP", ascending=False).reset_index(drop=True)
        
        row_count = len(data)
        canvas_height = self.config.IMG_HEADER_HEIGHT + (row_count * self.config.IMG_ROW_HEIGHT) + self.config.IMG_FOOTER_HEIGHT
        
        img = Image.new('RGBA', (self.config.IMG_WIDTH, canvas_height), self.config.COLOR_BACKGROUND)
        draw = ImageDraw.Draw(img)
        
        # Header
        draw.rectangle([(0, 0), (self.config.IMG_WIDTH, self.config.IMG_HEADER_HEIGHT)], fill=self.config.COLOR_PRIMARY)
        draw.ellipse([(900, -150), (1500, 450)], fill=self.config.COLOR_SECONDARY)
        
        cx = self.config.IMG_WIDTH // 2
        # Trophy Vector
        draw.polygon([(cx-60, 180), (cx+60, 180), (cx+30, 280), (cx-30, 280)], fill="#FFD700")
        draw.ellipse([(cx-60, 170), (cx+60, 190)], fill="#FFC107")
        
        self._draw_text_block(draw, "CLASSROOM LEADERBOARD", cx, 420, 1200, "bold", 70, self.config.COLOR_ACCENT, "mm")
        self._draw_text_block(draw, room_name, cx, 620, 1200, "bold", 160, "#FFFFFF", "mm")
        
        # Rows
        current_y = self.config.IMG_HEADER_HEIGHT + 50
        rank_themes = {
            0: "#F59E0B", 1: "#94A3B8", 2: "#B45309", "default": "#64748B"
        }
        
        for i, row in data.iterrows():
            xp = row['XP']
            rank_def = logic.get_rank_definition(xp)
            progress_pct, _ = logic.calculate_progress(xp)
            
            theme_color = rank_themes.get(i if i < 3 else "default")
            score_color = self.config.COLOR_DANGER if xp < 0 else self.config.COLOR_SUCCESS
            
            # Card
            c_x, c_w, c_h = self.config.IMG_PADDING, self.config.IMG_WIDTH - (self.config.IMG_PADDING * 2), self.config.IMG_ROW_HEIGHT - 40
            draw.rounded_rectangle([(c_x, current_y), (c_x+c_w, current_y+c_h)], radius=self.config.IMG_CARD_RADIUS, fill=self.config.COLOR_SURFACE)
            
            # Sticker
            s_cx, s_cy = c_x + 120, current_y + (c_h // 2)
            self._draw_vector_medal(draw, s_cx, s_cy, theme_color, i)
            draw.text((s_cx, s_cy), str(i+1), font=self._load_font("bold", 90), fill="white", anchor="mm")
            
            # Info Grid
            ix, iw = c_x + 280, 620
            self._draw_text_block(draw, str(row['GroupName']), ix, current_y + 60, iw, "bold", 90, self.config.COLOR_TEXT, "lt")
            self._draw_text_block(draw, TextUtils.truncate(str(row['Members']), 60), ix, current_y + 160, iw, "regular", 45, self.config.COLOR_TEXT_MUTED, "lt")
            
            # Bar
            draw.rounded_rectangle([(ix, current_y + 250), (ix+580, current_y + 266)], radius=8, fill=self.config.COLOR_BACKGROUND)
            if progress_pct > 0:
                draw.rounded_rectangle([(ix, current_y + 250), (ix+max(int(580*progress_pct), 20), current_y + 266)], radius=8, fill=rank_def['col'])
                
            self._draw_text_block(draw, rank_def['th'], ix, current_y + 320, iw, "bold", 50, rank_def['col'], "lt")
            self._draw_text_block(draw, rank_def['desc'], ix, current_y + 390, iw, "regular", 40, self.config.COLOR_TEXT_MUTED, "lt")
            
            # Score
            sx = self.config.IMG_WIDTH - self.config.IMG_PADDING - 50
            draw.text((sx, s_cy-10), f"{xp}", font=self._load_font("bold", 120), fill=score_color, anchor="rs")
            draw.text((sx, s_cy+60), "XP", font=self._load_font("bold", 50), fill=self.config.COLOR_TEXT_MUTED, anchor="rs")
            
            current_y += self.config.IMG_ROW_HEIGHT
            
        # Footer
        fy = canvas_height - (self.config.IMG_FOOTER_HEIGHT // 2)
        draw.text((self.config.IMG_WIDTH//2, fy), f"Generated by {self.config.APP_NAME}", font=self._load_font("regular", 40), fill=self.config.COLOR_TEXT_MUTED, anchor="mm")
        
        out = io.BytesIO()
        img.save(out, format='PNG')
        return out.getvalue()

# ==============================================================================
# SECTION 7: VIEW CONTROLLER (UI)
# ==============================================================================

class ClassroomOSApp:
    def __init__(self):
        self.config = SystemConfig()
        self.db = GoogleSheetsRepository()
        self.logic = GamificationService()
        self.gfx = GraphicsEngine()

    def run(self):
        st.set_page_config(page_title=self.config.APP_NAME, page_icon="🏫", layout="wide", initial_sidebar_state="expanded")
        self._inject_css()
        
        room = self._render_sidebar()
        all_df = self.db.fetch_all()
        room_df = all_df[all_df['Room'] == room].copy()
        
        self._render_hero(room, len(room_df))
        
        t1, t2, t3, t4, t5 = st.tabs(["Command", "Leaderboard", "Analytics", "Privileges", "Manage"])
        
        with t1: self._tab_command(room, room_df, all_df)
        with t2: self._tab_leaderboard(room, room_df)
        with t3: self._tab_analytics(room_df)
        with t4: self._tab_privileges()
        with t5: self._tab_manage(room, room_df, all_df)

    def _inject_css(self):
        st.markdown(f"""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&family=Prompt:wght@300;400;500;700&display=swap');
            :root {{ --primary: {self.config.COLOR_PRIMARY}; --bg: {self.config.COLOR_BACKGROUND}; }}
            html, body, .stApp {{ font-family: 'Sarabun', sans-serif; background-color: var(--bg); color: {self.config.COLOR_TEXT}; }}
            .glass-card {{ background: white; border-radius: 16px; padding: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid {self.config.COLOR_BORDER}; margin-bottom: 1rem; }}
            .hero-container {{ background: linear-gradient(135deg, {self.config.COLOR_PRIMARY}, {self.config.COLOR_SECONDARY}); padding: 2.5rem; border-radius: 20px; color: white; margin-bottom: 2rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }}
            .stTextInput input, .stTextArea textarea, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {{ border-radius: 10px; border: 1px solid {self.config.COLOR_BORDER}; }}
            </style>
        """, unsafe_allow_html=True)

    def _render_sidebar(self):
        with st.sidebar:
            st.title(f"🎛️ {self.config.APP_NAME}")
            st.caption(f"v{self.config.APP_VERSION}")
            st.divider()
            room = st.selectbox("Active Class", ["ม.1/1", "ม.1/2", "ม.1/10"])
            st.divider()
            if st.button("📥 Export CSV"):
                st.download_button("Download", self.db.fetch_all().to_csv(index=False).encode('utf-8'), "data.csv")
            return room

    def _render_hero(self, room, count):
        st.markdown(f"""<div class='hero-container'><div><h1>{room}</h1></div><div style='text-align:right;'><div style='font-size:3rem; font-weight:800;'>{count}</div>Teams</div></div>""", unsafe_allow_html=True)

    def _tab_command(self, room, room_df, all_df):
        st.header("⚡ Command Center")
        if room_df.empty: st.info("Create teams first."); return
        
        targets = st.multiselect("Select Teams (Batch)", sorted(room_df['GroupName'].unique()))
        st.divider()
        c1, c2 = st.columns(2)
        
        def _exec(r, a):
            if not targets: st.error("Select team"); return
            with st.status("Processing Batch...") as s:
                updates = {}
                for t in targets:
                    row = room_df[room_df['GroupName']==t].iloc[0]
                    try: h = json.loads(row['HistoryLog'])
                    except: h = []
                    xp, nh, nb = self.logic.calculate_new_state(row['XP'], h, r, a)
                    updates[t] = {"xp": xp, "history": nh, "badges": nb}
                
                if self.db.batch_update_state(updates, all_df):
                    s.update(label="Done!", state="complete"); time.sleep(0.5); st.rerun()
                else: s.update(label="Failed", state="error")

        with c1:
            st.button("📚 On Time (+50)", on_click=_exec, args=("ส่งงานตรงเวลา", 50), use_container_width=True)
            st.button("🙋 Participate (+20)", on_click=_exec, args=("มีส่วนร่วม", 20), use_container_width=True)
        with c2:
            with st.form("man"):
                r = st.text_input("Reason"); a = st.number_input("XP", step=5)
                if st.form_submit_button("Submit", use_container_width=True): _exec(r, a)

    def _tab_leaderboard(self, room, room_df):
        st.header("🏆 Leaderboard")
        if not room_df.empty:
            if st.button("✨ Generate Image", type="primary"):
                try:
                    img = self.gfx.render_leaderboard(room, room_df, self.logic)
                    st.image(img)
                    st.download_button("Download PNG", img, "lb.png", "image/png")
                except Exception as e: st.error(f"Render Error: {e}")
        
        st.divider()
        for _, r in room_df.sort_values("XP", ascending=False).iterrows():
            rank = self.logic.get_rank_definition(r['XP'])
            st.markdown(f"<div class='glass-card' style='border-left:6px solid {rank['col']}'><h3>{r['GroupName']}</h3>{r['XP']} XP | {rank['th']}</div>", unsafe_allow_html=True)

    def _tab_analytics(self, room_df):
        st.header("📈 Analytics")
        if not room_df.empty:
            # FIX: Explicit type casting for Altair
            data = [{"Team": str(r['GroupName']), "XP": int(r['XP']) if pd.notnull(r['XP']) else 0} for _, r in room_df.iterrows()]
            chart = alt.Chart(pd.DataFrame(data)).mark_bar().encode(
                x=alt.X('Team:N', sort='-y'), y=alt.Y('XP:Q'), color=alt.Color('XP:Q', scale={'scheme': 'viridis'})
            ).properties(use_container_width=True)
            st.altair_chart(chart, use_container_width=True)

    def _tab_privileges(self):
        st.header("ℹ️ Privileges")
        for rid, m in self.config.RANK_METADATA.items():
            if rid != RankID.PROBATION: st.info(f"**{m['th']}**: {m['desc']}")

    def _tab_manage(self, room, room_df, all_df):
        st.header("🛠️ Management")
        with st.expander("➕ Create Team", expanded=True):
            with st.form("new"):
                n = st.text_input("Name"); m = st.text_area("Members")
                if st.form_submit_button("Create") and n:
                    team = TeamModel(room, n, 0, m, TimeUtils.now_short())
                    if self.db.create_team(team, all_df): st.success("Created"); time.sleep(0.5); st.rerun()
                    else: st.error("Duplicate")
        
        st.divider()
        st.subheader("✏️ Edit Team")
        tl = sorted(room_df['GroupName'].unique())
        t = st.selectbox("Select", ["-"]+tl)
        if t != "-":
            curr = room_df[room_df['GroupName']==t].iloc[0]
            with st.form("edt"):
                nn = st.text_input("Name", value=curr['GroupName'])
                nm = st.text_area("Members", value=curr['Members'])
                if st.form_submit_button("Save"):
                    if self.db.update_team_details(room, t, nn, nm, all_df): st.success("Saved"); time.sleep(0.5); st.rerun()
                    else: st.error("Error")
        
        st.divider()
        d = st.selectbox("Delete", ["-"]+tl)
        if d != "-" and st.button("Confirm Delete"):
            self.db.delete_team(room, d, all_df); st.rerun()

if __name__ == "__main__":
    ClassroomOSApp().run()
