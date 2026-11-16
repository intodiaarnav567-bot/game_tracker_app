from app import auth, db
from app.services.catalog import KINDS


def query(sql, params=()):
    auth.identity('admin')
    return db.query('admin', sql, params)


def accounts():
    return query('''SELECT account_id,username,email,role,user_id,publisher_id,is_active,
                    created_at,last_login_at FROM App_Account ORDER BY username''')


def users():
    return query('SELECT user_id,username FROM User ORDER BY username')


def create_account(username, email, password, role, user_id=None, publisher_id=None, new_publisher_name=None):
    auth.identity('admin')
    if not username.strip() or '@' not in email:
        raise ValueError('Enter a username and valid email.')
    if role == 'game_publisher' and publisher_id is None and not (new_publisher_name or '').strip():
        raise ValueError('Enter a new publisher name or select an existing publisher.')
    hashed = auth.hash_password(password)
    with db.transaction('admin') as connection:
        with connection.cursor() as cursor:
            if role == 'gamer' and user_id is None:
                cursor.execute('SELECT lock_id FROM App_Lock WHERE lock_id=1 FOR UPDATE')
                cursor.fetchall()
                cursor.execute('SELECT COALESCE(MAX(user_id),0)+1 FROM User')
                user_id = cursor.fetchone()[0]
                cursor.execute('INSERT INTO User(user_id,username) VALUES(%s,%s)', (user_id, username.strip()))
            if role == 'game_publisher' and publisher_id is None:
                cursor.execute('INSERT INTO Publisher(publisher_name) VALUES(%s)', (new_publisher_name.strip(),))
                publisher_id = cursor.lastrowid
            cursor.execute('''INSERT INTO App_Account(username,email,password_hash,role,user_id,publisher_id)
                VALUES(%s,%s,%s,%s,%s,%s)''', (username.strip(), email.strip(), hashed, role, user_id, publisher_id))


def set_active(account_id, active):
    if account_id == auth.identity('admin')['account_id'] and not active:
        raise ValueError('Your signed-in account must remain active.')
    query('UPDATE App_Account SET is_active=%s WHERE account_id=%s', (active, account_id))


def reset_password(account_id, password):
    query('UPDATE App_Account SET password_hash=%s WHERE account_id=%s', (auth.hash_password(password), account_id))


def delete_account(account_id):
    if account_id == auth.identity('admin')['account_id']:
        raise ValueError('You cannot delete your signed-in account.')
    with db.transaction('admin') as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute('SELECT user_id FROM App_Account WHERE account_id=%s FOR UPDATE', (account_id,))
            account = cursor.fetchone()
            if not account:
                return
            if account['user_id']:
                cursor.execute('SELECT purchase_id FROM Purchase WHERE user_id=%s LIMIT 1', (account['user_id'],))
                if cursor.fetchone():
                    raise ValueError('This user has purchases. Deactivate their account instead.')
                cursor.execute('DELETE FROM User WHERE user_id=%s', (account['user_id'],))
            else:
                cursor.execute('DELETE FROM App_Account WHERE account_id=%s', (account_id,))


def save_game(appid, data):
    auth.identity('admin')
    if not data['name'].strip() or data['price'] < 0 or (data['is_free'] and data['price'] != 0):
        raise ValueError('Enter a game name and valid price. Free games must cost zero.')
    if not data['publishers']:
        raise ValueError('Choose at least one publisher.')
    columns = ('name', 'short_description', 'price', 'currency', 'release_date',
               'required_age', 'is_free', 'header_image_url')
    values = [data[key] or None if key == 'release_date' else data[key] for key in columns]
    with db.transaction('admin') as connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT lock_id FROM App_Lock WHERE lock_id=1 FOR UPDATE')
            cursor.fetchall()
            if appid is None:
                cursor.execute('SELECT COALESCE(MAX(appid),0)+1 FROM Game')
                appid = cursor.fetchone()[0]
                cursor.execute('INSERT INTO Game(appid,' + ','.join(columns) + ') VALUES(' + ','.join(['%s'] * 9) + ')', (appid, *values))
            else:
                cursor.execute('UPDATE Game SET ' + ','.join(f'{column}=%s' for column in columns) + ' WHERE appid=%s', (*values, appid))
            for kind, prefix in KINDS.items():
                ids = data['categories' if kind == 'Category' else prefix + 's']
                cursor.execute(f'DELETE FROM Game_{kind} WHERE appid=%s', (appid,))
                for identifier in ids:
                    cursor.execute(f'INSERT INTO Game_{kind}(appid,{prefix}_id) VALUES(%s,%s)', (appid, identifier))
            if data['new_developer'].strip():
                cursor.execute('INSERT INTO Developer(developer_name) VALUES(%s) ON DUPLICATE KEY UPDATE developer_id=LAST_INSERT_ID(developer_id)', (data['new_developer'].strip(),))
                cursor.execute('INSERT IGNORE INTO Game_Developer VALUES(%s,%s)', (appid, cursor.lastrowid))


def active(appid, active):
    query('UPDATE Game SET is_active=%s WHERE appid=%s', (active, appid))


def catalog_save(kind, identifier, name):
    prefix = KINDS[kind]
    if not name.strip():
        raise ValueError('Enter a name.')
    if identifier is None:
        query(f'INSERT INTO {kind}({prefix}_name) VALUES(%s)', (name.strip(),))
    else:
        query(f'UPDATE {kind} SET {prefix}_name=%s WHERE {prefix}_id=%s', (name.strip(), identifier))


def catalog_delete(kind, identifier):
    prefix = KINDS[kind]
    if query(f'SELECT appid FROM Game_{kind} WHERE {prefix}_id=%s LIMIT 1', (identifier,)):
        raise ValueError('This entry is used by a game. Update that game first.')
    if kind == 'Publisher' and query('SELECT account_id FROM App_Account WHERE publisher_id=%s LIMIT 1', (identifier,)):
        raise ValueError('This publisher is linked to an account.')
    query(f'DELETE FROM {kind} WHERE {prefix}_id=%s', (identifier,))


def purchases():
    return query('''SELECT p.*,u.username,g.name FROM Purchase p JOIN User u USING(user_id)
                    JOIN Game g USING(appid) ORDER BY purchased_at DESC''')


def overview():
    return query('''SELECT (SELECT COUNT(*) FROM User) AS users,
        (SELECT COUNT(*) FROM Game) AS games,(SELECT COUNT(*) FROM Game WHERE is_active=1) AS active_games,
        (SELECT COUNT(*) FROM Purchase) AS purchases,(SELECT COUNT(*) FROM Gaming_Session) AS sessions,
        (SELECT COUNT(*) FROM Review) AS reviews''')[0]


def stats():
    return query('SELECT * FROM Publisher_Game_Stats ORDER BY owners DESC')


def delete_review(review_id):
    query('DELETE FROM Review WHERE review_id=%s', (review_id,))
