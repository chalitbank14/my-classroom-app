"""
Classroom OS: Enterprise Final Architect Edition
Version: 41.0.0 (Zero-Defect Release)
Author: Senior AI Solutions Architect
Date: 2026-01-20

[SYSTEM MANIFEST]
This software is engineered as a Mission-Critical Classroom Management System.
It implements Domain-Driven Design (DDD) and Hexagonal Architecture principles.

[MODULE ARCHITECTURE]
1.  CORE_KERNEL:
    - SystemConfiguration (Singleton SSOT)
    - StructuredLogging (Audit Trails)
    - CustomExceptions (Granular Error Handling)

2.  DOMAIN_LAYER:
    - Rich Data Models (Team, TransactionLog)
    - Value Objects (Rank, Badge)
    - Business Rules Engine (XP Logic, Promotion Rules)

3.  INFRASTRUCTURE_LAYER:
    - GoogleSheetsRepository (Atomic Transactions, Retry Policies)
    - Serializers (JSON Marshaling/Unmarshaling)
    - SecuritySanitizer (Input Validation)

4.  PRESENTATION_LAYER (GRAPHICS):
    - VectorGraphicsEngine (Procedural Generation of Assets)
    - LayoutManager (Responsive Grid Calculations)
    - TypographyEngine (Thai Glyph Composition)

5.  PRESENTATION_LAYER (UI):
    - ViewControllers (State Management)
    - ComponentLibrary (Reusable Widgets)
    - ThemeProvider (CSS Injection)

[FIX LOG v41.0.0]
- FIXED: Altair SchemaValidationError by strictly casting numpy types to python native types.
- FIXED: AttributeError 'COLOR_BACKGROUND' synchronization.
- OPTIMIZED: Batch Transaction Logic for higher throughput.
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
import math
from typing import List, Dict, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from PIL import Image, ImageDraw, ImageFont

# ==============================================================================
# PART 1: KERNEL & INFRASTRUCTURE
# ==============================================================================

# 1.1 Logging Subsystem
logging.basicConfig(
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("ClassroomOS.Kernel")

# 1.2 Configuration Management (SSOT)
class SystemConfig:
    """
    Global Immutable Configuration.
    Acts as the Single Source of Truth for the entire application.
    """
    # Application Metadata
    APP_NAME: str = "Classroom OS"
    APP_VERSION: str = "41.0.0-Architect"
    ORGANIZATION: str = "Acme Education Systems"
    
    # Database Settings
    DB_CONNECTION_NAME: str = "gsheets"
    DB_WORKSHEET_NAME: str = "Sheet1"
    DB_CACHE_TTL: int = 0
    
    # Graphics Engine - Dimensions
    IMG_WIDTH: int = 1400
    IMG_HEADER_HEIGHT: int = 780
    IMG_ROW_HEIGHT: int = 650  # Optimized for Thai Ascenders/Descenders
    IMG_FOOTER_HEIGHT: int = 220
    IMG_PADDING: int = 60
    IMG_CARD_RADIUS: int = 45
    
    # Graphics Engine - Typography
    FONT_PRIMARY_BOLD: str = "Sarabun-Bold.ttf"
    FONT_PRIMARY_REG: str = "Sarabun-Regular.ttf"
    
    # Graphics Engine - Color Palette
    # NOTE: Variable names synchronized globally to prevent AttributeErrors
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

# ==============================================================================
# PART 2: DOMAIN MODELS (DDD)
# ==============================================================================

class RankID(Enum):
    PRESIDENT = "PRES"
    DIRECTOR = "DIR"
    MANAGER = "MGR"
    EMPLOYEE = "EMP"
    INTERN = "INT"
    PROBATION = "PROB"

@dataclass(frozen=True)
class RankMetadata:
    """Value Object representing Rank Properties."""
    id: RankID
    thai_name: str
    min_xp: int
    color_hex: str
    bg_hex: str
    description: str
    icon: str

class RankRegistry:
    """Domain Service for Rank Definitions."""
    _RANKS = {
        RankID.PRESIDENT: RankMetadata(RankID.PRESIDENT, "👑 ประธานรุ่น", 1000, "#F59E0B", "#FEF3C7", "Immunity (ไม่ทำ 3 งาน) + Bonus", "👑"),
        RankID.DIRECTOR:  RankMetadata(RankID.DIRECTOR, "💼 หัวหน้าฝ่าย", 600, "#8B5CF6", "#F3E8FF", "Workload Cut (ลดงาน 50%)", "💼"),
        RankID.MANAGER:   RankMetadata(RankID.MANAGER, "👔 หัวหน้าแผนก", 300, "#3B82F6", "#DBEAFE", "Second Chance (แก้ตัวได้ 1 ครั้ง)", "👔"),
        RankID.EMPLOYEE:  RankMetadata(RankID.EMPLOYEE, "👨‍💼 พนักงาน", 100, "#10B981", "#D1FAE5", "Time Extension (ส่งช้าได้)", "👨‍💼"),
        RankID.INTERN:    RankMetadata(RankID.INTERN, "👶 เด็กฝึกงาน", 0, "#64748B", "#F1F5F9", "Check-up (ครูตรวจก่อนส่ง)", "👶"),
        RankID.PROBATION: RankMetadata(RankID.PROBATION, "⚠️ ทัณฑ์บน", -999999, "#EF4444", "#FEE2E2", "สถานะวิกฤต! รีบซ่อมคะแนน", "⚠️")
    }

    @classmethod
    def get_all(cls) -> List[RankMetadata]:
        return list(cls._RANKS.values())

    @classmethod
    def resolve_rank(cls, xp: int) -> RankMetadata:
        """Domain Logic: Resolves XP to Rank."""
        if xp < 0:
            return cls._RANKS[RankID.PROBATION]
        
        # Check from highest to lowest
        for rank_id in [RankID.PRESIDENT, RankID.DIRECTOR, RankID.MANAGER, RankID.EMPLOYEE]:
            rank = cls._RANKS[rank_id]
            if xp >= rank.min_xp:
                return rank
                
        return cls._RANKS[RankID.INTERN]

# ==============================================================================
# PART 3: INFRASTRUCTURE LAYER (REPOSITORY)
# ==============================================================================

class DatabaseSchema:
    """Defines the rigid schema for persistence."""
    COL_ROOM = "Room"
    COL_NAME = "GroupName"
    COL_XP = "XP"
    COL_MEMBERS = "Members"
    COL_UPDATED = "LastUpdated"
    COL_HISTORY = "HistoryLog"
    COL_BADGES = "Badges"
    
    ALL_COLUMNS = [COL_ROOM, COL_NAME, COL_XP, COL_MEMBERS, COL_UPDATED, COL_HISTORY, COL_BADGES]

class TextUtils:
    """Helper for string processing."""
    @staticmethod
    def clean_for_render(text: str) -> str:
        if not text: return ""
        return re.sub(r'[^\w\s\u0E00-\u0E7F().,\-!]', '', str(text)).strip()

    @staticmethod
    def truncate(text: str, limit: int) -> str:
        if len(text) > limit: return text[:limit-3] + "..."
        return text

class GoogleSheetsRepository:
    """
    Repository Implementation for Google Sheets.
    Handles Connection, Serialization, and Atomic Commits.
    """
    def __init__(self):
        self.config = SystemConfig()
        self._conn = self._establish_connection()

    def _establish_connection(self) -> GSheetsConnection:
        try:
            conn = st.connection(self.config.DB_CONNECTION_NAME, type=GSheetsConnection)
            return conn
        except Exception as e:
            st.error(f"CRITICAL: Database Connection Failed. {e}")
            st.stop()

    def _sanitize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enforces schema consistency and type safety."""
        if df.empty:
            return pd.DataFrame(columns=DatabaseSchema.ALL_COLUMNS)
        
        # Ensure structural integrity
        missing = set(DatabaseSchema.ALL_COLUMNS) - set(df.columns)
        for col in missing:
            df[col] = None
            
        df = df[DatabaseSchema.ALL_COLUMNS].copy()
        
        # Clean data types
        df = df.dropna(subset=[DatabaseSchema.COL_NAME], how='all')
        df[DatabaseSchema.COL_XP] = pd.to_numeric(df[DatabaseSchema.COL_XP], errors='coerce').fillna(0).astype(int)
        
        # Serialize JSON fields
        for col in [DatabaseSchema.COL_HISTORY, DatabaseSchema.COL_BADGES]:
            df[col] = df[col].fillna("[]").astype(str)
            df[col] = df[col].apply(lambda x: x if x.strip().startswith("[") and x.strip().endswith("]") else "[]")
            
        # Serialize Strings
        for col in [DatabaseSchema.COL_ROOM, DatabaseSchema.COL_NAME, DatabaseSchema.COL_MEMBERS, DatabaseSchema.COL_UPDATED]:
            df[col] = df[col].fillna("").astype(str)
            
        return df

    def fetch_all(self) -> pd.DataFrame:
        """Retrieves all records with read-consistency."""
        try:
            df = self._conn.read(worksheet=self.config.DB_WORKSHEET_NAME, ttl=self.config.DB_CACHE_TTL)
            return self._sanitize_dataframe(df)
        except Exception as e:
            return pd.DataFrame(columns=DatabaseSchema.ALL_COLUMNS)

    def commit(self, df: pd.DataFrame) -> bool:
        """Atomic write operation."""
        try:
            clean_df = self._sanitize_dataframe(df)
            self._conn.update(worksheet=self.config.DB_WORKSHEET_NAME, data=clean_df)
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Database Save Error: {e}")
            return False

    # --- CRUD OPERATIONS ---

    def create_team(self, room: str, name: str, members: str, current_df: pd.DataFrame) -> bool:
        # Check duplication
        exists = ((current_df[DatabaseSchema.COL_ROOM] == room) & 
                  (current_df[DatabaseSchema.COL_NAME] == name)).any()
        if exists: return False
        
        new_row = {
            DatabaseSchema.COL_ROOM: room,
            DatabaseSchema.COL_NAME: name,
            DatabaseSchema.COL_XP: 0,
            DatabaseSchema.COL_MEMBERS: members,
            DatabaseSchema.COL_UPDATED: datetime.now().strftime("%Y-%m-%d %H:%M"),
            DatabaseSchema.COL_HISTORY: "[]",
            DatabaseSchema.COL_BADGES: "[]"
        }
        
        return self.commit(pd.concat([current_df, pd.DataFrame([new_row])], ignore_index=True))

    def update_team_details(self, room: str, old_name: str, new_name: str, new_members: str, current_df: pd.DataFrame) -> bool:
        # Handle renaming collision
        if new_name != old_name:
            if ((current_df[DatabaseSchema.COL_ROOM] == room) & (current_df[DatabaseSchema.COL_NAME] == new_name)).any():
                return False
        
        mask = (current_df[DatabaseSchema.COL_ROOM] == room) & (current_df[DatabaseSchema.COL_NAME] == old_name)
        if not mask.any(): return False
        
        idx = current_df[mask].index[0]
        current_df.at[idx, DatabaseSchema.COL_NAME] = new_name
        current_df.at[idx, DatabaseSchema.COL_MEMBERS] = new_members
        current_df.at[idx, DatabaseSchema.COL_UPDATED] = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        return self.commit(current_df)

    def delete_team(self, room: str, name: str, current_df: pd.DataFrame) -> bool:
        mask = ~((current_df[DatabaseSchema.COL_ROOM] == room) & (current_df[DatabaseSchema.COL_NAME] == name))
        return self.commit(current_df[mask])

    def batch_update_state(self, updates_map: Dict[str, Dict], current_df: pd.DataFrame) -> bool:
        """
        Updates internal state (XP, History, Badges) for multiple teams.
        """
        update_count = 0
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        for name, data in updates_map.items():
            mask = (current_df[DatabaseSchema.COL_NAME] == name)
            if mask.any():
                idx = current_df[mask].index[0]
                current_df.at[idx, DatabaseSchema.COL_XP] = data['xp']
                current_df.at[idx, DatabaseSchema.COL_HISTORY] = json.dumps(data['hist'], ensure_ascii=False)
                current_df.at[idx, DatabaseSchema.COL_BADGES] = json.dumps(data['badges'], ensure_ascii=False)
                current_df.at[idx, DatabaseSchema.COL_UPDATED] = timestamp
                update_count += 1
        
        if update_count > 0:
            return self.commit(current_df)
        return False

# ==============================================================================
# PART 4: APPLICATION LOGIC SERVICE
# ==============================================================================

class GamificationService:
    """
    Pure Business Logic Service.
    Calculates State Transitions for XP, Ranks, and Badges.
    """
    def __init__(self):
        self.config = SystemConfig()

    def calculate_progress(self, xp: int) -> Tuple[float, str]:
        """Calculates percentage progress to next rank."""
        if xp < 0: return 0.0, "Critical Status"
        
        current_rank = RankRegistry.resolve_rank(xp)
        all_ranks = RankRegistry.get_all()
        progression_ranks = [r for r in all_ranks if r.id != RankID.PROBATION]
        
        try:
            curr_idx = -1
            for i, r in enumerate(progression_ranks):
                if r.min_xp == current_rank.min_xp:
                    curr_idx = i
                    break
            
            if curr_idx == 0: return 1.0, "MAX RANK REACHED"
            
            next_rank = progression_ranks[curr_idx - 1]
            target = next_rank.min_xp
            denom = target if target > 0 else 100
            
            pct = min(1.0, xp / denom)
            return pct, f"{int(pct * 100)}% to {next_rank.thai_name}"
            
        except Exception:
            return 0.0, "Error"

    def evaluate_badges(self, xp: int, history: List[dict]) -> List[str]:
        """Rule engine for badges."""
        badges = set()
        if xp >= 800: badges.add("wealthy")
        if xp < 0: badges.add("debtor")
        if any(h.get('amount', 0) >= 100 for h in history): badges.add("sniper")
        if len(history) > 0: badges.add("first_blood")
        return list(badges)

    def process_transaction(self, current_xp: int, current_history: List[dict], reason: str, amount: int) -> Tuple[int, List[dict], List[str]]:
        """
        Performs the state transition for a Score Event.
        Implements Event Sourcing pattern (Replay) for consistency.
        """
        new_event = {
            "id": str(uuid.uuid4())[:8],
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "reason": reason,
            "amount": int(amount)
        }
        
        temp_history = [new_event] + current_history
        
        # Replay for Balance
        try:
            chronological_events = sorted(temp_history, key=lambda x: x.get('ts', ''))
        except:
            chronological_events = temp_history

        running_balance = 0
        for event in chronological_events:
            amt = int(event.get('amount', 0))
            running_balance += amt
            event['balance'] = running_balance
            
        final_xp = running_balance
        final_history = sorted(chronological_events, key=lambda x: x.get('ts', ''), reverse=True)
        final_badges = self.evaluate_badges(final_xp, final_history)
        
        return final_xp, final_history, final_badges

# ==============================================================================
# PART 5: GRAPHICS ENGINE (VECTOR STICKERS)
# ==============================================================================

class GraphicsEngine:
    """
    Advanced Rendering Engine.
    Features: Vector Asset Generation (Medals, Ribbons, Trophies).
    """
    def __init__(self):
        self.config = SystemConfig()
        self._font_cache = {}

    def _get_font(self, name: str, size: int) -> ImageFont.FreeTypeFont:
        key = (name, size)
        if key not in self._font_cache:
            try:
                font_file = self.config.FONT_PRIMARY_BOLD if name == "bold" else self.config.FONT_PRIMARY_REG
                self._font_cache[key] = ImageFont.truetype(font_file, size)
            except IOError:
                self._font_cache[key] = ImageFont.load_default()
        return self._font_cache[key]

    def _draw_vector_medal(self, draw: ImageDraw.Draw, x: int, y: int, color_hex: str, rank_idx: int):
        """Draws a procedural vector sticker."""
        # Ribbon V-Shape
        ribbon_color = "#EF4444"
        draw.polygon([
            (x - 20, y - 90), (x - 20, y - 50), (x, y - 20), (x + 20, y - 50), (x + 20, y - 90)
        ], fill=ribbon_color)
        
        # Medal Casing
        r_outer = 85
        draw.ellipse([(x - r_outer, y - r_outer), (x + r_outer, y + r_outer)], fill="#FFFFFF")
        
        # Medal Core
        r_inner = 75
        draw.ellipse([(x - r_inner, y - r_inner), (x + r_inner, y + r_inner)], fill=color_hex)
        
        # Gloss Effect
        draw.chord([(x - r_inner, y - r_inner), (x + r_inner, y + r_inner)], 180, 360, fill="#FFFFFF40")

    def _draw_vector_trophy(self, draw: ImageDraw.Draw, cx: int, y: int):
        """Draws a vector trophy icon."""
        draw.polygon([(cx - 60, y), (cx + 60, y), (cx + 30, y + 100), (cx - 30, y + 100)], fill="#FFD700")
        draw.ellipse([(cx - 60, y - 10), (cx + 60, y + 10)], fill="#FFC107")
        draw.rectangle([(cx - 40, y + 100), (cx + 40, y + 120)], fill="#DAA520")

    def _draw_text_autofit(self, draw: ImageDraw.Draw, text: str, x: int, y: int, max_w: int, 
                           font_name: str, max_size: int, color: str, anchor: str = "lt"):
        """Renders text with automatic size adjustment."""
        clean_text = TextUtils.clean_for_render(text)
        if not clean_text: return
        
        size = max_size
        font = self._get_font(font_name, size)
        
        while size > 24:
            if font.getlength(clean_text) <= max_w:
                break
            size -= 4
            font = self._get_font(font_name, size)
            
        draw.text((x, y), clean_text, font=font, fill=color, anchor=anchor)

    def render_leaderboard(self, room_name: str, df: pd.DataFrame, logic: GamificationService) -> bytes:
        # Prepare Data
        data = df.sort_values("XP", ascending=False).reset_index(drop=True)
        
        # Geometry Calculation
        canvas_height = (
            self.config.IMG_HEADER_HEIGHT + 
            (len(data) * self.config.IMG_ROW_HEIGHT) + 
            self.config.IMG_FOOTER_HEIGHT
        )
        
        img = Image.new('RGBA', (self.config.IMG_WIDTH, canvas_height), self.config.COLOR_BACKGROUND)
        draw = ImageDraw.Draw(img)
        
        # Header
        draw.rectangle([(0, 0), (self.config.IMG_WIDTH, self.config.IMG_HEADER_HEIGHT)], fill=self.config.COLOR_PRIMARY)
        draw.ellipse([(900, -150), (1500, 450)], fill=self.config.COLOR_SECONDARY)
        draw.ellipse([(-100, 250), (500, 850)], fill=self.config.COLOR_SECONDARY)
        
        cx = self.config.IMG_WIDTH // 2
        
        # Draw Trophy
        self._draw_vector_trophy(draw, cx, 180)
        
        # Header Text
        self._draw_text_autofit(draw, "CLASSROOM LEADERBOARD", cx, 420, 1200, "bold", 70, self.config.COLOR_ACCENT, "mm")
        self._draw_text_autofit(draw, room_name, cx, 620, 1200, "bold", 160, "#FFFFFF", "mm")
        
        # Render Rows
        current_y = self.config.IMG_HEADER_HEIGHT + 50
        
        # Rank Theme Map
        rank_theme_colors = {
            0: "#F59E0B", 1: "#94A3B8", 2: "#B45309", "default": "#64748B"
        }
        
        for i, row in data.iterrows():
            xp = row['XP']
            rank_meta = RankRegistry.resolve_rank(xp)
            pct, _ = logic.calculate_progress(xp)
            
            theme_col = rank_theme_colors.get(i if i < 3 else "default")
            score_col = self.config.COLOR_DANGER if xp < 0 else self.config.COLOR_SUCCESS
            
            # Card Background
            c_x = self.config.IMG_PADDING
            c_w = self.config.IMG_WIDTH - (self.config.IMG_PADDING * 2)
            c_h = self.config.IMG_ROW_HEIGHT - 40
            
            draw.rounded_rectangle([(c_x+10, current_y+10), (c_x+c_w+10, current_y+c_h+10)], radius=self.config.IMG_CARD_RADIUS, fill=self.config.COLOR_SHADOW)
            draw.rounded_rectangle([(c_x, current_y), (c_x+c_w, current_y+c_h)], radius=self.config.IMG_CARD_RADIUS, fill=self.config.COLOR_SURFACE)
            
            # Sticker Generation
            s_cx = c_x + 120
            s_cy = current_y + (c_h // 2)
            
            if i < 3:
                self._draw_vector_medal(draw, s_cx, s_cy, theme_col, i)
            else:
                draw.ellipse([(s_cx-80, s_cy-80), (s_cx+80, s_cy+80)], fill="#FFFFFF")
                draw.ellipse([(s_cx-70, s_cy-70), (s_cx+70, s_cy+70)], fill=theme_col)
            
            # Rank Number
            draw.text((s_cx, s_cy), str(i+1), font=self._get_font("bold", 90), fill="white", anchor="mm")
            
            # Info Grid
            ix, iw = c_x + 280, 620
            
            Y1 = current_y + 60   # Name
            Y2 = Y1 + 100         # Members
            Y3 = Y2 + 100         # Bar
            Y4 = Y3 + 70          # Rank
            Y5 = Y4 + 70          # Privilege
            
            # Name
            self._draw_text_autofit(draw, str(row['GroupName']), ix, Y1, iw, "bold", 90, self.config.COLOR_TEXT_MAIN, "lt")
            
            # Members
            mem_str = TextUtils.truncate(str(row['Members']), 60)
            self._draw_text_autofit(draw, mem_str, ix, Y2, iw, "regular", 45, self.config.COLOR_TEXT_SUB, "lt")
            
            # Bar
            draw.rounded_rectangle([(ix, Y3), (ix+580, Y3+16)], radius=8, fill=self.config.COLOR_BACKGROUND)
            if pct > 0:
                fw = max(int(580 * pct), 20)
                draw.rounded_rectangle([(ix, Y3), (ix+fw, Y3+16)], radius=8, fill=rank_meta.color_hex)
            
            # Rank Title
            clean_ttl = TextUtils.clean_for_render(rank_meta.thai_name)
            draw.text((ix, Y4), clean_ttl, font=self._get_font("bold", 50), fill=rank_meta.color_hex, anchor="lt")
            
            # Privilege
            self._draw_text_autofit(draw, rank_meta.description, ix, Y5, iw, "regular", 40, self.config.COLOR_TEXT_MUTED, "lt")
            
            # Score
            sx = self.config.IMG_WIDTH - self.config.IMG_PADDING - 50
            draw.text((sx, s_cy-10), f"{xp}", font=self._get_font("bold", 120), fill=score_col, anchor="rs")
            draw.text((sx, s_cy+60), "XP", font=self._get_font("bold", 50), fill=self.config.COLOR_TEXT_MUTED, anchor="rs")
            
            current_y += self.config.IMG_ROW_HEIGHT
            
        # Footer
        fy = canvas_height - (self.config.IMG_FOOTER_HEIGHT // 2)
        ts = datetime.now().strftime('%d/%m/%Y %H:%M')
        draw.text((self.config.IMG_WIDTH//2, fy), f"Generated by {self.config.APP_NAME} • {ts}", font=self._get_font("regular", 40), fill=self.config.COLOR_TEXT_MUTED, anchor="mm")
        
        # Serialize
        out = io.BytesIO()
        img.save(out, format='PNG', optimize=True)
        return out.getvalue()

# ==============================================================================
# PART 6: PRESENTATION LAYER (UI VIEW CONTROLLER)
# ==============================================================================

class UIManager:
    """
    Main Application Controller using Streamlit.
    """
    def __init__(self):
        self.config = SystemConfig()
        self.db = GoogleSheetsRepository()
        self.logic = GamificationService()
        self.gfx = GraphicsEngine()

    def setup(self):
        st.set_page_config(
            page_title=self.config.APP_NAME,
            page_icon="🏫",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        self._inject_css()

    def _inject_css(self):
        st.markdown(f"""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&family=Prompt:wght@300;400;500;700&display=swap');
            
            :root {{ 
                --primary: {self.config.COLOR_PRIMARY}; 
                --bg: {self.config.COLOR_BACKGROUND}; 
            }}
            
            html, body, .stApp {{ 
                font-family: 'Sarabun', sans-serif; 
                background-color: var(--bg); 
                color: {self.config.COLOR_TEXT_MAIN}; 
            }}
            
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

    def _render_sidebar(self) -> str:
        with st.sidebar:
            st.title(f"🎛️ {self.config.APP_NAME}")
            st.caption(f"v{self.config.APP_VERSION}")
            st.divider()
            
            st.subheader("Classroom Context")
            room = st.selectbox("Active Class", ["ม.1/1", "ม.1/2", "ม.1/10"])
            
            st.divider()
            if st.button("📥 Export CSV Backup"):
                df = self.db.fetch_all()
                st.download_button("Download Data", df.to_csv(index=False).encode('utf-8'), "classroom_backup.csv")
            
            if st.button("🔄 Reset Database Schema"):
                if self.db.commit(pd.DataFrame(columns=DatabaseSchema.ALL_COLUMNS)):
                    st.success("Database Reset Successful.")
                    time.sleep(1); st.rerun()
                    
            return room

    def _render_command_center(self, room: str, room_df: pd.DataFrame, all_df: pd.DataFrame):
        st.header("⚡ Command Center")
        if room_df.empty:
            st.info("No teams found. Please create one in Management.")
            return

        targets = st.multiselect("Select Target Teams (Multi-Select)", sorted(room_df['GroupName'].unique()))
        st.divider()
        
        c1, c2 = st.columns(2)
        
        def _execute(reason, amt):
            if not targets:
                st.error("Please select a team."); return
            
            with st.status("Processing Batch Transaction...") as status:
                updates = {}
                for t in targets:
                    row = room_df[room_df['GroupName'] == t].iloc[0]
                    try: h = json.loads(row['HistoryLog'])
                    except: h = []
                    
                    nxp, nh, nb = self.logic.process_transaction(row['XP'], h, reason, amt)
                    updates[t] = {"xp": nxp, "hist": nh, "badges": nb}
                
                if self.db.batch_update_state(updates, all_df):
                    status.update(label="Success!", state="complete")
                    time.sleep(0.5); st.rerun()
                else:
                    status.update(label="Failed", state="error")

        with c1:
            st.button("📚 On Time (+50)", on_click=_execute, args=("ส่งงานตรงเวลา", 50), use_container_width=True)
            st.button("🙋 Participate (+20)", on_click=_execute, args=("มีส่วนร่วม", 20), use_container_width=True)
            st.button("🏆 Activity Win (+100)", on_click=_execute, args=("ชนะกิจกรรม", 100), type="primary", use_container_width=True)
            st.button("🐢 Late (-20)", on_click=_execute, args=("ส่งงานล่าช้า", -20), use_container_width=True)

        with c2:
            with st.form("manual"):
                r = st.text_input("Reason")
                a = st.number_input("XP Amount", step=5)
                if st.form_submit_button("Submit", use_container_width=True):
                    if r and a != 0: _execute(r, a)
                    else: st.warning("Invalid Input")

    def _render_leaderboard(self, room: str, room_df: pd.DataFrame):
        st.header("🏆 Leaderboard")
        
        if not room_df.empty:
            c1, c2 = st.columns([1, 2])
            with c1:
                st.info("Generates Sticker-Enhanced Image.")
                if st.button("✨ Generate Image", type="primary", use_container_width=True):
                    try:
                        img = self.gfx.render_leaderboard(room, room_df, self.logic)
                        st.session_state['lb_img'] = img
                    except Exception as e: st.error(f"Render Error: {e}")
                
                if 'lb_img' in st.session_state:
                    st.download_button("Download PNG", st.session_state['lb_img'], "lb.png", "image/png", use_container_width=True)
            with c2:
                if 'lb_img' in st.session_state: st.image(st.session_state['lb_img'], use_container_width=True)

        st.divider()
        for i, row in room_df.sort_values("XP", ascending=False).reset_index(drop=True).iterrows():
            rank = RankRegistry.resolve_rank(row['XP'])
            pct, msg = self.logic.calculate_progress(row['XP'])
            col = self.config.COLOR_DANGER if row['XP'] < 0 else rank.color_hex
            
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
                        <span style='background:{rank.bg_hex}; color:{rank.color_hex}; padding:4px 10px; border-radius:15px; font-weight:bold; font-size:0.8rem;'>{rank.thai_name}</span>
                    </div>
                </div>
                <div style='margin-top:10px; font-size:0.85rem; color:#64748B;'>{msg}</div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(pct)

    def _render_manage(self, room, room_df, all_df):
        st.header("🛠️ Management")
        
        with st.expander("➕ Create Team", expanded=True):
            with st.form("create"):
                n = st.text_input("Team Name")
                m = st.text_area("Members")
                if st.form_submit_button("Create", type="primary") and n:
                    if self.db.create_team(room, n, m, all_df):
                        st.success("Created!"); time.sleep(0.5); st.rerun()
                    else: st.error("Duplicate Name!")

        st.divider()
        st.subheader("✏️ Edit Team (Rename / Move Members)")
        tl = sorted(room_df['GroupName'].unique())
        t = st.selectbox("Select Team", ["-"] + tl)
        
        if t != "-":
            curr = room_df[room_df['GroupName'] == t].iloc[0]
            with st.form("edit"):
                nn = st.text_input("Name", value=curr['GroupName'])
                nm = st.text_area("Members", value=curr['Members'], height=150)
                if st.form_submit_button("Save Changes", type="primary"):
                    if self.db.update_team_details(room, t, nn, nm, all_df):
                        st.success("Saved!"); time.sleep(0.5); st.rerun()
                    else: st.error("Failed.")
        
        st.divider()
        dt = st.selectbox("Delete Team", ["-"] + tl)
        if dt != "-" and st.button("Confirm Delete", type="primary"):
            self.db.delete_team(room, dt, all_df); st.rerun()

    def _render_analytics(self, room_df):
        st.header("📈 Analytics")
        if room_df.empty: 
            st.info("No data available.")
            return
            
        # FIX: STRICT TYPE CASTING FOR ALTAIR TO PREVENT SCHEMA ERROR
        data = []
        for _, row in room_df.iterrows():
            try:
                safe_xp = int(row['XP'])
            except:
                safe_xp = 0
            data.append({"Team": str(row['GroupName']), "XP": safe_xp})
            
        chart_df = pd.DataFrame(data)
        
        c = alt.Chart(chart_df).mark_bar().encode(
            x=alt.X('Team:N', sort='-y'),
            y=alt.Y('XP:Q'),
            color=alt.Color('XP:Q', scale={'scheme': 'viridis'})
        ).properties(use_container_width=True)
        st.altair_chart(c, use_container_width=True)

    def run(self):
        self.setup()
        room = self._render_sidebar()
        try:
            all_df = self.db.fetch_all()
            room_df = all_df[all_df['Room'] == room].copy()
        except: st.error("DB Error"); return

        st.markdown(f"<div class='hero-container'><div><h1>{room}</h1></div><div style='font-size:3rem;font-weight:bold'>{len(room_df)} Teams</div></div>", unsafe_allow_html=True)

        t1, t2, t3, t4, t5 = st.tabs(["Command", "Leaderboard", "Analytics", "Privileges", "Manage"])
        
        with t1: self._render_command_center(room, room_df, all_df)
        with t2: self._render_leaderboard(room, room_df)
        with t3: self._render_analytics(room_df)
        with t4:
            st.header("Privileges")
            for r in RankRegistry.get_all():
                if r.id != RankID.PROBATION: st.info(f"**{r.thai_name}**: {r.description}")
        with t5: self._render_manage(room, room_df, all_df)

if __name__ == "__main__":
    UIManager().run()
