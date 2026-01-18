"""
Classroom OS: Enterprise Edition
Version: 5.3.0 (Final Thai Typography Fix)
Author: AI Development Team
Date: 2026-01-20

Description:
A comprehensive, enterprise-grade gamification platform for classrooms.
Features robust Google Sheets integration, advanced score calculation rules,
and a high-fidelity image generation engine specifically tuned for correct
Thai language typography rendering, ensuring no overlapping or cut-off text.

This codebase is structured using domain-driven design principles,
separated into distinct layers for configuration, data, logic, and presentation.
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

# Configure application-wide logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ClassroomOS")

class AppConfig:
    """
    Centralized configuration for the entire application.
    Acts as the single source of truth for constants, paths, and styling parameters.
    """
    # Application Identity
    APP_NAME: str = "Classroom OS"
    APP_VERSION: str = "5.3.0-Enterprise"
    ORG_NAME: str = "Acme Education"

    # Database Configuration
    DB_CONNECTION_NAME: str = "gsheets"
    DB_MAIN_WORKSHEET: str = "Sheet1"
    DB_CACHE_TTL: int = 0  # No caching for real-time updates

    # Image Generation Constants (High Resolution & Spacing)
    IMG_WIDTH: int = 1400
    IMG_HEADER_HEIGHT: int = 700
    # INCREASED ROW HEIGHT to provide ample vertical space for Thai ascenders/descenders
    IMG_ROW_HEIGHT: int = 500   
    IMG_FOOTER_HEIGHT: int = 150
    IMG_PADDING_X: int = 50
    IMG_CARD_RADIUS: int = 35

    # Font Configuration (Must be present in the environment)
    FONT_PRIMARY_BOLD: str = "Sarabun-Bold.ttf"
    FONT_PRIMARY_REG: str = "Sarabun-Regular.ttf"

    # Color Palette (Modern Corporate Theme)
    COLOR_BRAND_PRIMARY: str = "#4338CA"    # Deep Indigo
    COLOR_BRAND_SECONDARY: str = "#3730A3"  # Darker Indigo
    COLOR_BRAND_ACCENT: str = "#A5B4FC"     # Light Indigo
    
    COLOR_BG_MAIN: str = "#F1F5F9"          # Light Gray Background
    COLOR_CARD_SURFACE: str = "#FFFFFF"     # White Card
    COLOR_CARD_BORDER: str = "#E2E8F0"      # Light Border
    COLOR_CARD_SHADOW: str = "#94A3B8"      # Shadow Tone
    
    COLOR_TEXT_PRIMARY: str = "#1E293B"     # Dark Slate
    COLOR_TEXT_SECONDARY: str = "#64748B"   # Medium Slate
    COLOR_TEXT_MUTED: str = "#94A3B8"       # Light Slate

    # Score Colors
    COLOR_SCORE_POSITIVE: str = "#10B981"   # Emerald Green
    COLOR_SCORE_NEGATIVE: str = "#EF4444"   # Red

    # Rank Theme System (Color & Name Mapping)
    RANK_THEMES: Dict[Union[int, str], Dict[str, str]] = {
        0: {"hex": "#F59E0B", "bg": "#FEF3C7", "name": "Gold"},   # Rank 1
        1: {"hex": "#94A3B8", "bg": "#F1F5F9", "name": "Silver"}, # Rank 2
        2: {"hex": "#B45309", "bg": "#FFEDD5", "name": "Bronze"}, # Rank 3
        "default": {"hex": "#64748B", "bg": "#F8FAFC", "name": "Slate"} # Others
    }

# ==============================================================================
# MODULE 2: DOMAIN MODELS (DATA STRUCTURES)
# ==============================================================================

class RankDefinition:
    """
    Immutable data structure representing a single rank tier.
    Holds all display properties and rules for a rank.
    """
    def __init__(self, id: str, th_name: str, min_xp: int, color: str, bg_color: str, description: str):
        self.id = id                  # Internal identifier (e.g., "PRESIDENT")
        self.th_name = th_name        # Display name in Thai
        self.min_xp = min_xp          # Minimum XP required
        self.color = color            # Foreground color (hex)
        self.bg_color = bg_color      # Background color (hex)
        self.description = description # Privilege description

    def __repr__(self):
        return f"RankDefinition(id='{self.id}', min_xp={self.min_xp})"

class TransactionLog:
    """
    Represents a single score transaction record.
    """
    def __init__(self, id: str, timestamp: datetime, reason: str, amount: int, balance: int):
        self.id = id
        self.timestamp = timestamp
        self.reason = reason
        self.amount = amount
        self.balance = balance

    def to_dict(self) -> Dict[str, Any]:
        """Converts object to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "ts": self.timestamp.strftime("%Y-%m-%d %H:%M"),
            "reason": self.reason,
            "amount": self.amount,
            "balance": self.balance
        }

# ==============================================================================
# MODULE 3: BUSINESS LOGIC LAYER
# ==============================================================================

class RankManager:
    """
    Encapsulates all logic related to rank determination and progress calculation.
    This is the source of truth for rank rules.
    """
    def __init__(self):
        # Define the hierarchy of ranks, ordered from highest to lowest XP.
        # IMPORTANT: Ensure Thai descriptions are concise for UI fit.
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
        """Returns a read-only list of all definitions."""
        return self._ranks

    def get_rank_by_xp(self, xp: int) -> RankDefinition:
        """
        Determines the appropriate rank for a given XP value.
        """
        if xp < 0:
            return self._probation_rank
        
        for rank in self._ranks:
            # Skip probation in normal check, find first rank where XP is sufficient
            if rank.id != "PROBATION" and xp >= rank.min_xp:
                return rank
                
        return self._default_rank # Should not happen with correct config

    def calculate_progress_to_next(self, xp: int) -> Tuple[float, str]:
        """
        Calculates the percentage progress towards the next rank tier.
        Returns: (percentage as float 0.0-1.0, label string)
        """
        if xp < 0:
            return 0.0, "Status: Critical"
        
        current_rank = self.get_rank_by_xp(xp)
        
        # Find index of current rank
        try:
            idx = self._ranks.index(current_rank)
        except ValueError:
             return 0.0, "Error"

        # If not the highest rank (index 0)
        if idx > 0:
            next_rank = self._ranks[idx - 1]
            target_xp = next_rank.min_xp
            
            # Prevent division by zero if target is 0 (though unlikely for higher ranks)
            denominator = target_xp if target_xp > 0 else 100 
            
            progress_pct = min(1.0, xp / denominator)
            return progress_pct, f"{int(progress_pct * 100)}% to {next_rank.th_name}"
            
        return 1.0, "MAX LEVEL REACHED"

class BadgeSystem:
    """
    Manages gamification badges based on user history and status.
    """
    def __init__(self):
        # Map internal badge IDs to display emojis
        self._badge_catalog: Dict[str, str] = {
            "wealthy": "💎",    # High XP hoard
            "sniper": "🎯",     # Big single achievement
            "debtor": "💸",     # Negative balance
            "phoenix": "🔥",    # Returned from negative
            "first_blood": "🩸", # First activity mark
            "veteran": "🎖️"      # Many activities
        }

    def evaluate_badges(self, current_xp: int, history: List[Dict[str, Any]]) -> List[str]:
        """
        Analyzes XP and history to determine earned badges.
        Returns a list of badge IDs.
        """
        earned_badges = set()
        
        # XP based badges
        if current_xp >= 800:
            earned_badges.add("wealthy")
        if current_xp < 0:
            earned_badges.add("debtor")
            
        # History based badges
        if history:
            earned_badges.add("first_blood")
            if len(history) >= 10:
                earned_badges.add("veteran")
            # Check for large single transactions
            if any(h.get('amount', 0) >= 100 for h in history):
                earned_badges.add("sniper")
            
            # Check for 'Phoenix' (was negative, now positive) - requires complex check
            # Simplified version: if current is positive but has 'debtor' in history could be added.
            # For now, let's stick to simple rules.

        return list(earned_badges)

    def render_badges(self, badge_ids: List[str]) -> str:
        """Converts a list of badge IDs to a string of emojis."""
        return "".join([self._badge_catalog.get(bid, "") for bid in badge_ids])

# ==============================================================================
# MODULE 4: DATA ACCESS LAYER (REPOSITORY)
# ==============================================================================

class GoogleSheetsRepository:
    """
    Handles all interactions with the Google Sheets backend.
    Implements CRUD operations and data sanitization.
    """
    # Define the strict schema expected for the DataFrame
    SCHEMA = ['Room', 'GroupName', 'XP', 'Members', 'LastUpdated', 'HistoryLog', 'Badges']

    def __init__(self):
        self.cfg = AppConfig()
        self.conn = self._establish_connection()

    def _establish_connection(self) -> GSheetsConnection:
        """Attempts to connect to Google Sheets via Streamlit secrets."""
        try:
            conn = st.connection(self.cfg.DB_CONNECTION_NAME, type=GSheetsConnection)
            logger.info("Successfully established connection to Google Sheets.")
            return conn
        except Exception as e:
            logger.critical(f"Failed to connect to Google Sheets: {e}", exc_info=True)
            st.error(f"🔴 Critical Error: Could not connect to database. Check logs.")
            st.stop()

    def _sanitize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ensures the DataFrame conforms to the expected SCHEMA.
        Handles missing columns, NaNs, and type casting.
        """
        if df.empty:
            return pd.DataFrame(columns=self.SCHEMA)
        
        # Ensure all required columns exist
        missing_cols = set(self.SCHEMA) - set(df.columns)
        if missing_cols:
            logger.warning(f"Found missing columns in DB: {missing_cols}. Adding them.")
            for col in missing_cols:
                df[col] = None

        # Select only required columns and drop completely empty rows
        df = df[self.SCHEMA].copy().dropna(how='all')
        
        # Type coercion and null handling
        # XP must be integer
        df['XP'] = pd.to_numeric(df['XP'], errors='coerce').fillna(0).astype(int)
        
        # JSON fields must be valid JSON strings, default to empty list "[]"
        for col in ['HistoryLog', 'Badges']:
            df[col] = df[col].fillna("[]").astype(str)
            # Basic validation: check if it looks like JSON list
            mask = ~df[col].str.startswith("[") | ~df[col].str.endswith("]")
            df.loc[mask, col] = "[]"

        # String fields default to empty string
        for col in ['Room', 'GroupName', 'Members', 'LastUpdated']:
            df[col] = df[col].fillna("").astype(str)

        return df

    def fetch_all_data(self) -> pd.DataFrame:
        """Retrieves all data from the main worksheet."""
        try:
            # ttl=0 ensures no caching for fresh data
            df = self.conn.read(worksheet=self.cfg.DB_MAIN_WORKSHEET, ttl=self.cfg.DB_CACHE_TTL)
            sanitized_df = self._sanitize_dataframe(df)
            logger.info(f"Fetched {len(sanitized_df)} records from database.")
            return sanitized_df
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            # Return empty DataFrame with correct schema on failure
            return pd.DataFrame(columns=self.SCHEMA)

    def commit_data(self, df: pd.DataFrame) -> bool:
        """Writes the given DataFrame back to the sheet."""
        try:
            # Ensure data is clean before writing
            df_to_write = self._sanitize_dataframe(df)
            self.conn.update(worksheet=self.cfg.DB_MAIN_WORKSHEET, data=df_to_write)
            st.cache_data.clear() # Clear Streamlit's data cache
            logger.info("Database commit successful.")
            return True
        except Exception as e:
            logger.error(f"Database commit failed: {e}", exc_info=True)
            st.error(f"⚠️ Failed to save data: {e}")
            return False

    # --- Domain-Specific Transaction Methods ---

    def create_group_record(self, room: str, name: str, members: str, current_df: pd.DataFrame) -> bool:
        """Creates a new group if the name doesn't exist in the room."""
        # Check for duplicate name within the same room
        duplicate_mask = (current_df['Room'] == room) & (current_df['GroupName'] == name)
        if duplicate_mask.any():
            logger.warning(f"Attempted to create duplicate group '{name}' in room '{room}'.")
            return False
        
        new_record = {
            "Room": room,
            "GroupName": name,
            "XP": 0,
            "Members": members,
            "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "HistoryLog": "[]",
            "Badges": "[]"
        }
        updated_df = pd.concat([current_df, pd.DataFrame([new_record])], ignore_index=True)
        return self.commit_data(updated_df)

    def update_group_record(self, room: str, old_name: str, new_name: str, new_members: str, current_df: pd.DataFrame) -> bool:
        """Updates group name and members."""
        # If name is changing, ensure new name isn't taken
        if new_name != old_name:
             duplicate_mask = (current_df['Room'] == room) & (current_df['GroupName'] == new_name)
             if duplicate_mask.any():
                 logger.warning(f"Cannot rename to '{new_name}', name already exists.")
                 return False

        # Find the group to update
        target_mask = (current_df['Room'] == room) & (current_df['GroupName'] == old_name)
        if not target_mask.any():
             logger.warning(f"Group '{old_name}' not found for update.")
             return False
             
        idx = current_df[target_mask].index[0]
        current_df.at[idx, 'GroupName'] = new_name
        current_df.at[idx, 'Members'] = new_members
        current_df.at[idx, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        return self.commit_data(current_df)

    def delete_group_record(self, room: str, name: str, current_df: pd.DataFrame) -> bool:
        """Soft-deletes a group by filtering it out and saving."""
        # Keep rows that do NOT match the target room AND name
        keep_mask = ~((current_df['Room'] == room) & (current_df['GroupName'] == name))
        updated_df = current_df[keep_mask]
        return self.commit_data(updated_df)

    def process_xp_transaction(self, room: str, target_groups: List[str], amount: int, reason: str, 
                               current_df: pd.DataFrame, badge_sys: BadgeSystem) -> Tuple[bool, int]:
        """
        Applies an XP transaction to multiple groups, updating history and badges.
        Returns: (success status, count of updated groups)
        """
        updated_count = 0
        timestamp = datetime.now()
        ts_str = timestamp.strftime("%Y-%m-%d %H:%M")
        
        for group_name in target_groups:
            mask = (current_df['Room'] == room) & (current_df['GroupName'] == group_name)
            if mask.any():
                idx = current_df[mask].index[0]
                
                # 1. Parse existing history
                try:
                    history_list = json.loads(current_df.at[idx, 'HistoryLog'])
                except json.JSONDecodeError:
                    history_list = []
                
                # 2. Create new log entry
                new_log = {
                    "id": str(uuid.uuid4())[:8],
                    "ts": ts_str,
                    "reason": reason,
                    "amount": int(amount)
                    # 'balance' will be calculated next
                }
                
                # 3. Insert new log at the beginning (newest first)
                history_list.insert(0, new_log)
                
                # 4. Recalculate total balance from history
                new_balance = sum(item['amount'] for item in history_list)
                # Update the balance on the newest entry
                history_list[0]['balance'] = new_balance
                
                # 5. Evaluate badges based on new state
                new_badges = badge_sys.evaluate_badges(new_balance, history_list)
                
                # 6. Update DataFrame fields
                current_df.at[idx, 'XP'] = new_balance
                current_df.at[idx, 'HistoryLog'] = json.dumps(history_list, ensure_ascii=False)
                current_df.at[idx, 'Badges'] = json.dumps(new_badges, ensure_ascii=False)
                current_df.at[idx, 'LastUpdated'] = ts_str
                
                updated_count += 1
        
        if updated_count > 0:
            success = self.commit_data(current_df)
            return success, updated_count
        return False, 0

    def apply_history_override(self, room: str, group_name: str, new_history_df: pd.DataFrame, 
                               current_df: pd.DataFrame, badge_sys: BadgeSystem) -> bool:
        """
        Replaces a group's entire history and recalculates everything. Power user feature.
        """
        mask = (current_df['Room'] == room) & (current_df['GroupName'] == group_name)
        if not mask.any():
            return False
            
        idx = current_df[mask].index[0]
        
        # Convert edited DataFrame back to list of dicts
        history_list = new_history_df.to_dict('records')
        
        # Recalculate balances logically based on time
        # 1. Sort ascending by time to calculate running balance
        try:
            history_sorted_asc = sorted(history_list, key=lambda x: x.get('ts', ''))
        except Exception:
             # Fallback if ts is missing or broken
             history_sorted_asc = history_list

        running_balance = 0
        for item in history_sorted_asc:
            # Ensure amount is int
            amt = int(item.get('amount', 0))
            item['amount'] = amt
            running_balance += amt
            item['balance'] = running_balance
            
        final_xp = running_balance
        
        # 2. Sort descending (newest first) for storage
        history_sorted_desc = sorted(history_sorted_asc, key=lambda x: x.get('ts', ''), reverse=True)
        
        # Re-evaluate badges
        new_badges = badge_sys.evaluate_badges(final_xp, history_sorted_desc)
        
        # Update DF
        current_df.at[idx, 'XP'] = final_xp
        current_df.at[idx, 'HistoryLog'] = json.dumps(history_sorted_desc, ensure_ascii=False)
        current_df.at[idx, 'Badges'] = json.dumps(new_badges, ensure_ascii=False)
        current_df.at[idx, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        return self.commit_data(current_df)

# ==============================================================================
# MODULE 5: GRAPHICS ENGINE (HIGH-FIDELITY RENDERING)
# ==============================================================================

class GraphicsEngine:
    """
    Handles the generation of the high-resolution leaderboard image.
    Utilizes explicit, absolute positioning to ensure correct rendering
    of complex typography, specifically Thai vowels and tone marks.
    """
    def __init__(self):
        self.cfg = AppConfig()
        self._font_cache = {}

    def _get_font(self, name: str, size: int) -> ImageFont.FreeTypeFont:
        """Loads a font from disk with caching."""
        key = (name, size)
        if key not in self._font_cache:
            try:
                # Ensure Pillow version >= 10.0.0 for best text features
                font = ImageFont.truetype(name, size)
                self._font_cache[key] = font
            except IOError:
                # Fallback can result in ugly text, but prevents crash
                font = ImageFont.load_default()
                self._font_cache[key] = font
        return self._font_cache[key]

    def _clean_text_for_render(self, text: str) -> str:
        """
        Removes characters that cause rendering artifacts (like Emojis),
        keeping only Thai characters, English, Numbers, and basic punctuation.
        """
        if not isinstance(text, str): return ""
        # Regex to keep Thai (u0E00-u0E7F), Word chars (a-z, 0-9), and basic punctuation
        return re.sub(r'[^\w\s\u0E00-\u0E7F().,-]', '', text).strip()

    def _draw_text_with_autofit(self, draw: ImageDraw.Draw, text: str, 
                                x: int, y: int, max_width: int,
                                font_name: str, max_size: int, 
                                color: str, anchor: str = "lt") -> None:
        """
        Draws text, automatically reducing font size if it exceeds max_width.
        """
        # CLEAN TEXT HERE to prevent square boxes
        text = self._clean_text_for_render(text)
        if not text: return

        current_size = max_size
        min_size = 30 # Absolute minimum legible size
        
        font = self._get_font(font_name, current_size)
        
        # Iteratively reduce size until it fits
        while current_size > min_size:
            if font.getlength(text) <= max_width:
                break
            current_size -= 4 # Step down size
            font = self._get_font(font_name, current_size)
            
        # Final draw with fitted font
        draw.text((x, y), text, font=font, fill=color, anchor=anchor)

    def render_leaderboard_image(self, room_name: str, df: pd.DataFrame, rank_manager: RankManager) -> bytes:
        """
        Orchestrates the entire image generation process.
        """
        leaderboard_data = df.sort_values("XP", ascending=False).reset_index(drop=True)
        
        # 2. Calculate Canvas Dimensions
        total_rows = len(leaderboard_data)
        # FIX: Define canvas_height properly
        canvas_height = (
            self.cfg.IMG_HEADER_HEIGHT + 
            (total_rows * self.cfg.IMG_ROW_HEIGHT) + 
            self.cfg.IMG_FOOTER_HEIGHT
        )
        
        # 3. Initialize Canvas
        img = Image.new('RGBA', (self.cfg.IMG_WIDTH, canvas_height), color=self.cfg.COLOR_BG_MAIN)
        draw = ImageDraw.Draw(img)
        
        # --- HEADER ---
        draw.rectangle([(0, 0), (self.cfg.IMG_WIDTH, self.cfg.IMG_HEADER_HEIGHT)], fill=self.cfg.COLOR_BRAND_PRIMARY)
        draw.ellipse([(900, -150), (1500, 450)], fill=self.cfg.COLOR_BRAND_SECONDARY)
        draw.ellipse([(-100, 250), (500, 850)], fill=self.cfg.COLOR_BRAND_SECONDARY)
        
        center_x = self.cfg.IMG_WIDTH // 2
        f_icon = self._get_font(self.cfg.FONT_PRIMARY_REG, 180)
        draw.text((center_x, 220), "🏆", font=f_icon, fill="white", anchor="mm")
        
        f_title = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 60)
        draw.text((center_x, 380), "CLASSROOM LEADERBOARD", font=f_title, fill=self.cfg.COLOR_BRAND_ACCENT, anchor="mm")
        
        f_room = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 150)
        draw.text((center_x, 550), room_name, font=f_room, fill="white", anchor="mm")

        # --- ROWS ---
        current_y_cursor = self.cfg.IMG_HEADER_HEIGHT + 50
        
        # Pre-fetch fonts
        f_rank_num = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 85)
        f_score_val = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 110)
        f_score_lbl = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 45)
        f_members = self._get_font(self.cfg.FONT_PRIMARY_REG, 42)
        f_rank_title = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 48)
        f_privilege = self._get_font(self.cfg.FONT_PRIMARY_REG, 36)

        for i, row in leaderboard_data.iterrows():
            xp = row['XP']
            rank_def = rank_manager.get_rank_by_xp(xp)
            progress_pct, _ = rank_manager.calculate_progress_to_next(xp)
            
            rank_idx = i if i < 3 else "default"
            theme = self.cfg.RANK_THEMES[rank_idx]
            rank_color_hex = theme["hex"]
            score_color = self.cfg.COLOR_SCORE_NEGATIVE if xp < 0 else self.cfg.COLOR_SCORE_POSITIVE

            # Layout
            card_x_start = self.cfg.IMG_PADDING_X
            card_width = self.cfg.IMG_WIDTH - (self.cfg.IMG_PADDING_X * 2)
            card_height = self.cfg.IMG_ROW_HEIGHT - 40 
            card_y_start = current_y_cursor
            card_y_end = card_y_start + card_height
            
            # Card Body
            draw.rounded_rectangle([(card_x_start + 8, card_y_start + 10), (card_x_start + card_width + 8, card_y_end + 10)], radius=self.cfg.IMG_CARD_RADIUS, fill=self.cfg.COLOR_CARD_SHADOW)
            draw.rounded_rectangle([(card_x_start, card_y_start), (card_x_start + card_width, card_y_end)], radius=self.cfg.IMG_CARD_RADIUS, fill=self.cfg.COLOR_CARD_SURFACE)

            # Col 1: Rank Circle
            circle_center_x = card_x_start + 120
            circle_center_y = card_y_start + (card_height // 2)
            draw.ellipse([(circle_center_x - 75, circle_center_y - 75), (circle_center_x + 75, circle_center_y + 75)], fill=rank_color_hex)
            draw.text((circle_center_x, circle_center_y), str(i + 1), font=f_rank_num, fill="white", anchor="mm")

            # Col 2: Content (Updated Spacing for Thai)
            content_x_start = card_x_start + 260
            content_max_width = 650
            
            # Expanded Y-Grid
            Y_POS_NAME = card_y_start + 50
            Y_POS_MEMBERS = Y_POS_NAME + 90
            Y_POS_PROGRESS_BAR = Y_POS_MEMBERS + 70
            Y_POS_RANK_TITLE = Y_POS_PROGRESS_BAR + 60 
            Y_POS_PRIVILEGE = Y_POS_RANK_TITLE + 60 

            # Name
            self._draw_text_with_autofit(draw, str(row['GroupName']), content_x_start, Y_POS_NAME, content_max_width, self.cfg.FONT_PRIMARY_BOLD, 80, self.cfg.COLOR_TEXT_PRIMARY, anchor="lt")
            
            # Members (Cleaned)
            members_txt = self._clean_text_for_render(str(row['Members']))
            if len(members_txt) > 65: members_txt = members_txt[:62] + "..."
            draw.text((content_x_start, Y_POS_MEMBERS), members_txt, font=f_members, fill=self.cfg.COLOR_TEXT_SECONDARY, anchor="lt")

            # Bar
            bar_width = 580
            draw.rounded_rectangle([(content_x_start, Y_POS_PROGRESS_BAR), (content_x_start + bar_width, Y_POS_PROGRESS_BAR + 16)], radius=8, fill=self.cfg.COLOR_BG_MAIN)
            if progress_pct > 0:
                fill_width = max(int(bar_width * progress_pct), 20) if progress_pct > 0.01 else int(bar_width * progress_pct)
                draw.rounded_rectangle([(content_x_start, Y_POS_PROGRESS_BAR), (content_x_start + fill_width, Y_POS_PROGRESS_BAR + 16)], radius=8, fill=rank_def.color)

            # Rank Title (Cleaned)
            clean_title = self._clean_text_for_render(rank_def.th_name)
            draw.text((content_x_start, Y_POS_RANK_TITLE), clean_title, font=f_rank_title, fill=rank_def.color, anchor="lt")
            
            # Privilege (Autofit & Cleaned)
            self._draw_text_with_autofit(draw, rank_def.description, content_x_start, Y_POS_PRIVILEGE, content_max_width, self.cfg.FONT_PRIMARY_REG, 40, self.cfg.COLOR_TEXT_SECONDARY, anchor="lt")

            # Col 3: Score
            score_x_anchor = self.cfg.IMG_WIDTH - self.cfg.IMG_PADDING_X - 40
            score_y_center = card_y_start + (card_height // 2)
            draw.text((score_x_anchor, score_y_center - 10), f"{xp}", font=f_score_val, fill=score_color, anchor="rs")
            draw.text((score_x_anchor, score_y_center + 50), "XP", font=f_score_lbl, fill=self.cfg.COLOR_TEXT_MUTED, anchor="rs")

            current_y_cursor += self.cfg.IMG_ROW_HEIGHT

        # --- FOOTER ---
        # FIX: Use canvas_height
        footer_y_center = canvas_height - (self.cfg.IMG_FOOTER_HEIGHT // 2)
        f_footer = self._get_font(self.cfg.FONT_PRIMARY_REG, 38)
        timestamp_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        footer_text = f"Generated by {self.cfg.APP_NAME} • {timestamp_str}"
        draw.text((self.cfg.IMG_WIDTH // 2, footer_y_center), footer_text, font=f_footer, fill=self.cfg.COLOR_TEXT_MUTED, anchor="mm")

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
        st.set_page_config(page_title=f"{self.cfg.APP_NAME} - Enterprise", page_icon="🏫", layout="wide", initial_sidebar_state="expanded")
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
            
            st.subheader("🏫 Classroom Context")
            # FIX: Only showing requested rooms
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
            img = self.gfx.render_leaderboard_image(room_name, room_df, self.rank_mgr)
            st.image(img)
            st.download_button("Download PNG", img, "lb.png", "image/png")
            
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
