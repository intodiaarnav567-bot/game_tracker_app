from contextlib import contextmanager

import mysql.connector

from app.config import connection_settings


@contextmanager
def transaction(role):
    connection = mysql.connector.connect(**connection_settings(role))
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def query(role, sql, params=()):
    with transaction(role) as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall() if cursor.with_rows else []


def call(role, procedure, params=()):
    # Procedure names are literals supplied by service code, never by widgets.
    with transaction(role) as connection:
        with connection.cursor(dictionary=True) as cursor:
            placeholders = ','.join(['%s'] * len(params))
            cursor.execute(f'CALL {procedure}({placeholders})', params)
            rows = cursor.fetchall() if cursor.with_rows else []
            while cursor.nextset():
                if cursor.with_rows:
                    rows.extend(cursor.fetchall())
            return rows
