"""Create missing demo logins without resetting existing passwords."""
from pathlib import Path
import re
import sys

from app import auth

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import db


def seed():
    accounts = [('admin', 'Admin@123', 'admin', None, None)]
    users = db.query('admin', 'SELECT user_id FROM User ORDER BY user_id LIMIT 3')
    accounts.extend((f'gamer{i}', 'Gamer@123', 'gamer', row['user_id'], None)
                    for i, row in enumerate(users, 1))
    publishers = db.query('admin', 'SELECT * FROM Publisher ORDER BY publisher_id')
    for row in publishers:
        slug = re.sub('[^a-z0-9]+', '_', row['publisher_name'].lower()).strip('_')
        accounts.append((f'pub_{slug}', 'Publisher@123', 'game_publisher', None, row['publisher_id']))
    for username, password, role, user_id, publisher_id in accounts:
        if not db.query('admin', 'SELECT account_id FROM App_Account WHERE username=%s', (username,)):
            db.query('admin', '''INSERT INTO App_Account
                (username,email,password_hash,role,user_id,publisher_id) VALUES(%s,%s,%s,%s,%s,%s)''',
                (username, username + '@example.com', auth.hash_password(password), role, user_id, publisher_id))
        print(f'{username:40} {password:16} {role}')


if __name__ == '__main__':
    seed()
