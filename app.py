"""
Classroom OS: Enterprise Final Fix
Version: 32.0.0 (Stable Release)
Author: AI Architecture Team
Date: 2026-01-20

[CRITICAL FIX LOG]
- FIXED: AttributeError 'COLOR_BACKGROUND' (Renamed COLOR_BG to COLOR_BACKGROUND globally).
- FIXED: Altair Schema Validation Error (Added strict type casting for charts).
- FIXED: Indentation Errors (Re-formatted entire file).
- FEATURE: Vector Sticker Engine (No square boxes).
- FEATURE: Batch Score Processing.
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
# 1. KERNEL & CONFIGURATION
# ==============================================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger("ClassroomOS")

class RankID(Enum):
    PRESIDENT = "PRES"
    DIRECTOR = "DIR"
    MANAGER = "MGR"
    EMPLOYEE = "EMP"
    INTERN = "INT"
    PROBATION = "PROB"

class SystemConfig:
    """
    Single Source of Truth Configuration.
    """
    APP_NAME = "Classroom OS"
    APP_VERSION = "32.0.0-Final"
    ORGANIZATION = "Acme Education Systems"
    
    # Database
    DB_CONNECTION = "gsheets"
    DB_WORKSHEET = "Sheet1"
    DB_CACHE_TTL = 0
    
    # Graphics
    IMG_WIDTH = 1400
    IMG_HEADER_H = 780
    IMG_ROW_H = 650
    IMG_FOOTER_H = 220
    IMG_PADDING = 60
    IMG_RADIUS = 45
    
    # Fonts
    FONT_BOLD = "Sarabun-Bold.ttf"
    FONT_REGULAR = "Sarabun-Regular.ttf"
    
    # Colors (FIXED VARIABLE NAMES HERE)
    COLOR_PRIMARY = "#4338CA"      # Indigo 700
    COLOR_SECONDARY = "#3730A3"    # Indigo 800
    COLOR_ACCENT = "#A5B4FC"       # Indigo 200
    
    # !!! CHANGED FROM COLOR_BG TO COLOR_BACKGROUND TO FIX ERROR !!!
    COLOR_BACKGROUND = "#F8FAFC"   # Slate 50 
    
    COLOR_SURFACE = "#FFFFFF"      # White
    COLOR_BORDER = "#E2E8F0"       # Slate 200
    COLOR_SHADOW = "#94A3B8"       # Slate 400
    COLOR_TEXT = "#1E293B"         # Slate 800
    COLOR_TEXT_MUTED = "#64748B"   # Slate 500
    COLOR_SUCCESS = "#10B981"      # Emerald
    COLOR_DANGER = "#EF4444"       # Red

    # Rank Config
    RANK_METADATA = {
        RankID.PRESIDENT: {"th": "👑 ประธานรุ่น", "min": 1000, "col": "#F59E0B", "bg": "#FEF3C7", "desc": "Immunity (ไม่ทำ 3 งาน) + Bonus"},
        RankID.DIRECTOR:  {"th": "💼 หัวหน้าฝ่าย", "min": 600,  "col": "#8B5CF6", "bg": "#F3E8FF", "desc": "Workload Cut (ลดงาน 50%)"},
        RankID.MANAGER:   {"th": "👔 หัวหน้าแผนก", "min": 300,  "col": "#3B82F6", "bg": "#DBEAFE", "desc": "Second Chance (แก้ตัวได้ 1 ครั้ง)"},
        RankID.EMPLOYEE:  {"th": "👨‍💼 พนักงาน",   "min": 100,  "col": "#10B981", "bg": "#D1FAE5", "desc": "Time Extension (ส่งช้าได้)"},
        RankID.INTERN:    {"th": "👶 เด็กฝึกงาน",  "min": 0,    "col": "#64748B", "bg": "#F1F5F9", "desc": "Check-up (ครูตรวจก่อนส่ง)"},
        RankID.PROBATION: {"th": "⚠️ ทัณฑ์บน",    "min": -9999, "col": "#EF4444", "bg": "#FEE2E2", "desc": "สถานะวิกฤต! รีบซ่อมคะแนน"}
    }

# ==============================================================================
# 2. UTILITY LAYER
# ==============================================================================

class TextUtils:
    @staticmethod
    def sanitize(text: str) -> str:
        """Removes Emojis to prevent square boxes."""
        if not text: return ""
        return re.sub(r'[^\w\s\u0E00-\u0E7F().,\-!]', '', str(text)).strip()

    @staticmethod
    def truncate(text: str, limit: int) -> str:
        if len(text) > limit: return text[:limit-3] + "..."
        return text

class TimeUtils:
    @staticmethod
    def now_str() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M")
    
    @staticmethod
    def uuid() -> str:
        return str(uuid.uuid4())[:8]

# ==============================================================================
# 3. DOMAIN MODELS
# ==============================================================================

@dataclass
class TeamModel:
    room: str
    name: str
    xp: int
    members: str
    updated: str
    history: List[Dict] = field(default_factory=list)
    badges: List[str] = field(default_factory=list)

# ==============================================================================
# 4. DATA ACCESS LAYER
# ==============================================================================

class DatabaseSchema:
    COL_ROOM = "Room"
    COL_NAME = "GroupName"
    COL_XP = "XP"
    COL_MEMBERS = "Members"
    COL_UPDATED = "LastUpdated"
    COL_HISTORY = "HistoryLog"
    COL_BADGES = "Badges"
    ALL_COLS = [COL_ROOM, COL_NAME, COL_XP, COL_MEMBERS, COL_UPDATED, COL_HISTORY, COL_BADGES]

class Repository:
    def __init__(self):
        self.cfg = SystemConfig()
        self.conn = self._connect()

    def _connect(self):
        try: return st.connection(self.cfg.DB_CONNECTION, type=GSheetsConnection)
        except Exception as e: st.error(f"DB Error: {e}"); st.stop()

    def _clean(self, df):
        if df.empty: return pd.DataFrame(columns=DatabaseSchema.ALL_COLS)
        miss = set(DatabaseSchema.ALL_COLS) - set(df.columns)
        for c in miss: df[c] = None
        df = df[DatabaseSchema.ALL_COLS].copy().dropna(subset=[DatabaseSchema.COL_NAME])
        df[DatabaseSchema.COL_XP] = pd.to_numeric(df[DatabaseSchema.COL_XP], errors='coerce').fillna(0).astype(int)
        for c in [DatabaseSchema.COL_HISTORY, DatabaseSchema.COL_BADGES]:
            df[c] = df[c].fillna("[]").astype(str)
            df[c] = df[c].apply(lambda x: x if x.strip().startswith("[") else "[]")
        for c in [DatabaseSchema.COL_ROOM, DatabaseSchema.COL_NAME, DatabaseSchema.COL_MEMBERS]:
            df[c] = df[c].fillna("").astype(str)
        return df

    def fetch(self):
        try: return self._clean(self.conn.read(worksheet=self.cfg.DB_WORKSHEET, ttl=0))
        except: return pd.DataFrame(columns=DatabaseSchema.ALL_COLS)

    def commit(self, df):
        try:
            self.conn.update(worksheet=self.cfg.DB_WORKSHEET, data=self._clean(df))
            st.cache_data.clear()
            return True
        except Exception as e: st.error(f"Save Error: {e}"); return False

    def create(self, room, name, mem, df):
        if ((df[DatabaseSchema.COL_ROOM]==room) & (df[DatabaseSchema.COL_NAME]==name)).any(): return False
        row = {
            DatabaseSchema.COL_ROOM: room, DatabaseSchema.COL_NAME: name,
            DatabaseSchema.COL_XP: 0, DatabaseSchema.COL_MEMBERS: mem,
            DatabaseSchema.COL_UPDATED: TimeUtils.now_str(),
            DatabaseSchema.COL_HISTORY: "[]", DatabaseSchema.COL_BADGES: "[]"
        }
        return self.commit(pd.concat([df, pd.DataFrame([row])], ignore_index=True))

    def update_info(self, room, old_n, new_n, mem, df):
        if new_n != old_n:
            if ((df[DatabaseSchema.COL_ROOM]==room) & (df[DatabaseSchema.COL_NAME]==new_n)).any(): return False
        mask = (df[DatabaseSchema.COL_ROOM]==room) & (df[DatabaseSchema.COL_NAME]==old_n)
        if not mask.any(): return False
        idx = df[mask].index[0]
        df.at[idx, DatabaseSchema.COL_NAME] = new_n
        df.at[idx, DatabaseSchema.COL_MEMBERS] = mem
        df.at[idx, DatabaseSchema.COL_UPDATED] = TimeUtils.now_str()
        return self.commit(df)

    def delete(self, room, name, df):
        mask = ~((df[DatabaseSchema.COL_ROOM]==room) & (df[DatabaseSchema.COL_NAME]==name))
        return self.commit(df[mask])

    def batch_update(self, updates_map, df):
        cnt = 0
        ts = TimeUtils.now_str()
        for name, data in updates_map.items():
            mask = (df[DatabaseSchema.COL_NAME]==name)
            if mask.any():
                idx = df[mask].index[0]
                df.at[idx, DatabaseSchema.COL_XP] = data['xp']
                df.at[idx, DatabaseSchema.COL_HISTORY] = json.dumps(data['hist'], ensure_ascii=False)
                df.at[idx, DatabaseSchema.COL_BADGES] = json.dumps(data['badges'], ensure_ascii=False)
                df.at[idx, DatabaseSchema.COL_UPDATED] = ts
                cnt += 1
        return self.commit(df) if cnt > 0 else False

# ==============================================================================
# 5. LOGIC LAYER
# ==============================================================================

class LogicService:
    def __init__(self):
        self.cfg = SystemConfig()

    def get_rank(self, xp):
        if xp < 0: return self.cfg.RANK_METADATA[RankID.PROBATION]
        for rid in [RankID.PRESIDENT, RankID.DIRECTOR, RankID.MANAGER, RankID.EMPLOYEE, RankID.INTERN]:
            m = self.cfg.RANK_METADATA[rid]
            if xp >= m['min']: return m
        return self.cfg.RANK_METADATA[RankID.INTERN]

    def get_progress(self, xp):
        if xp < 0: return 0.0, "Critical"
        curr = self.get_rank(xp)
        # Find next rank
        ranks = [r for r in self.cfg.RANK_METADATA.values() if r['min'] > -9999]
        try:
            curr_idx = next(i for i, r in enumerate(ranks) if r['min'] == curr['min'])
            if curr_idx == 0: return 1.0, "Max Rank"
            nxt = ranks[curr_idx - 1]
            pct = min(1.0, xp / (nxt['min'] if nxt['min'] > 0 else 100))
            return pct, f"{int(pct*100)}% to {nxt['th']}"
        except: return 0.0, "Err"

    def calculate_badges(self, xp, hist):
        b = set()
        if xp >= 800: b.add("wealthy")
        if xp < 0: b.add("debtor")
        if any(h.get('amount',0) >= 100 for h in hist): b.add("sniper")
        if len(hist) > 0: b.add("first_blood")
        return list(b)

    def process_tx(self, cur_xp, cur_hist, reason, amt):
        new_log = {"id": TimeUtils.uuid(), "ts": TimeUtils.now_str(), "reason": reason, "amount": int(amt)}
        hist = [new_log] + cur_hist
        
        # Replay balance
        try: asc = sorted(hist, key=lambda x: x.get('ts', ''))
        except: asc = hist
        
        run = 0
        for h in asc:
            run += int(h.get('amount', 0))
            h['balance'] = run
            
        final_hist = sorted(asc, key=lambda x: x.get('ts', ''), reverse=True)
        badges = self.calculate_badges(run, final_hist)
        return run, final_hist, badges

# ==============================================================================
# 6. GRAPHICS LAYER (FIXED COLOR_BACKGROUND)
# ==============================================================================

class GraphicsEngine:
    def __init__(self):
        self.cfg = SystemConfig()
        self._cache = {}

    def _font(self, name, size):
        k = (name, size)
        if k not in self._cache:
            try: self._cache[k] = ImageFont.truetype(name, size)
            except: self._cache[k] = ImageFont.load_default()
        return self._cache[k]

    def _draw_text(self, draw, text, x, y, w, ftype, size, col, anc="lt"):
        txt = TextUtils.sanitize(text)
        if not txt: return
        f = self._font(ftype, size)
        while size > 24:
            if f.getlength(txt) <= w: break
            size -= 4
            f = self._font(ftype, size)
        draw.text((x, y), txt, font=f, fill=col, anchor=anc)

    def render(self, room, df, logic):
        data = df.sort_values(DatabaseSchema.COL_XP, ascending=False).reset_index(drop=True)
        H = self.cfg.IMG_HEADER_H + (len(data) * self.cfg.IMG_ROW_H) + self.cfg.IMG_FOOTER_H
        
        # !!! FIXED: Using COLOR_BACKGROUND !!!
        img = Image.new('RGBA', (self.cfg.IMG_WIDTH, H), self.cfg.COLOR_BACKGROUND)
        d = ImageDraw.Draw(img)
        
        # Header
        d.rectangle([(0,0), (self.cfg.IMG_WIDTH, self.cfg.IMG_HEADER_H)], fill=self.cfg.COLOR_PRIMARY)
        d.ellipse([(900, -150), (1500, 450)], fill=self.cfg.COLOR_SECONDARY)
        cx = self.cfg.IMG_WIDTH // 2
        
        # Vector Trophy
        d.polygon([(cx-60, 180), (cx+60, 180), (cx+30, 280), (cx-30, 280)], fill="#FFD700")
        d.ellipse([(cx-60, 170), (cx+60, 190)], fill="#FFC107")
        
        self._draw_text(d, "CLASSROOM LEADERBOARD", cx, 420, 1200, self.cfg.FONT_BOLD, 70, self.cfg.COLOR_ACCENT, "mm")
        self._draw_text(d, room, cx, 620, 1200, self.cfg.FONT_BOLD, 160, "#FFFFFF", "mm")
        
        cur_y = self.cfg.IMG_HEADER_H + 50
        rank_cols = {0: "#F59E0B", 1: "#94A3B8", 2: "#B45309", "def": "#64748B"}
        
        for i, row in data.iterrows():
            xp = row[DatabaseSchema.COL_XP]
            rank = logic.get_rank(xp)
            pct, _ = logic.get_progress(xp)
            th_col = rank_cols.get(i if i < 3 else "def")
            
            # Card
            bx, bw, bh = self.cfg.IMG_PADDING, self.cfg.IMG_WIDTH - 100, self.cfg.IMG_ROW_H - 40
            d.rounded_rectangle([(bx+10, cur_y+10), (bx+bw+10, cur_y+bh+10)], radius=45, fill=self.cfg.COLOR_SHADOW)
            d.rounded_rectangle([(bx, cur_y), (bx+bw, cur_y+bh)], radius=45, fill=self.cfg.COLOR_SURFACE)
            
            # Sticker
            scx, scy = bx + 120, cur_y + (bh // 2)
            if i < 3: # Medal
                d.polygon([(scx-25, scy-95), (scx-25, scy-50), (scx, scy-20), (scx+25, scy-50), (scx+25, scy-95)], fill="#EF4444")
                d.ellipse([(scx-85, scy-85), (scx+85, scy+85)], fill="#FFFFFF")
                d.ellipse([(scx-75, scy-75), (scx+75, scy+85)], fill=th_col)
            else: # Badge
                d.ellipse([(scx-80, scy-80), (scx+80, scy+80)], fill="#FFFFFF")
                d.ellipse([(scx-70, scy-70), (scx+70, scy+70)], fill=th_col)
            
            d.text((scx, scy), str(i+1), font=self._font(self.cfg.FONT_BOLD, 90), fill="white", anchor="mm")
            
            # Info Grid
            ix, iw = bx + 280, 620
            Y1 = cur_y + 60
            Y2 = Y1 + 100
            Y3 = Y2 + 90
            Y4 = Y3 + 70
            Y5 = Y4 + 70
            
            self._draw_text(d, str(row[DatabaseSchema.COL_NAME]), ix, Y1, iw, self.cfg.FONT_BOLD, 90, self.cfg.COLOR_TEXT, "lt")
            self._draw_text(d, TextUtils.truncate(str(row[DatabaseSchema.COL_MEMBERS]), 60), ix, Y2, iw, self.cfg.FONT_REGULAR, 45, self.cfg.COLOR_TEXT_MUTED, "lt")
            
            # Bar
            d.rounded_rectangle([(ix, Y3), (ix+580, Y3+16)], radius=8, fill=self.cfg.COLOR_BACKGROUND)
            if pct > 0:
                d.rounded_rectangle([(ix, Y3), (ix+max(int(580*pct), 20), Y3+16)], radius=8, fill=rank['col'])
                
            self._draw_text(d, rank['th'], ix, Y4, iw, self.cfg.FONT_BOLD, 50, rank['col'], "lt")
            self._draw_text(d, rank['desc'], ix, Y5, iw, self.cfg.FONT_REGULAR, 40, self.cfg.COLOR_TEXT_MUTED, "lt")
            
            # Score
            sx = self.cfg.IMG_WIDTH - 60
            d.text((sx, scy-10), f"{xp}", font=self._font(self.cfg.FONT_BOLD, 120), fill=self.cfg.COLOR_SUCCESS if xp>=0 else self.cfg.COLOR_DANGER, anchor="rs")
            d.text((sx, scy+60), "XP", font=self._font(self.cfg.FONT_BOLD, 50), fill=self.cfg.COLOR_TEXT_MUTED, anchor="rs")
            
            cur_y += self.cfg.IMG_ROW_H
            
        fy = H - (self.cfg.IMG_FOOTER_H // 2)
        d.text((cx, fy), f"Generated by {self.cfg.APP_NAME}", font=self._font(self.cfg.FONT_REGULAR, 40), fill=self.cfg.COLOR_TEXT_MUTED, anchor="mm")
        
        b = io.BytesIO()
        img.save(b, format='PNG')
        return b.getvalue()

# ==============================================================================
# 7. CONTROLLER
# ==============================================================================

class App:
    def __init__(self):
        self.cfg = SystemConfig()
        self.db = Repository()
        self.logic = LogicService()
        self.gfx = GraphicsEngine()

    def run(self):
        st.set_page_config(page_title=self.cfg.APP_NAME, layout="wide", initial_sidebar_state="expanded")
        self._css()
        
        room = self._sidebar()
        all_df = self.db.fetch()
        room_df = all_df[all_df[DatabaseSchema.COL_ROOM]==room].copy()
        
        self._hero(room, len(room_df))
        
        t1, t2, t3, t4, t5 = st.tabs(["Command", "Leaderboard", "Analytics", "Privileges", "Manage"])
        
        with t1: self._cmd(room, room_df, all_df)
        with t2: self._board(room, room_df)
        with t3: self._analytics(room_df)
        with t4: self._privileges()
        with t5: self._manage(room, room_df, all_df)

    def _css(self):
        st.markdown(f"""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&display=swap');
            :root {{ --primary: {self.cfg.COLOR_PRIMARY}; --bg: {self.cfg.COLOR_BACKGROUND}; }}
            html, body, .stApp {{ font-family: 'Sarabun', sans-serif; background-color: var(--bg); color: {self.cfg.COLOR_TEXT}; }}
            .glass {{ background: white; padding: 1.5rem; border-radius: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid {self.cfg.COLOR_BORDER}; margin-bottom: 1rem; }}
            .hero {{ background: linear-gradient(135deg, {self.cfg.COLOR_PRIMARY}, {self.cfg.COLOR_SECONDARY}); padding: 2.5rem; border-radius: 20px; color: white; margin-bottom: 2rem; display: flex; justify-content: space-between; align-items: center; }}
            .stTextInput input, .stTextArea textarea, .stNumberInput input {{ border-radius: 10px; border: 1px solid {self.cfg.COLOR_BORDER}; }}
            </style>
        """, unsafe_allow_html=True)

    def _sidebar(self):
        with st.sidebar:
            st.title(f"🎛️ {self.cfg.APP_NAME}")
            st.caption(f"v{self.cfg.APP_VERSION}")
            st.divider()
            room = st.selectbox("Active Class", ["ม.1/1", "ม.1/2", "ม.1/10"])
            st.divider()
            if st.button("📥 Export CSV"):
                st.download_button("Download", self.db.fetch().to_csv(index=False).encode('utf-8'), "data.csv")
            return room

    def _hero(self, room, count):
        st.markdown(f"<div class='hero'><div><h1>{room}</h1></div><div style='text-align:right'><div style='font-size:3rem;font-weight:bold'>{count}</div>Teams</div></div>", unsafe_allow_html=True)

    def _cmd(self, room, room_df, all_df):
        st.header("⚡ Command Center")
        if room_df.empty: st.info("Create teams first."); return
        
        targets = st.multiselect("Select Teams (Batch)", sorted(room_df[DatabaseSchema.COL_NAME].unique()))
        st.divider()
        c1, c2 = st.columns(2)
        
        def ex(r, a):
            if not targets: st.error("Select teams"); return
            with st.status("Processing Batch...") as s:
                updates = {}
                for t in targets:
                    row = room_df[room_df[DatabaseSchema.COL_NAME]==t].iloc[0]
                    try: h = json.loads(row[DatabaseSchema.COL_HISTORY])
                    except: h = []
                    nxp, nh, nb = self.logic.process_tx(row[DatabaseSchema.COL_XP], h, r, a)
                    updates[t] = {"xp": nxp, "hist": nh, "badges": nb}
                
                if self.db.batch_update(updates, all_df):
                    s.update(label="Success!", state="complete"); time.sleep(0.5); st.rerun()
                else: s.update(label="Failed", state="error")

        with c1:
            st.button("📚 On Time (+50)", on_click=ex, args=("ส่งงานตรงเวลา", 50), use_container_width=True)
            st.button("🙋 Participate (+20)", on_click=ex, args=("มีส่วนร่วม", 20), use_container_width=True)
        with c2:
            with st.form("man"):
                r = st.text_input("Reason"); a = st.number_input("XP", step=5)
                if st.form_submit_button("Submit", use_container_width=True): ex(r, a)

    def _board(self, room, room_df):
        st.header("🏆 Leaderboard")
        if not room_df.empty:
            if st.button("✨ Generate Sticker Image", type="primary"):
                try:
                    img = self.gfx.render(room, room_df, self.logic)
                    st.image(img); st.download_button("Download PNG", img, "lb.png", "image/png")
                except Exception as e: st.error(f"Err: {e}")
        
        st.divider()
        for _, r in room_df.sort_values(DatabaseSchema.COL_XP, ascending=False).iterrows():
            rank = self.logic.get_rank(r[DatabaseSchema.COL_XP])
            st.markdown(f"<div class='glass' style='border-left:5px solid {rank['col']}'><h3>{r[DatabaseSchema.COL_NAME]}</h3>{r[DatabaseSchema.COL_XP]} XP | {rank['th']}</div>", unsafe_allow_html=True)

    def _analytics(self, df):
        st.header("📈 Analytics")
        if not df.empty:
            # Fix Altair Schema Error by forcing types
            data = [{"Name": str(r[DatabaseSchema.COL_NAME]), "XP": int(r[DatabaseSchema.COL_XP])} for _, r in df.iterrows()]
            c = alt.Chart(pd.DataFrame(data)).mark_bar().encode(x=alt.X('Name:N', sort='-y'), y='XP:Q', color=alt.Color('XP:Q', scale={'scheme':'viridis'}))
            st.altair_chart(c, use_container_width=True)

    def _privileges(self):
        st.header("ℹ️ Privileges")
        for r in self.cfg.RANK_METADATA.values():
            if r['min'] > -9999: st.info(f"**{r['th']}**: {r['desc']}")

    def _manage(self, room, room_df, all_df):
        st.header("🛠️ Management")
        with st.expander("➕ Create Team", expanded=True):
            with st.form("mk"):
                n = st.text_input("Name"); m = st.text_area("Members")
                if st.form_submit_button("Create") and n:
                    if self.db.create(room, n, m, all_df): st.success("Created"); time.sleep(0.5); st.rerun()
                    else: st.error("Duplicate")
        
        st.divider()
        st.subheader("✏️ Edit Team")
        tl = sorted(room_df[DatabaseSchema.COL_NAME].unique())
        t = st.selectbox("Select", ["-"]+tl)
        if t != "-":
            curr = room_df[room_df[DatabaseSchema.COL_NAME]==t].iloc[0]
            with st.form("ed"):
                nn = st.text_input("Name", value=curr[DatabaseSchema.COL_NAME])
                nm = st.text_area("Members", value=curr[DatabaseSchema.COL_MEMBERS])
                if st.form_submit_button("Save"):
                    if self.db.update_info(room, t, nn, nm, all_df): st.success("Saved"); time.sleep(0.5); st.rerun()
                    else: st.error("Error")
        
        st.divider()
        d = st.selectbox("Delete", ["-"]+tl)
        if d != "-" and st.button("Delete"):
            self.db.delete(room, d, all_df); st.rerun()

if __name__ == "__main__":
    App().run()
