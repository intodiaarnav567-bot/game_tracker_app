from app import auth, db


def perform(procedure, *args):
    user_id = auth.identity('gamer')['user_id']
    return db.call('gamer', procedure, (user_id, *args))


def library():
    return perform('sp_my_library')


def sessions():
    return perform('sp_my_sessions')


def achievements():
    return perform('sp_my_achievements')


def purchases():
    return perform('sp_my_purchases')


def buy(appid):
    return perform('sp_purchase_game', appid)


def ownership(appid, status):
    return perform('sp_set_ownership', appid, status)


def start(appid):
    return perform('sp_start_session', appid)


def end(appid):
    return perform('sp_end_session', appid)


def unlock(appid, achievement_id):
    return perform('sp_unlock_achievement', appid, achievement_id)


def review(appid, text, recommended):
    if not text.strip():
        raise ValueError('Write a review first.')
    return perform('sp_post_review', appid, text.strip(), recommended)


def vote(review_id, helpful):
    return perform('sp_vote_review', review_id, helpful)


def profile():
    return db.query('gamer', 'SELECT * FROM User_Public WHERE user_id=%s',
                    (auth.identity('gamer')['user_id'],))[0]


def update_profile(username, url):
    if not username.strip():
        raise ValueError('Enter a username.')
    return perform('sp_update_profile', username.strip(), url)
