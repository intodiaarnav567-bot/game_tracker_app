import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')


def _setting(name, default=''):
    """Read Streamlit Cloud secrets first, then local environment variables."""
    try:
        value = st.secrets.get(name)
    except (FileNotFoundError, KeyError, TypeError):
        value = None
    return value if value not in (None, '') else os.getenv(name, default)


DEMO_MODE = str(_setting('DEMO_MODE', 'false')).lower() == 'true'


def connection_settings(role):
    prefix = {'login': 'LOGIN', 'gamer': 'GAMER', 'game_publisher': 'PUBLISHER',
              'admin': 'ADMIN', 'dba': 'DBA'}[role]
    password = _setting(f'MYSQL_{prefix}_PASSWORD', '')
    if not password and role != 'dba':
        raise ValueError('Database credentials have not been configured.')
    return dict(host=_setting('MYSQL_HOST', '127.0.0.1'),
                port=int(_setting('MYSQL_PORT', '3306')),
                database=_setting('MYSQL_DATABASE', 'game_tracker'),
                user=_setting(f'MYSQL_{prefix}_USER', ''), password=password,
                connection_timeout=5, charset='utf8mb4', autocommit=False)
