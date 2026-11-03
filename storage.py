import os
import sqlite3


def db_path(user_data_dir):
    os.makedirs(user_data_dir, exist_ok=True)
    return os.path.join(user_data_dir, "mexc_mobile.db")


def init_db(user_data_dir):
    with sqlite3.connect(db_path(user_data_dir)) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("""CREATE TABLE IF NOT EXISTS paper_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, entry REAL, exit REAL,
            amount REAL, pnl REAL, pnl_pct REAL, reason TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")


def save_setting(user_data_dir, key, value):
    with sqlite3.connect(db_path(user_data_dir)) as conn:
        conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, str(value)))


def get_setting(user_data_dir, key, default=""):
    with sqlite3.connect(db_path(user_data_dir)) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def save_trade(user_data_dir, symbol, entry, exit_price, amount, pnl, pnl_pct, reason):
    with sqlite3.connect(db_path(user_data_dir)) as conn:
        conn.execute("INSERT INTO paper_trades(symbol,entry,exit,amount,pnl,pnl_pct,reason) VALUES(?,?,?,?,?,?,?)",
                     (symbol, entry, exit_price, amount, pnl, pnl_pct, reason))


def get_trades(user_data_dir, limit=50):
    with sqlite3.connect(db_path(user_data_dir)) as conn:
        return conn.execute("SELECT symbol,entry,exit,amount,pnl,pnl_pct,reason FROM paper_trades ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
