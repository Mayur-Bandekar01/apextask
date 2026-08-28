import os
import sqlite3
import pymysql
from pymysql.cursors import DictCursor
from pathlib import Path
from api.config import Config

DB_ENGINE = None
LOCAL_SQLITE_PATH = Path(__file__).resolve().parent.parent / 'todo_app.db'

class SQLiteCursorWrapper:
    """Wraps sqlite3.Cursor to provide a DictCursor and %s parameter compatibility."""
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query, params=None):
        # Convert %s placeholders to ? for SQLite
        q = query.replace('%s', '?')
        # Compatibility replacements
        q = q.replace('INT AUTO_INCREMENT PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
        q = q.replace('INT AUTOINCREMENT PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
        q = q.replace('AUTO_INCREMENT', 'AUTOINCREMENT')
        q = q.replace('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP', 'CURRENT_TIMESTAMP')
        q = q.replace('ENUM(\'low\', \'medium\', \'high\')', 'TEXT')
        q = q.replace('ENUM(\'pending\', \'complete\', \'missed\')', 'TEXT')
        
        if params is not None:
            res = self.cursor.execute(q, params)
        else:
            res = self.cursor.execute(q)
        return res

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self):
        rows = self.cursor.fetchall()
        return [dict(r) for r in rows]

    @property
    def lastrowid(self):
        return self.cursor.lastrowid

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def close(self):
        try:
            self.cursor.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class SQLiteConnectionWrapper:
    """Wraps sqlite3.Connection with dictionary row factory and autocommit."""
    def __init__(self, conn):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    def cursor(self):
        return SQLiteCursorWrapper(self.conn.cursor())

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


def get_db_connection():
    global DB_ENGINE

    # Try MySQL first (Cloud or Local)
    try:
        connect_args = {
            'host': Config.DB_HOST,
            'port': Config.DB_PORT,
            'user': Config.DB_USER,
            'password': Config.DB_PASSWORD,
            'database': Config.DB_NAME,
            'cursorclass': DictCursor,
            'autocommit': True,
            'connect_timeout': 5,
            'charset': 'utf8mb4'
        }

        # Add SSL configuration for Cloud MySQL (TiDB Cloud, PlanetScale, Railway, Aiven, etc.)
        if Config.DB_SSL_CA:
            connect_args['ssl'] = {'ca': Config.DB_SSL_CA}
        elif Config.DB_HOST not in ('localhost', '127.0.0.1', '0.0.0.0') and not Config.DB_HOST.startswith('192.168.'):
            connect_args['ssl'] = {'ssl': {}}

        conn = pymysql.connect(**connect_args)
        DB_ENGINE = 'mysql'
        return conn
    except Exception as e:
        # Fallback to local SQLite persistence
        DB_ENGINE = 'sqlite'
        sqlite_conn = sqlite3.connect(str(LOCAL_SQLITE_PATH), timeout=15)
        # Enable WAL mode for high concurrency
        sqlite_conn.execute("PRAGMA journal_mode = WAL;")
        sqlite_conn.execute("PRAGMA foreign_keys = ON;")
        return SQLiteConnectionWrapper(sqlite_conn)


def get_engine_name():
    global DB_ENGINE
    if DB_ENGINE is None:
        conn = get_db_connection()
        conn.close()
    return DB_ENGINE


def init_db():
    """Initializes schema and seeds default single-user account."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        # 1. Users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL,
                title VARCHAR(100) DEFAULT 'Productivity Architect',
                xp INT DEFAULT 0,
                level INT DEFAULT 1,
                streak INT DEFAULT 0,
                last_active DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Tasks table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                title VARCHAR(255) NOT NULL,
                notes TEXT,
                priority VARCHAR(20) DEFAULT 'medium',
                status VARCHAR(20) DEFAULT 'pending',
                original_date DATE NOT NULL,
                deadline DATETIME,
                rollover_count INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)

        # 3. Task logs table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS task_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                task_id INT,
                change_description VARCHAR(255),
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            );
        """)

        # 4. Badges table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS badges (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                badge_name VARCHAR(100),
                earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)

        # 5. Daily records table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                record_date DATE NOT NULL,
                tasks_completed INT DEFAULT 0,
                tasks_missed INT DEFAULT 0,
                xp_earned INT DEFAULT 0,
                focus_time INT DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)

        # Seed or sync the single default user (Mayur)
        cur.execute("SELECT id, username FROM users ORDER BY id ASC LIMIT 1;")
        row = cur.fetchone()

        if not row:
            cur.execute("""
                INSERT INTO users (username, title, xp, level, streak, last_active)
                VALUES (%s, 'Productivity Architect', 0, 1, 0, CURRENT_DATE);
            """, (Config.APP_USERNAME,))
        elif row.get('username') != Config.APP_USERNAME:
            cur.execute("UPDATE users SET username = %s WHERE id = %s;", (Config.APP_USERNAME, row['id']))

        if hasattr(conn, 'commit'):
            conn.commit()

    conn.close()
    print(f"[DATABASE] Initialized using engine: {DB_ENGINE}")
