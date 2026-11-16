from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app import ui
from app import db

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def app_test(monkeypatch):
    monkeypatch.setattr(ui,'poster',lambda appid,url,name:ui.placeholder(name))
    def create(username):
        account=db.query('admin','SELECT account_id,username,role,user_id,publisher_id FROM App_Account WHERE username=%s',(username,))[0]
        test=AppTest.from_file(str(ROOT/'app/main.py'),default_timeout=30)
        test.session_state['account']=account
        return test.run()
    return create


@pytest.mark.parametrize('username,folder,pages',[
    ('gamer1','gamer',['store','home','library','wishlist','achievements','profile']),
    ('pub_valve','publisher',['dashboard','games','add','achievements','reviews']),
    ('admin','admin',['overview','users','games','catalog','purchases','reviews'])])
def test_all_menu_pages(app_test,username,folder,pages):
    test=app_test(username)
    for page in pages:
        test.switch_page(f'pages/{folder}/{page}.py').run()
        assert not test.exception
        assert not test.error, [e.value for e in test.error]


def test_search_detail_back_logout(app_test):
    test=app_test('gamer1')
    test.text_input(key='store_search').set_value('no such game qwerty').run()
    assert test.info
    test.text_input(key='store_search').set_value('Hades').run()
    test.button(key='store_view_1145360').click().run()
    assert not test.exception and not test.error
    test.button(key='detail_back').click().run()
    assert test.session_state['selected_appid'] is None
    test.button(key='logout').click().run()
    assert test.session_state['account'] is None
    assert test.text_input(key='login_username')


def assert_clean(test):
    assert not test.exception
    assert not test.error, [e.value for e in test.error]


def test_gamer_forms_and_sessions(app_test):
    test=app_test('gamer1')
    test.switch_page('pages/gamer/library.py').run()
    test.button(key='library_play_105600').click().run()
    assert_clean(test)
    test.button(key='library_play_105600').click().run()
    assert_clean(test)
    test.switch_page('pages/gamer/profile.py').run()
    test.text_input(key='profile_username').set_value('')
    test.button(key='profile_save').click().run()
    assert test.error
    test.text_input(key='profile_username').set_value('Demo gamer')
    test.button(key='profile_save').click().run()
    assert_clean(test)
    test.switch_page('pages/gamer/store.py').run()
    test.text_input(key='store_search').set_value('Terraria').run()
    test.button(key='store_view_105600').click().run()
    test.text_area(key='review_text_105600').set_value('')
    test.button(key='save_review_105600').click().run()
    assert test.error
    test.text_area(key='review_text_105600').set_value('A useful college demo review.')
    test.button(key='save_review_105600').click().run()
    assert_clean(test)


def test_empty_player(app_test):
    from app import auth
    db.query('admin','INSERT INTO User(user_id,username) VALUES(%s,%s)',(900001,'Empty player'))
    db.query('admin', '''INSERT INTO App_Account(username,email,password_hash,role,user_id)
                        VALUES(%s,%s,%s,%s,%s)''',
             ('empty_test','empty@example.com',auth.hash_password('Example@123'),'gamer',900001))
    test=app_test('empty_test')
    for page in ('home','library','wishlist','achievements','profile'):
        test.switch_page(f'pages/gamer/{page}.py').run()
        assert_clean(test)


def test_publisher_form_validations(app_test):
    test=app_test('pub_valve')
    test.switch_page('pages/publisher/add.py').run()
    key='game_None_0'
    test.button(key=key+'_submit').click().run()
    assert test.error
    test.text_input(key=key+'_name').set_value('UI test game with a very long title ' * 4)
    test.number_input(key=key+'_price').set_value(-1)
    test.button(key=key+'_submit').click().run()
    assert test.error
    test.number_input(key=key+'_price').set_value(0)
    test.checkbox(key=key+'_free').check()
    test.button(key=key+'_submit').click().run()
    assert_clean(test)
    test.switch_page('pages/publisher/games.py').run()
    assert_clean(test)


def test_admin_create_catalog_and_account(app_test):
    test=app_test('admin')
    test.switch_page('pages/admin/users.py').run()
    test.button(key='create_account_submit').click().run()
    assert test.error
    test.text_input(key='new_username').set_value('ui_created')
    test.text_input(key='new_email').set_value('ui_created@example.com')
    test.text_input(key='new_password').set_value('Example@123')
    test.button(key='create_account_submit').click().run()
    assert_clean(test)
    test.switch_page('pages/admin/catalog.py').run()
    version=test.session_state['form_version']
    key=f'catalog_Genre_None_{version}'
    test.text_input(key=key+'_name').set_value('UI test genre')
    test.button(key=key+'_save').click().run()
    assert_clean(test)


def test_login_failure_success_and_lockout(monkeypatch):
    monkeypatch.setattr(ui,'poster',lambda appid,url,name:ui.placeholder(name))
    test=AppTest.from_file(str(ROOT/'app/main.py'),default_timeout=30).run()
    test.text_input(key='login_username').set_value('gamer1')
    test.text_input(key='login_password').set_value('wrong')
    for _ in range(5):
        test.button(key='login_submit').click().run()
        assert test.error
    test.text_input(key='login_password').set_value('Gamer@123')
    test.button(key='login_submit').click().run()
    assert 'Too many attempts' in test.error[0].value
    test.session_state['locked_until']=0
    test.button(key='login_submit').click().run()
    assert_clean(test)
    assert test.session_state['account']['user_id']==100001
