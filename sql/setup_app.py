"""Provision application DB logins and apply the additive extension."""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import config, db


def statements(path):
    delimiter = ';'
    pending = []
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if line.strip().upper().startswith('DELIMITER '):
            delimiter = line.strip().split()[1]
            continue
        if not pending and (not line.strip() or line.lstrip().startswith('--')):
            continue
        pending.append(line)
        if line.rstrip().endswith(delimiter):
            yield '\n'.join(pending).rstrip()[:-len(delimiter)]
            pending = []
    if pending:
        raise ValueError('SQL file has an unfinished statement.')


def setup():
    with db.transaction('dba') as connection:
        with connection.cursor() as cursor:
            for statement in statements(config.ROOT / 'sql/00_app_extension.sql'):
                cursor.execute(statement)
                while cursor.nextset():
                    pass
            host = os.getenv('MYSQL_ACCOUNT_HOST', 'localhost')
            for role in ('login', 'gamer', 'game_publisher', 'admin'):
                settings = config.connection_settings(role)
                user = settings['user']
                cursor.execute('CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s',
                               (user, host, settings['password']))
                cursor.execute('ALTER USER %s@%s IDENTIFIED BY %s', (user, host, settings['password']))
                if role == 'login':
                    cursor.execute('GRANT SELECT, UPDATE(last_login_at) ON game_tracker.App_Account TO %s@%s', (user, host))
                else:
                    role_name = role + '_role'
                    cursor.execute('GRANT %s TO %s@%s', (role_name, user, host))
                    cursor.execute('SET DEFAULT ROLE %s TO %s@%s', (role_name, user, host))
    print('Application extension and database users are ready.')


if __name__ == '__main__':
    setup()
