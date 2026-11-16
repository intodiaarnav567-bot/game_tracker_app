import json

from app import auth, db


def perform(procedure, *args):
    publisher_id = auth.identity('game_publisher')['publisher_id']
    return db.call('game_publisher', procedure, (publisher_id, *args))


def games():
    return perform('sp_pub_my_games')


def stats():
    return perform('sp_pub_game_stats')


def reviews(appid):
    return perform('sp_pub_game_reviews', appid)


def save_game(appid, data):
    if appid is None:
        return perform('sp_pub_create_game', json.dumps(data))
    return perform('sp_pub_update_game', appid, json.dumps(data))


def active(appid, value):
    return perform('sp_pub_set_active', appid, value)


def save_achievement(appid, achievement_id, name, description, points, hidden):
    return perform('sp_pub_upsert_achievement', appid, achievement_id, name, description, points, hidden)


def delete_achievement(appid, achievement_id):
    return perform('sp_pub_delete_achievement', appid, achievement_id)
