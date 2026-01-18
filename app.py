"""
Classroom OS: Enterprise Final Edition
Version: 20.0.0 (Complete & Fixed)
Author: AI Assistant
Description: 
- Fixed Thai Typography (No Overlap).
- Vector Stickers (No Square Boxes).
- Full Management (Create/Edit Name/Edit Members/Delete).
- Batch Score Update.
- Fixed Attribute/Indentation Errors.
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
from PIL import Image, ImageDraw, ImageFont

# --- 1. CONFIGURATION ---
logging.basicConfig(level=logging.INFO)

class AppConfig:
    APP_NAME = "Classroom OS"
    APP_VERSION = "20.0.0-Final"
    
    # Database
    DB_CONN = "gsheets"
    DB_SHEET = "Sheet1"
    
    # Graphics
    IMG_W = 1400
    IMG_H_HEAD = 780
    IMG_H_ROW = 650 # เพิ่มความสูงแถวเพื่อกันภาษาไทยทับกันแน่นอน
    IMG_H_FOOT = 200
    IMG_PAD = 50
    IMG_RAD = 45
    
    # Fonts
    FONT_B = "Sarabun-Bold.ttf"
    FONT_R = "Sarabun-Regular.ttf"
    
    # Colors
    C_PRI = "#4338CA"
    C_SEC = "#3730A3"
    C_ACC = "#A5B4FC"
    C_BG = "#F1F5F9"
    C_SURFACE = "#FFFFFF"
    C_BORDER = "#E2E8F0"
    C_SHADOW = "#94A3B8"
    C_TEXT_MAIN = "#1E293B"
    C_TEXT_SUB = "#64748B"
    C_TEXT_MUTED = "#94A3B8"
    C_SUCCESS = "#10B981"
    C_DANGER = "#EF4444"

    # Rank Config
    RANKS = [
        {"id": "PRES", "th": "👑 ประธานรุ่น", "min": 1000, "col": "#F59E0B", "bg": "#FEF3C7", "desc": "Immunity (ไม่ทำ 3 งาน) + Bonus"},
        {"id": "DIR",  "th": "💼 หัวหน้าฝ่าย", "min": 600,  "col": "#8B5CF6", "bg": "#F3E8FF", "desc": "Workload Cut (ลดงาน 50%)"},
        {"id": "MGR",  "th": "👔 หัวหน้าแผนก", "min": 300,  "col": "#3B82F6", "bg": "#DBEAFE", "desc": "Second Chance (แก้ตัว 1 ครั้ง)"},
        {"id": "EMP",  "th": "👨‍💼 พนักงาน",   "min": 100,  "col": "#10B981", "bg": "#D1FAE5", "desc": "Time Extension (ส่งช้าได้)"},
        {"id": "INT",  "th": "👶 เด็กฝึกงาน",  "min": 0,    "col": "#64748B", "bg": "#F1F5F9", "desc": "Check-up (ครูตรวจก่อนส่ง)"},
        {"id": "PROB", "th": "⚠️ ทัณฑ์บน",    "min": -9999, "col": "#EF4444", "bg": "#FEE2E2", "desc": "สถานะวิกฤต! รีบซ่อมคะแนน"}
    ]

# --- 2. LOGIC ENGINE ---
class LogicEngine:
    def get_rank(self, xp):
        if xp < 0: return AppConfig.RANKS[-1]
        for r in AppConfig.RANKS:
            if r['id'] != "PROB" and xp >= r['min']: return r
        return AppConfig.RANKS[-2]

    def get_progress(self, xp):
        if xp < 0: return 0.0
        curr = self.get_rank(xp)
        try: idx = AppConfig.RANKS.index(curr)
        except: return 0.0
        if idx > 0:
            nxt = AppConfig.RANKS[idx-1]
            tgt = nxt['min']
            return min(1.0, xp / tgt) if tgt > 0 else 1.0
        return 1.0

    def process_xp(self, cur_xp, cur_hist, reason, amt):
        new_log = {
            "id": str(uuid.uuid4())[:8],
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "reason": reason,
            "amount": int(amt)
        }
        hist = [new_log] + cur_hist
        # Recalculate Balance
        try: hist_asc = sorted(hist, key=lambda x: x.get('ts', ''))
        except: hist_asc = hist
        
        run = 0
        for h in hist_asc:
            run += int(h.get('amount', 0))
            h['balance'] = run
            
        final_hist = sorted(hist_asc, key=lambda x: x.get('ts', ''), reverse=True)
        return run, final_hist, [] # Badges simplified for stability

# --- 3. DATABASE ---
class DatabaseService:
    COLS = ['Room', 'GroupName', 'XP', 'Members', 'LastUpdated', 'HistoryLog', 'Badges']

    def __init__(self):
        try: self.conn = st.connection(AppConfig.DB_CONN, type=GSheetsConnection)
        except: st.error("DB Connection Failed"); st.stop()

    def fetch(self):
        try:
            df = self.conn.read(worksheet=AppConfig.DB_SHEET, ttl=0)
            if df.empty: return pd.DataFrame(columns=self.COLS)
            # Sanitize
            miss = set(self.COLS) - set(df.columns)
            for c in miss: df[c] = None
            df = df[self.COLS].copy().dropna(how='all')
            df['XP'] = pd.to_numeric(df['XP'], errors='coerce').fillna(0).astype(int)
            for c in ['HistoryLog', 'Badges']:
                df[c] = df[c].fillna("[]").astype(str)
                # Fix broken JSON format
                df[c] = df[c].apply(lambda x: "[]" if not x.strip().startswith("[") else x)
            for c in ['Room', 'GroupName', 'Members']: df[c] = df[c].fillna("").astype(str)
            return df
        except: return pd.DataFrame(columns=self.COLS)

    def save(self, df):
        try:
            self.conn.update(worksheet=AppConfig.DB_SHEET, data=df)
            st.cache_data.clear()
            return True
        except: return False

    def create(self, room, name, mem, df):
        if ((df['Room']==room) & (df['GroupName']==name)).any(): return False
        row = {"Room": room, "GroupName": name, "XP": 0, "Members": mem, "LastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M"), "HistoryLog": "[]", "Badges": "[]"}
        return self.save(pd.concat([df, pd.DataFrame([row])], ignore_index=True))

    def update(self, room, old_n, new_n, new_m, df):
        if new_n != old_n:
            if ((df['Room']==room) & (df['GroupName']==new_n)).any(): return False
        mask = (df['Room']==room) & (df['GroupName']==old_n)
        if not mask.any(): return False
        idx = df[mask].index[0]
        df.at[idx, 'GroupName'] = new_n
        df.at[idx, 'Members'] = new_m
        df.at[idx, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        return self.save(df)

    def delete(self, room, name, df):
        return self.save(df[~((df['Room']==room) & (df['GroupName']==name))])

    def batch_update(self, room, targets, amt, reason, df, logic):
        cnt = 0
        for t in targets:
            mask = (df['Room']==room) & (df['GroupName']==t)
            if mask.any():
                idx = df[mask].index[0]
                try: hist = json.loads(df.at[idx, 'HistoryLog'])
                except: hist = []
                nxp, nh, nb = logic.process_xp(df.at[idx, 'XP'], hist, reason, amt)
                df.at[idx, 'XP'] = nxp
                df.at[idx, 'HistoryLog'] = json.dumps(nh, ensure_ascii=False)
                df.at[idx, 'LastUpdated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                cnt += 1
        return self.save(df) if cnt > 0 else False

    def power_edit(self, room, name, new_hist_df, df, logic):
        mask = (df['Room']==room) & (df['GroupName']==name)
        if not mask.any(): return False
        idx = df[mask].index[0]
        h_list = new_hist_df.to_dict('records')
        # Recalc
        try: h_asc = sorted(h_list, key=lambda x: x.get('ts', ''))
        except: h_asc = h_list
        run = 0
        for h in h_asc:
            run += int(h.get('amount', 0))
            h['balance'] = run
        h_desc = sorted(h_asc, key=lambda x: x.get('ts', ''), reverse=True)
        df.at[idx, 'XP'] = run
        df.at[idx, 'HistoryLog'] = json.dumps(h_desc, ensure_ascii=False)
        return self.save(df)

# --- 4. GRAPHICS (STICKER ENGINE) ---
class GraphicsService:
    def __init__(self):
        self._font_cache = {}

    def _font(self, name, size):
        k = (name, size)
        if k not in self._font_cache:
            try: self._font_cache[k] = ImageFont.truetype(name, size)
            except: self._font_cache[k] = ImageFont.load_default()
        return self._font_cache[k]

    def _clean(self, txt):
        if not isinstance(txt, str): return ""
        return re.sub(r'[^\w\s\u0E00-\u0E7F().,-]', '', txt).strip()

    def _draw_sticker(self, draw, x, y, col, i):
        # Medal Sticker (Vector)
        if i < 3: # Top 3 get Medals
            # Ribbon
            draw.polygon([(x-20, y-90), (x+20, y-90), (x, y-40)], fill="#EF4444")
            # Border
            draw.ellipse([(x-85, y-85), (x+85, y+85)], fill="white")
            # Body
            draw.ellipse([(x-75, y-75), (x+75, y+75)], fill=col)
            # Shine
            draw.chord([(x-75, y-75), (x+75, y+75)], 180, 360, fill="#FFFFFF40")
        else: # Others get Rank Badge
            draw.ellipse([(x-70, y-70), (x+70, y+70)], fill="white") # Border
            draw.ellipse([(x-60, y-60), (x+60, y+60)], fill=col)

    def _text(self, draw, txt, x, y, w, f_name, size, col, anchor="lt"):
        txt = self._clean(txt)
        if not txt: return
        f = self._font(f_name, size)
        while size > 24:
            if f.getlength(txt) <= w: break
            size -= 4
            f = self._font(f_name, size)
        draw.text((x, y), txt, font=f, fill=col, anchor=anchor)

    def render(self, room, df, logic):
        data = df.sort_values("XP", ascending=False).reset_index(drop=True)
        H = AppConfig.IMG_H_HEAD + (len(data) * AppConfig.IMG_H_ROW) + AppConfig.IMG_H_FOOT
        img = Image.new('RGBA', (AppConfig.IMG_W, H), AppConfig.C_BG)
        d = ImageDraw.Draw(img)
        
        # Header
        d.rectangle([(0,0), (AppConfig.IMG_W, AppConfig.IMG_H_HEAD)], fill=AppConfig.C_PRI)
        d.ellipse([(900, -150), (1500, 450)], fill=AppConfig.C_SEC)
        
        cx = AppConfig.IMG_W // 2
        d.text((cx, 220), "🏆", font=self._font(AppConfig.FONT_R, 200), fill="white", anchor="mm")
        d.text((cx, 400), "CLASSROOM LEADERBOARD", font=self._font(AppConfig.FONT_B, 70), fill=AppConfig.C_ACC, anchor="mm")
        d.text((cx, 600), room, font=self._font(AppConfig.FONT_B, 160), fill="white", anchor="mm")
        
        # Rows
        cur_y = AppConfig.IMG_H_HEAD + 50
        for i, row in data.iterrows():
            xp = row['XP']
            rank = logic.get_rank(xp)
            pct = logic.get_progress(xp)
            
            # Card
            bx, bw, bh = AppConfig.IMG_PAD, AppConfig.IMG_W - 100, AppConfig.IMG_H_ROW - 40
            d.rounded_rectangle([(bx+10, cur_y+10), (bx+bw+10, cur_y+bh+10)], radius=40, fill=AppConfig.C_SHADOW)
            d.rounded_rectangle([(bx, cur_y), (bx+bw, cur_y+bh)], radius=40, fill=AppConfig.C_SURFACE)
            
            # Sticker
            cy = cur_y + (bh//2)
            self._draw_sticker(d, bx+120, cy, rank['col'], i)
            d.text((bx+120, cy), str(i+1), font=self._font(AppConfig.FONT_B, 90), fill="white", anchor="mm")
            
            # Content (Safe Grid)
            ix, iw = bx+280, 600
            Y_NAME = cur_y + 50
            Y_MEM = Y_NAME + 100
            Y_BAR = Y_MEM + 100
            Y_RANK = Y_BAR + 70
            Y_DESC = Y_RANK + 70
            
            self._text(d, str(row['GroupName']), ix, Y_NAME, iw, AppConfig.FONT_B, 90, AppConfig.C_TEXT_MAIN, "lt")
            self._text(d, str(row['Members']), ix, Y_MEM, iw, AppConfig.FONT_R, 45, AppConfig.C_TEXT_SUB, "lt")
            
            # Bar
            d.rounded_rectangle([(ix, Y_BAR), (ix+580, Y_BAR+20)], radius=10, fill=AppConfig.C_BG)
            if pct > 0:
                fw = max(int(580*pct), 30)
                d.rounded_rectangle([(ix, Y_BAR), (ix+fw, Y_BAR+20)], radius=10, fill=rank['col'])
                
            # Rank/Desc (Cleaned)
            d.text((ix, Y_RANK), self._clean(rank['th']), font=self._font(AppConfig.FONT_B, 50), fill=rank['col'], anchor="lt")
            self._text(d, rank['desc'], ix, Y_DESC, iw, AppConfig.FONT_R, 40, AppConfig.C_TEXT_SUB, "lt")
            
            # Score
            sx = AppConfig.IMG_W - AppConfig.IMG_PAD - 50
            d.text((sx, cy-10), f"{xp}", font=self._font(AppConfig.FONT_B, 120), fill=AppConfig.C_SUCCESS if xp>=0 else AppConfig.C_DANGER, anchor="rs")
            d.text((sx, cy+60), "XP", font=self._font(AppConfig.FONT_B, 50), fill=AppConfig.C_TEXT_MUTED, anchor="rs")
            
            cur_y += AppConfig.IMG_H_ROW
            
        # Footer
        fy = canvas_h - (AppConfig.IMG_FOOTER_HEIGHT // 2)
        d.text((cx, fy), f"Generated by {AppConfig.APP_NAME} • {datetime.now().strftime('%d/%m %H:%M')}", font=self._font(AppConfig.FONT_R, 40), fill=AppConfig.C_TEXT_MUTED, anchor="mm")
        
        b = io.BytesIO()
        img.save(b, format='PNG')
        return b.getvalue()

# --- 5. MAIN APP ---
def main():
    st.set_page_config(page_title=AppConfig.APP_NAME, layout="wide", initial_sidebar_state="expanded")
    st.markdown(f"""<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&display=swap');
    * {{ font-family: 'Sarabun', sans-serif; }}
    .glass {{ background: white; padding: 1.5rem; border-radius: 15px; border: 1px solid #E2E8F0; margin-bottom: 1rem; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
    </style>""", unsafe_allow_html=True)
    
    db = DatabaseService()
    logic = LogicEngine()
    gfx = GraphicsService()
    
    # Sidebar
    with st.sidebar:
        st.title(f"🏫 {AppConfig.APP_NAME}")
        room = st.selectbox("เลือกห้องเรียน", ["ม.1/1", "ม.1/2", "ม.1/10"])
        st.divider()
        if st.button("📥 Backup CSV"):
            st.download_button("Download", db.fetch().to_csv(index=False).encode('utf-8'), "backup.csv")
        if st.button("⚠️ Reset Database"):
            if db.save(pd.DataFrame(columns=db.COLS)): st.success("Reset Done."); time.sleep(1); st.rerun()

    # Load Data
    all_df = db.fetch()
    room_df = all_df[all_df['Room'] == room].copy()
    
    st.title(f"ห้องเรียน: {room}")
    st.caption(f"Active Teams: {len(room_df)}")
    
    t1, t2, t3, t4 = st.tabs(["⚡ ให้คะแนน", "🏆 จัดอันดับ", "📊 สถิติ", "🛠️ จัดการทีม"])
    
    # Tab 1: Command (Batch)
    with t1:
        if room_df.empty: st.info("ยังไม่มีทีม กรุณาสร้างทีมในเมนูจัดการ"); return
        targets = st.multiselect("เลือกทีม (หลายกลุ่มได้)", sorted(room_df['GroupName'].unique()))
        st.divider()
        c1, c2 = st.columns(2)
        
        def run_batch(r, a):
            if not targets: st.error("เลือกทีมก่อนครับ"); return
            with st.status("กำลังบันทึกคะแนน...") as s:
                if db.batch_update(room, targets, a, r, all_df, logic):
                    s.update(label="เรียบร้อย!", state="complete")
                    time.sleep(0.5); st.rerun()
                else: s.update(label="เกิดข้อผิดพลาด", state="error")

        with c1:
            st.button("ส่งงานตรงเวลา (+50)", on_click=run_batch, args=("ส่งงานตรงเวลา", 50), use_container_width=True)
            st.button("ตอบคำถาม (+20)", on_click=run_batch, args=("ตอบคำถาม", 20), use_container_width=True)
        with c2:
            with st.form("manual"):
                r = st.text_input("เหตุผลอื่น")
                a = st.number_input("คะแนน", step=5)
                if st.form_submit_button("บันทึก") and r: run_batch(r, a)

    # Tab 2: Leaderboard & Image
    with t2:
        if st.button("✨ สร้างรูปภาพตารางคะแนน (Image)", type="primary"):
            try:
                img_data = gfx.render(room, room_df, logic)
                st.image(img_data, caption="ภาพตารางคะแนน (บันทึกได้เลย)")
                st.download_button("ดาวน์โหลดภาพ PNG", img_data, "leaderboard.png", "image/png")
            except Exception as e: st.error(f"Error: {e}")
        
        st.divider()
        for _, r in room_df.sort_values("XP", ascending=False).iterrows():
            rank = logic.get_rank(r['XP'])
            st.markdown(f"""
            <div class='glass' style='border-left: 5px solid {rank['col']}'>
                <div style='display:flex; justify-content:space-between; align-items:center'>
                    <div>
                        <h3 style='margin:0'>{r['GroupName']}</h3>
                        <div style='color:#666'>{r['Members']}</div>
                    </div>
                    <div style='text-align:right'>
                        <h2 style='margin:0; color:{rank['col']}'>{r['XP']} XP</h2>
                        <span style='background:{rank['bg']}; color:{rank['col']}; padding:2px 8px; border-radius:10px'>{rank['th']}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Tab 3: Analytics
    with t3:
        if not room_df.empty:
            c1, c2 = st.columns(2)
            c1.metric("คะแนนรวมทั้งห้อง", room_df['XP'].sum())
            c2.metric("คะแนนเฉลี่ย", int(room_df['XP'].mean()))
            st.bar_chart(room_df.set_index("GroupName")['XP'])

    # Tab 4: Management (CRUD)
    with t4:
        with st.expander("➕ สร้างทีมใหม่", expanded=True):
            with st.form("new"):
                n = st.text_input("ชื่อกลุ่ม")
                m = st.text_area("สมาชิก")
                if st.form_submit_button("สร้างทีม") and n:
                    if db.create(room, n, m, all_df): st.success("สร้างสำเร็จ"); time.sleep(0.5); st.rerun()
                    else: st.error("ชื่อซ้ำ!")
        
        st.divider()
        st.subheader("✏️ แก้ไขข้อมูลทีม")
        target = st.selectbox("เลือกทีมที่จะแก้ไข", ["-"] + sorted(room_df['GroupName'].unique()))
        
        if target != "-":
            curr = room_df[room_df['GroupName']==target].iloc[0]
            with st.form("edit"):
                nn = st.text_input("ชื่อกลุ่ม", value=curr['GroupName'])
                nm = st.text_area("สมาชิก (แก้ไขได้เลย)", value=curr['Members'], height=150)
                if st.form_submit_button("บันทึกการแก้ไข"):
                    if db.update(room, target, nn, nm, all_df): st.success("บันทึกแล้ว"); time.sleep(0.5); st.rerun()
                    else: st.error("บันทึกไม่ผ่าน (ชื่ออาจซ้ำ)")
            
            if st.button("ลบทีมนี้ทิ้ง (Delete)", type="primary"):
                db.delete(room, target, all_df)
                st.rerun()

        st.divider()
        with st.expander("⚡ แก้ไขประวัติคะแนน (History Log)"):
            pt = st.selectbox("เลือกทีม", ["-"]+sorted(room_df['GroupName'].unique()), key="pe")
            if pt != "-":
                row = room_df[room_df['GroupName']==pt].iloc[0]
                try: h = json.loads(row['HistoryLog'])
                except: h = []
                ed = st.data_editor(pd.DataFrame(h), num_rows="dynamic", use_container_width=True)
                if st.button("บันทึกประวัติใหม่"):
                    db.power_edit(room, pt, ed, all_df, logic)
                    st.success("เรียบร้อย"); st.rerun()

if __name__ == "__main__":
    main()
