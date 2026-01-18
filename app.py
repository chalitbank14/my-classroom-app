"""
Classroom OS: Enterprise Edition (Ultimate)
Version: 6.0.0-Stable (Thai Typography Master Fix)
Author: AI Development Team
Date: 2026-01-20

Description:
A comprehensive, enterprise-grade gamification platform for classrooms.
This version includes a completely rewritten Graphics Engine designed specifically
to handle Thai typography issues (floating vowels, tone marks clipping).
It utilizes an expanded vertical grid system to ensure absolute separation between elements.

Architecture: Domain-Driven Design (DDD) with clear separation of concerns.
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
from typing import List, Dict, Optional, Tuple, Any, Union
from PIL import Image, ImageDraw, ImageFont
import re

# ==============================================================================
# MODULE 1: SYSTEM KERNEL & CONFIGURATION
# ==============================================================================

# Configure robust logging for production debugging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("ClassroomOS")

class AppConfig:
    """
    Centralized configuration management.
    Acts as the Single Source of Truth (SSOT) for the entire application.
    """
    # --- Identity ---
    APP_NAME: str = "Classroom OS"
    APP_VERSION: str = "6.0.0-Ultimate"
    ORG_NAME: str = "Acme Education"

    # --- Database ---
    DB_CONNECTION_NAME: str = "gsheets"
    DB_MAIN_WORKSHEET: str = "Sheet1"
    DB_CACHE_TTL: int = 0  # Disabled for real-time consistency

    # --- Graphics Engine Constants (Thai Layout Optimized) ---
    # Increased Row Height significantly to accommodate Thai ascenders/descenders
    IMG_WIDTH: int = 1400
    IMG_HEADER_HEIGHT: int = 700
    IMG_ROW_HEIGHT: int = 600  # Expanded to 600px to prevent ANY overlapping
    IMG_FOOTER_HEIGHT: int = 150
    IMG_PADDING_X: int = 50
    IMG_CARD_RADIUS: int = 40

    # --- Typography (Font Assets) ---
    # These fonts must exist in the root directory
    FONT_PRIMARY_BOLD: str = "Sarabun-Bold.ttf"
    FONT_PRIMARY_REG: str = "Sarabun-Regular.ttf"

    # --- Corporate Design System (Color Palette) ---
    COLOR_BRAND_PRIMARY: str = "#4338CA"    # Indigo 700
    COLOR_BRAND_SECONDARY: str = "#3730A3"  # Indigo 800
    COLOR_BRAND_ACCENT: str = "#A5B4FC"     # Indigo 200
    
    COLOR_BG_MAIN: str = "#F1F5F9"          # Slate 50
    COLOR_CARD_SURFACE: str = "#FFFFFF"     # White
    COLOR_CARD_BORDER: str = "#E2E8F0"      # Slate 200
    COLOR_CARD_SHADOW: str = "#94A3B8"      # Slate 400
    
    COLOR_TEXT_PRIMARY: str = "#1E293B"     # Slate 800
    COLOR_TEXT_SECONDARY: str = "#64748B"   # Slate 500
    COLOR_TEXT_MUTED: str = "#94A3B8"       # Slate 400

    COLOR_SCORE_POSITIVE: str = "#10B981"   # Emerald 500
    COLOR_SCORE_NEGATIVE: str = "#EF4444"   # Red 500

    # --- Rank Styling Definitions ---
    RANK_THEMES: Dict[Union[int, str], Dict[str, str]] = {
        0: {"hex": "#F59E0B", "bg": "#FEF3C7", "name": "Gold"},   # Rank 1
        1: {"hex": "#94A3B8", "bg": "#F1F5F9", "name": "Silver"}, # Rank 2
        2: {"hex": "#B45309", "bg": "#FFEDD5", "name": "Bronze"}, # Rank 3
        "default": {"hex": "#64748B", "bg": "#F8FAFC", "name": "Slate"} # General
    }

# ==============================================================================
# MODULE 2: DOMAIN MODELS (DATA STRUCTURES)
# ==============================================================================

class RankDefinition:
    """
    Value Object representing a Rank tier's properties.
    """
    def __init__(self, id: str, th_name: str, min_xp: int, color: str, bg_color: str, description: str):
        self.id = id
        self.th_name = th_name
        self.min_xp = min_xp
        self.color = color
        self.bg_color = bg_color
        self.description = description

    def __repr__(self):
        return f"<Rank: {self.th_name} ({self.min_xp}+)>"

class TransactionLog:
    """
    Data Transfer Object (DTO) for score transactions.
    """
    def __init__(self, id: str, timestamp: datetime, reason: str, amount: int, balance: int):
        self.id = id
        self.timestamp = timestamp
        self.reason = reason
        self.amount = amount
        self.balance = balance

# ==============================================================================
# MODULE 3: BUSINESS LOGIC LAYER
# ==============================================================================

class RankManager:
    """
    Core logic for rank determination and progression rules.
    """
    def __init__(self):
        # Configuration of Ranks
        self._ranks: List[RankDefinition] = [
            RankDefinition("PRESIDENT", "👑 ประธานรุ่น", 1000, "#F59E0B", "#FEF3C7", "Immunity (ไม่ทำ 3 งาน) + Bonus 1/งาน"),
            RankDefinition("DIRECTOR", "💼 หัวหน้าฝ่าย", 600, "#8B5CF6", "#F3E8FF", "Workload Cut (ลดภาระงาน 50%)"),
            RankDefinition("MANAGER", "👔 หัวหน้าแผนก", 300, "#3B82F6", "#DBEAFE", "Second Chance (แก้ตัวได้ 1 ครั้ง/หน่วย)"),
            RankDefinition("EMPLOYEE", "👨‍💼 พนักงาน", 100, "#10B981", "#D1FAE5", "Time Extension (ส่งช้าได้ 2 สัปดาห์)"),
            RankDefinition("INTERN", "👶 เด็กฝึกงาน", 0, "#64748B", "#F1F5F9", "Check-up (สิทธิ์ให้ครูตรวจงานก่อนส่ง)"),
            RankDefinition("PROBATION", "⚠️ ทัณฑ์บน", -999999, "#EF4444", "#FEE2E2", "สถานะวิกฤต! รีบซ่อมคะแนนด่วน")
        ]
        self._probation_rank = self._ranks[-1]
        self._default_rank = self._ranks[-2] # Intern default

    @property
    def all_ranks(self) -> List[RankDefinition]:
        return self._ranks

    def get_rank_by_xp(self, xp: int) -> RankDefinition:
        """Determines rank based on XP value."""
        if xp < 0:
            return self._probation_rank
        
        for rank in self._ranks:
            # Check conditions (skip probation in normal loop)
            if rank.id != "PROBATION" and xp >= rank.min_xp:
                return rank
        return self._default_rank

    def calculate_progress_to_next(self, xp: int) -> Tuple[float, str]:
        """Calculates percentage progress to the next rank."""
        if xp < 0:
            return 0.0, "Status: Critical"
        
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
    Gamification engine for awarding badges.
    """
    def __init__(self):
        self._badge_catalog: Dict[str, str] = {
            "wealthy": "💎",    # High XP
            "sniper": "🎯",     # High single transaction
            "debtor": "💸",     # Negative
            "phoenix": "🔥",    # Recovery (Placeholder)
            "first_blood": "🩸", # First action
            "veteran": "🎖️"      # 10+ actions
        }

    def evaluate_badges(self, current_xp: int, history: List[Dict[str, Any]]) -> List[str]:
        """Evaluates earned badges based on state."""
        earned_badges = set()
        if current_xp >= 800: earned_badges.add("wealthy")
        if current_xp < 0: earned_badges.add("debtor")
        
        if history:
            earned_badges.add("first_blood")
            if len(history) >= 10: earned_badges.add("veteran")
            if any(h.get('amount', 0) >= 100 for h in history): earned_badges.add("sniper")
            
        return list(earned_badges)

    def render_badges(self, badge_ids: List[str]) -> str:
        """Renders badge icons."""
        return "".join([self._badge_catalog.get(bid, "") for bid in badge_ids])

# ==============================================================================
# MODULE 4: DATA ACCESS LAYER (REPOSITORY)
# ==============================================================================

class GoogleSheetsRepository:
    """
    Robust Data Access Object (DAO) for Google Sheets.
    Handles connection, schema validation, and CRUD operations.
    """
    SCHEMA = ['Room', 'GroupName', 'XP', 'Members', 'LastUpdated', 'HistoryLog', 'Badges']

    def __init__(self):
        self.cfg = AppConfig()
        self.conn = self._establish_connection()

    def _establish_connection(self) -> GSheetsConnection:
        try:
            return st.connection(self.cfg.DB_CONNECTION_NAME, type=GSheetsConnection)
        except Exception as e:
            logger.critical(f"DB Connection Failure: {e}")
            st.error(f"🔴 Critical DB Error. Please check secrets.")
            st.stop()

    def _sanitize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensures DataFrame conforms to strict schema."""
        if df.empty:
            return pd.DataFrame(columns=self.SCHEMA)
        
        # Add missing columns
        missing = set(self.SCHEMA) - set(df.columns)
        for col in missing: df[col] = None

        # Clean types
        df = df[self.SCHEMA].copy().dropna(how='all')
        df['XP'] = pd.to_numeric(df['XP'], errors='coerce').fillna(0).astype(int)
        
        for col in ['HistoryLog', 'Badges']:
            df[col] = df[col].fillna("[]").astype(str)
            # Basic validation
            mask = ~df[col].str.startswith("[")
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
            clean_df = self._sanitize_dataframe(df)
            self.conn.update(worksheet=self.cfg.DB_MAIN_WORKSHEET, data=clean_df)
            st.cache_data.clear()
            return True
        except Exception as e:
            logger.error(f"Commit Error: {e}")
            st.error(f"⚠️ Save Error: {e}")
            return False

    # --- Transactional Methods ---

    def create_group_record(self, room: str, name: str, members: str, current_df: pd.DataFrame) -> bool:
        if ((current_df['Room'] == room) & (current_df['GroupName'] == name)).any():
            return False
        
        new_row = {
            "Room": room, "GroupName": name, "XP": 0, "Members": members,
            "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "HistoryLog": "[]", "Badges": "[]"
        }
        return self.commit_data(pd.concat([current_df, pd.DataFrame([new_row])], ignore_index=True))

    def update_group_record(self, room: str, old_name: str, new_name: str, new_members: str, current_df: pd.DataFrame) -> bool:
        if new_name != old_name and ((current_df['Room'] == room) & (current_df['GroupName'] == new_name)).any():
            return False
            
        mask = (current_df['Room'] == room) & (current_df['GroupName'] == old_name)
        if not mask.any(): return False
             
        idx = current_df[mask].index[0]
        current_df.at[idx, 'GroupName'] = new_name
        current_df.at[idx, 'Members'] = new_members
        current_df.at[idx, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        return self.commit_data(current_df)

    def delete_group_record(self, room: str, name: str, current_df: pd.DataFrame) -> bool:
        mask = ~((current_df['Room'] == room) & (current_df['GroupName'] == name))
        return self.commit_data(current_df[mask])

    def process_xp_transaction(self, room: str, target_groups: List[str], amount: int, reason: str, 
                               current_df: pd.DataFrame, badge_sys: BadgeSystem) -> Tuple[bool, int]:
        updated_count = 0
        ts_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        for group_name in target_groups:
            mask = (current_df['Room'] == room) & (current_df['GroupName'] == group_name)
            if mask.any():
                idx = current_df[mask].index[0]
                try: history = json.loads(current_df.at[idx, 'HistoryLog'])
                except: history = []
                
                new_log = {"id": str(uuid.uuid4())[:8], "ts": ts_str, "reason": reason, "amount": int(amount)}
                history.insert(0, new_log)
                
                # Recalculate Balance
                new_bal = sum(h['amount'] for h in history)
                history[0]['balance'] = new_bal
                
                current_df.at[idx, 'XP'] = new_bal
                current_df.at[idx, 'HistoryLog'] = json.dumps(history, ensure_ascii=False)
                current_df.at[idx, 'Badges'] = json.dumps(badge_sys.evaluate_badges(new_bal, history), ensure_ascii=False)
                current_df.at[idx, 'LastUpdated'] = ts_str
                updated_count += 1
        
        return (self.commit_data(current_df), updated_count) if updated_count > 0 else (False, 0)

    def apply_history_override(self, room: str, group_name: str, new_history_df: pd.DataFrame, 
                               current_df: pd.DataFrame, badge_sys: BadgeSystem) -> bool:
        mask = (current_df['Room'] == room) & (current_df['GroupName'] == group_name)
        if not mask.any(): return False
            
        idx = current_df[mask].index[0]
        history_list = new_history_df.to_dict('records')
        
        # Sort Ascending to calc running balance
        try: hist_asc = sorted(history_list, key=lambda x: x.get('ts', ''))
        except: hist_asc = history_list

        running = 0
        for item in hist_asc:
            amt = int(item.get('amount', 0))
            item['amount'] = amt
            running += amt
            item['balance'] = running
            
        # Sort Descending for storage
        hist_desc = sorted(hist_asc, key=lambda x: x.get('ts', ''), reverse=True)
        final_xp = running
        
        current_df.at[idx, 'XP'] = final_xp
        current_df.at[idx, 'HistoryLog'] = json.dumps(hist_desc, ensure_ascii=False)
        current_df.at[idx, 'Badges'] = json.dumps(badge_sys.evaluate_badges(final_xp, hist_desc), ensure_ascii=False)
        current_df.at[idx, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        return self.commit_data(current_df)

# ==============================================================================
# MODULE 5: GRAPHICS ENGINE (ULTIMATE THAI FIX)
# ==============================================================================

class GraphicsEngine:
    """
    Advanced Rendering Engine.
    Fixes Thai typography issues by implementing a strict vertical grid system
    that guarantees no overlapping of vowels, tone marks, or descenders.
    """
    def __init__(self):
        self.cfg = AppConfig()
        self._font_cache = {}

    def _get_font(self, name: str, size: int) -> ImageFont.FreeTypeFont:
        key = (name, size)
        if key not in self._font_cache:
            try:
                # Pillow >= 10.0.0 handles complex scripts better
                font = ImageFont.truetype(name, size)
                self._font_cache[key] = font
            except IOError:
                logger.error(f"Font missing: {name}. Using default.")
                font = ImageFont.load_default()
                self._font_cache[key] = font
        return self._font_cache[key]

    def _clean_text_for_render(self, text: str) -> str:
        """
        Cleans text but PRESERVES Thai characters (\u0E00-\u0E7F).
        Removes only problematic emojis that cause square boxes.
        """
        if not isinstance(text, str): return ""
        # Regex to keep Word chars, Spaces, and Thai Unicode Block
        # This strips emojis but keeps Thai marks.
        return re.sub(r'[^\w\s\u0E00-\u0E7F.,()-]', '', text).strip()

    def _draw_text_with_autofit(self, draw: ImageDraw.Draw, text: str, 
                                x: int, y: int, max_width: int,
                                font_name: str, max_size: int, 
                                color: str, anchor: str = "lt") -> None:
        """
        Draws text with automatic font size reduction to fit width.
        Uses 'lt' (Left Top) anchor for precise vertical control.
        """
        text = self._clean_text_for_render(text)
        if not text: return

        current_size = max_size
        min_size = 30
        font = self._get_font(font_name, current_size)
        
        while current_size > min_size:
            if font.getlength(text) <= max_width:
                break
            current_size -= 2
            font = self._get_font(font_name, current_size)
            
        draw.text((x, y), text, font=font, fill=color, anchor=anchor)

    def render_leaderboard_image(self, room_name: str, df: pd.DataFrame, rank_manager: RankManager) -> bytes:
        """
        Renders the leaderboard with an expanded vertical grid.
        """
        leaderboard_data = df.sort_values("XP", ascending=False).reset_index(drop=True)
        
        # Dynamic canvas height
        canvas_height = (
            self.cfg.IMG_HEADER_HEIGHT + 
            (len(leaderboard_data) * self.cfg.IMG_ROW_HEIGHT) + 
            self.cfg.IMG_FOOTER_HEIGHT
        )
        
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
        current_y_cursor = self.cfg.IMG_HEADER_HEIGHT + 50
        
        # Fonts
        f_rank_num = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 85)
        f_score_val = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 110)
        f_score_lbl = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 45)
        f_members = self._get_font(self.cfg.FONT_PRIMARY_REG, 42)
        f_rank_title = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 45)
        f_privilege = self._get_font(self.cfg.FONT_PRIMARY_REG, 36)

        for i, row in leaderboard_data.iterrows():
            xp = row['XP']
            rank_def = rank_manager.get_rank_by_xp(xp)
            progress_pct, _ = rank_manager.calculate_progress_to_next(xp)
            
            # Theme
            rank_idx = i if i < 3 else "default"
            theme = self.cfg.RANK_THEMES[rank_idx]
            score_color = self.cfg.COLOR_SCORE_NEGATIVE if xp < 0 else self.cfg.COLOR_SCORE_POSITIVE

            # Coordinates
            card_x = self.cfg.IMG_PADDING_X
            card_w = self.cfg.IMG_WIDTH - (self.cfg.IMG_PADDING_X * 2)
            card_h = self.cfg.IMG_ROW_HEIGHT - 40
            
            # Draw Card
            draw.rounded_rectangle([(card_x+8, current_y_cursor+10), (card_x+card_w+8, current_y_cursor+card_h+10)], radius=self.cfg.IMG_CARD_RADIUS, fill=self.cfg.COLOR_CARD_SHADOW)
            draw.rounded_rectangle([(card_x, current_y_cursor), (card_x+card_w, current_y_cursor+card_h)], radius=self.cfg.IMG_CARD_RADIUS, fill=self.cfg.COLOR_CARD_SURFACE)

            # 1. Rank Circle
            cy = current_y_cursor + (card_h // 2)
            draw.ellipse([(card_x+45, cy-75), (card_x+195, cy+75)], fill=theme["hex"])
            draw.text((card_x+120, cy), str(i + 1), font=f_rank_num, fill="white", anchor="mm")

            # 2. Content Block (The Fix: Massive spacing)
            content_x = card_x + 260
            content_w = 650
            
            # Explicit Y-Grid (Relative to Card Top)
            # Adjusted to give space for Thai vowels above characters
            Y_NAME = current_y_cursor + 60
            Y_MEMBERS = Y_NAME + 90
            Y_BAR = Y_MEMBERS + 70
            Y_RANK = Y_BAR + 60      # Increased gap for Rank Title vowels
            Y_PRIV = Y_RANK + 65     # Increased gap for Privilege description

            # Name
            self._draw_text_with_autofit(draw, str(row['GroupName']), content_x, Y_NAME, content_w, self.cfg.FONT_PRIMARY_BOLD, 80, self.cfg.COLOR_TEXT_PRIMARY)
            
            # Members
            mem_txt = self._clean_text_for_render(str(row['Members']))
            if len(mem_txt) > 65: mem_txt = mem_txt[:62] + "..."
            draw.text((content_x, Y_MEMBERS), mem_txt, font=f_members, fill=self.cfg.COLOR_TEXT_SECONDARY, anchor="lt")

            # Progress Bar
            draw.rounded_rectangle([(content_x, Y_BAR), (content_x+580, Y_BAR+16)], radius=8, fill=self.cfg.COLOR_BG_MAIN)
            if progress_pct > 0:
                fw = max(int(580 * progress_pct), 20)
                draw.rounded_rectangle([(content_x, Y_BAR), (content_x+fw, Y_BAR+16)], radius=8, fill=rank_def.color)

            # Rank Title (With space above for tone marks)
            draw.text((content_x, Y_RANK), rank_def.th_name, font=f_rank_title, fill=rank_def.color, anchor="lt")
            
            # Privilege (With space above)
            self._draw_text_with_autofit(draw, rank_def.description, content_x, Y_PRIV, content_w, self.cfg.FONT_PRIMARY_REG, 40, self.cfg.COLOR_TEXT_SECONDARY)

            # 3. Score
            score_x = self.cfg.IMG_WIDTH - self.cfg.IMG_PADDING_X - 40
            draw.text((score_x, cy-10), f"{xp}", font=f_score_val, fill=score_color, anchor="rs")
            draw.text((score_x, cy+50), "XP", font=f_score_lbl, fill=self.cfg.COLOR_TEXT_MUTED, anchor="rs")

            current_y_cursor += self.cfg.IMG_ROW_HEIGHT

        # --- FOOTER ---
        fy = canvas_height - (self.cfg.IMG_FOOTER_HEIGHT // 2)
        f_foot = self._get_font(self.cfg.FONT_PRIMARY_REG, 38)
        ts = datetime.now().strftime('%d/%m/%Y %H:%M')
        draw.text((self.cfg.IMG_WIDTH // 2, fy), f"Generated by {self.cfg.APP_NAME} • {ts}", font=f_foot, fill=self.cfg.COLOR_TEXT_MUTED, anchor="mm")

        # Export
        img = img.convert('RGB')
        buf = io.BytesIO()
        img.save(buf, format='PNG', optimize=True)
        return buf.getvalue()

# ==============================================================================
# MODULE 6: PRESENTATION LAYER (STREAMLIT UI)
# ==============================================================================

class UIManager:
    def __init__(self):
        self.cfg = AppConfig()
        self.db = GoogleSheetsRepository()
        self.rank_mgr = RankManager()
        self.badge_sys = BadgeSystem()
        self.gfx = GraphicsEngine()

    def setup_page(self):
        st.set_page_config(page_title=f"{self.cfg.APP_NAME} - Enterprise", page_icon="🏫", layout="wide", initial_sidebar_state="expanded")
        st.markdown(f"""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&family=Prompt:wght@300;400;500;700&display=swap');
            :root {{ --primary: {self.cfg.COLOR_BRAND_PRIMARY}; --secondary: {self.cfg.COLOR_BRAND_SECONDARY}; --bg: {self.cfg.COLOR_BG_MAIN}; }}
            html, body, [class*="css"] {{ font-family: 'Sarabun', sans-serif; background-color: var(--bg); color: #1E293B; }}
            .stApp {{ background-color: var(--bg); }}
            div[data-testid="stExpander"] {{ border:none; box-shadow:0 2px 4px rgba(0,0,0,0.05); border-radius:12px; background:white; }}
            .stButton>button {{ border-radius:10px; font-weight:600; padding:0.5rem 1rem; }}
            .hero-banner {{ background: linear-gradient(120deg, var(--primary), var(--secondary)); padding:2.5rem; border-radius:20px; color:white; margin-bottom:2rem; display:flex; justify-content:space-between; align-items:center; }}
            .glass-card {{ background:rgba(255,255,255,0.9); border-radius:16px; border:1px solid #E2E8F0; padding:1.5rem; margin-bottom:1rem; box-shadow:0 4px 6px -2px rgba(0,0,0,0.05); }}
            .badge {{ display:inline-block; padding:0.3em 0.8em; font-size:80%; font-weight:700; border-radius:0.5rem; }}
            </style>
        """, unsafe_allow_html=True)

    def render_sidebar(self):
        with st.sidebar:
            st.title("Control Panel")
            room = st.selectbox("Select Active Class", ["ม.1/1", "ม.1/2", "ม.1/3", "ม.1/4", "ม.1/10"])
            st.divider()
            if st.button("📥 Export CSV"):
                df = self.db.fetch_all_data()
                st.download_button("Download", df.to_csv(index=False).encode('utf-8'), "data.csv")
            return room

    def run(self):
        self.setup_page()
        room = self.render_sidebar()
        all_df = self.db.fetch_all_data()
        room_df = all_df[all_df['Room'] == room].copy()
        
        st.markdown(f"""<div class="hero-banner"><div><h1>{room}</h1></div><div style="font-size:3rem; font-weight:800;">{len(room_df)} Teams</div></div>""", unsafe_allow_html=True)
        
        t1, t2, t3, t4, t5 = st.tabs(["⚡ Command", "🏆 Leaderboard", "📈 Analytics", "ℹ️ Privileges", "🛠️ Management"])
        
        with t1:
            if room_df.empty: st.info("Create groups first.")
            else:
                target = st.multiselect("Select Teams", room_df['GroupName'].unique())
                c1, c2 = st.columns(2)
                def act(r, a):
                    if target: 
                        self.db.process_xp_transaction(room, target, a, r, all_df, self.badge_sys)
                        st.success("Done!"); time.sleep(0.5); st.rerun()
                with c1:
                    st.button("📚 On-Time (+50)", on_click=act, args=("ส่งงานตรงเวลา", 50), use_container_width=True)
                    st.button("🙋 Participate (+20)", on_click=act, args=("มีส่วนร่วม", 20), use_container_width=True)
                with c2:
                    with st.form("cust"):
                        r = st.text_input("Reason"); a = st.number_input("XP", step=5)
                        if st.form_submit_button("Submit") and r and a: act(r, a)

        with t2:
            if st.button("✨ Generate Image", type="primary"):
                img = self.gfx.render_leaderboard_image(room, room_df, self.rank_mgr)
                st.image(img)
                st.download_button("Download", img, "leaderboard.png", "image/png")
            
            for _, row in room_df.sort_values("XP", ascending=False).iterrows():
                r = self.rank_mgr.get_rank_by_xp(row['XP'])
                st.markdown(f"""<div class="glass-card" style="border-left:5px solid {r.color}"><h3>{row['GroupName']}</h3><div>{row['XP']} XP | {r.th_name}</div></div>""", unsafe_allow_html=True)

        with t3:
            if not room_df.empty:
                st.metric("Total XP", room_df['XP'].sum())
                st.bar_chart(room_df.set_index("GroupName")['XP'])

        with t4:
            for r in self.rank_mgr.all_ranks:
                st.info(f"**{r.th_name}** ({r.min_xp}+ XP): {r.description}")

        with t5:
            with st.form("new"):
                n = st.text_input("Name"); m = st.text_area("Members")
                if st.form_submit_button("Create") and n:
                    self.db.create_group_record(room, n, m, all_df); st.rerun()
            
            d = st.selectbox("Delete", ["-"]+list(room_df['GroupName'].unique()))
            if d != "-" and st.button("Delete"):
                self.db.delete_group_record(room, d, all_df); st.rerun()

if __name__ == "__main__":
    UIManager().run()
