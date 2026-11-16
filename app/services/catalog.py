from app import auth, db

KINDS = {'Genre': 'genre', 'Category': 'category', 'Platform': 'platform',
         'Developer': 'developer', 'Publisher': 'publisher'}


def games():
    return db.query(auth.identity()['role'], '''SELECT g.*,
        (SELECT COUNT(*) FROM Review r WHERE r.appid=g.appid) AS review_count,
        (SELECT COALESCE(AVG(recommended)*100,0) FROM Review r WHERE r.appid=g.appid) AS rating
        FROM Game g ORDER BY name''')


def reference(kind):
    prefix = KINDS[kind]
    return db.query(auth.identity()['role'], f'SELECT {prefix}_id AS id,{prefix}_name AS name FROM {kind} ORDER BY {prefix}_name')


def links(appid, kind):
    prefix = KINDS[kind]
    return db.query(auth.identity()['role'], f'''SELECT t.{prefix}_id AS id,t.{prefix}_name AS name
        FROM {kind} t JOIN Game_{kind} j USING({prefix}_id) WHERE j.appid=%s''', (appid,))


def achievements(appid):
    return db.query(auth.identity()['role'], 'SELECT * FROM Achievement WHERE appid=%s ORDER BY achievement_id', (appid,))


def reviews(appid=None):
    return db.query(auth.identity()['role'], '''SELECT r.*,u.username,
        (SELECT COUNT(*) FROM Review_Vote v WHERE v.review_id=r.review_id AND is_helpful=1) AS helpful
        FROM Review r JOIN User_Public u USING(user_id)
        WHERE (%s IS NULL OR appid=%s) ORDER BY review_date DESC''', (appid, appid))
