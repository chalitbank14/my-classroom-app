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

    # Image Generation Constants
    IMG_WIDTH: int = 1400
    IMG_HEADER_HEIGHT: int = 700
    # แก้ไข: ลดความสูงแถวลงเหลือ 550 เพื่อให้การ์ดกระชับขึ้น
    IMG_ROW_HEIGHT: int = 550
    IMG_FOOTER_HEIGHT: int = 150
    IMG_PADDING_X: int = 50
    IMG_CARD_RADIUS: int = 35

    # Font Configuration (Must be present in the environment)
    FONT_PRIMARY_BOLD: str = "Sarabun-Bold.ttf"
    FONT_PRIMARY_REG: str = "Sarabun-Regular.ttf"

    # Color Palette (Modern Corporate Theme)
    COLOR_BRAND_PRIMARY: str = "#4338CA"
    COLOR_BRAND_SECONDARY: str = "#3730A3"
    COLOR_BRAND_ACCENT: str = "#A5B4FC"
    
    # แก้ไข: เปลี่ยนจาก COLOR_BG_MAIN เป็น COLOR_BACKGROUND ให้ตรงกับที่อื่นเรียกใช้
    COLOR_BACKGROUND: str = "#F1F5F9"      # Light Gray Background
    
    COLOR_CARD_SURFACE: str = "#FFFFFF"
    COLOR_CARD_BORDER: str = "#E2E8F0"
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
        # แก้ไข: ลบ Emoji ออกจากชื่อยศภาษาไทย เพื่อแก้ปัญหากรอบสี่เหลี่ยม
        self._ranks: List[RankDefinition] = [
            RankDefinition("PRESIDENT", "ประธานรุ่น", 1000, "#F59E0B", "#FEF3C7", "เลือกไม่ทํา 3 งาน ได้คะแนนเต็ม; +1 คะแนนพิเศษฟรีทุกงานที่ส่ง"),
            RankDefinition("DIRECTOR", "หัวหน้าฝ่าย", 600, "#8B5CF6", "#F3E8FF", "ลดภาระงาน 50% ทำงานครึ่งหนึ่งก็ได้คะแนนเต็มในทุกๆงาน"),
            RankDefinition("MANAGER", "หัวหน้าแผนก", 300, "#3B82F6", "#DBEAFE", "สอบแก้ตัวหรือทําใบงานใหม่เพื่อปรับคะแนนให้ดีขึ้น เลือกทําใหม่ได้ หน่วยละ 1 งาน"),
            RankDefinition("EMPLOYEE", "พนักงาน", 100, "#10B981", "#D1FAE5", "ส่งช้าได้สูงสุด 2 สัปดาห์ โดยไม่ถูกหักคะแนน ใช้ได้ทุกงานหลังกลางภาค"),
            RankDefinition("INTERN", "เด็กฝึกงาน", 0, "#64748B", "#F1F5F9", "ก่อนส่งใบงานสำคัญ นำให้ครู 'ตรวจทานเบื้องต้น วงจุดผิดให้กลับไปแก้ก่อนส่งจริง"),
            RankDefinition("PROBATION", "ทัณฑ์บน", -300, "#EF4444", "#FEE2E2", "ทํางานรูปแบบออฟไลน์, เขียนใส่กระดาษ, ส่งเฉพาะตอนเจอครูเท่านั้น")
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
        # แก้ไข: ต้องติดลบ 300 หรือต่ำกว่า ถึงจะได้ยศทัณฑ์บน
        if xp <= -300:
            return self._probation_rank
        
        for rank in self._ranks:
            if rank.id != "PROBATION" and xp >= rank.min_xp:
                return rank
                
        return self._default_rank # ถ้าคะแนน -1 ถึง -299 จะยังเป็น Intern (เด็กฝึกงาน)

    def calculate_progress_to_next(self, xp: int) -> Tuple[float, str]:
        """
        Calculates the percentage progress towards the next rank tier.
        """
        # ถ้าติดลบหนักเกิน -300 ให้ขึ้นสถานะ Critical
        if xp <= -300:
            return 0.0, "Status: Critical (Probation)"
        
        current_rank = self.get_rank_by_xp(xp)
        
        try:
            idx = self._ranks.index(current_rank)
        except ValueError:
             return 0.0, "Error"

        if idx > 0:
            next_rank = self._ranks[idx - 1]
            target_xp = next_rank.min_xp
            
            # แก้ไข: ถ้าคะแนนติดลบ (เช่น -200) แต่อยู่ยศ Intern (0) 
            # เราจะคำนวณเทียบกับ 0 ไม่ได้ ต้องจัดการให้หลอดเป็น 0% ไปเลย
            if xp < 0 and current_rank.min_xp == 0:
                 return 0.0, f"Recovering... ({xp} XP)"

            denominator = target_xp if target_xp > 0 else 100 
            
            # สูตรคำนวณปกติ
            raw_pct = xp / denominator
            
            # แก้ไข: บังคับค่าให้อยู่ระหว่าง 0.0 ถึง 1.0 เสมอ (กันกราฟพัง)
            progress_pct = max(0.0, min(1.0, raw_pct))
            
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
        Deep cleaning to prevent Google API 500 Errors.
        """
        if df.empty:
            return pd.DataFrame(columns=self.SCHEMA)
        
        # 1. Ensure all columns exist
        for col in self.SCHEMA:
            if col not in df.columns:
                df[col] = None

        # 2. Select only schema columns
        df = df[self.SCHEMA].copy()
        
        # 3. Clean Data Types (Aggressive)
        
        # XP: Must be pure Integer (No NaNs, No Floats)
        df['XP'] = pd.to_numeric(df['XP'], errors='coerce').fillna(0).astype(int)
        
        # JSON Fields: Must be valid strings, empty list if fail
        for col in ['HistoryLog', 'Badges']:
            df[col] = df[col].astype(str).replace(["None", "nan", "<NA>"], "[]")
            # ถ้าช่องว่างๆ ให้ใส่ []
            df.loc[df[col].str.strip() == "", col] = "[]"

        # Text Fields: Must be string, no NaNs
        for col in ['Room', 'GroupName', 'Members', 'LastUpdated']:
            df[col] = df[col].astype(str).replace(["None", "nan", "<NA>"], "")

        return df

    def fetch_all_data(self) -> pd.DataFrame:
        """Retrieves all data from the main worksheet."""
        try:
            # เพิ่ม Spinner เพื่อบอก user ว่ากำลังโหลด
            with st.spinner("กำลังเชื่อมต่อฐานข้อมูล Google Sheets..."):
                # ttl=0 ensures no caching for fresh data
                df = self.conn.read(worksheet=self.cfg.DB_MAIN_WORKSHEET, ttl=self.cfg.DB_CACHE_TTL)
                sanitized_df = self._sanitize_dataframe(df)
                logger.info(f"Fetched {len(sanitized_df)} records from database.")
                return sanitized_df
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return pd.DataFrame(columns=self.SCHEMA)

    def commit_data(self, df: pd.DataFrame) -> bool:
        """
        Writes the given DataFrame back to the sheet.
        Includes RETRY LOGIC to handle Google API 500 errors.
        """
        max_retries = 3
        
        # ทำความสะอาดข้อมูลรอบสุดท้ายก่อนส่ง
        df_to_write = self._sanitize_dataframe(df)
        
        for attempt in range(max_retries):
            try:
                # พยายามบันทึก
                self.conn.update(worksheet=self.cfg.DB_MAIN_WORKSHEET, data=df_to_write)
                st.cache_data.clear() # เคลียร์ cache เพื่อให้เห็นข้อมูลใหม่ทันที
                logger.info("Database commit successful.")
                return True
                
            except Exception as e:
                # ถ้าพัง ให้รอแป๊บแล้วลองใหม่ (Backoff strategy)
                wait_time = (attempt + 1) * 2
                logger.warning(f"Database commit failed (Attempt {attempt+1}/{max_retries}). Retrying in {wait_time}s... Error: {e}")
                time.sleep(wait_time)
                
                # ถ้าลองครบโควต้าแล้วยังพัง ให้แจ้งเตือน user
                if attempt == max_retries - 1:
                    logger.error(f"Final database commit failed: {e}", exc_info=True)
                    st.error(f"⚠️ Failed to save data (Google Server Error). Please try again in a moment. Details: {e}")
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
    
    # [CHECK] วางต่อจากฟังก์ชัน commit_data และต้องย่อหน้าให้เท่ากัน (4 เคาะ)
    
    def create_group_record(self, room: str, name: str, members: str, current_df: pd.DataFrame) -> bool:
        """Creates a new group if the name doesn't exist in the room."""
        # เช็คชื่อซ้ำในห้องเดียวกัน
        duplicate_mask = (current_df['Room'] == room) & (current_df['GroupName'] == name)
        if duplicate_mask.any():
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
        # ถ้าเปลี่ยนชื่อ ต้องเช็คว่าชื่อใหม่ซ้ำไหม
        if new_name != old_name:
             duplicate_mask = (current_df['Room'] == room) & (current_df['GroupName'] == new_name)
             if duplicate_mask.any():
                 return False

        # หาแถวที่จะแก้
        target_mask = (current_df['Room'] == room) & (current_df['GroupName'] == old_name)
        if not target_mask.any():
             return False
             
        idx = current_df[target_mask].index[0]
        current_df.at[idx, 'GroupName'] = new_name
        current_df.at[idx, 'Members'] = new_members
        current_df.at[idx, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        return self.commit_data(current_df)

    def delete_group_record(self, room: str, name: str, current_df: pd.DataFrame) -> bool:
        """Soft-deletes a group by filtering it out and saving."""
        # เก็บแถวที่ *ไม่ใช่* (ห้องนี้ และ ชื่อนี้) เอาไว้
        keep_mask = ~((current_df['Room'] == room) & (current_df['GroupName'] == name))
        updated_df = current_df[keep_mask]
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
        Applies an XP transaction to multiple groups using Atomic Batch strategy.
        Updates all groups in memory first, then performs a SINGLE database commit.
        """
        updated_count = 0
        timestamp = datetime.now()
        ts_str = timestamp.strftime("%Y-%m-%d %H:%M")
        
        # 1. วนลูปอัปเดตข้อมูลใน DataFrame (หน่วยความจำ) ให้ครบทุกกลุ่มก่อน
        for group_name in target_groups:
            # ค้นหาแถวที่ต้องการ
            mask = (current_df['Room'] == room) & (current_df['GroupName'] == group_name)
            
            if mask.any():
                idx = current_df[mask].index[0]
                
                # A. ดึงประวัติเก่า
                try:
                    history_list = json.loads(current_df.at[idx, 'HistoryLog'])
                except json.JSONDecodeError:
                    history_list = []
                
                # B. สร้าง Log ใหม่
                new_log = {
                    "id": str(uuid.uuid4())[:8],
                    "ts": ts_str,
                    "reason": reason,
                    "amount": int(amount)
                }
                
                # C. ใส่ Log ใหม่ไว้บนสุด
                history_list.insert(0, new_log)
                
                # D. คำนวณยอดรวมใหม่ (Re-calculate Balance)
                new_balance = sum(item['amount'] for item in history_list)
                history_list[0]['balance'] = new_balance
                
                # E. คำนวณเหรียญรางวัลใหม่
                new_badges = badge_sys.evaluate_badges(new_balance, history_list)
                
                # F. อัปเดตค่าลงใน DataFrame (ยังไม่บันทึกเข้า Google Sheets)
                current_df.at[idx, 'XP'] = new_balance
                current_df.at[idx, 'HistoryLog'] = json.dumps(history_list, ensure_ascii=False)
                current_df.at[idx, 'Badges'] = json.dumps(new_badges, ensure_ascii=False)
                current_df.at[idx, 'LastUpdated'] = ts_str
                
                updated_count += 1
        
        # 2. บันทึกครั้งเดียว (Atomic Commit) หลังจากคำนวณครบทุกกลุ่มแล้ว
        # ถ้าเน็ตหลุดก่อนถึงบรรทัดนี้ ข้อมูลจะไม่ถูกบันทึกเลย (ปลอดภัยกว่าบันทึกครึ่งๆ กลางๆ)
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
            except IOError as e:
                logger.error(f"Could not load font '{name}'. Falling back to default. Error: {e}")
                # Fallback can result in ugly text, but prevents crash
                font = ImageFont.load_default()
                self._font_cache[key] = font
        return self._font_cache[key]

    def _clean_text_for_render(self, text: str) -> str:
        """
        Prepares text for rendering by removing characters known to cause
        issues with PIL's standard font renderer (like complex emojis).
        Thai characters are preserved.
        """
        if not isinstance(text, str): return ""
        # Blocklist of problematic emoji ranges/characters
        # Note: Standard text & Thai characters are allowed.
        problematic_chars = ["👑", "💼", "👔", "👨‍💼", "👶", "⚠️", "🩸", "💎", "💸", "🎯", "🔥", "🏆"]
        cleaned = text
        for char in problematic_chars:
            cleaned = cleaned.replace(char, "")
        return cleaned.strip()

    def _draw_text_with_autofit(self, draw: ImageDraw.Draw, text: str, 
                                x: int, y: int, max_width: int,
                                font_name: str, max_size: int, 
                                color: str, anchor: str = "lt") -> None:
        """
        Draws text, automatically reducing font size if it exceeds max_width.
        Uses 'lt' (Left Top) anchor for predictable vertical positioning.
        """
        text = self._clean_text_for_render(text)
        if not text: return

        current_size = max_size
        min_size = 30 # Absolute minimum legible size
        
        font = self._get_font(font_name, current_size)
        
        # Iteratively reduce size until it fits
        while current_size > min_size:
            # getlength is efficient for checking width
            if font.getlength(text) <= max_width:
                break
            current_size -= 4 # Step down size
            font = self._get_font(font_name, current_size)
            
        # Final draw with fitted font
        # Using 'lt' anchor means (x, y) is the top-left corner of the text bounding box.
        # This is crucial for predictable stacking of Thai text.
        draw.text((x, y), text, font=font, fill=color, anchor=anchor)

# [ADD THIS] เพิ่มฟังก์ชันนี้ลงใน Class GraphicsEngine
    def _draw_vector_medal(self, draw: ImageDraw.Draw, x: int, y: int, color_hex: str, rank_idx: int):
        """
        วาดเหรียญรางวัลแบบ Vector (แก้ไขปัญหากรอบขาวบัง)
        ใช้วิธีวาดรูปทรงเรขาคณิตซ้อนกัน เพื่อความคมชัดและไม่มีปัญหาเรื่องฟอนต์หรือรูปภาพ
        """
        # 1. ริบบิ้น (Ribbon) - วาดเป็นรูปห้าเหลี่ยมสีแดงอยู่ด้านหลังสุด
        ribbon_color = "#EF4444"
        draw.polygon([
            (x - 20, y - 90), # จุดบนซ้าย
            (x - 20, y - 40), # จุดล่างซ้าย (ตรงคอคอด)
            (x, y - 10),      # จุดล่างสุดตรงกลาง
            (x + 20, y - 40), # จุดล่างขวา (ตรงคอคอด)
            (x + 20, y - 90)  # จุดบนขวา
        ], fill=ribbon_color)
        
        # 2. ตัวเหรียญ (Medal Body) - วาดทับริบบิ้น
        # 2.1 ขอบนอกสีขาว (Outer Ring)
        r_outer = 85
        draw.ellipse([(x - r_outer, y - r_outer), (x + r_outer, y + r_outer)], fill="#FFFFFF")
        
        # 2.2 พื้นที่สีด้านใน (Inner Color Circle) - สีตามระดับยศ
        r_inner = 75
        draw.ellipse([(x - r_inner, y - r_inner), (x + r_inner, y + r_inner)], fill=color_hex)
        
        # (ผมเอา Gloss Effect เงาสีขาวโปร่งแสงออกไปก่อน เพื่อความชัวร์ว่าจะไม่เกิดปัญหากรอบขาวครับ)

    # [ADD THIS] เพิ่มฟังก์ชันนี้ลงใน Class GraphicsEngine
    def _draw_vector_trophy(self, draw: ImageDraw.Draw, cx: int, y: int):
        """วาดถ้วยรางวัลแบบ Vector สำหรับหัวกระดาษ (แก้ปัญหากล่องสี่เหลี่ยม)"""
        # ตัวถ้วย
        draw.polygon([(cx - 60, y), (cx + 60, y), (cx + 30, y + 100), (cx - 30, y + 100)], fill="#FFD700")
        # ขอบปากถ้วย
        draw.ellipse([(cx - 60, y - 10), (cx + 60, y + 10)], fill="#FFC107")
        # ฐานถ้วย
        draw.rectangle([(cx - 40, y + 100), (cx + 40, y + 120)], fill="#DAA520")

    def render_leaderboard_image(self, room_name: str, df: pd.DataFrame, rank_manager: RankManager) -> bytes:
        """
        Orchestrates the entire image generation process.
        Uses explicit vertical spacing to solve Thai typography overlaps.
        """
        logger.info(f"Starting image generation for room: {room_name}")
        start_time = time.time()

        # 1. Prepare Data (Sort and Filter)
        leaderboard_data = df.sort_values("XP", ascending=False).reset_index(drop=True)
        
        # 2. Calculate Canvas Dimensions
        total_rows = len(leaderboard_data)
        canvas_height = (
            self.cfg.IMG_HEADER_HEIGHT + 
            (total_rows * self.cfg.IMG_ROW_HEIGHT) + 
            self.cfg.IMG_FOOTER_HEIGHT
        )
        
        # 3. Initialize Canvas
        # แก้ไข: เปลี่ยน color=self.cfg.COLOR_BG_MAIN เป็น self.cfg.COLOR_BACKGROUND
        img = Image.new('RGBA', (self.cfg.IMG_WIDTH, canvas_height), color=self.cfg.COLOR_BACKGROUND)
        draw = ImageDraw.Draw(img)
        
        # ==========================================================================
        # HEADER SECTION Rendering
        # ==========================================================================
        # Background Header
        draw.rectangle([(0, 0), (self.cfg.IMG_WIDTH, self.cfg.IMG_HEADER_HEIGHT)], fill=self.cfg.COLOR_BRAND_PRIMARY)
        
        # Decorative Abstract Shapes
        draw.ellipse([(900, -150), (1500, 450)], fill=self.cfg.COLOR_BRAND_SECONDARY)
        draw.ellipse([(-100, 250), (500, 850)], fill=self.cfg.COLOR_BRAND_SECONDARY)
        
        # Header Typography
        center_x = self.cfg.IMG_WIDTH // 2
        
        # Trophy Icon (Vector Draw - No Emoji)
        self._draw_vector_trophy(draw, center_x, 180)
        
        # Main Title
        f_title = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 60)
        draw.text((center_x, 380), "CLASSROOM LEADERBOARD", font=f_title, fill=self.cfg.COLOR_BRAND_ACCENT, anchor="mm")
        
        # Room Name (Large)
        f_room = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 150)
        draw.text((center_x, 550), room_name, font=f_room, fill="white", anchor="mm")

        # ==========================================================================
        # LEADERBOARD ROWS Rendering
        # ==========================================================================
        # Starting Y position for the first card based on config
        current_y_cursor = self.cfg.IMG_HEADER_HEIGHT + 50
        
        # Pre-fetch fonts used repeatedly in loop
        f_rank_num = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 85)
        f_score_val = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 110)
        f_score_lbl = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 45)
        f_members = self._get_font(self.cfg.FONT_PRIMARY_REG, 42)
        f_rank_title = self._get_font(self.cfg.FONT_PRIMARY_BOLD, 48)
        f_privilege = self._get_font(self.cfg.FONT_PRIMARY_REG, 36)

        for i, row in leaderboard_data.iterrows():
            # A. Resolve Row Data
            xp = row['XP']
            rank_def = rank_manager.get_rank_by_xp(xp)
            progress_pct, _ = rank_manager.calculate_progress_to_next(xp)
            
            # Determine Theme Colors
            rank_idx = i if i < 3 else "default"
            theme = self.cfg.RANK_THEMES[rank_idx]
            rank_color_hex = theme["hex"]
            
            score_color = self.cfg.COLOR_SCORE_NEGATIVE if xp < 0 else self.cfg.COLOR_SCORE_POSITIVE

            # B. Card Layout Definitions
            card_x_start = self.cfg.IMG_PADDING_X
            card_width = self.cfg.IMG_WIDTH - (self.cfg.IMG_PADDING_X * 2)
            # Card height is row height minus gaps between cards
            card_height = self.cfg.IMG_ROW_HEIGHT - 40 
            card_y_start = current_y_cursor
            card_y_end = card_y_start + card_height
            
            # C. Draw Card Background & Shadow
            # Shadow layer (offset slightly)
            draw.rounded_rectangle(
                [(card_x_start + 8, card_y_start + 10), (card_x_start + card_width + 8, card_y_end + 10)],
                radius=self.cfg.IMG_CARD_RADIUS, fill=self.cfg.COLOR_CARD_SHADOW
            )
            # Main surface layer
            draw.rounded_rectangle(
                [(card_x_start, card_y_start), (card_x_start + card_width, card_y_end)],
                radius=self.cfg.IMG_CARD_RADIUS, fill=self.cfg.COLOR_CARD_SURFACE
            )

            # --- COLUMN 1: Rank Position / Sticker Generation ---
            sticker_cx = card_x_start + 120
            sticker_cy = card_y_start + (card_height // 2)
            
            if i < 3:
                # วาดเหรียญรางวัลสำหรับ Top 3 (Vector Medal)
                self._draw_vector_medal(draw, sticker_cx, sticker_cy, rank_color_hex, i)
            else:
                # วาดป้ายวงกลมปกติสำหรับอันดับอื่น (Vector Badge)
                # วาดขอบขาวก่อน
                draw.ellipse([(sticker_cx - 80, sticker_cy - 80), (sticker_cx + 80, sticker_cy + 80)], fill="#FFFFFF")
                # วาดวงกลมสี
                draw.ellipse([(sticker_cx - 70, sticker_cy - 70), (sticker_cx + 70, sticker_cy + 70)], fill=rank_color_hex)
            
            # วาดเลขลำดับทับลงไป
            draw.text((sticker_cx, sticker_cy), str(i + 1), font=f_rank_num, fill="white", anchor="mm")

            # --- COLUMN 2: Group Details & Status (Middle) ---
            content_x_start = card_x_start + 260
            content_max_width = 650
            
            # แก้ไข: ปรับลดระยะห่างบรรทัดให้กระชับขึ้น
            # (ลดจาก +100 เหลือ +80 และจาก +70 เหลือ +60)
            Y_POS_NAME = card_y_start + 50          # ขยับบรรทัดแรกขึ้นนิดหน่อย
            Y_POS_MEMBERS = Y_POS_NAME + 80         # ลดช่องว่าง
            Y_POS_PROGRESS_BAR = Y_POS_MEMBERS + 80 # ลดช่องว่าง
            Y_POS_RANK_TITLE = Y_POS_PROGRESS_BAR + 60 # บีบให้ชิดหลอดพลังมากขึ้น
            Y_POS_PRIVILEGE = Y_POS_RANK_TITLE + 60    # บีบคำอธิบายให้ชิดขึ้น

            # 2.1 Group Name (Auto-fit, Bold)
            self._draw_text_with_autofit(
                draw, str(row['GroupName']),
                content_x_start, Y_POS_NAME, content_max_width,
                self.cfg.FONT_PRIMARY_BOLD, 80, self.cfg.COLOR_TEXT_PRIMARY, anchor="lt"
            )

            # 2.2 Members List (Truncated if too long)
            members_txt = self._clean_text_for_render(str(row['Members']))
            if len(members_txt) > 65:
                members_txt = members_txt[:62] + "..."
            draw.text((content_x_start, Y_POS_MEMBERS), members_txt, font=f_members, fill=self.cfg.COLOR_TEXT_SECONDARY, anchor="lt")

            # 2.3 Progress Bar
            bar_height = 16
            bar_width = 580
            # Draw background track
            # แก้ไข: เปลี่ยน fill=self.cfg.COLOR_BG_MAIN เป็น self.cfg.COLOR_BACKGROUND
            draw.rounded_rectangle(
                [(content_x_start, Y_POS_PROGRESS_BAR), (content_x_start + bar_width, Y_POS_PROGRESS_BAR + bar_height)],
                radius=8, fill=self.cfg.COLOR_BACKGROUND
            )

            # Draw fill based on progress
            if progress_pct > 0:
                fill_width = int(bar_width * progress_pct)
                # Ensure minimum visibility if progress > 0
                fill_width = max(fill_width, 20) if progress_pct > 0.01 else fill_width
                draw.rounded_rectangle(
                    [(content_x_start, Y_POS_PROGRESS_BAR), (content_x_start + fill_width, Y_POS_PROGRESS_BAR + bar_height)],
                    radius=8, fill=rank_def.color
                )

            # 2.4 Rank Title (Colored based on rank)
            draw.text((content_x_start, Y_POS_RANK_TITLE), rank_def.th_name, font=f_rank_title, fill=rank_def.color, anchor="lt")

            # 2.5 Privilege Description (Grey, Auto-fit)
            # Important: Use the clean Thai description from RankDefinition
            privilege_txt = rank_def.description
            self._draw_text_with_autofit(
                draw, privilege_txt,
                content_x_start, Y_POS_PRIVILEGE, content_max_width,
                self.cfg.FONT_PRIMARY_REG, 40, self.cfg.COLOR_TEXT_SECONDARY, anchor="lt"
            )

            # --- COLUMN 3: XP Score (Right Aligned) ---
            score_x_anchor = self.cfg.IMG_WIDTH - self.cfg.IMG_PADDING_X - 40
            # Center score block vertically within the card
            score_y_center = card_y_start + (card_height // 2)

            # Draw Score Value
            # Using 'rs' (Right Baseline) anchor, adjusted up slightly
            draw.text((score_x_anchor, score_y_center - 10), f"{xp}", font=f_score_val, fill=score_color, anchor="rs")
            # Draw "XP" Label below value
            draw.text((score_x_anchor, score_y_center + 50), "XP", font=f_score_lbl, fill=self.cfg.COLOR_TEXT_MUTED, anchor="rs")

            # D. Advance Cursor for Next Row
            current_y_cursor += self.cfg.IMG_ROW_HEIGHT

# ==========================================================================
        # FOOTER SECTION Rendering
        # ==========================================================================
        # แก้ไข: เปลี่ยนจาก total_height เป็น canvas_height ให้ตรงกับที่ประกาศไว้ตอนต้นฟังก์ชัน
        footer_y_center = canvas_height - (self.cfg.IMG_FOOTER_HEIGHT // 2)
        
        f_footer = self._get_font(self.cfg.FONT_PRIMARY_REG, 38)
        timestamp_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        footer_text = f"Generated by {self.cfg.APP_NAME} • {timestamp_str}"
        
        draw.text((self.cfg.IMG_WIDTH // 2, footer_y_center), footer_text, font=f_footer, fill=self.cfg.COLOR_TEXT_MUTED, anchor="mm")

        # 4. Finalize Image
        img_final = img.convert('RGB')
        
        end_time = time.time()
        logger.info(f"Image generation completed in {end_time - start_time:.2f} seconds.")
        
        # Save to buffer
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
    Composition root that ties backend services to the frontend.
    """
    def __init__(self):
        self.cfg = AppConfig()
        # Initialize backend services
        self.db = GoogleSheetsRepository()
        self.rank_mgr = RankManager()
        self.badge_sys = BadgeSystem()
        self.gfx = GraphicsEngine()

    def setup_page(self):
        """Configures page settings and injects global CSS."""
        st.set_page_config(
            page_title=f"{self.cfg.APP_NAME} - Enterprise",
            page_icon="🏫",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        self._inject_custom_css()

    def _inject_custom_css(self):
        """Injects advanced CSS for a polished, corporate look."""
        st.markdown(f"""
            <style>
            /* Import Google Fonts */
            @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&family=Prompt:wght@300;400;500;700&display=swap');
            
            /* Global Theme Variables */
            :root {{
                --primary: {self.cfg.COLOR_BRAND_PRIMARY};
                --secondary: {self.cfg.COLOR_BRAND_SECONDARY};
                --accent: {self.cfg.COLOR_BRAND_ACCENT};
                /* แก้ไข: เรียกใช้ COLOR_BACKGROUND */
                --bg-body: {self.cfg.COLOR_BACKGROUND};
                --text-main: {self.cfg.COLOR_TEXT_PRIMARY};
            }}

            /* Base Typography */
            html, body, [class*="css"] {{
                font-family: 'Sarabun', 'Prompt', sans-serif;
                color: var(--text-main);
                background-color: var(--bg-body);
            }}
            
            /* Component Overrides */
            .stApp {{ background-color: var(--bg-body); }}
            
            /* Modern Card Styling */
            div[data-testid="stExpander"] {{
                border: none;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                border-radius: 12px;
                background: white;
            }}
            
            /* Custom Buttons */
            .stButton>button {{
                border-radius: 10px;
                font-weight: 600;
                padding: 0.5rem 1rem;
                transition: all 0.2s ease-in-out;
            }}
            .stButton>button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}
            /* Primary Button Style */
            button[kind="primary"] {{
                background: linear-gradient(135deg, var(--primary), var(--secondary));
                border: none;
            }}

            /* Custom Form Inputs */
            .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stNumberInput>div>div>input, .stSelectbox>div>div>div {{
                border-radius: 10px;
                border: 1px solid #E2E8F0;
                background-color: #F8FAFC;
            }}
            .stTextInput>div>div>input:focus {{
                 border-color: var(--primary);
                 box-shadow: 0 0 0 1px var(--primary);
            }}

            /* Hero Banner Styling */
            .hero-banner {{
                background: linear-gradient(120deg, var(--primary), var(--secondary));
                padding: 2.5rem;
                border-radius: 20px;
                color: white;
                margin-bottom: 2rem;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2);
                display: flex;
                align-items: center;
                justify-content: space-between;
                border: 1px solid rgba(255,255,255,0.1);
            }}
            .hero-title h1 {{ font-size: 3.5rem; font-weight: 800; margin: 0; line-height: 1.1; }}
            .hero-subtitle {{ font-size: 1rem; font-weight: 500; opacity: 0.9; letter-spacing: 1px; text-transform: uppercase; }}
            .hero-stat {{ text-align: right; }}
            .hero-stat-number {{ font-size: 4rem; font-weight: 800; line-height: 1; }}
            
            /* Card Glassmorphism */
            .glass-card {{
                background: rgba(255, 255, 255, 0.9);
                backdrop-filter: blur(8px);
                border-radius: 16px;
                border: 1px solid {self.cfg.COLOR_CARD_BORDER};
                box-shadow: 0 4px 6px -2px rgba(0, 0, 0, 0.05);
                padding: 1.5rem;
                margin-bottom: 1rem;
                transition: transform 0.2s;
            }}
            .glass-card:hover {{ transform: translateY(-3px); }}

            /* Status Badges */
            .badge {{
                display: inline-block;
                padding: 0.3em 0.8em;
                font-size: 80%;
                font-weight: 700;
                line-height: 1;
                text-align: center;
                white-space: nowrap;
                vertical-align: baseline;
                border-radius: 0.5rem;
            }}
            </style>
        """, unsafe_allow_html=True)

    def render_sidebar(self) -> str:
        """Renders the sidebar and returns the selected classroom."""
        with st.sidebar:
            st.image("https://cdn-icons-png.flaticon.com/512/4738/4738983.png", width=60)
            st.title("Control Panel")
            st.markdown(f"v{self.cfg.APP_VERSION}")
            st.divider()
            
            st.subheader("🏫 Classroom Context")
            # Add your actual classroom lists here
            selected_room = st.selectbox(
                "Select Active Class",
                ["ม.1/1", "ม.1/2", "ม.1/10"],
                index=0,
                help="Choose the classroom you want to manage."
            )
            
            st.divider()
            st.subheader("💾 Data Operations")
            
            # Fetch data for export
            current_df = self.db.fetch_all_data()
            
            # Export button
            csv_data = current_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Database (CSV)",
                data=csv_data,
                file_name=f"classroom_data_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            with st.expander("⚠️ Danger Zone"):
                st.warning("Advanced actions. Proceed with caution.")
                if st.button("🔄 Reset Database Schema", help="Clears all data and rebuilds headers. Irreversible!"):
                    confirm = st.checkbox("I understand this will delete all data.")
                    if confirm:
                        empty_df = pd.DataFrame(columns=self.db.SCHEMA)
                        if self.db.commit_data(empty_df):
                            st.success("Database reset successful.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Reset failed.")
            
            return selected_room

    def render_hero_section(self, room_name: str, group_count: int):
        """Renders the top banner with context info."""
        st.markdown(f"""
            <div class="hero-banner">
                <div class="hero-title">
                    <div class="hero-subtitle">{self.cfg.ORG_NAME} • {self.cfg.APP_NAME}</div>
                    <h1>{room_name}</h1>
                </div>
                <div class="hero-stat">
                    <div class="hero-stat-number">{group_count}</div>
                    <div style="font-weight:600; opacity:0.9;">Active Teams</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # ================= Main Tab Rendering Methods =================

    def _render_command_center_tab(self, room_name: str, room_df: pd.DataFrame, all_df: pd.DataFrame):
        st.header("⚡ Command Center")
        st.caption("Manage scores and activities for teams.")
        
        if room_df.empty:
            st.info("👋 Welcome! Get started by creating your first group in the **Management** tab.")
            return

        # Target Selection
        col_mode, col_target = st.columns([1, 2])
        with col_mode:
            st.subheader("1. Select Mode")
            selection_mode = st.radio("Operation Mode", ["Single Group", "Multi-Group Batch"], label_visibility="collapsed")
        
        with col_target:
            st.subheader("2. Select Targets")
            all_groups = sorted(room_df['GroupName'].unique().tolist())
            if selection_mode == "Single Group":
                target_groups = [st.selectbox("Choose Team", all_groups)]
            else:
                target_groups = st.multiselect("Choose Teams", all_groups, placeholder="Select one or more teams...")

        # Show Quick Stats for Single Selection
        if len(target_groups) == 1:
            group_data = room_df[room_df['GroupName'] == target_groups[0]].iloc[0]
            current_xp = group_data['XP']
            rank = self.rank_mgr.get_rank_by_xp(current_xp)
            
            st.markdown(f"""
                <div style="background:white; padding:20px; border-radius:16px; border:1px solid #E2E8F0; text-align:center; margin: 1.5rem 0; display:flex; align-items:center; justify-content:space-around;">
                    <div>
                        <div style="color:{self.cfg.COLOR_TEXT_MUTED}; font-weight:600; font-size:0.9rem;">CURRENT STANDING</div>
                        <div style="font-size:3.5rem; font-weight:900; color:{self.cfg.COLOR_SCORE_POSITIVE if current_xp >= 0 else self.cfg.COLOR_SCORE_NEGATIVE}; line-height:1.1;">{current_xp:,} <span style="font-size:1.5rem;">XP</span></div>
                    </div>
                    <div style="text-align:right;">
                        <span class="badge" style="background:{rank.bg_color}; color:{rank.color}; font-size:1.1rem; padding: 0.6em 1.2em;">{rank.th_name}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        st.divider()
        st.subheader("3. Execute Action")

        # Action Panels
        col_quick, col_manual = st.columns(2)
        
        # Callback for action execution
        def _execute_transaction(reason_txt, amount_val):
            if not target_groups:
                st.toast("⚠️ Please select at least one team first.", icon="🛑")
                return
            
            with st.spinner("Processing transaction..."):
                success, count = self.db.process_xp_transaction(
                    room=room_name,
                    target_groups=target_groups,
                    amount=amount_val,
                    reason=reason_txt,
                    current_df=all_df,
                    badge_sys=self.badge_sys
                )
            
            if success:
                st.toast(f"✅ Successfully updated {count} team(s)!", icon="🎉")
                time.sleep(0.8)
                st.rerun()
            else:
                st.toast("❌ Failed to process transaction. Check database connection.", icon="🔥")

        with col_quick:
            st.markdown("**🚀 Quick Presets**")
            st.caption("One-click standard actions.")
            c1, c2 = st.columns(2)
            c1.button("📚 On-Time submission (+50)", on_click=_execute_transaction, args=("ส่งงานตรงเวลา", 50), use_container_width=True)
            c2.button("🙋 Class Participation (+20)", on_click=_execute_transaction, args=("มีส่วนร่วมในชั้นเรียน", 20), use_container_width=True)
            c1.button("🏆 Activity Winner (+100)", on_click=_execute_transaction, args=("ชนะกิจกรรมพิเศษ", 100), type="primary", use_container_width=True)
            c2.button("🐢 Late Submission (-20)", on_click=_execute_transaction, args=("ส่งงานล่าช้า", -20), use_container_width=True)

        with col_manual:
            st.markdown("**✍️ Custom Transaction**")
            st.caption("Specify custom reason and amount.")
            with st.form("manual_transaction_form", clear_on_submit=True):
                reason_input = st.text_input("Reason / Activity Name", placeholder="e.g., Bonus Project, Helping friend...")
                amount_input = st.number_input("XP Amount (+/-)", step=5, value=0)
                
                submitted = st.form_submit_button("📢 Submit Transaction", type="primary", use_container_width=True)
                if submitted:
                    if not reason_input or amount_input == 0:
                         st.error("Please provide both a valid reason and a non-zero amount.")
                    else:
                         _execute_transaction(reason_input, amount_input)

    def _render_leaderboard_tab(self, room_name: str, room_df: pd.DataFrame):
        st.header("🏆 Leaderboard & Rankings")
        
        if room_df.empty:
            st.warning("No data to display.")
            return

        tabs_lb = st.tabs(["🖼️ High-Fidelity Image", "📋 Live List View"])
        
        # --- Image Generation Tab ---
        with tabs_lb[0]:
            st.caption("Generate a publication-ready image with correct Thai typography rendering.")
            
            col_gen_btn, col_gen_preview = st.columns([1, 2])
            with col_gen_btn:
                st.info("Tips: This process generates a high-resolution image where all Thai vowels and tone marks are correctly placed without overlapping.")
                if st.button("✨ Generate Leaderboard Image", type="primary", use_container_width=True):
                    with st.spinner("🎨 Rendering high-fidelity image... This may take a moment."):
                        try:
                            # Generate image using the robust engine
                            img_bytes = self.gfx.render_leaderboard_image(room_name, room_df, self.rank_mgr)
                            st.session_state['generated_image'] = img_bytes
                            st.success("Image generated successfully!")
                        except Exception as e:
                            st.error(f"Image generation failed: {e}")
                            logger.error(f"Image Gen Error: {e}", exc_info=True)

                # Show download button if image exists in session state
                if 'generated_image' in st.session_state:
                     st.download_button(
                        label="📥 Download Image (PNG)",
                        data=st.session_state['generated_image'],
                        file_name=f"Leaderboard_{room_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
                        mime="image/png",
                        type="primary",
                        use_container_width=True
                    )

            with col_gen_preview:
                 if 'generated_image' in st.session_state:
                     st.image(st.session_state['generated_image'], caption="High-Fidelity Preview", use_container_width=True, output_format='PNG')
                 else:
                     st.markdown("""
                        <div style="border: 2px dashed #E2E8F0; border-radius:16px; height:400px; display:flex; align-items:center; justify-content:center; color:#94A3B8; flex-direction:column;">
                            <div style="font-size:3rem;">🖼️</div>
                            <div>Click generate to preview image here.</div>
                        </div>
                     """, unsafe_allow_html=True)

        # --- Live List View Tab ---
        with tabs_lb[1]:
            st.caption("Real-time interactive ranking list.")
            sorted_df = room_df.sort_values("XP", ascending=False).reset_index(drop=True)
            
            for i, row in sorted_df.iterrows():
                rank = self.rank_mgr.get_rank_by_xp(row['XP'])
                prog_pct, prog_lbl = self.rank_mgr.calculate_progress_to_next(row['XP'])
                
                # Parse badges
                try:
                    badges_list = json.loads(row['Badges'])
                except:
                    badges_list = []
                badges_str = self.badge_sys.render_badges(badges_list)
                
                card_border_color = self.cfg.COLOR_SCORE_NEGATIVE if row['XP'] < 0 else rank.color
                
                # Render list item using HTML card
                st.markdown(f"""
                <div class="glass-card" style="border-left: 6px solid {card_border_color};">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div style="flex-grow:1;">
                             <div style="display:flex; align-items:center; margin-bottom:5px;">
                                <span style="font-size:1.4rem; font-weight:800; color:{self.cfg.COLOR_TEXT_MUTED}; margin-right:12px; min-width:30px;">#{i+1}</span>
                                <h3 style="margin:0; font-size:1.3rem;">{row['GroupName']}</h3>
                             </div>
                             <div style="color:{self.cfg.COLOR_TEXT_SECONDARY}; font-size:0.95rem; margin-bottom:8px;">👥 {row['Members']}</div>
                             <div style="font-size:1.1rem;">{badges_str}</div>
                        </div>
                        <div style="text-align:right;">
                             <div style="font-size:2.2rem; font-weight:900; color:{card_border_color}; line-height:1;">{row['XP']:,}</div>
                             <div style="font-size:0.85rem; color:{self.cfg.COLOR_TEXT_MUTED}; font-weight:600;">TOTAL XP</div>
                        </div>
                    </div>
                    <div style="margin-top:15px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px;">
                             <span class="badge" style="background:{rank.bg_color}; color:{rank.color};">{rank.th_name}</span>
                             <span style="font-size:0.85rem; color:{self.cfg.COLOR_TEXT_SECONDARY};">{prog_lbl}</span>
                        </div>
                        <st-progress value="{prog_pct}"></st-progress>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                # Use streamlit's native progress bar for simplicity in HTML embedding
                st.progress(prog_pct)

    def _render_analytics_tab(self, room_df: pd.DataFrame):
        st.header("📈 Performance Analytics")
        if room_df.empty:
            st.warning("No data available for analysis.")
            return

        # 1. KPI Metrics
        # ใช้ try-except เพื่อกันค่าที่ไม่ใช่ตัวเลข
        try:
            total_xp = room_df['XP'].sum()
            avg_xp = room_df['XP'].mean()
        except:
            total_xp = 0
            avg_xp = 0
            
        top_team_row = room_df.loc[room_df['XP'].idxmax()] if not room_df.empty else None
        top_team = top_team_row['GroupName'] if top_team_row is not None else "-"
        active_teams = len(room_df[room_df['XP'] != 0])

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("🏆 Leading Team", top_team)
        kpi2.metric("✨ Total Class XP", f"{int(total_xp):,}")
        kpi3.metric("📊 Average XP", f"{int(avg_xp):,}")
        kpi4.metric("🔥 Active Teams", f"{active_teams} / {len(room_df)}")
        
        st.divider()
        
        # 2. XP History Chart (Timeline) - Fix Schema Validation Error
        st.subheader("🏎️ XP Race Timeline")
        st.caption("Track progress over time.")
        
        history_data = []
        for _, row in room_df.iterrows():
            try:
                # แปลง JSON string เป็น list, ถ้าพังให้เป็น list ว่าง
                log_str = str(row['HistoryLog'])
                if not log_str.strip() or log_str == "nan":
                    logs = []
                else:
                    logs = json.loads(log_str)
                
                # วนลูปดึงข้อมูลประวัติ
                for log in logs:
                    ts_val = pd.to_datetime(log.get('ts'), errors='coerce')
                    
                    # กรองข้อมูลขยะ: ต้องมีเวลา และ ยอดเงินต้องแปลงเป็น int ได้
                    if ts_val is not pd.NaT:
                        try:
                            balance_val = int(log.get('balance', 0))
                        except:
                            balance_val = 0
                            
                        history_data.append({
                            "Team": str(row['GroupName']),
                            "Timestamp": ts_val,
                            "Total XP": balance_val
                        })
            except Exception as e:
                # ข้ามแถวที่มีปัญหาไปเลย กันกราฟพัง
                continue
        
        if history_data:
            chart_df = pd.DataFrame(history_data)
            
            # Create Altair Line Chart with Strict Typing
            chart = alt.Chart(chart_df).mark_line(
                point=alt.OverlayMarkDef(filled=False, fill="white", strokeWidth=2)
            ).encode(
                # ระบุ Type ชัดเจน :T (Time), :Q (Quantitative), :N (Nominal)
                x=alt.X('Timestamp:T', title='Date & Time', axis=alt.Axis(format='%d/%m %H:%M')),
                y=alt.Y('Total XP:Q', title='Accumulated XP'),
                color=alt.Color('Team:N', title='Team Name', scale={"scheme": "category20"}),
                tooltip=[
                    alt.Tooltip('Timestamp:T', format='%d/%m/%Y %H:%M', title='Time'),
                    alt.Tooltip('Team:N', title='Team Name'),
                    alt.Tooltip('Total XP:Q', title='XP Balance', format=',')
                ]
            ).properties(
                height=450,
                title="Score Progression History"
            ).interactive()
            
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Not enough history data to generate timeline chart yet.")

    def _render_privileges_tab(self):
        st.header("ℹ️ Rank & Privilege System")
        st.caption("Understanding the hierarchy and rewards.")
        
        ranks = self.rank_mgr.all_ranks
        
        # Display Normal Ranks
        st.subheader("Normal Progression Tier")
        for rank in ranks:
            if rank.id == "PROBATION": continue
            
            st.markdown(f"""
            <div style="background:white; border-radius:12px; border-left: 5px solid {rank.color}; padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="margin:0; color:{rank.color}; display:flex; align-items:center;">
                        {rank.th_name}
                    </h3>
                    <span class="badge" style="background:{rank.bg_color}; color:{rank.color}; font-size:0.9rem;">Req: {rank.min_xp}+ XP</span>
                </div>
                <hr style="margin: 10px 0; border-color:#F1F5F9;">
                <div style="display:flex; align-items:start;">
                    <span style="font-size:1.2rem; margin-right:10px;">🎁</span>
                    <div>
                        <strong style="color:{self.cfg.COLOR_TEXT_PRIMARY};">Privilege Benefits:</strong>
                        <div style="color:{self.cfg.COLOR_TEXT_SECONDARY}; margin-top:5px;">{rank.description}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        # Display Probation
        st.subheader("Special Status Tier")
        prob = ranks[-1]
        st.markdown(f"""
        <div style="background:#FFF1F2; border-radius:12px; border-left: 5px solid {prob.color}; padding: 15px; margin-bottom: 15px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h3 style="margin:0; color:{prob.color}; display:flex; align-items:center;">
                    {prob.th_name}
                </h3>
                 <span class="badge" style="background:{prob.bg_color}; color:{prob.color}; font-size:0.9rem;">Negative XP</span>
            </div>
             <hr style="margin: 10px 0; border-color:#FECACA;">
             <div style="display:flex; align-items:start;">
                    <span style="font-size:1.2rem; margin-right:10px;">⚠️</span>
                    <div>
                        <strong style="color:#991B1B;">Condition:</strong>
                        <div style="color:#7F1D1D; margin-top:5px;">{prob.description}</div>
                    </div>
                </div>
        </div>
        """, unsafe_allow_html=True)

    def _render_management_tab(self, room_name: str, room_df: pd.DataFrame, all_df: pd.DataFrame):
        st.header("🛠️ Team Management")
        st.caption("Create, update, or delete teams.")

        # 1. Creation Form
        with st.expander("➕ Create New Team", expanded=True):
            with st.form("create_team_form"):
                new_name = st.text_input("Team Name (Must be unique in this class)", placeholder="e.g., Alpha Squad")
                new_members = st.text_area("Member List", placeholder="e.g., John, Mary, Peter...")
                
                if st.form_submit_button("Create Team", type="primary"):
                    if not new_name:
                        st.error("Team name is required.")
                    elif self.db.create_group_record(room_name, new_name, new_members, all_df):
                        st.success(f"Team '{new_name}' created successfully!")
                        time.sleep(0.8)
                        st.rerun()
                    else:
                        st.error(f"Failed to create team. Name '{new_name}' may already exist.")

        st.divider()

        if room_df.empty:
            return

        # 2. Edit & Delete Section
        col_edit, col_delete = st.columns([2, 1])
        all_teams_list = sorted(room_df['GroupName'].unique().tolist())

        with col_edit:
            st.subheader("✏️ Edit Team Details")
            target_edit = st.selectbox("Select Team to Edit", ["-"] + all_teams_list)
            
            if target_edit != "-":
                current_data = room_df[room_df['GroupName'] == target_edit].iloc[0]
                with st.form("edit_team_form"):
                    edit_name = st.text_input("Edit Name", value=current_data['GroupName'])
                    edit_members = st.text_area("Edit Members", value=current_data['Members'])
                    
                    if st.form_submit_button("Save Changes"):
                        if self.db.update_group_record(room_name, target_edit, edit_name, edit_members, all_df):
                             st.success("Team updated successfully!")
                             time.sleep(0.8)
                             st.rerun()
                        else:
                             st.error("Update failed. New name might be a duplicate.")

        with col_delete:
            st.subheader("🗑️ Delete Team")
            target_delete = st.selectbox("Select Team to Delete", ["-"] + all_teams_list)
            
            if target_delete != "-":
                st.warning(f"Are you sure you want to delete '{target_delete}'? This action cannot be undone and all history will be lost.")
                if st.button("Confirm Delete", type="primary"):
                     if self.db.delete_group_record(room_name, target_delete, all_df):
                          st.success(f"Team '{target_delete}' deleted.")
                          time.sleep(0.8)
                          st.rerun()
                     else:
                          st.error("Deletion failed.")

        st.divider()
        
        # 3. Advanced Power Edit
        with st.expander("⚡ Advanced: History Log Override (Power User)"):
            st.warning("This feature completely rewrites a team's history. Use only for corrections.")
            target_pe = st.selectbox("Select Team for History Override", ["-"] + all_teams_list)
            
            if target_pe != "-":
                row_pe = room_df[room_df['GroupName'] == target_pe].iloc[0]
                try:
                    history_data = json.loads(row_pe['HistoryLog'])
                except:
                    history_data = []
                
                # --- [FIX START] แปลงข้อมูลให้ตรง Type ก่อนส่งเข้า Editor ---
                df_history = pd.DataFrame(history_data)
                
                # 1. ถ้าไม่มีข้อมูล ให้สร้าง DataFrame เปล่าที่มีหัวตารางครบถ้วน
                if df_history.empty:
                    df_history = pd.DataFrame(columns=["ts", "amount", "reason", "id", "balance"])
                
                # 2. แปลงคอลัมน์ 'ts' จาก String ให้เป็น Datetime Object จริงๆ
                if "ts" in df_history.columns:
                    df_history["ts"] = pd.to_datetime(df_history["ts"], errors='coerce')
                
                # 3. แปลง amount/balance ให้เป็นตัวเลขแน่นอน
                if "amount" in df_history.columns:
                    df_history["amount"] = pd.to_numeric(df_history["amount"], errors='coerce').fillna(0).astype(int)
                if "balance" in df_history.columns:
                    df_history["balance"] = pd.to_numeric(df_history["balance"], errors='coerce').fillna(0).astype(int)
                # --- [FIX END] ---

                # Use data editor with PREPARED DataFrame
                edited_history_df = st.data_editor(
                    df_history, # ใช้ตัวแปรใหม่ที่แปลงค่าแล้ว
                    num_rows="dynamic",
                    use_container_width=True,
                    column_config={
                        "ts": st.column_config.DatetimeColumn(
                            "Timestamp", 
                            format="YYYY-MM-DD HH:mm",
                            step=60
                        ),
                        "amount": st.column_config.NumberColumn("XP Amount", required=True),
                        "reason": st.column_config.TextColumn("Reason", required=True),
                        "id": st.column_config.TextColumn("Transaction ID", disabled=True),
                        "balance": st.column_config.NumberColumn("Running Balance", disabled=True)
                    },
                    key=f"editor_{target_pe}"
                )
                
                if st.button("💾 Save & Recalculate History"):
                    # แปลง datetime กลับเป็น string format ก่อนส่งไปบันทึก
                    # (เพราะ JSON เก็บ datetime object ไม่ได้)
                    if not edited_history_df.empty and "ts" in edited_history_df.columns:
                        edited_history_df["ts"] = edited_history_df["ts"].dt.strftime("%Y-%m-%d %H:%M")
                        
                    if self.db.apply_history_override(room_name, target_pe, edited_history_df, all_df, self.badge_sys):
                        st.success("History overwritten and XP recalculated successfully!")
                        time.sleep(0.8)
                        st.rerun()
                    else:
                        st.error("Failed to save history override.")

    def run(self):
        """Main application lifecycle loop."""
        self.setup_page()
        
        # Render Sidebar & Get Context
        selected_room = self.render_sidebar()
        
        # Load Data Context
        try:
            all_df = self.db.fetch_all_data()
            room_df = all_df[all_df['Room'] == selected_room].copy()
        except Exception as e:
            st.error(f"Failed to load data: {e}")
            return

        # Render Main Layout
        self.render_hero_section(selected_room, len(room_df))
        
        # Main Content Tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "⚡ Command", "🏆 Leaderboard", "📈 Analytics", "ℹ️ Privileges", "🛠️ Management"
        ])
        
        with tab1:
            self._render_command_center_tab(selected_room, room_df, all_df)
        with tab2:
            self._render_leaderboard_tab(selected_room, room_df)
        with tab3:
            self._render_analytics_tab(room_df)
        with tab4:
            self._render_privileges_tab()
        with tab5:
            self._render_management_tab(selected_room, room_df, all_df)

# ==============================================================================
# EXECUTION ENTRY POINT
# ==============================================================================
if __name__ == "__main__":
    app = UIManager()
    app.run()
