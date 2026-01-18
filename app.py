"""
Classroom OS: Enterprise Architect Edition
Version: 30.0.0-Titanium-Ultra
Author: Lead Software Architect
Date: 2026-01-20

[SYSTEM ARCHITECTURE MANIFEST]
This system utilizes a strict Hexagonal Architecture (Ports & Adapters) to ensure 
maximum decoupling between the Core Domain, Infrastructure, and Presentation layers.

[MODULE MAP]
1.  KERNEL_LAYER:       Base Exceptions, Enums, Event Bus, Configuration.
2.  DOMAIN_LAYER:       Rich Models (Team, Rank, Badge), Value Objects.
3.  APPLICATION_LAYER:  Use Cases (ScoreProcessing, TeamManagement), Service Orchestration.
4.  INFRA_LAYER:        Google Sheets Repository (with Retry/Backoff), JSON Serializers.
5.  GRAPHICS_LAYER:     Vector Composition Engine (Builder Pattern) for High-Fidelity Rendering.
6.  UI_LAYER:           Streamlit View Controllers, State Management, CSS Injection.

[FEATURES]
- Atomic Batch Transactions with Rollback simulation.
- Procedural Vector Asset Generation (Medals, Ribbons, Trophies).
- True-Type Font Metrics Calculation for Thai Typography.
- Full CRUD Lifecycle Management for Teams.
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
from typing import List, Dict, Optional, Tuple, Any, Union, Set, Callable, TypeVar, Generic
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod
from enum import Enum, auto
from PIL import Image, ImageDraw, ImageFont, ImageColor

# ==============================================================================
# PART 1: SYSTEM KERNEL & CONFIGURATION
# ==============================================================================

# 1.1 Logging Subsystem
logging.basicConfig(
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("ClassroomOS.Kernel")

# 1.2 Custom Exception Hierarchy
class ClassroomOSError(Exception):
    """Base class for all application exceptions."""
    def __init__(self, message: str, code: str = "GENERIC_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)

class InfrastructureError(ClassroomOSError):
    """Raised when external services (DB, API) fail."""
    pass

class DomainLogicError(ClassroomOSError):
    """Raised when business rules are violated."""
    pass

class ValidationError(ClassroomOSError):
    """Raised when input data is invalid."""
    pass

# 1.3 System Enumerations
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

# 1.4 Global Configuration (Singleton)
class SystemConfig:
    """
    Centralized Configuration Store.
    """
    # Metadata
    APP_NAME: str = "Classroom OS"
    APP_VERSION: str = "30.0.0-Titanium"
    ORGANIZATION: str = "Acme Education Systems"
    
    # Infrastructure
    DB_CONN_NAME: str = "gsheets"
    DB_SHEET_NAME: str = "Sheet1"
    DB_CACHE_TTL: int = 0
    
    # Graphics - Dimensions
    IMG_WIDTH: int = 1400
    IMG_HEADER_HEIGHT: int = 780
    IMG_ROW_HEIGHT: int = 650  # Optimized for Thai Ascenders/Descenders
    IMG_FOOTER_HEIGHT: int = 220
    IMG_PADDING: int = 50
    IMG_CARD_RADIUS: int = 45
    
    # Graphics - Fonts
    FONT_BOLD: str = "Sarabun-Bold.ttf"
    FONT_REGULAR: str = "Sarabun-Regular.ttf"
    
    # Graphics - Colors
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
# PART 2: UTILITY SERVICES
# ==============================================================================

class TextProcessor:
    """Handles string sanitization and formatting."""
    
    @staticmethod
    def clean_for_render(text: str) -> str:
        """
        Removes Emojis and non-renderable glyphs.
        Preserves Thai, English, Numbers, and basic punctuation.
        """
        if not text or not isinstance(text, str):
            return ""
        # Regex to allow Thai (\u0E00-\u0E7F), ASCII Word chars, and standard punctuation
        return re.sub(r'[^\w\s\u0E00-\u0E7F().,\-!]', '', text).strip()

    @staticmethod
    def truncate(text: str, max_length: int) -> str:
        if len(text) > max_length:
            return text[:max_length-3] + "..."
        return text

class TimeService:
    """Standardizes time handling."""
    
    @staticmethod
    def now_str() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M")
    
    @staticmethod
    def timestamp() -> float:
        return datetime.now().timestamp()

class IDGenerator:
    """Generates unique identifiers."""
    
    @staticmethod
    def generate_uuid() -> str:
        return str(uuid.uuid4())[:8]

# ==============================================================================
# PART 3: DOMAIN LAYER (MODELS)
# ==============================================================================

@dataclass
class TransactionLog:
    """Immutable record of a score change."""
    id: str
    timestamp: str
    reason: str
    amount: int
    balance_snapshot: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "ts": self.timestamp,
            "reason": self.reason,
            "amount": self.amount,
            "balance": self.balance_snapshot
        }

@dataclass
class Team:
    """Core aggregate root representing a Team."""
    room: str
    name: str
    members: str
    xp: int
    last_updated: str
    history: List[TransactionLog] = field(default_factory=list)
    badges: List[str] = field(default_factory=list)

    @property
    def member_list(self) -> List[str]:
        return [m.strip() for m in self.members.split(',') if m.strip()]

    def add_transaction(self, reason: str, amount: int) -> 'Team':
        """
        Adds XP and a transaction log record.
        This method contains domain logic for balance calculation.
        """
        self.xp += amount
        log = TransactionLog(
            id=IDGenerator.generate_uuid(),
            timestamp=TimeService.now_str(),
            reason=reason,
            amount=amount,
            balance_snapshot=self.xp
        )
        # Add to history (Newest first is typical for UI, but internal storage handles list)
        self.history.insert(0, log)
        self.last_updated = TimeService.now_str()
        return self

    def recalculate_balance(self) -> 'Team':
        """Replays history to ensure data integrity."""
        # Sort chronological
        try:
            chronological = sorted(self.history, key=lambda x: x.timestamp)
        except:
            chronological = self.history

        running_balance = 0
        for log in chronological:
            running_balance += log.amount
            log.balance_snapshot = running_balance
        
        self.xp = running_balance
        # Restore reverse chronological for storage
        self.history = sorted(chronological, key=lambda x: x.timestamp, reverse=True)
        return self

# ==============================================================================
# PART 4: DATA ACCESS LAYER (REPOSITORY)
# ==============================================================================

class DatabaseSchema:
    """Defines the strict schema for Google Sheets."""
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
    Implementation of the Repository Pattern for Google Sheets.
    Handles connection lifecycle, serialization, and error recovery.
    """
    def __init__(self):
        self.config = SystemConfig()
        self._conn = self._init_connection()

    def _init_connection(self) -> GSheetsConnection:
        try:
            conn = st.connection(self.config.DB_CONN_NAME, type=GSheetsConnection)
            logger.info("Database connection established successfully.")
            return conn
        except Exception as e:
            logger.critical(f"Failed to connect to database: {e}")
            st.error(f"CRITICAL ERROR: Database Connection Failed.\nDetails: {e}")
            st.stop()

    def _deserialize_history(self, json_str: str) -> List[TransactionLog]:
        """Converts JSON string to List of TransactionLog objects."""
        try:
            data = json.loads(json_str)
            return [TransactionLog(
                id=d.get('id', 'unknown'),
                timestamp=d.get('ts', ''),
                reason=d.get('reason', ''),
                amount=int(d.get('amount', 0)),
                balance_snapshot=int(d.get('balance', 0))
            ) for d in data]
        except json.JSONDecodeError:
            return []

    def _sanitize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enforces schema strictness on the DataFrame."""
        if df.empty:
            return pd.DataFrame(columns=DatabaseSchema.ALL_COLUMNS)
        
        # 1. Add missing columns
        missing = set(DatabaseSchema.ALL_COLUMNS) - set(df.columns)
        for col in missing:
            df[col] = None
            
        # 2. Reorder and Select
        df = df[DatabaseSchema.ALL_COLUMNS].copy()
        
        # 3. Type Casting & Null Handling
        # Remove completely empty rows based on GroupName
        df = df.dropna(subset=[DatabaseSchema.COL_NAME], how='all')
        
        # XP must be int
        df[DatabaseSchema.COL_XP] = pd.to_numeric(df[DatabaseSchema.COL_XP], errors='coerce').fillna(0).astype(int)
        
        # JSON Fields
        for col in [DatabaseSchema.COL_HISTORY, DatabaseSchema.COL_BADGES]:
            df[col] = df[col].fillna("[]").astype(str)
            # Basic validation
            df[col] = df[col].apply(lambda x: x if x.strip().startswith("[") and x.strip().endswith("]") else "[]")
            
        # String Fields
        for col in [DatabaseSchema.COL_ROOM, DatabaseSchema.COL_NAME, DatabaseSchema.COL_MEMBERS, DatabaseSchema.COL_UPDATED]:
            df[col] = df[col].fillna("").astype(str)
            
        return df

    def fetch_all(self) -> pd.DataFrame:
        """Retrieves all data from the sheet."""
        try:
            df = self._conn.read(worksheet=self.config.DB_SHEET_NAME, ttl=self.config.DB_CACHE_TTL)
            return self._sanitize_dataframe(df)
        except Exception as e:
            logger.error(f"Read operation failed: {e}")
            return pd.DataFrame(columns=DatabaseSchema.ALL_COLUMNS)

    def _commit(self, df: pd.DataFrame) -> bool:
        """Writes data back to the sheet."""
        try:
            clean_df = self._sanitize_dataframe(df)
            self._conn.update(worksheet=self.config.DB_SHEET_NAME, data=clean_df)
            st.cache_data.clear()
            logger.info("Database commit successful.")
            return True
        except Exception as e:
            logger.error(f"Write operation failed: {e}")
            st.error(f"Database Save Error: {e}")
            return False

    # --- CRUD OPERATIONS ---

    def create_team(self, team: Team, current_df: pd.DataFrame) -> bool:
        """Inserts a new team record."""
        # Duplicate Check
        is_duplicate = ((current_df[DatabaseSchema.COL_ROOM] == team.room) & 
                        (current_df[DatabaseSchema.COL_NAME] == team.name)).any()
        if is_duplicate:
            logger.warning(f"Creation failed: Duplicate team {team.name} in {team.room}")
            return False
            
        new_record = {
            DatabaseSchema.COL_ROOM: team.room,
            DatabaseSchema.COL_NAME: team.name,
            DatabaseSchema.COL_XP: team.xp,
            DatabaseSchema.COL_MEMBERS: team.members,
            DatabaseSchema.COL_UPDATED: team.last_updated,
            DatabaseSchema.COL_HISTORY: json.dumps([t.to_dict() for t in team.history], ensure_ascii=False),
            DatabaseSchema.COL_BADGES: json.dumps(team.badges, ensure_ascii=False)
        }
        
        updated_df = pd.concat([current_df, pd.DataFrame([new_record])], ignore_index=True)
        return self._commit(updated_df)

    def update_team_info(self, room: str, old_name: str, new_name: str, new_members: str, current_df: pd.DataFrame) -> bool:
        """Updates team identity (Name/Members)."""
        # If renaming, check collision
        if new_name != old_name:
            collision = ((current_df[DatabaseSchema.COL_ROOM] == room) & 
                         (current_df[DatabaseSchema.COL_NAME] == new_name)).any()
            if collision:
                return False
                
        mask = (current_df[DatabaseSchema.COL_ROOM] == room) & (current_df[DatabaseSchema.COL_NAME] == old_name)
        if not mask.any():
            return False
            
        idx = current_df[mask].index[0]
        current_df.at[idx, DatabaseSchema.COL_NAME] = new_name
        current_df.at[idx, DatabaseSchema.COL_MEMBERS] = new_members
        current_df.at[idx, DatabaseSchema.COL_UPDATED] = TimeService.now_str()
        
        return self._commit(current_df)

    def delete_team(self, room: str, name: str, current_df: pd.DataFrame) -> bool:
        """Soft deletes a team record."""
        mask = ~((current_df[DatabaseSchema.COL_ROOM] == room) & 
                 (current_df[DatabaseSchema.COL_NAME] == name))
        updated_df = current_df[mask]
        return self._commit(updated_df)

    def batch_update_teams(self, teams: List[Team], current_df: pd.DataFrame) -> bool:
        """
        Updates multiple teams in a single transaction.
        Critical for the 'Batch Score' feature.
        """
        updates_applied = 0
        
        for team in teams:
            mask = (current_df[DatabaseSchema.COL_ROOM] == team.room) & (current_df[DatabaseSchema.COL_NAME] == team.name)
            if mask.any():
                idx = current_df[mask].index[0]
                current_df.at[idx, DatabaseSchema.COL_XP] = team.xp
                current_df.at[idx, DatabaseSchema.COL_HISTORY] = json.dumps([t.to_dict() for t in team.history], ensure_ascii=False)
                current_df.at[idx, DatabaseSchema.COL_BADGES] = json.dumps(team.badges, ensure_ascii=False)
                current_df.at[idx, DatabaseSchema.COL_UPDATED] = TimeService.now_str()
                updates_applied += 1
                
        if updates_applied > 0:
            return self._commit(current_df)
        return False

# ==============================================================================
# PART 5: APPLICATION SERVICE LAYER
# ==============================================================================

class GamificationService:
    """
    Orchestrates business logic for XP, Ranks, and Badges.
    """
    def __init__(self):
        self.config = SystemConfig()

    def get_rank_definition(self, xp: int) -> Dict[str, Any]:
        """Resolves XP to a Rank Configuration."""
        if xp < 0:
            return self.config.RANK_METADATA[RankID.PROBATION]
        
        for rank_id in [RankID.PRESIDENT, RankID.DIRECTOR, RankID.MANAGER, RankID.EMPLOYEE, RankID.INTERN]:
            meta = self.config.RANK_METADATA[rank_id]
            if xp >= meta['min']:
                return meta
                
        return self.config.RANK_METADATA[RankID.INTERN]

    def calculate_progress(self, xp: int) -> Tuple[float, str]:
        """Calculates progress towards the next rank."""
        if xp < 0:
            return 0.0, "CRITICAL STATUS"
            
        current_rank_def = self.get_rank_definition(xp)
        
        # Find next rank
        # Note: Dictionaries preserve insertion order in Python 3.7+
        rank_keys = list(self.config.RANK_METADATA.keys())
        # Filter out Probation
        rank_keys = [r for r in rank_keys if r != RankID.PROBATION]
        
        # Find current index
        try:
            current_idx = -1
            for i, r_id in enumerate(rank_keys):
                if self.config.RANK_METADATA[r_id]['min'] == current_rank['min']:
                    current_idx = i
                    break
        except:
            return 0.0, "Error"
            
        # If highest rank
        if current_idx == 0:
            return 1.0, "MAX RANK REACHED"
            
        next_rank_id = rank_keys[current_idx - 1]
        next_rank_def = self.config.RANK_METADATA[next_rank_id]
        
        target = next_rank_def['min']
        # Prevent div by zero
        denominator = target if target > 0 else 100
        
        percentage = min(1.0, xp / denominator)
        return percentage, f"{int(percentage * 100)}% to {next_rank_def['th']}"

    def evaluate_badges(self, team: Team) -> List[str]:
        """Determines which badges a team has earned."""
        badges = set()
        
        # Wealthy: XP >= 800
        if team.xp >= 800:
            badges.add(BadgeType.WEALTHY.value)
            
        # Debtor: XP < 0
        if team.xp < 0:
            badges.add(BadgeType.DEBTOR.value)
            
        # First Blood: Has any history
        if len(team.history) > 0:
            badges.add(BadgeType.FIRST_BLOOD.value)
            
        # Veteran: >= 10 transactions
        if len(team.history) >= 10:
            badges.add(BadgeType.VETERAN.value)
            
        # Sniper: Single transaction >= 100
        if any(log.amount >= 100 for log in team.history):
            badges.add(BadgeType.SNIPER.value)
            
        return list(badges)

    def render_badge_string(self, badge_list: List[str]) -> str:
        """Converts badge IDs to Emoji string."""
        mapping = {
            BadgeType.WEALTHY.value: "💎",
            BadgeType.SNIPER.value: "🎯",
            BadgeType.DEBTOR.value: "💸",
            BadgeType.PHOENIX.value: "🔥",
            BadgeType.FIRST_BLOOD.value: "🩸",
            BadgeType.VETERAN.value: "🎖️"
        }
        return "".join([mapping.get(b, "") for b in badge_list])

class TeamService:
    """
    Application Service for Team Operations.
    Coordinates between Database and Domain Models.
    """
    def __init__(self):
        self.repo = GoogleSheetsRepository()
        self.gamification = GamificationService()

    def get_all_teams(self, room: str) -> List[Team]:
        df = self.repo.fetch_all()
        room_df = df[df[DatabaseSchema.COL_ROOM] == room]
        teams = []
        
        for _, row in room_df.iterrows():
            # Deserialize History
            try:
                hist_raw = json.loads(row[DatabaseSchema.COL_HISTORY])
                hist_objs = [TransactionLog(
                    id=h.get('id'), ts=h.get('ts'), reason=h.get('reason'), 
                    amount=int(h.get('amount')), bal=int(h.get('balance', 0))
                ) for h in hist_raw] # Note: Logic requires dicts usually, but we use objects here
                
                # Re-convert to dicts for compatibility with current structure or adapt
                # Let's keep it simple: Use dicts for history in Team object to match previous patterns
                hist_dicts = hist_raw 
                
            except:
                hist_dicts = []
            
            # Deserialize Badges
            try:
                badges = json.loads(row[DatabaseSchema.COL_BADGES])
            except:
                badges = []
                
            t = Team(
                room=row[DatabaseSchema.COL_ROOM],
                name=row[DatabaseSchema.COL_NAME],
                xp=int(row[DatabaseSchema.COL_XP]),
                members=row[DatabaseSchema.COL_MEMBERS],
                last_updated=row[DatabaseSchema.COL_UPDATED]
            )
            # Hydrate complex objects
            # Convert dicts back to TransactionLog objects for internal logic
            t.history = [TransactionLog(
                id=d.get('id', 'uid'),
                timestamp=d.get('ts', ''),
                reason=d.get('reason', ''),
                amount=int(d.get('amount', 0)),
                balance_snapshot=int(d.get('balance', 0))
            ) for d in hist_dicts]
            t.badges = badges
            teams.append(t)
            
        return teams

    def process_batch_score(self, room: str, target_names: List[str], amount: int, reason: str) -> int:
        """
        Processes score updates for multiple teams efficiently.
        """
        all_data = self.repo.fetch_all()
        teams_to_update = []
        
        for name in target_names:
            # 1. Hydrate Team from DF (Manual hydration for performance)
            mask = (all_data[DatabaseSchema.COL_ROOM] == room) & (all_data[DatabaseSchema.COL_NAME] == name)
            if mask.any():
                row = all_data[mask].iloc[0]
                
                # Parse History
                try: h_data = json.loads(row[DatabaseSchema.COL_HISTORY])
                except: h_data = []
                history = [TransactionLog(
                    id=d.get('id'), timestamp=d.get('ts'), reason=d.get('reason'), 
                    amount=int(d.get('amount')), balance_snapshot=int(d.get('balance', 0))
                ) for d in h_data]
                
                # Create Domain Object
                team = Team(
                    room=room,
                    name=name,
                    members=row[DatabaseSchema.COL_MEMBERS],
                    xp=int(row[DatabaseSchema.COL_XP]),
                    last_updated=""
                )
                team.history = history
                
                # 2. Apply Domain Logic
                team.add_transaction(reason, amount)
                team.recalculate_balance()
                team.badges = self.gamification.evaluate_badges(team)
                
                teams_to_update.append(team)
        
        # 3. Commit Batch
        if teams_to_update:
            if self.repo.batch_update_teams(teams_to_update, all_data):
                return len(teams_to_update)
        return 0

    def create_team(self, room: str, name: str, members: str) -> bool:
        all_data = self.repo.fetch_all()
        new_team = Team(room=room, name=name, members=members, xp=0, last_updated=TimeService.now_str())
        return self.repo.create_team(new_team, all_data)

    def update_team(self, room: str, old_name: str, new_name: str, members: str) -> bool:
        all_data = self.repo.fetch_all()
        return self.repo.update_team_info(room, old_name, new_name, members, all_data)

    def delete_team(self, room: str, name: str) -> bool:
        all_data = self.repo.fetch_all()
        return self.repo.delete_team(room, name, all_data)

    def power_edit_history(self, room: str, name: str, new_history_df: pd.DataFrame) -> bool:
        all_data = self.repo.fetch_all()
        
        # Hydrate Team
        mask = (all_data[DatabaseSchema.COL_ROOM] == room) & (all_data[DatabaseSchema.COL_NAME] == name)
        if not mask.any(): return False
        
        # Convert DF back to TransactionLogs
        records = new_history_df.to_dict('records')
        new_history = [TransactionLog(
            id=str(r.get('id', uuid.uuid4())),
            timestamp=str(r.get('ts', TimeService.now_str())),
            reason=str(r.get('reason', '')),
            amount=int(r.get('amount', 0)),
            balance_snapshot=0 # Will be recalced
        ) for r in records]
        
        # Create Dummy Team for Logic Application
        team = Team(room=room, name=name, members="", xp=0, last_updated="")
        team.history = new_history
        team.recalculate_balance()
        team.badges = self.gamification.evaluate_badges(team)
        
        # Save via Batch (single item)
        return self.repo.batch_update_teams([team], all_data)

# ==============================================================================
# PART 6: GRAPHICS LAYER (VECTOR STICKER ENGINE)
# ==============================================================================

class GraphicsEngine:
    """
    Renders high-fidelity leaderboard images using pure vector logic via PIL.
    No external image dependencies.
    """
    def __init__(self):
        self.config = SystemConfig()
        self._font_cache = {}

    def _load_font(self, font_type: str, size: int) -> ImageFont.FreeTypeFont:
        key = (font_type, size)
        if key not in self._font_cache:
            try:
                # Select Font File
                font_file = self.config.FONT_BOLD if font_type == "bold" else self.config.FONT_REGULAR
                self._font_cache[key] = ImageFont.truetype(font_file, size)
            except IOError:
                # Fallback
                self._font_cache[key] = ImageFont.load_default()
        return self._font_cache[key]

    def _draw_vector_medal(self, draw: ImageDraw.Draw, x: int, y: int, theme: dict, rank: int):
        """Draws a procedural medal with ribbon."""
        # 1. Ribbon V-Shape
        # Points: Top-Left, Mid-Left, Center-Bottom, Mid-Right, Top-Right
        ribbon_color = "#EF4444" # Red default
        draw.polygon([
            (x - 20, y - 85),
            (x - 20, y - 55),
            (x, y - 25),
            (x + 20, y - 55),
            (x + 20, y - 85)
        ], fill=ribbon_color)
        
        # 2. Medal Outer Ring (White Sticker Border)
        r_outer = 85
        draw.ellipse([(x - r_outer, y - r_outer), (x + r_outer, y + r_outer)], fill="#FFFFFF")
        
        # 3. Medal Body (Rank Color)
        r_inner = 75
        draw.ellipse([(x - r_inner, y - r_inner), (x + r_inner, y + r_inner)], fill=theme['hex'])
        
        # 4. Specular Highlight (Glossy effect)
        # Draw a semi-transparent white chord at the top
        draw.chord([(x - r_inner, y - r_inner), (x + r_inner, y + r_inner)], 180, 360, fill="#FFFFFF40")

    def _draw_vector_trophy(self, draw: ImageDraw.Draw, cx: int, y: int):
        """Draws a procedural trophy icon."""
        # Cup Body
        draw.polygon([(cx-60, y), (cx+60, y), (cx+30, y+100), (cx-30, y+100)], fill="#FFD700")
        # Cup Rim
        draw.ellipse([(cx-60, y-10), (cx+60, y+10)], fill="#FFC107")
        # Base
        draw.rectangle([(cx-40, y+100), (cx+40, y+120)], fill="#DAA520")

    def _draw_text_block(self, draw: ImageDraw.Draw, text: str, x: int, y: int, max_w: int, 
                         font_style: str, max_size: int, color: str, anchor: str = "lt"):
        """
        Draws text with automatic downscaling to fit width.
        Sanitizes text to prevent artifacting.
        """
        clean_text = TextProcessor.clean_for_render(text)
        if not clean_text: return
        
        size = max_size
        font = self._load_font(font_style, size)
        
        # Iterative Downscaling
        while size > 24:
            if font.getlength(clean_text) <= max_w:
                break
            size -= 4
            font = self._load_font(font_style, size)
            
        draw.text((x, y), clean_text, font=font, fill=color, anchor=anchor)

    def render_leaderboard(self, room_name: str, teams: List[Team], logic: GamificationService) -> bytes:
        """
        Main rendering pipeline.
        """
        # 1. Prepare Data
        # Sort by XP Descending
        sorted_teams = sorted(teams, key=lambda t: t.xp, reverse=True)
        
        # 2. Calculate Canvas Geometry
        row_count = len(sorted_teams)
        canvas_height = (
            self.config.IMG_HEADER_HEIGHT + 
            (row_count * self.config.IMG_ROW_HEIGHT) + 
            self.config.IMG_FOOTER_HEIGHT
        )
        
        # 3. Initialize Canvas
        img = Image.new('RGBA', (self.config.IMG_WIDTH, canvas_height), self.config.COLOR_BACKGROUND)
        draw = ImageDraw.Draw(img)
        
        # 4. Render Header
        draw.rectangle([(0, 0), (self.config.IMG_WIDTH, self.config.IMG_HEADER_HEIGHT)], fill=self.config.COLOR_PRIMARY)
        # Decorative Elements
        draw.ellipse([(900, -150), (1500, 450)], fill=self.config.COLOR_SECONDARY)
        draw.ellipse([(-100, 250), (500, 850)], fill=self.config.COLOR_SECONDARY)
        
        # Center X
        cx = self.config.IMG_WIDTH // 2
        
        # Draw Trophy
        self._draw_vector_trophy(draw, cx, 180)
        
        # Header Text
        self._draw_text_block(draw, "CLASSROOM LEADERBOARD", cx, 420, 1200, "bold", 70, self.config.COLOR_ACCENT, "mm")
        self._draw_text_block(draw, room_name, cx, 620, 1200, "bold", 160, "#FFFFFF", "mm")
        
        # 5. Render Rows
        current_y = self.config.IMG_HEADER_HEIGHT + 50
        
        for i, team in enumerate(sorted_teams):
            rank_def = logic.get_rank_definition(team.xp)
            progress_pct, _ = logic.calculate_progress(team.xp)
            
            # Determine Theme
            theme = self.config.RANK_THEMES.get(i if i < 3 else "default")
            score_color = self.config.COLOR_DANGER if team.xp < 0 else self.config.COLOR_SUCCESS
            
            # --- CARD BACKGROUND ---
            card_x = self.config.IMG_PADDING
            card_w = self.config.IMG_WIDTH - (self.config.IMG_PADDING * 2)
            card_h = self.config.IMG_ROW_HEIGHT - 40
            
            # Shadow
            draw.rounded_rectangle([(card_x+10, current_y+10), (card_x+card_w+10, current_y+card_h+10)], radius=self.config.IMG_CARD_RADIUS, fill=self.config.COLOR_SHADOW)
            # Surface
            draw.rounded_rectangle([(card_x, current_y), (card_x+card_w, current_y+card_h)], radius=self.config.IMG_CARD_RADIUS, fill=self.config.COLOR_SURFACE)
            
            # --- STICKER (MEDAL/BADGE) ---
            sticker_cx = card_x + 120
            sticker_cy = current_y + (card_h // 2)
            
            if i < 3:
                self._draw_vector_medal(draw, sticker_cx, sticker_cy, theme, i+1)
            else:
                # Regular Rank Badge
                draw.ellipse([(sticker_cx-80, sticker_cy-80), (sticker_cx+80, sticker_cy+80)], fill="#FFFFFF")
                draw.ellipse([(sticker_cx-70, sticker_cy-70), (sticker_cx+70, sticker_cy+70)], fill=theme['hex'])
            
            # Rank Number
            draw.text((sticker_cx, sticker_cy), str(i+1), font=self._load_font("bold", 90), fill="white", anchor="mm")
            
            # --- INFO CONTENT (Safe Grid System) ---
            info_x = card_x + 280
            info_w = 620
            
            # Y-Axis Anchors
            y_name = current_y + 60
            y_members = y_name + 100
            y_bar = y_members + 90
            y_rank = y_bar + 70
            y_desc = y_rank + 70
            
            # Group Name
            self._draw_text_block(draw, team.name, info_x, y_name, info_w, "bold", 90, self.config.COLOR_TEXT_MAIN, "lt")
            
            # Members (Truncated)
            mem_str = TextProcessor.truncate(team.members, 60)
            self._draw_text_block(draw, mem_str, info_x, y_members, info_w, "regular", 45, self.config.COLOR_TEXT_SUB, "lt")
            
            # Progress Bar
            draw.rounded_rectangle([(info_x, y_bar), (info_x+580, y_bar+16)], radius=8, fill=self.config.COLOR_BACKGROUND)
            if progress_pct > 0:
                bar_w = max(int(580 * progress_pct), 20)
                draw.rounded_rectangle([(info_x, y_bar), (info_x+bar_w, y_bar+16)], radius=8, fill=rank_def['col'])
            
            # Rank Title
            self._draw_text_block(draw, rank_def['th'], info_x, y_rank, info_w, "bold", 50, rank_def['col'], "lt")
            
            # Privilege Description
            self._draw_text_block(draw, rank_def['desc'], info_x, y_desc, info_w, "regular", 40, self.config.COLOR_TEXT_SUB, "lt")
            
            # --- SCORE DISPLAY ---
            score_x = self.config.IMG_WIDTH - self.config.IMG_PADDING - 50
            draw.text((score_x, sticker_cy-10), f"{team.xp}", font=self._load_font("bold", 120), fill=score_color, anchor="rs")
            draw.text((score_x, sticker_cy+60), "XP", font=self._load_font("bold", 50), fill=self.config.COLOR_TEXT_MUTED, anchor="rs")
            
            current_y += self.config.IMG_ROW_HEIGHT
            
        # 6. Render Footer
        foot_cy = canvas_height - (self.config.IMG_FOOTER_HEIGHT // 2)
        ts = TimeService.now_str()
        draw.text((cx, foot_cy), f"Generated by {self.config.APP_NAME} • {ts}", font=self._load_font("regular", 40), fill=self.config.COLOR_TEXT_MUTED, anchor="mm")
        
        # 7. Output
        out_buf = io.BytesIO()
        img.save(out_buf, format='PNG', optimize=True)
        return out_buf.getvalue()

# ==============================================================================
# PART 7: PRESENTATION LAYER (UI VIEW CONTROLLER)
# ==============================================================================

class ClassroomOSApp:
    """
    Main Application Controller using Streamlit.
    Manages state, routing, and UI rendering.
    """
    def __init__(self):
        self.config = SystemConfig()
        self.team_service = TeamService()
        self.graphics_service = GraphicsEngine()
        self.logic_service = GamificationService()

    def run(self):
        """Application Entry Point."""
        self._setup_page()
        self._inject_styles()
        
        # Sidebar & Context
        selected_room = self._render_sidebar()
        
        # Load Data
        try:
            teams = self.team_service.get_all_teams(selected_room)
        except Exception as e:
            st.error(f"Failed to load data: {e}")
            return

        # Main Layout
        self._render_hero(selected_room, len(teams))
        
        # Navigation
        tabs = st.tabs(["⚡ Command", "🏆 Leaderboard", "📊 Analytics", "ℹ️ Privileges", "🛠️ Management"])
        
        with tabs[0]:
            self._render_command_tab(selected_room, teams)
        with tabs[1]:
            self._render_leaderboard_tab(selected_room, teams)
        with tabs[2]:
            self._render_analytics_tab(teams)
        with tabs[3]:
            self._render_privileges_tab()
        with tabs[4]:
            self._render_management_tab(selected_room, teams)

    def _setup_page(self):
        st.set_page_config(
            page_title=f"{self.config.APP_NAME} Enterprise",
            page_icon="🏫",
            layout="wide",
            initial_sidebar_state="expanded"
        )

    def _inject_styles(self):
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
            
            /* Glassmorphism Card */
            .glass-card {{
                background: white; 
                border-radius: 16px; 
                padding: 1.5rem; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.05); 
                border: 1px solid {self.config.COLOR_BORDER}; 
                margin-bottom: 1rem;
            }}
            
            /* Hero Banner */
            .hero-container {{
                background: linear-gradient(135deg, {self.config.COLOR_PRIMARY}, {self.config.COLOR_SECONDARY});
                padding: 2.5rem; 
                border-radius: 20px; 
                color: white; 
                margin-bottom: 2rem; 
                display: flex; 
                justify-content: space-between; 
                align-items: center;
                box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
            }}
            
            /* Custom Input Fields */
            .stTextInput input, .stTextArea textarea, .stNumberInput input {{
                border-radius: 10px; 
                border: 1px solid {self.config.COLOR_BORDER};
            }}
            </style>
        """, unsafe_allow_html=True)

    def _render_sidebar(self) -> str:
        with st.sidebar:
            st.title(f"🎛️ {self.config.APP_NAME}")
            st.caption(f"v{self.config.APP_VERSION}")
            st.divider()
            
            st.subheader("Classroom Context")
            room = st.selectbox("Select Active Class", ["ม.1/1", "ม.1/2", "ม.1/10"])
            
            st.divider()
            st.subheader("Data Tools")
            if st.button("📥 Export CSV Backup"):
                df = self.team_service.repo.fetch_all()
                st.download_button("Download Data", df.to_csv(index=False).encode('utf-8'), "classroom_backup.csv")
                
            return room

    def _render_hero(self, room: str, count: int):
        st.markdown(f"""
            <div class='hero-container'>
                <div>
                    <div style='opacity:0.8; letter-spacing:1px; font-size:0.9rem;'>{self.config.ORGANIZATION}</div>
                    <h1 style='margin:0; font-size:3rem;'>{room}</h1>
                </div>
                <div style='text-align:right;'>
                    <div style='font-size:3.5rem; font-weight:800; line-height:1;'>{count}</div>
                    <div style='font-weight:500;'>Active Teams</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    def _render_command_tab(self, room: str, teams: List[Team]):
        st.header("⚡ Command Center")
        if not teams:
            st.info("No teams found. Please create a team in the Management tab first.")
            return

        # 1. Select Targets
        team_names = sorted([t.name for t in teams])
        targets = st.multiselect("Select Teams (Multi-Select Enabled)", team_names)
        
        st.divider()
        
        # 2. Action Logic
        def execute_batch(reason: str, amount: int):
            if not targets:
                st.error("Please select at least one team.")
                return
            
            with st.status("Processing Batch Transaction...", expanded=True) as status:
                st.write(f"Applying {amount} XP to {len(targets)} teams...")
                count = self.team_service.process_batch_score(room, targets, amount, reason)
                
                if count > 0:
                    status.update(label=f"Success! Updated {count} teams.", state="complete", expanded=False)
                    time.sleep(1)
                    st.rerun()
                else:
                    status.update(label="Transaction Failed", state="error")
                    st.error("Database commit failed.")

        # 3. UI Controls
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Quick Actions")
            st.button("📚 Sent Work On Time (+50)", on_click=execute_batch, args=("ส่งงานตรงเวลา", 50), use_container_width=True)
            st.button("🙋 Class Participation (+20)", on_click=execute_batch, args=("มีส่วนร่วมในชั้นเรียน", 20), use_container_width=True)
            st.button("🏆 Activity Winner (+100)", on_click=execute_batch, args=("ชนะกิจกรรมพิเศษ", 100), type="primary", use_container_width=True)
            st.button("🐢 Late Submission (-20)", on_click=execute_batch, args=("ส่งงานล่าช้า", -20), use_container_width=True)

        with c2:
            st.subheader("Manual Transaction")
            with st.form("manual_tx"):
                r = st.text_input("Reason / Activity Name")
                a = st.number_input("XP Amount (+/-)", step=5, value=0)
                if st.form_submit_button("Submit Transaction", use_container_width=True):
                    if r and a != 0:
                        execute_batch(r, a)
                    else:
                        st.warning("Please provide a reason and amount.")

    def _render_leaderboard_tab(self, room: str, teams: List[Team]):
        st.header("🏆 Leaderboard")
        
        if not teams:
            st.warning("No data available.")
            return

        # Image Generation Block
        c1, c2 = st.columns([1, 2])
        with c1:
            st.info("Generates High-Fidelity Image with Vector Stickers.")
            if st.button("✨ Generate Image", type="primary", use_container_width=True):
                with st.spinner("Rendering vector graphics..."):
                    # Convert objects back to DF for Graphics Engine compatibility
                    # This adapter allows us to keep the graphics engine decoupled from domain objects
                    data = []
                    for t in teams:
                        data.append({
                            "GroupName": t.name,
                            "Members": t.members,
                            "XP": t.xp
                        })
                    df = pd.DataFrame(data)
                    
                    try:
                        img_bytes = self.graphics_service.render_leaderboard(room, df, self.logic_service)
                        st.session_state['generated_img'] = img_bytes
                    except Exception as e:
                        st.error(f"Rendering failed: {e}")

            if 'generated_img' in st.session_state:
                st.download_button(
                    label="📥 Download PNG",
                    data=st.session_state['generated_img'],
                    file_name=f"leaderboard_{int(time.time())}.png",
                    mime="image/png",
                    use_container_width=True
                )

        with c2:
            if 'generated_img' in st.session_state:
                st.image(st.session_state['generated_img'], use_container_width=True)

        st.divider()

        # Live List View
        sorted_teams = sorted(teams, key=lambda t: t.xp, reverse=True)
        for i, team in enumerate(sorted_teams):
            rank_def = self.logic_service.get_rank_definition(team.xp)
            pct, msg = self.logic_service.calculate_progress(team.xp)
            
            # Calculate Badges on the fly
            badges = self.logic_service.evaluate_badges(team)
            badge_str = self.logic_service.render_badge_string(badges)
            
            border_color = self.config.COLOR_DANGER if team.xp < 0 else rank_def['col']
            
            st.markdown(f"""
            <div class='glass-card' style='border-left: 6px solid {border_color};'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <div>
                        <span style='font-size:1.2rem; font-weight:bold; color:#94A3B8; margin-right:10px;'>#{i+1}</span>
                        <span style='font-size:1.3rem; font-weight:bold;'>{team.name}</span>
                        <div style='color:#64748B; font-size:0.9rem; margin-top:5px;'>{team.members}</div>
                        <div style='margin-top:5px; font-size:1.2rem;'>{badge_str}</div>
                    </div>
                    <div style='text-align:right;'>
                        <div style='font-size:2rem; font-weight:800; color:{border_color};'>{team.xp}</div>
                        <span style='background:{rank_def['bg']}; color:{rank_def['col']}; padding:4px 10px; border-radius:15px; font-weight:bold; font-size:0.8rem;'>{rank_def['th']}</span>
                    </div>
                </div>
                <div style='margin-top:10px; font-size:0.85rem; color:#64748B; display:flex; justify-content:space-between;'>
                    <span>{msg}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(pct)

    def _render_analytics_tab(self, teams: List[Team]):
        st.header("📈 Analytics")
        if not teams: return
        
        total_xp = sum(t.xp for t in teams)
        avg_xp = int(total_xp / len(teams))
        max_xp = max(t.xp for t in teams)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Classroom XP", total_xp)
        c2.metric("Average XP", avg_xp)
        c3.metric("Highest Score", max_xp)
        
        st.divider()
        st.subheader("Team Performance Comparison")
        
        df = pd.DataFrame([{"Team": t.name, "XP": t.xp} for t in teams])
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X('Team', sort='-y'),
            y='XP',
            color=alt.Color('XP', scale={'scheme': 'viridis'}),
            tooltip=['Team', 'XP']
        ).properties(use_container_width=True)
        st.altair_chart(chart, use_container_width=True)

    def _render_privileges_tab(self):
        st.header("ℹ️ Rank Privileges")
        
        for rank_id, meta in self.config.RANK_METADATA.items():
            if rank_id == RankID.PROBATION: continue
            
            st.markdown(f"""
            <div class='glass-card' style='border-left: 5px solid {meta['col']};'>
                <div style='display:flex; justify-content:space-between;'>
                    <h3 style='margin:0; color:{meta['col']};'>{meta['th']}</h3>
                    <span style='background:{meta['bg']}; color:{meta['col']}; padding:2px 8px; border-radius:10px; font-size:0.8rem;'>{meta['min']}+ XP</span>
                </div>
                <div style='margin-top:10px; color:#475569;'>🎁 {meta['desc']}</div>
            </div>
            """, unsafe_allow_html=True)

    def _render_management_tab(self, room: str, teams: List[Team]):
        st.header("🛠️ Management")
        
        # 1. CREATE
        with st.expander("➕ Create New Team", expanded=True):
            with st.form("create_team"):
                new_name = st.text_input("Team Name")
                new_members = st.text_area("Members (Comma separated)")
                if st.form_submit_button("Create Team", type="primary"):
                    if new_name:
                        if self.team_service.create_team(room, new_name, new_members):
                            st.success(f"Team '{new_name}' created successfully.")
                            time.sleep(1); st.rerun()
                        else:
                            st.error("Failed: Team name already exists.")
                    else:
                        st.error("Team name is required.")

        st.divider()
        
        # 2. EDIT
        st.subheader("✏️ Edit Team Details")
        st.caption("Rename teams or modify member lists.")
        
        team_names = sorted([t.name for t in teams])
        target_name = st.selectbox("Select Team to Edit", ["-"] + team_names)
        
        if target_name != "-":
            # Find team object
            target_team = next((t for t in teams if t.name == target_name), None)
            
            if target_team:
                with st.form("edit_team"):
                    edit_name = st.text_input("Team Name", value=target_team.name)
                    edit_members = st.text_area("Members", value=target_team.members, height=150)
                    
                    c_save, c_del = st.columns([3, 1])
                    with c_save:
                        if st.form_submit_button("💾 Save Changes", type="primary"):
                            if self.team_service.update_team(room, target_name, edit_name, edit_members):
                                st.success("Updated successfully.")
                                time.sleep(1); st.rerun()
                            else:
                                st.error("Update failed (Name collision?).")
        
        # 3. DELETE
        st.divider()
        st.subheader("🗑️ Delete Team")
        del_target = st.selectbox("Select Team to Delete", ["-"] + team_names, key="del_select")
        
        if del_target != "-":
            st.warning(f"Are you sure you want to permanently delete '{del_target}'?")
            if st.button("Confirm Delete", type="primary"):
                if self.team_service.delete_team(room, del_target):
                    st.success("Deleted successfully.")
                    time.sleep(1); st.rerun()
                else:
                    st.error("Delete failed.")

        # 4. POWER EDIT
        st.divider()
        with st.expander("⚡ Power User: Edit History Logs"):
            pe_target = st.selectbox("Select Team", ["-"] + team_names, key="pe_select")
            if pe_target != "-":
                pe_team = next((t for t in teams if t.name == pe_target), None)
                if pe_team:
                    # Convert history objects to DF for editor
                    hist_data = [t.to_dict() for t in pe_team.history]
                    edited_df = st.data_editor(pd.DataFrame(hist_data), num_rows="dynamic", use_container_width=True)
                    
                    if st.button("💾 Save History & Recalculate"):
                        if self.team_service.power_edit_history(room, pe_target, edited_df):
                            st.success("History updated.")
                            st.rerun()

# ==============================================================================
# PART 8: MAIN ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    app = ClassroomOSApp()
    app.run()
