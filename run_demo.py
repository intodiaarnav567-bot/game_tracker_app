"""Start the college demo on a private local MySQL instance."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser

import mysql.connector

ROOT = Path(__file__).resolve().parent
HOST = '127.0.0.1'
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def free_port():
    with socket.socket() as sock:
        sock.bind((HOST, 0))
        return sock.getsockname()[1]


def open_browser_when_ready(url, port):
    """Open the app only after Streamlit is accepting local connections."""
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((HOST, port), timeout=.5):
                webbrowser.open(url)
                return
        except OSError:
            time.sleep(.2)


def recover_previous_mysql(folder):
    """Clean up a private MySQL process left behind by a closed launcher window."""
    state_file = folder / 'server.json'
    state = {}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            pass

    port = state.get('port')
    settings_file = folder / 'credentials.json'
    if port and settings_file.exists():
        try:
            password = json.loads(settings_file.read_text(encoding='utf-8'))['MYSQL_DBA_PASSWORD']
            connection = mysql.connector.connect(host=HOST, port=int(port), user='root',
                                                 password=password, connection_timeout=2)
            try:
                with connection.cursor() as cursor:
                    cursor.execute('SHUTDOWN')
            finally:
                connection.close()
            time.sleep(.5)
        except (OSError, ValueError, KeyError, mysql.connector.Error):
            pass

    # A console window can be closed before Python executes its finally block.
    # On Windows, remove only mysqld processes whose command line names this
    # project's exact private data directory. The system MySQL service is untouched.
    if os.name == 'nt':
        target = str((folder / 'data').resolve()).replace("'", "''")
        script = (
            f"$target = '{target}'; "
            "Get-CimInstance Win32_Process -Filter \"Name = 'mysqld.exe'\" | "
            "Where-Object { $_.CommandLine -like ('*--datadir=' + $target + '*') } | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        try:
            subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                           check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=15, creationflags=NO_WINDOW)
        except (OSError, subprocess.TimeoutExpired):
            pass

    state_file.unlink(missing_ok=True)


def configure(port, folder):
    settings_file = folder / 'credentials.json'
    if not settings_file.exists():
        settings = {f'MYSQL_{role}_PASSWORD': secrets.token_urlsafe(24)
                    for role in ('DBA', 'LOGIN', 'GAMER', 'PUBLISHER', 'ADMIN')}
        settings_file.write_text(json.dumps(settings), encoding='utf-8')
    os.environ.update(json.loads(settings_file.read_text(encoding='utf-8')))
    os.environ.update(MYSQL_HOST=HOST, MYSQL_PORT=str(port), MYSQL_DATABASE='game_tracker',
                      MYSQL_DBA_USER='root', MYSQL_ACCOUNT_HOST='localhost',
                      MYSQL_LOGIN_USER='app_login_user', MYSQL_GAMER_USER='app_gamer',
                      MYSQL_PUBLISHER_USER='app_publisher', MYSQL_ADMIN_USER='app_admin', DEMO_MODE='true')


def wait_for_mysql(server, port, fresh):
    deadline = time.monotonic() + 45
    while server.poll() is None and time.monotonic() < deadline:
        try:
            password = os.environ['MYSQL_DBA_PASSWORD']
            connection = mysql.connector.connect(host=HOST, port=port, user='root',
                                                 password='' if fresh else password, connection_timeout=2)
            if fresh:
                with connection.cursor() as cursor:
                    cursor.execute("ALTER USER 'root'@'localhost' IDENTIFIED BY %s", (password,))
            return connection
        except mysql.connector.Error:
            time.sleep(.25)
    raise RuntimeError('Local MySQL could not start. See .demo-db/mysql.log.')


@contextmanager
def launcher_lock(folder):
    with (folder / 'launcher.lock').open('a+b') as lock:
        if os.name == 'nt':
            import msvcrt
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                yield False
                return
        else:
            import fcntl
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                yield False
                return
        yield True


def main():
    folder = ROOT / '.demo-db'
    folder.mkdir(exist_ok=True)
    address = folder / 'address.txt'
    with launcher_lock(folder) as acquired:
        if not acquired:
            url = address.read_text(encoding='utf-8').strip() if address.exists() else ''
            print(f'The app is already running. Open {url}' if url else 'The app is already starting. Check the first terminal.')
            return
        address.unlink(missing_ok=True)
        try:
            run(folder, address)
        finally:
            address.unlink(missing_ok=True)


def run(folder, address):
    mysqld = shutil.which('mysqld')
    if not mysqld:
        raise RuntimeError('Add the MySQL Server bin folder to PATH, then run this command again.')
    recover_previous_mysql(folder)
    data = folder / 'data'
    marker = folder / 'ready'
    state_file = folder / 'server.json'
    port = free_port()
    configure(port, folder)
    command = [mysqld, '--no-defaults', f'--datadir={data}', f'--log-error={folder / "mysql.log"}', '--skip-log-bin']
    fresh = not data.exists()
    if fresh:
        print('Creating the local demo database…', flush=True)
        subprocess.run([*command, '--initialize-insecure'], check=True, stdin=subprocess.DEVNULL,
                       creationflags=NO_WINDOW)
    server = subprocess.Popen([*command, f'--bind-address={HOST}', f'--port={port}', '--mysqlx=OFF'],
                              stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
    state_file.write_text(json.dumps({'pid': server.pid, 'port': port}), encoding='utf-8')
    connection = None
    try:
        connection = wait_for_mysql(server, port, fresh)
        if not marker.exists():
            from sql.setup_app import setup, statements
            from sql.seed_demo_accounts import seed

            with connection.cursor() as cursor:
                for name in ('schema.sql', 'sample_data (1).sql', 'game_tracker_role_setup.sql'):
                    for statement in statements(ROOT / name):
                        cursor.execute(statement)
                        while cursor.nextset():
                            pass
            connection.commit()
            setup()
            seed()
            marker.touch()
        # Strip DBA settings from the frontend child environment.
        frontend_env = {key: value for key, value in os.environ.items() if not key.startswith('MYSQL_DBA_')}
        frontend_port = free_port()
        url = f'http://{HOST}:{frontend_port}'
        address.write_text(url, encoding='utf-8')
        print(f'Open {url}', flush=True)
        if '--no-browser' not in sys.argv:
            threading.Thread(target=open_browser_when_ready, args=(url, frontend_port), daemon=True).start()
        subprocess.run([sys.executable, '-m', 'streamlit', 'run', 'app/main.py',
                        '--server.address', HOST, '--server.port', str(frontend_port),
                        '--server.headless', 'true'], cwd=ROOT, env=frontend_env, check=True)
    finally:
        try:
            if connection is not None:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute('SHUTDOWN')
                finally:
                    connection.close()
        finally:
            if server.poll() is None:
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.terminate()
                    server.wait(timeout=10)
            state_file.unlink(missing_ok=True)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
