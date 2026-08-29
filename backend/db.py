import pymysql
import pymysql.cursors
import sqlite3
from pathlib import Path
from backend.config import Config

_db_engine = "mysql"
_sqlite_path = Path(__file__).resolve().parent.parent / "todo_app.db"

def get_db_connection():
    global _db_engine
    if _db_engine == "mysql":
        try:
            conn = pymysql.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True,
                connect_timeout=2
            )
            return conn
        except Exception:
            _db_engine = "sqlite"
            return get_sqlite_connection()
    else:
        return get_sqlite_connection()

class SQLiteDictCursor:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor()
        self.lastrowid = None

    def execute(self, query, params=None):
        q = query.replace('%s', '?')
        q = q.replace('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP', 'CURRENT_TIMESTAMP')
        q = q.replace('GREATEST(', 'MAX(')

        if params is None:
            res = self.cursor.execute(q)
        else:
            if isinstance(params, (list, tuple)):
                res = self.cursor.execute(q, params)
            elif isinstance(params, dict):
                res = self.cursor.execute(q, params)
            else:
                res = self.cursor.execute(q, (params,))
        self.lastrowid = self.cursor.lastrowid
        return res

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self):
        rows = self.cursor.fetchall()
        return [dict(r) for r in rows]

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
    def __init__(self, conn):
        self.conn = conn

    def cursor(self, *args, **kwargs):
        return SQLiteDictCursor(self.conn)

    def commit(self):
        try:
            self.conn.commit()
        except Exception:
            pass

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

def get_sqlite_connection():
    conn = sqlite3.connect(str(_sqlite_path), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None # autocommit mode
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return SQLiteConnectionWrapper(conn)

def init_db():
    global _db_engine
    try:
        conn = pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            charset='utf8mb4',
            autocommit=True
        )
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.close()

        db_conn = get_db_connection()
        with db_conn.cursor() as cur:
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

            cur.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                title VARCHAR(255) NOT NULL,
                notes TEXT,
                priority ENUM('low', 'medium', 'high') DEFAULT 'medium',
                status ENUM('pending', 'complete', 'missed') DEFAULT 'pending',
                original_date DATE NOT NULL,
                deadline DATETIME,
                rollover_count INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS task_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                task_id INT,
                change_description VARCHAR(255),
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS subtasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                task_id INT NOT NULL,
                title VARCHAR(255) NOT NULL,
                is_done TINYINT(1) DEFAULT 0,
                order_index INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                INDEX idx_subtasks_task (task_id, order_index)
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS badges (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                badge_name VARCHAR(100),
                earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                record_date DATE NOT NULL,
                tasks_completed INT DEFAULT 0,
                tasks_missed INT DEFAULT 0,
                xp_earned INT DEFAULT 0,
                focus_time INT DEFAULT 0,
                UNIQUE KEY unique_user_date (user_id, record_date),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """)

            cur.execute("SELECT id FROM users WHERE id = 1;")
            if not cur.fetchone():
                cur.execute("""
                INSERT INTO users (id, username, title, xp, level, streak, last_active)
                VALUES (1, 'Master Productivity', 'Productivity Architect', 0, 1, 0, CURRENT_DATE);
                """)
        db_conn.close()
        _db_engine = "mysql"
        print("[DATABASE] Successfully connected to and initialized MySQL database.")
    except Exception as e:
        print(f"[DATABASE NOTICE] Operating on persistence layer ({e}). Initializing local storage fallback...")
        _db_engine = "sqlite"
        conn = get_sqlite_connection()
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                title TEXT DEFAULT 'Productivity Architect',
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                streak INTEGER DEFAULT 0,
                last_active TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT NOT NULL,
                notes TEXT,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                original_date TEXT NOT NULL,
                deadline TEXT,
                rollover_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                change_description TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS subtasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                is_done INTEGER DEFAULT 0,
                order_index INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            );
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS badges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                badge_name TEXT,
                earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                record_date TEXT NOT NULL,
                tasks_completed INTEGER DEFAULT 0,
                tasks_missed INTEGER DEFAULT 0,
                xp_earned INTEGER DEFAULT 0,
                focus_time INTEGER DEFAULT 0,
                UNIQUE (user_id, record_date),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """)
            cur.execute("SELECT id FROM users WHERE id = 1;")
            if not cur.fetchone():
                cur.execute("""
                INSERT INTO users (id, username, title, xp, level, streak, last_active)
                VALUES (1, 'Master Productivity', 'Productivity Architect', 0, 1, 0, date('now'));
                """)
            conn.commit()
        conn.close()
        print("[DATABASE] Local storage initialized successfully.")

def get_engine_name():
    return _db_engine
