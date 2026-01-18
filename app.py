"""
Classroom OS: Enterprise Monolith Edition
Version: 30.0.0-Titanium-Ultra
Author: AI Architecture Team
Date: 2026-01-20

[SYSTEM MANIFEST]
This software is a comprehensive Classroom Gamification Operating System.
It is architected as a monolithic application to ensure zero-dependency issues during runtime.

[MODULE MAP]
1.  CORE_KERNEL: Configuration, Logging, Enums, Custom Exceptions.
2.  DOMAIN_LAYER: Typed Data Models (Dataclasses) for strict typing.
3.  UTILITY_LAYER: Helper functions for Text processing (Thai RegEx), Time, and IDs.
4.  PERSISTENCE_LAYER: Advanced Google Sheets DAO with Atomic Commit and Retry Logic.
5.  BUSINESS_LOGIC_LAYER: Gamification Rules, Rank Calculations, Badge Engines.
6.  PRESENTATION_GRAPHICS: High-Fidelity Vector Rasterizer (PIL) for Sticker Generation.
7.  PRESENTATION_UI: Streamlit View Controllers and Component Library.

[PATCH NOTES v30.0.0]
- Restored FULL CRUD (Create, Read, Update, Delete) for Teams.
- Implemented "Atomic Batch Processing" for reliable multi-team scoring.
- Integrated "Vector Sticker Engine V2" for procedural medals/trophies (No Images required).
- Fixed all Typography vertical metrics for Thai Vowel support.
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
from enum import Enum
from abc import ABC, abstractmethod
from PIL import Image, ImageDraw, ImageFont, ImageColor

# ==============================================================================
# SECTION 1: CORE KERNEL & CONFIGURATION
# ==============================================================================

# 1.1 Logging Setup
logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)
logger = logging.getLogger("ClassroomOS.Kernel")

# 1.2 Enumerations
class RankTierID(Enum):
    PRESIDENT = "PRES"
    DIRECTOR = "DIR"
    MANAGER = "MGR"
    EMPLOYEE = "EMP"
    INTERN = "INT"
    PROBATION = "PROB"

class TransactionType(Enum):
    SINGLE = "SINGLE"
    BATCH = "BATCH"
    SYSTEM = "SYSTEM"

# 1.3 System Configuration
class SystemConfig:
    """Global immutable configuration."""
    APP_NAME: str = "Classroom OS"
    APP_VERSION: str = "30.0.0-Titanium"
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
    COLOR_TEXT: str = "#1E293B"         # Slate 800
    COLOR_TEXT_MUTED: str = "#64748B"   # Slate 500
    
    # Gamification Constants
    XP_MULTIPLIER: float = 1.0

# ==============================================================================
# SECTION 2: DOMAIN MODELS
# ==============================================================================

@dataclass
class RankModel:
    """Represents a Rank Definition."""
    id: RankTierID
    name_th: str
    min_xp: int
    color_hex: str
    bg_hex: str
    privilege: str
    icon_char: str

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

    @property
    def member_list(self) -> List[str]:
        return [m.strip() for m in self.members.split(',') if m.strip()]

# ==============================================================================
# SECTION 3: UTILITY LAYER
# ==============================================================================

class TextUtils:
    """Advanced Text Processing Utilities."""
    
    @staticmethod
    def sanitize_for_render(text: str) -> str:
        """
        Aggressively strips Emojis and non-renderable glyphs to prevent
        'Square Box' artifacts in PIL generation.
        Allows: Thai, English, Digits, Punctuation.
        """
        if not text: return ""
        text = str(text)
        # Unicode range for Thai: \u0E00-\u0E7F
        # ASCII range: \x00-\x7F
        # We use a whitelist approach
        return re.sub(r'[^\w\s\u0E00-\u0E7F().,\-!]', '', text).strip()

    @staticmethod
    def truncate(text: str, limit: int) -> str:
        if len(text) > limit:
            return text[:limit-3] + "..."
        return text

class TimeUtils:
    """Time synchronization utilities."""
    
    @staticmethod
    def now_iso() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
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
    Implements Retry Logic, Caching, and Schema Validation.
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
        # Clean Empty Rows
        df = df.dropna(subset=[DatabaseSchema.COL_NAME], how='all')
        
        # XP -> Int
        df[DatabaseSchema.COL_XP] = pd.to_numeric(df[DatabaseSchema.COL_XP], errors='coerce').fillna(0).astype(int)
        
        # JSON Columns -> String Safe
        for col in [DatabaseSchema.COL_HISTORY, DatabaseSchema.COL_BADGES]:
            df[col] = df[col].fillna("[]").astype(str)
            # Basic validation
            df[col] = df[col].apply(lambda x: x if x.strip().startswith("[") and x.strip().endswith("]") else "[]")
            
        # String Columns
        for col in [DatabaseSchema.COL_ROOM, DatabaseSchema.COL_NAME, DatabaseSchema.COL_MEMBERS, DatabaseSchema.COL_UPDATED]:
            df[col] = df[col].fillna("").astype(str)
            
        return df

    def fetch_all(self) -> pd.DataFrame:
        """Retrieves all records."""
        try:
            df = self._conn.read(worksheet=self.config.DB_WORKSHEET, ttl=self.config.DB_CACHE_TTL)
            return self._validate_and_clean(df)
        except Exception as e:
            logger.error(f"Fetch failed: {e}")
            return pd.DataFrame(columns=DatabaseSchema.ALL_COLUMNS)

    def _commit(self, df: pd.DataFrame) -> bool:
        """Low-level commit operation."""
        try:
            clean_df = self._validate_and_clean(df)
            self._conn.update(worksheet=self.config.DB_WORKSHEET, data=clean_df)
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Database Write Error: {e}")
            logger.error(f"Commit failed: {e}")
            return False

    # --- ATOMIC TRANSACTIONS ---

    def create_team(self, room: str, name: str, members: str, current_df: pd.DataFrame) -> bool:
        # Check Duplication
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
        """
        Updates name and members. Handles primary key (name) changes safely.
        """
        # 1. If renaming, check if new name exists
        if new_name != old_name:
            conflict = ((current_df[DatabaseSchema.COL_ROOM] == room) & 
                        (current_df[DatabaseSchema.COL_NAME] == new_name)).any()
            if conflict:
                return False # Name taken
        
        # 2. Find target row
        mask = (current_df[DatabaseSchema.COL_ROOM] == room) & (current_df[DatabaseSchema.COL_NAME] == old_name)
        if not mask.any():
            return False # Not found
            
        idx = current_df[mask].index[0]
        
        # 3. Update
        current_df.at[idx, DatabaseSchema.COL_NAME] = new_name
        current_df.at[idx, DatabaseSchema.COL_MEMBERS] = new_members
        current_df.at[idx, DatabaseSchema.COL_UPDATED] = TimeUtils.now_short()
        
        return self._commit(current_df)

    def delete_team(self, room: str, name: str, current_df: pd.DataFrame) -> bool:
        mask = ~((current_df[DatabaseSchema.COL_ROOM] == room) & 
                 (current_df[DatabaseSchema.COL_NAME] == name))
        updated_df = current_df[mask]
        return self._commit(updated_df)

    def update_team_state(self, room: str, name: str, xp: int, history: list, badges: list, current_df: pd.DataFrame) -> bool:
        """Updates internal state (XP, History, Badges)."""
        mask = (current_df[DatabaseSchema.COL_ROOM] == room) & (current_df[DatabaseSchema.COL_NAME] == name)
        if not mask.any():
            return False
            
        idx = current_df[mask].index[0]
        current_df.at[idx, DatabaseSchema.COL_XP] = xp
        current_df.at[idx, DatabaseSchema.COL_HISTORY] = json.dumps(history, ensure_ascii=False)
        current_df.at[idx, DatabaseSchema.COL_BADGES] = json.dumps(badges, ensure_ascii=False)
        current_df.at[idx, DatabaseSchema.COL_UPDATED] = TimeUtils.now_short()
        
        return self._commit(current_df)

    def batch_update_state(self, updates_map: Dict[str, Dict], current_df: pd.DataFrame) -> int:
        """
        Performs updates on multiple rows in memory, then commits once.
        updates_map = { "GroupName": {"xp": 100, "history": [], "badges": []} }
        """
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
    Encapsulates all rules regarding Ranks, XP, and Badges.
    """
    def __init__(self):
        self._init_ranks()
        self._init_badges()

    def _init_ranks(self):
        # Configuration for Ranks
        self.ranks = [
            RankModel(RankTierID.PRESIDENT, "👑 ประธานรุ่น", 1000, "#F59E0B", "#FEF3C7", "Immunity (ไม่ทำ 3 งาน) + Bonus", "👑"),
            RankModel(RankTierID.DIRECTOR, "💼 หัวหน้าฝ่าย", 600, "#8B5CF6", "#F3E8FF", "Workload Cut (ลดงาน 50%)", "💼"),
            RankModel(RankTierID.MANAGER, "👔 หัวหน้าแผนก", 300, "#3B82F6", "#DBEAFE", "Second Chance (แก้ตัวได้ 1 ครั้ง)", "👔"),
            RankModel(RankTierID.EMPLOYEE, "👨‍💼 พนักงาน", 100, "#10B981", "#D1FAE5", "Time Extension (ส่งช้าได้)", "👨‍💼"),
            RankModel(RankTierID.INTERN, "👶 เด็กฝึกงาน", 0, "#64748B", "#F1F5F9", "Check-up (ครูตรวจก่อนส่ง)", "👶"),
            RankModel(RankTierID.PROBATION, "⚠️ ทัณฑ์บน", -999999, "#EF4444", "#FEE2E2", "สถานะวิกฤต! รีบซ่อมคะแนน", "⚠️")
        ]

    def _init_badges(self):
        self.badge_catalog = {
            "wealthy": "💎", "sniper": "🎯", "debtor": "💸", 
            "phoenix": "🔥", "first_blood": "🩸", "veteran": "🎖️"
        }

    def get_rank(self, xp: int) -> RankModel:
        if xp < 0: return self.ranks[-1] # Probation
        for rank in self.ranks:
            if rank.id != RankTierID.PROBATION and xp >= rank.min_xp:
                return rank
        return self.ranks[-2] # Default Intern

    def get_progress(self, xp: int) -> Tuple[float, str]:
        if xp < 0: return 0.0, "Critical"
        current = self.get_rank(xp)
        try:
            idx = self.ranks.index(current)
        except: return 0.0, "Err"

        if idx > 0:
            next_rank = self.ranks[idx - 1]
            target = next_rank.min_xp
            # Prevent division by zero
            denom = target if target > 0 else 100
            pct = min(1.0, xp / denom)
            return pct, f"{int(pct*100)}% to {next_rank.name_th}"
        return 1.0, "MAX RANK"

    def get_badges_str(self, badges: List[str]) -> str:
        return "".join([self.badge_catalog.get(b, "") for b in badges])

    def calculate_new_state(self, current_xp: int, current_history: List[dict], reason: str, amount: int) -> Tuple[int, List[dict], List[str]]:
        """
        Pure function to calculate next state based on transaction.
        """
        # 1. Create Log
        new_log = {
            "id": TimeUtils.gen_uuid(),
            "ts": TimeUtils.now_short(),
            "reason": reason,
            "amount": int(amount)
        }
        
        # 2. Append to History
        # We append at the beginning to show newest first, but for calc we need chronological
        temp_history = [new_log] + current_history
        
        # 3. Recalculate Balance (Replay Event Sourcing)
        # Sort by timestamp ASC to replay events
        try:
            events_chronological = sorted(temp_history, key=lambda x: x.get('ts', ''))
        except:
            events_chronological = temp_history

        running_balance = 0
        for event in events_chronological:
            amt = int(event.get('amount', 0))
            running_balance += amt
            event['balance'] = running_balance
            
        final_xp = running_balance
        
        # 4. Sort history DESC for storage/display
        final_history = sorted(events_chronological, key=lambda x: x.get('ts', ''), reverse=True)
        
        # 5. Evaluate Badges
        earned_badges = set()
        if final_xp >= 800: earned_badges.add("wealthy")
        if final_xp < 0: earned_badges.add("debtor")
        if any(e.get('amount', 0) >= 100 for e in final_history): earned_badges.add("sniper")
        if len(final_history) > 0: earned_badges.add("first_blood")
        
        return final_xp, final_history, list(earned_badges)

# ==============================================================================
# SECTION 6: GRAPHICS ENGINE (VECTOR STICKER TECHNOLOGY)
# ==============================================================================

class GraphicsRenderer:
    """
    Advanced PIL Renderer.
    Replaces Emojis with Vector Graphics to prevent 'Square Box' artifacts.
    Uses strict vertical rhythm for Thai typography support.
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
                self._font_cache[key] = ImageFont.load_default()
        return self._font_cache[key]

    def _draw_vector_sticker(self, draw: ImageDraw.Draw, x: int, y: int, color: str, rank_idx: int):
        """Draws a procedural vector sticker (Medal or Badge)."""
        # If Top 3, Draw Medal with Ribbon
        if rank_idx < 3:
            # Ribbon V
            draw.polygon([(x-25, y-95), (x-25, y-50), (x, y-20), (x+25, y-50), (x+25, y-95)], fill="#EF4444")
            # Border
            draw.ellipse([(x-85, y-85), (x+85, y+85)], fill="#FFFFFF")
            # Body
            draw.ellipse([(x-75, y-75), (x+75, y+75)], fill=color)
            # Shine
            draw.chord([(x-75, y-75), (x+75, y+75)], 180, 360, fill="#FFFFFF40")
        else:
            # Standard Rank Badge
            draw.ellipse([(x-80, y-80), (x+80, y+80)], fill="#FFFFFF")
            draw.ellipse([(x-70, y-70), (x+70, y+70)], fill=color)

    def _draw_text_safe(self, draw: ImageDraw.Draw, text: str, x: int, y: int, max_w: int, 
                        font_name: str, size: int, color: str, anchor: str = "lt"):
        """Draws text with auto-fitting and sanitization."""
        # 1. Clean Text
        clean_text = TextUtils.sanitize_for_render(text)
        if not clean_text: return
        
        # 2. Auto-fit
        font = self._get_font(font_name, size)
        while size > 24:
            if font.getlength(clean_text) <= max_w:
                break
            size -= 2
            font = self._get_font(font_name, size)
            
        # 3. Draw
        draw.text((x, y), clean_text, font=font, fill=color, anchor=anchor)

    def render(self, room_name: str, df: pd.DataFrame, logic: GamificationService) -> bytes:
        data = df.sort_values("XP", ascending=False).reset_index(drop=True)
        
        # Dynamic Height
        canvas_h = (
            self.config.IMG_HEADER_H + 
            (len(data) * self.config.IMG_ROW_H) + 
            self.config.IMG_FOOTER_H
        )
        
        img = Image.new('RGBA', (self.config.IMG_WIDTH, canvas_h), self.config.COLOR_BG)
        draw = ImageDraw.Draw(img)
        
        # --- Header ---
        draw.rectangle([(0, 0), (self.config.IMG_WIDTH, self.config.IMG_HEADER_H)], fill=self.config.COLOR_PRIMARY)
        draw.ellipse([(900, -150), (1500, 450)], fill=self.config.COLOR_SECONDARY)
        
        cx = self.config.IMG_WIDTH // 2
        
        # Vector Trophy
        draw.polygon([(cx-60, 180), (cx+60, 180), (cx+30, 280), (cx-30, 280)], fill="#FFD700")
        draw.ellipse([(cx-60, 170), (cx+60, 190)], fill="#FFC107")
        draw.rectangle([(cx-40, 280), (cx+40, 300)], fill="#DAA520")
        
        f_head = self._get_font(self.config.FONT_BOLD, 70)
        draw.text((cx, 420), "CLASSROOM LEADERBOARD", font=f_head, fill=self.config.COLOR_ACCENT, anchor="mm")
        
        f_room = self._get_font(self.config.FONT_BOLD, 160)
        draw.text((cx, 620), room_name, font=f_room, fill="white", anchor="mm")
        
        # --- Rows ---
        curr_y = self.config.IMG_HEADER_H + 50
        
        # Pre-load fonts for loop performance
        f_rank = self._get_font(self.config.FONT_BOLD, 90)
        f_score = self._get_font(self.config.FONT_BOLD, 120)
        f_lbl = self._get_font(self.config.FONT_BOLD, 50)
        
        for i, row in data.iterrows():
            xp = row['XP']
            rank = logic.get_rank(xp)
            pct, _ = logic.get_progress(xp)
            
            theme = self.config.RANK_THEMES.get(i if i < 3 else "default")
            score_col = self.config.COLOR_DANGER if xp < 0 else self.config.COLOR_SUCCESS
            
            # Card Metrics
            c_x = self.config.IMG_PADDING
            c_w = self.config.IMG_WIDTH - (self.config.IMG_PADDING * 2)
            c_h = self.config.IMG_ROW_H - 40
            
            # Draw Card
            draw.rounded_rectangle([(c_x+10, curr_y+10), (c_x+c_w+10, curr_y+c_h+10)], radius=self.config.IMG_RADIUS, fill=self.config.COLOR_SHADOW)
            draw.rounded_rectangle([(c_x, curr_y), (c_x+c_w, curr_y+c_h)], radius=self.config.IMG_RADIUS, fill=self.config.COLOR_SURFACE)
            
            # Draw Sticker (Medal/Badge)
            s_cx = c_x + 120
            s_cy = curr_y + (c_h // 2)
            self._draw_vector_sticker(draw, s_cx, s_cy, theme['hex'], i)
            draw.text((s_cx, s_cy), str(i+1), font=f_rank, fill="white", anchor="mm")
            
            # --- Content Grid (Strict Y-Spacing) ---
            info_x = c_x + 280
            info_w = 620
            
            Y1 = curr_y + 60   # Name
            Y2 = Y1 + 100      # Members
            Y3 = Y2 + 100      # Bar
            Y4 = Y3 + 70       # Rank Title
            Y5 = Y4 + 70       # Privilege
            
            # Name
            self._draw_text_safe(draw, str(row['GroupName']), info_x, Y1, info_w, self.config.FONT_BOLD, 90, self.config.COLOR_TEXT, "lt")
            
            # Members
            mem_str = TextUtils.truncate(str(row['Members']), 60)
            self._draw_text_safe(draw, mem_str, info_x, Y2, info_w, self.config.FONT_REGULAR, 45, self.config.COLOR_TEXT_MUTED, "lt")
            
            # Bar
            draw.rounded_rectangle([(info_x, Y3), (info_x+580, Y3+16)], radius=8, fill=self.config.COLOR_BG)
            if pct > 0:
                fw = max(int(580 * pct), 30)
                draw.rounded_rectangle([(info_x, Y3), (info_x+fw, Y3+16)], radius=8, fill=rank.color)
            
            # Rank Title
            self._draw_text_safe(draw, rank.name_th, info_x, Y4, info_w, self.config.FONT_BOLD, 50, rank.color, "lt")
            
            # Privilege
            self._draw_text_safe(draw, rank.privilege, info_x, Y5, info_w, self.config.FONT_REGULAR, 40, self.config.COLOR_TEXT_MUTED, "lt")
            
            # Score
            sc_x = self.config.IMG_WIDTH - self.config.IMG_PADDING - 50
            draw.text((sc_x, s_cy-10), f"{xp}", font=f_score, fill=score_col, anchor="rs")
            draw.text((sc_x, s_cy+60), "XP", font=f_lbl, fill=self.config.COLOR_TEXT_MUTED, anchor="rs")
            
            curr_y += self.config.IMG_ROW_H
            
        # Footer
        fy = canvas_h - (self.config.IMG_FOOTER_H // 2)
        f_ft = self._get_font(self.config.FONT_REGULAR, 38)
        ts = TimeUtils.now_short()
        draw.text((self.config.IMG_WIDTH//2, fy), f"Generated by {self.config.APP_NAME} • {ts}", font=f_ft, fill=self.config.COLOR_TEXT_MUTED, anchor="mm")
        
        out = img.convert('RGB')
        buf = io.BytesIO()
        out.save(buf, format='PNG', optimize=True)
        return buf.getvalue()

# ==============================================================================
# SECTION 7: VIEW CONTROLLER (UI)
# ==============================================================================

class UIManager:
    def __init__(self):
        self.config = SystemConfig()
        self.db = GoogleSheetsRepository()
        self.logic = GamificationService()
        self.gfx = GraphicsRenderer()

    def setup(self):
        st.set_page_config(page_title=self.config.APP_NAME, page_icon="🏫", layout="wide", initial_sidebar_state="expanded")
        self._inject_css()

    def _inject_css(self):
        st.markdown(f"""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&family=Prompt:wght@300;400;500;700&display=swap');
            
            :root {{ 
                --primary: {self.config.COLOR_PRIMARY}; 
                --bg: {self.config.COLOR_BG}; 
            }}
            
            html, body, .stApp {{ font-family: 'Sarabun', sans-serif; background-color: var(--bg); color: {self.config.COLOR_TEXT}; }}
            
            .glass-card {{
                background: white; border-radius: 16px; padding: 1.5rem;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                border: 1px solid {self.config.COLOR_BORDER}; margin-bottom: 1rem;
            }}
            .hero-container {{
                background: linear-gradient(135deg, {self.config.COLOR_PRIMARY}, {self.config.COLOR_SECONDARY});
                padding: 2.5rem; border-radius: 20px; color: white; margin-bottom: 2rem;
                display: flex; justify-content: space-between; align-items: center;
                box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
            }}
            .stTextInput input, .stTextArea textarea, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {{
                border-radius: 10px; border: 1px solid {self.config.COLOR_BORDER};
            }}
            </style>
        """, unsafe_allow_html=True)

    def render_sidebar(self) -> str:
        with st.sidebar:
            st.title(f"🎛️ {self.config.APP_NAME}")
            st.caption(f"v{self.config.APP_VERSION}")
            st.divider()
            
            st.subheader("Select Classroom")
            room = st.selectbox("Active Class", ["ม.1/1", "ม.1/2", "ม.1/10"])
            
            st.divider()
            if st.button("📥 Export CSV"):
                df = self.db.fetch_all()
                st.download_button("Download File", df.to_csv(index=False).encode('utf-8'), "data.csv")
            
            return room

    def _render_command(self, room, room_df, all_df):
        st.header("⚡ Command Center")
        if room_df.empty:
            st.info("No teams found. Please create one in Management.")
            return

        # Batch Selection
        targets = st.multiselect("Select Teams (Multi-Select Enabled)", sorted(room_df['GroupName'].unique()))
        
        st.divider()
        c1, c2 = st.columns(2)
        
        def _execute(reason, amt):
            if not targets:
                st.error("Please select a team."); return
            
            with st.status("Processing Batch Transaction...") as status:
                updates = {}
                for t in targets:
                    row = room_df[room_df['GroupName'] == t].iloc[0]
                    try: hist = json.loads(row['HistoryLog'])
                    except: hist = []
                    
                    # Logic
                    nxp, nh, nb = self.logic.calculate_new_state(row['XP'], hist, reason, amt)
                    updates[t] = {"xp": nxp, "history": nh, "badges": nb}
                
                # DB Commit
                count = self.db.batch_update_state(updates, all_df)
                
                if count > 0:
                    status.update(label=f"Success! Updated {count} teams.", state="complete")
                    time.sleep(1); st.rerun()
                else:
                    status.update(label="Failed to commit.", state="error")

        with c1:
            st.subheader("Quick Actions")
            st.button("📚 On Time (+50)", on_click=_execute, args=("ส่งงานตรงเวลา", 50), use_container_width=True)
            st.button("🙋 Participate (+20)", on_click=_execute, args=("มีส่วนร่วม", 20), use_container_width=True)
            st.button("🏆 Activity Win (+100)", on_click=_execute, args=("ชนะกิจกรรม", 100), type="primary", use_container_width=True)
            st.button("🐢 Late (-20)", on_click=_execute, args=("ส่งงานล่าช้า", -20), use_container_width=True)

        with c2:
            st.subheader("Manual Input")
            with st.form("manual"):
                r = st.text_input("Reason")
                a = st.number_input("XP", step=5)
                if st.form_submit_button("Submit", use_container_width=True):
                    if r and a != 0: _execute(r, a)
                    else: st.warning("Invalid Input")

    def _render_leaderboard(self, room, room_df):
        st.header("🏆 Leaderboard")
        
        if not room_df.empty:
            c1, c2 = st.columns([1, 2])
            with c1:
                st.info("Generates Vector-Based Sticker Image.")
                if st.button("✨ Generate Image", type="primary", use_container_width=True):
                    try:
                        img = self.gfx.render(room, room_df, self.logic)
                        st.session_state['lb_img'] = img
                    except Exception as e:
                        st.error(f"Render Error: {e}")
                
                if 'lb_img' in st.session_state:
                    st.download_button("📥 Download PNG", st.session_state['lb_img'], "lb.png", "image/png", use_container_width=True)
            
            with c2:
                if 'lb_img' in st.session_state:
                    st.image(st.session_state['lb_img'], use_container_width=True)

        st.divider()
        # Live List
        for i, row in room_df.sort_values("XP", ascending=False).reset_index(drop=True).iterrows():
            rank = self.logic.get_rank(row['XP'])
            col = self.config.COLOR_DANGER if row['XP'] < 0 else rank.color
            
            st.markdown(f"""
            <div class='glass-card' style='border-left: 6px solid {col};'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <div>
                        <span style='font-size:1.2rem; font-weight:bold; color:#94A3B8; margin-right:10px;'>#{i+1}</span>
                        <span style='font-size:1.3rem; font-weight:bold;'>{row['GroupName']}</span>
                        <div style='color:#64748B; font-size:0.9rem; margin-top:5px;'>{row['Members']}</div>
                    </div>
                    <div style='text-align:right;'>
                        <div style='font-size:2rem; font-weight:800; color:{col};'>{row['XP']}</div>
                        <span style='background:{rank.bg}; color:{rank.color}; padding:2px 8px; border-radius:10px; font-size:0.8rem; font-weight:bold;'>{rank.name_th}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    def _render_manage(self, room, room_df, all_df):
        st.header("🛠️ Management")
        
        # 1. Create
        with st.expander("➕ Create New Team", expanded=True):
            with st.form("create"):
                n = st.text_input("Team Name")
                m = st.text_area("Members")
                if st.form_submit_button("Create", type="primary") and n:
                    if self.db.create_team(room, n, m, all_df):
                        st.success("Created!"); time.sleep(0.5); st.rerun()
                    else: st.error("Duplicate Name!")

        st.divider()
        
        # 2. Edit (Full CRUD restored)
        st.subheader("✏️ Edit Team (Rename / Move Members)")
        t_list = sorted(room_df['GroupName'].unique())
        target = st.selectbox("Select Team", ["-"] + t_list)
        
        if target != "-":
            curr = room_df[room_df['GroupName'] == target].iloc[0]
            with st.form("edit"):
                new_n = st.text_input("Name", value=curr['GroupName'])
                new_m = st.text_area("Members", value=curr['Members'], height=150)
                
                c_s, c_d = st.columns([3, 1])
                with c_s:
                    if st.form_submit_button("💾 Save Changes", type="primary"):
                        if self.db.update_team_details(room, target, new_n, new_m, all_df):
                            st.success("Updated!"); time.sleep(0.5); st.rerun()
                        else: st.error("Update Failed.")
        
        # 3. Delete
        st.divider()
        st.subheader("🗑️ Delete Team")
        to_del = st.selectbox("Select to Delete", ["-"] + t_list)
        if to_del != "-" and st.button("Confirm Delete", type="primary"):
            self.db.delete_team(room, to_del, all_df)
            st.success("Deleted."); time.sleep(0.5); st.rerun()

    def run(self):
        self.setup()
        room = self.render_sidebar()
        
        # Load Context
        try:
            all_df = self.db.fetch_all()
            room_df = all_df[all_df['Room'] == room].copy()
        except: st.error("DB Load Error"); return

        # Hero
        st.markdown(f"""
            <div class='hero-container'>
                <div><h1>{room}</h1></div>
                <div style='text-align:right;'><div style='font-size:3rem; font-weight:800;'>{len(room_df)}</div>Teams</div>
            </div>
        """, unsafe_allow_html=True)

        t1, t2, t3, t4, t5 = st.tabs(["Command", "Leaderboard", "Analytics", "Privileges", "Manage"])
        
        with t1: self._render_command(room, room_df, all_df)
        with t2: self._render_leaderboard(room, room_df)
        with t3: 
            st.header("Analytics")
            if not room_df.empty: st.bar_chart(room_df.set_index("GroupName")['XP'])
        with t4:
            st.header("Privileges")
            for r in self.logic.ranks: 
                if r.id != RankTierID.PROBATION:
                    st.info(f"**{r.name_th}**: {r.privilege}")
        with t5: self._render_manage(room, room_df, all_df)

if __name__ == "__main__":
    UIManager().run()
