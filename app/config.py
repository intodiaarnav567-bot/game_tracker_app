import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
DEMO_MODE = os.getenv('DEMO_MODE', 'false').lower() == 'true'


def connection_settings(role):
    prefix = {'login': 'LOGIN', 'gamer': 'GAMER', 'game_publisher': 'PUBLISHER',
              'admin': 'ADMIN', 'dba': 'DBA'}[role]
    password = os.getenv(f'MYSQL_{prefix}_PASSWORD', '')
    if not password and role != 'dba':
        raise ValueError('Database credentials have not been configured.')
    return dict(host=os.getenv('MYSQL_HOST', '127.0.0.1'),
                port=int(os.getenv('MYSQL_PORT', '3306')),
                database=os.getenv('MYSQL_DATABASE', 'game_tracker'),
                user=os.getenv(f'MYSQL_{prefix}_USER', ''), password=password,
                connection_timeout=5, charset='utf8mb4', autocommit=False)
