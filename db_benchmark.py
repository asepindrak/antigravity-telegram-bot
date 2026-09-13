import os
import json
import pymysql
from typing import Dict, Any, Optional

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASS", os.environ.get("DB_PASSWORD", "")),
    "database": os.environ.get("DB_NAME", os.environ.get("DB_DATABASE", "benchmark_db")),
    "port": int(os.environ.get("DB_PORT", 3306)),
    "autocommit": True
}

def init_db():
    """Ensure database and table exist."""
    try:
        conn = pymysql.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            port=DB_CONFIG["port"]
        )
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}`")
        conn.close()

        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                test_id VARCHAR(100),
                client_ip VARCHAR(50),
                model_name VARCHAR(100),
                request_type VARCHAR(50),
                prompt TEXT,
                response TEXT,
                status VARCHAR(50),
                prompt_tokens INT DEFAULT 0,
                completion_tokens INT DEFAULT 0,
                total_tokens INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        conn.close()
        print("[DB] Database & table benchmark_results initialized successfully.")
    except Exception as e:
        print(f"[DB] Error initializing database: {e}")

def save_benchmark_result(
    test_id: Optional[str] = None,
    client_ip: Optional[str] = None,
    model_name: Optional[str] = None,
    request_type: str = "http",
    prompt: Optional[str] = None,
    response: Optional[str] = None,
    status: str = "completed",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0
):
    """Save benchmark result row to MySQL WAMP."""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO benchmark_results 
            (test_id, client_ip, model_name, request_type, prompt, response, status, prompt_tokens, completion_tokens, total_tokens)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                test_id,
                client_ip,
                model_name,
                request_type,
                prompt,
                response,
                status,
                prompt_tokens,
                completion_tokens,
                total_tokens
            ))
        conn.close()
    except Exception as e:
        print(f"[DB] Failed to save benchmark result: {e}")
