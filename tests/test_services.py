from concurrent.futures import ThreadPoolExecutor

import mysql.connector
import pytest

from app import db
from app.services import publisher
from app.services import admin
from app.services import gamer


def test_purchase_is_atomic_and_idempotent(session):
    session('gamer1')
    before = db.query('admin','SELECT COUNT(*) n FROM Purchase WHERE user_id=100001 AND appid=1145360')[0]['n']
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(gamer.buy, [1145360,1145360]))
    assert db.query('admin','SELECT COUNT(*) n FROM Purchase WHERE user_id=100001 AND appid=1145360')[0]['n'] == before+1
    assert next(g for g in gamer.library() if g['appid']==1145360)['ownership_status']=='owned'


def test_wishlist_cannot_unlock(session):
    session('gamer1')
    with pytest.raises(mysql.connector.Error):
        gamer.unlock(1966720,52)


def test_one_session_and_idempotent_end(session):
    session('gamer1')
    gamer.start(105600)
    with pytest.raises(mysql.connector.Error):
        gamer.start(230410)
    gamer.end(105600)
    gamer.end(105600)
    assert not [s for s in gamer.sessions() if s['end_time'] is None]


def test_publisher_scope(session):
    session('pub_valve')
    with pytest.raises(mysql.connector.Error):
        publisher.active(1145360,False)
    assert {570,730,440}.issubset({g['appid'] for g in publisher.games()})
    assert 1145360 not in {g['appid'] for g in publisher.games()}
    with pytest.raises(PermissionError):
        gamer.library()


def test_gamer_identity_is_session_only(session):
    session('gamer2')
    assert all(g['user_id']==100002 for g in gamer.library())
    with pytest.raises(TypeError):
        gamer.library(100001)
    with pytest.raises(PermissionError):
        admin.accounts()


def test_purchase_blocks_user_delete(session):
    selected=session('gamer1').copy()
    session('admin')
    with pytest.raises(ValueError,match='purchases'):
        admin.delete_account(selected['account_id'])


def test_free_price_and_publisher_create(session):
    session('pub_valve')
    data=dict(name='Test game',short_description='',price=1,currency='USD',release_date='',required_age=0,
              is_free=1,header_image_url='',genres=[],categories=[],platforms=[],developers=[],new_developer='')
    with pytest.raises(mysql.connector.Error):
        publisher.save_game(None,data)
    data['price']=0
    appid=publisher.save_game(None,data)[0]['appid']
    data['name']='Updated game'
    publisher.save_game(appid,data)
    assert next(g for g in publisher.games() if g['appid']==appid)['name']=='Updated game'


@pytest.mark.parametrize('role',['gamer','game_publisher'])
@pytest.mark.parametrize('table',['User_Account','App_Account','Purchase'])
def test_private_table_grants(role,table):
    with pytest.raises(mysql.connector.Error):
        db.query(role,f'SELECT * FROM {table} LIMIT 1')


def test_publisher_cannot_bypass_procedures():
    with pytest.raises(mysql.connector.Error):
        db.query('game_publisher','UPDATE Game SET name=%s WHERE appid=%s',('Wrong',1145360))


def test_cannot_vote_on_own_review(session):
    session('gamer1')
    gamer.review(105600,'Good game',True)
    identifier=db.query('admin','SELECT review_id FROM Review WHERE user_id=100001 AND appid=105600')[0]['review_id']
    with pytest.raises(mysql.connector.Error):
        gamer.vote(identifier,True)
