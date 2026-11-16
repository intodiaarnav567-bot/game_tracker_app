import importlib.util
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time

import mysql.connector
import pytest

from app import auth

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'sql' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='session', autouse=True)
def database(tmp_path_factory):
    binary = shutil.which('mysqld') or r'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe'
    if not Path(binary).exists():
        pytest.fail('Install MySQL Server to run the isolated integration tests.')
    directory = tmp_path_factory.mktemp('mysql')
    data = directory / 'data'
    log = directory / 'mysql.log'
    base = [binary, '--no-defaults', f'--datadir={data}', f'--log-error={log}', '--skip-log-bin']
    subprocess.run([*base, '--initialize-insecure'], check=True, timeout=90, capture_output=True, stdin=subprocess.DEVNULL)
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0))
        port = reservation.getsockname()[1]
    process = subprocess.Popen([*base, f'--port={port}', '--bind-address=127.0.0.1', '--mysqlx=OFF'],
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    saved = dict(os.environ)
    try:
        for _ in range(80):
            try:
                connection = mysql.connector.connect(host='127.0.0.1', port=port, user='root', connection_timeout=1)
                break
            except mysql.connector.Error:
                if process.poll() is not None:
                    raise RuntimeError(log.read_text())
                time.sleep(.25)
        else:
            raise RuntimeError(log.read_text())
        setup = load_script('setup_app')
        with connection.cursor() as cursor:
            for filename in ('schema.sql', 'sample_data (1).sql', 'game_tracker_role_setup.sql'):
                for statement in setup.statements(ROOT / filename):
                    cursor.execute(statement)
                    while cursor.nextset():
                        pass
        connection.commit()
        connection.close()
        os.environ.update(MYSQL_HOST='127.0.0.1', MYSQL_PORT=str(port), MYSQL_DATABASE='game_tracker',
                          MYSQL_DBA_USER='root', MYSQL_DBA_PASSWORD='', MYSQL_ACCOUNT_HOST='localhost')
        for name, username in [('LOGIN','app_login_user'),('GAMER','app_gamer'),('PUBLISHER','app_publisher'),('ADMIN','app_admin')]:
            os.environ[f'MYSQL_{name}_USER'] = username
            os.environ[f'MYSQL_{name}_PASSWORD'] = secrets.token_urlsafe(24)
        setup.setup()
        setup.setup()  # The extension and user setup must be repeatable.
        load_script('seed_demo_accounts').seed()
        load_script('seed_demo_accounts').seed()
        yield
    finally:
        try:
            connection = mysql.connector.connect(host='127.0.0.1', port=port, user='root')
            connection.cursor().execute('SHUTDOWN')
            connection.close()
            process.wait(timeout=15)
        except Exception:
            process.terminate()
            process.wait(timeout=15)
        os.environ.clear()
        os.environ.update(saved)


@pytest.fixture
def session(monkeypatch):
    from app import db
    account = {}

    def identity(*roles):
        if not account or (roles and account['role'] not in roles):
            raise PermissionError('Access denied')
        return account

    def select(username):
        account.clear()
        account.update(db.query('admin', 'SELECT account_id,username,role,user_id,publisher_id FROM App_Account WHERE username=%s', (username,))[0])
        return account

    monkeypatch.setattr(auth, 'identity', identity)
    return select
