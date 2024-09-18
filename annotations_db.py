import os
import sqlite3
import pandas as pd
from pathlib import Path

import portalocker

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = BASE_DIR / "data"
ANNOTATIONS_DB_FILE = DATA_DIR / "hindsight_annotations.db"

class HindsightAnnotationsDB:
    def __init__(self, db_file=ANNOTATIONS_DB_FILE):
        self.db_file = db_file
        self.lock_file = str(db_file) + '.lock'
        self.create_tables()

    def get_connection(self):
        """Get a new connection every time for thread safety."""
        connection = sqlite3.connect(self.db_file, timeout=50)
        connection.execute('PRAGMA journal_mode=WAL;')
        connection.execute('PRAGMA busy_timeout = 10000;')
        return connection
    
    def with_lock(func):
        """Decorator to handle database locking."""
        def wrapper(self, *args, **kwargs):
            with open(self.lock_file, 'a') as lock_file:
                portalocker.lock(lock_file, portalocker.LOCK_EX)
                try:
                    result = func(self, *args, **kwargs)
                finally:
                    portalocker.unlock(lock_file)
                return result
        return wrapper
    
    @with_lock
    def create_tables(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS object_detection_annotations (
                            id INTEGER PRIMARY KEY,
                            frame_id INTEGER NOT NULL,
                            x DOUBLE NOT NULL,
                            y DOUBLE NOT NULL,
                            w DOUBLE NOT NULL,
                            h DOUBLE NOT NULL,
                            rotation DOUBLE DEFAULT 0,
                            label TEXT,
                            conf DOUBLE NOT NULL,
                            model_name TEXT NOT NULL,
                            model_version TEXT,
                            model_file_hash STR NOT NULL
                           )
            ''')

    @with_lock
    def insert_annotation(self, frame_id, x, y, w, h, rotation, label, conf, model_name, model_version=None, model_file_hash=None):
        """Insert a new annotation into the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO object_detection_annotations 
                            (frame_id, x, y, w, h, rotation, label, conf, model_name, model_version, model_file_hash) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                            (frame_id, x, y, w, h, rotation, label, conf, model_name, model_version, model_file_hash))
            conn.commit()

    @with_lock
    def get_annotations(self):
        """Retrieve all annotations."""
        with self.get_connection() as conn:
            query = '''SELECT * from object_detection_annotations'''
            df = pd.read_sql_query(query, conn)
            return df
