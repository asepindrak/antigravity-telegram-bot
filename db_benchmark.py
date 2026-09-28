import os
import json
import threading
import pymysql
import pymysql.cursors
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def is_db_logging_enabled() -> bool:
    """Check if database logging is enabled via environment variable."""
    val = os.environ.get("ENABLE_DB_LOGGING", "true").strip().lower()
    return val in ("true", "1", "yes", "on", "enabled")

def get_db_config() -> Dict[str, Any]:
    """Get MySQL database connection configuration with short timeout."""
    return {
        "host": os.environ.get("DB_HOST", "localhost"),
        "user": os.environ.get("DB_USER", "root"),
        "password": os.environ.get("DB_PASS", os.environ.get("DB_PASSWORD", "")),
        "database": os.environ.get("DB_NAME", os.environ.get("DB_DATABASE", "benchmark_db")),
        "port": int(os.environ.get("DB_PORT", 3306)),
        "charset": "utf8mb4",
        "autocommit": True,
        "connect_timeout": 2  # 2 second timeout to prevent any blocking if MySQL is down
    }

def init_db():
    """Ensure database and benchmark_results table exist if DB logging is enabled. Runs safely in background."""
    if not is_db_logging_enabled():
        print("[DB Logging] Database logging is DISABLED (ENABLE_DB_LOGGING=false).")
        return

    def _init_task():
        config = get_db_config()
        db_name = config["database"]

        try:
            # Step 1: Ensure database exists
            conn = pymysql.connect(
                host=config["host"],
                user=config["user"],
                password=config["password"],
                port=config["port"],
                charset=config["charset"],
                connect_timeout=config["connect_timeout"],
                autocommit=True
            )
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.close()

            # Step 2: Ensure table exists with LONGTEXT columns for prompt and response
            conn = pymysql.connect(**config)
            with conn.cursor() as cursor:
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS benchmark_results (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    test_id VARCHAR(100),
                    client_ip VARCHAR(50),
                    model_name VARCHAR(100),
                    request_type VARCHAR(50),
                    prompt LONGTEXT,
                    response LONGTEXT,
                    status VARCHAR(50),
                    prompt_tokens INT DEFAULT 0,
                    completion_tokens INT DEFAULT 0,
                    total_tokens INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """)

                try:
                    cursor.execute("ALTER TABLE benchmark_results MODIFY prompt LONGTEXT")
                    cursor.execute("ALTER TABLE benchmark_results MODIFY response LONGTEXT")
                except Exception:
                    pass

            conn.close()
            print(f"[DB Logging] MySQL database '{db_name}' initialized successfully on {config['host']}:{config['port']}.")
        except Exception as e:
            print(f"[DB Logging] MySQL server offline or unreachable ({e}). Log creation skipped.")

    # Run DB init in a background thread so app startup is never blocked
    threading.Thread(target=_init_task, daemon=True).start()

def _worker_save_result(kwargs: Dict[str, Any]):
    """Background worker thread function to write log row to MySQL."""
    try:
        config = get_db_config()
        conn = pymysql.connect(**config)
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO benchmark_results 
            (test_id, client_ip, model_name, request_type, prompt, response, status, prompt_tokens, completion_tokens, total_tokens)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                kwargs.get("test_id"),
                kwargs.get("client_ip"),
                kwargs.get("model_name"),
                kwargs.get("request_type", "http"),
                kwargs.get("prompt"),
                kwargs.get("response"),
                kwargs.get("status", "completed"),
                kwargs.get("prompt_tokens", 0),
                kwargs.get("completion_tokens", 0),
                kwargs.get("total_tokens", 0)
            ))
        conn.close()
    except Exception:
        # If MySQL is down or fails, skip log creation silently without blocking or throwing errors
        pass

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
    """Save benchmark / AGY bridge prompt and response log row asynchronously (non-blocking)."""
    if not is_db_logging_enabled():
        return

    kwargs = {
        "test_id": test_id,
        "client_ip": client_ip,
        "model_name": model_name,
        "request_type": request_type,
        "prompt": prompt,
        "response": response,
        "status": status,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens
    }

    # Asynchronous thread execution: returns immediately (0ms delay) to caller
    threading.Thread(target=_worker_save_result, args=(kwargs,), daemon=True).start()

def get_recent_logs(limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve recent log records from MySQL database if available."""
    if not is_db_logging_enabled():
        return []
    
    try:
        config = get_db_config()
        conn = pymysql.connect(**config, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, test_id, client_ip, model_name, request_type, prompt, response, status, 
                       prompt_tokens, completion_tokens, total_tokens, created_at 
                FROM benchmark_results 
                ORDER BY id DESC 
                LIMIT %s
            """, (limit,))
            rows = cursor.fetchall()
            for row in rows:
                if row.get("created_at"):
                    row["created_at"] = str(row["created_at"])
        conn.close()
        return rows
    except Exception:
        return []
