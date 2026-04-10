import sqlite3
import os
from datetime import datetime

class BuildDatabase:
    def __init__(self, db_path="monitor/history.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 建立表格，增加 workspace_path
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS build_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    build_number TEXT,
                    build_type TEXT,
                    status TEXT,
                    timestamp DATETIME,
                    workspace_path TEXT,
                    image_path TEXT,
                    report_path TEXT,
                    UNIQUE(build_number, build_type)
                )
            ''')
            
            # 檢查並補上缺失的欄位 (例如從舊版 Polling 升級到新版的工作空間架構)
            cursor.execute("PRAGMA table_info(build_history)")
            existing_columns = [column[1] for column in cursor.fetchall()]
            
            needed_columns = {
                'build_type': 'TEXT',
                'workspace_path': 'TEXT'
            }
            
            for col_name, col_type in needed_columns.items():
                if col_name not in existing_columns:
                    cursor.execute(f"ALTER TABLE build_history ADD COLUMN {col_name} {col_type}")
            
            conn.commit()

    def get_build_status(self, build_number, build_type):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM build_history WHERE build_number = ? AND build_type = ?", 
                          (build_number, build_type))
            result = cursor.fetchone()
            return result[0] if result else None

    def add_build(self, build_number, build_type, workspace_path, status="PENDING"):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO build_history (build_number, build_type, workspace_path, status, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (build_number, build_type, workspace_path, status, datetime.now().isoformat()))
            conn.commit()

    def update_status(self, build_number, build_type, status, report_path=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if report_path:
                cursor.execute('''
                    UPDATE build_history 
                    SET status = ?, report_path = ?, timestamp = ?
                    WHERE build_number = ? AND build_type = ?
                ''', (status, report_path, datetime.now().isoformat(), build_number, build_type))
            else:
                cursor.execute('''
                    UPDATE build_history 
                    SET status = ?, timestamp = ?
                    WHERE build_number = ? AND build_type = ?
                ''', (status, datetime.now().isoformat(), build_number, build_type))
            conn.commit()

    def get_recent_zips(self, limit=2):
        """獲取最近幾次有 Image 的紀錄，用於清理"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT build_number, build_type, workspace_path 
                FROM build_history 
                WHERE workspace_path IS NOT NULL 
                ORDER BY timestamp DESC LIMIT ?
            ''', (limit,))
            return cursor.fetchall()

    def get_all_history(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM build_history ORDER BY timestamp DESC")
            return cursor.fetchall()
