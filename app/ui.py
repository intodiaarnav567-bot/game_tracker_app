import base64
import html
from io import BytesIO
import logging
from pathlib import Path
import textwrap

import pandas as pd
import mysql.connector
from PIL import Image, ImageDraw, ImageOps
import requests
import streamlit as st

from app import auth, config
from app.services import catalog, gamer, publisher, admin

LOGGER = logging.getLogger(__name__)


def theme():
    st.html('''<style>.game-title{height:3.4em;overflow:hidden;display:-webkit-box;
        -webkit-line-clamp:2;-webkit-box-orient:vertical;font-weight:600}
        .poster{width:100%;aspect-ratio:460/215;object-fit:cover;border-radius:8px}
        .poster:hover{filter:brightness(1.08)}
        .pill{display:inline-block;border-radius:20px;padding:3px 10px;background:#263e54;color:#bfe2ff}
        .game-metrics{display:flex;flex-wrap:wrap;gap:1rem;margin:0}
        .game-metric{min-width:min(155px,100%);max-width:100%;box-sizing:border-box;
            border:1px solid rgba(128,128,128,.38);border-radius:8px;padding:1rem}
        .game-metric dt,.game-metric dd{overflow-wrap:anywhere}
        .game-metric dd{margin:0;font-size:clamp(1.55rem,3vw,2rem);line-height:1.35;
            font-variant-numeric:tabular-nums}
        </style>''')


def page_header(title, subtitle=''):
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def metrics(items):
    cards = []
    for label, value in items:
        cards.append(
            f'<div class="game-metric"><dt>{html.escape(str(label))}</dt>'
            f'<dd>{html.escape(str(value))}</dd></div>'
        )
    if cards:
        st.html('<dl class="game-metrics">' + ''.join(cards) + '</dl>')


def empty_state(message='Nothing here yet. Browse the Store →'):
    st.info(message)


def fmt_money(price, currency='USD'):
    if not price:
        return 'Free'
    symbol = {'USD': '$', 'INR': '₹', 'EUR': '€', 'GBP': '£'}.get(currency, currency + ' ')
    return f'{symbol}{float(price):,.2f}'


def fmt_playtime(minutes):
    hours, minutes = divmod(int(minutes or 0), 60)
    return f'{hours}h {minutes}m'


def fmt_date(value):
    return value.strftime('%d %b %Y') if value else '—'


def badge(label):
    st.html(f'<span class="pill">{html.escape(label)}</span>')


def placeholder(name):
    image = Image.new('RGB', (460, 215), '#22364c')
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((20, 20, 440, 195), radius=14, outline='#517393', width=2)
    draw.multiline_text((40, 75), '\n'.join(textwrap.wrap(name[:90], 28)), fill='#eef3fa', spacing=10)
    return image


@st.cache_data(ttl=3600, max_entries=250, show_spinner=False)
def poster(appid, url, name):
    cache = config.ROOT / 'app/assets/posters'
    path = cache / f'{int(appid)}.jpg'
    candidates = [url, path, f'https://cdn.cloudflare.steamstatic.com/steam/apps/{int(appid)}/header.jpg']
    for candidate in candidates:
        try:
            if isinstance(candidate, Path):
                image = Image.open(candidate)
            elif candidate and str(candidate).startswith(('https://', 'http://')):
                # Seed image URLs are intentional placeholders.
                if 'example.com/' in candidate:
                    continue
                with requests.get(candidate, timeout=3, stream=True) as response:
                    response.raise_for_status()
                    data = response.raw.read(5_000_001)
                if len(data) > 5_000_000:
                    continue
                image = Image.open(BytesIO(data))
            else:
                continue
            image = ImageOps.fit(image.convert('RGB'), (460, 215))
            try:
                cache.mkdir(parents=True, exist_ok=True)
                image.save(path, 'JPEG')
            except OSError:
                pass
            return image
        except Exception:
            continue
    return placeholder(name)


def action(function, *args):
    if st.session_state.busy:
        return
    st.session_state.busy = True
    try:
        function(*args)
    except (ValueError, PermissionError) as error:
        st.error(str(error))
        return
    except mysql.connector.Error as error:
        LOGGER.exception('Database action rejected')
        messages = {
            1062: 'That name, email, or record already exists.',
            1451: 'This record is still in use. Update its linked records first.',
            1452: 'A linked record has changed. Refresh and try again.',
            3819: 'Check the values in this form and try again.',
        }
        if error.errno == 1644:
            st.error(error.msg)
        else:
            st.error(messages.get(error.errno, 'Something went wrong. Please try again.'))
        return
    except Exception:
        LOGGER.exception('Application action failed')
        st.error('Something went wrong. Please try again.')
        return
    finally:
        st.session_state.busy = False
    st.session_state.flash = 'Saved successfully'
    st.session_state.form_version += 1
    st.cache_data.clear()
    st.rerun()


@st.dialog('Please confirm')
def confirm_dialog(message, function, *args):
    st.write(message)
    if st.button('Confirm', key='confirm_action', type='primary'):
        action(function, *args)
    if st.button('Cancel', key='cancel_action'):
        st.rerun()


def paginate(rows, key):
    if not rows:
        empty_state('Nothing here yet.')
        return []
    count = (len(rows) + 11) // 12
    if count == 1:
        return rows
    page = st.number_input('Page', min_value=1, max_value=count, value=1, step=1,
                           key=f'page_{key}_{count}')
    st.session_state.page_numbers[key] = page
    return rows[(page - 1) * 12:page * 12]


def table(rows, key):
    selected = paginate(rows, key)
    if selected:
        frame = pd.DataFrame(selected)
        for column in frame:
            if column.endswith(('_at', '_date', '_time')) or column == 'last_played':
                frame[column] = frame[column].apply(lambda value: fmt_date(value) if pd.notna(value) else '—')
        st.dataframe(frame, hide_index=True, width='stretch')


def game_card(game, key, mode='store', status=None, open_session=None):
    appid = game['appid']
    with st.container(border=True, height=500):
        image = poster(appid, game.get('header_image_url'), game['name'])
        data = BytesIO()
        image.save(data, 'PNG')
        encoded = base64.b64encode(data.getvalue()).decode()
        st.html(f'<img class="poster" alt="{html.escape(game["name"])}" src="data:image/png;base64,{encoded}">')
        st.html(f'<div class="game-title" title="{html.escape(game["name"])}">{html.escape(game["name"])}</div>')
        st.caption(fmt_money(game['price'], game['currency']))
        label = 'Delisted' if not game['is_active'] else {'owned': 'Owned', 'borrowed': 'Borrowed', 'wishlist': 'Wishlisted'}.get(status, 'Active')
        badge('Playing now' if open_session and open_session['appid'] == appid else label)
        if mode == 'library':
            st.caption(f'{fmt_playtime(game["playtime_forever"])} · {fmt_date(game["last_played"])}')
            playing = open_session and open_session['appid'] == appid
            if st.button('End session' if playing else 'Start session', key=f'{key}_play_{appid}',
                         disabled=bool(open_session and not playing), help='End your current session first.' if open_session and not playing else None):
                action(gamer.end if playing else gamer.start, appid)
            if st.button('Remove', key=f'{key}_remove_{appid}'):
                confirm_dialog('Remove this game from your Library? Your history will be kept.', gamer.ownership, appid, 'removed')
        elif mode == 'wishlist':
            if st.button('Buy', key=f'{key}_buy_{appid}', disabled=not game['is_active'], help='This game is delisted.' if not game['is_active'] else None):
                action(gamer.buy, appid)
            if st.button('Remove', key=f'{key}_remove_{appid}'):
                confirm_dialog('Remove this game from your Wishlist?', gamer.ownership, appid, 'removed')
        elif mode == 'store' and auth.identity()['role'] == 'gamer':
            unavailable = not game['is_active'] or status in ('owned', 'borrowed')
            if st.button('Buy', key=f'{key}_buy_{appid}', type='primary', disabled=unavailable,
                         help='Already in your Library or unavailable.' if unavailable else None):
                action(gamer.buy, appid)
            if st.button('Wishlist', key=f'{key}_wish_{appid}', disabled=bool(status in ('owned','borrowed','wishlist') or not game['is_active']),
                         help='Already in your Library or unavailable.' if status in ('owned','borrowed','wishlist') or not game['is_active'] else None):
                action(gamer.ownership, appid, 'wishlist')
        if st.button('View game', key=f'{key}_view_{appid}', width='stretch'):
            st.session_state.selected_appid = appid
            st.rerun()


def grid(rows, key, mode='store', statuses=None, open_session=None):
    for offset in range(0, len(rows), 4):
        # Two pairs stack at narrow widths while each pair keeps two columns.
        pairs = st.columns(2)
        for pair_index, pair in enumerate(pairs):
            with pair:
                columns = st.columns(2, wrap=False)
                for column, game in zip(columns, rows[offset + pair_index * 2:offset + pair_index * 2 + 2]):
                    with column:
                        status = game.get('ownership_status') or (statuses or {}).get(game['appid'])
                        game_card(game, key, mode, status, open_session)


def review_form(game, existing=None):
    existing = existing or {}
    with st.form(f'review_{game["appid"]}_{st.session_state.form_version}'):
        text = st.text_area('Your review', value=existing.get('review_text') or '', key=f'review_text_{game["appid"]}')
        recommended = st.checkbox('Recommended', value=bool(existing.get('recommended', True)), key=f'recommended_{game["appid"]}')
        if st.form_submit_button('Save review', type='primary', key=f'save_review_{game["appid"]}'):
            action(gamer.review, game['appid'], text, recommended)


def detail():
    appid = st.session_state.selected_appid
    if appid is None:
        return False
    if st.button('← Back', key='detail_back'):
        st.session_state.selected_appid = None
        st.rerun()
    game = next((g for g in catalog.games() if g['appid'] == appid), None)
    if not game:
        empty_state('This game is unavailable.')
        return True
    page_header(game['name'], fmt_money(game['price'], game['currency']))
    st.image(poster(appid, game.get('header_image_url'), game['name']), width=700)
    st.write(game.get('short_description') or 'No description yet.')
    for kind in ('Developer', 'Publisher', 'Genre', 'Platform'):
        st.caption(kind + ' · ' + (', '.join(row['name'] for row in catalog.links(appid, kind)) or '—'))
    st.caption(f'Released {fmt_date(game["release_date"])} · Age {game["required_age"] or 0}+')
    account = auth.identity()
    library = {g['appid']: g for g in gamer.library()} if account['role'] == 'gamer' else {}
    entry = library.get(appid)
    if account['role'] == 'gamer':
        owned = entry and entry['ownership_status'] in ('owned', 'borrowed')
        if st.button('Buy', key='detail_buy', type='primary', disabled=bool(owned or not game['is_active']), help='Already in your Library or unavailable.' if owned or not game['is_active'] else None):
            action(gamer.buy, appid)
        if st.button('Wishlist', key='detail_wishlist', disabled=bool((entry and entry['ownership_status'] != 'removed') or not game['is_active']), help='Already in your Library or unavailable.' if (entry and entry['ownership_status'] != 'removed') or not game['is_active'] else None):
            action(gamer.ownership, appid, 'wishlist')
    st.subheader('Achievements')
    unlocked = {a['achievement_id'] for a in gamer.achievements() if a['unlock_time']} if account['role'] == 'gamer' else set()
    for item in paginate(catalog.achievements(appid), 'detail_achievements'):
        hidden = item['hidden'] and account['role'] == 'gamer' and item['achievement_id'] not in unlocked
        st.write('Hidden achievement' if hidden else item['achievement_name'])
        if not hidden:
            st.caption(item['description'] or '')
    st.subheader('Reviews')
    reviews = catalog.reviews(appid)
    st.caption(f'{float(game.get("rating", 0)):.0f}% recommended · {len(reviews)} reviews')
    if entry and entry['ownership_status'] != 'wishlist':
        own = next((r for r in reviews if r['user_id'] == account['user_id']), None)
        review_form(game, own)
    for review in paginate(reviews, 'detail_reviews'):
        st.write(review['username'] + (' · Recommended' if review['recommended'] else ' · Not recommended'))
        st.write(review['review_text'])
        st.caption(f'{fmt_date(review["review_date"])} · {review["helpful"]} helpful votes')
        if account['role'] == 'gamer':
            for helpful, label in ((True, 'Helpful'), (False, 'Not helpful')):
                if st.button(label, key=f'vote_{review["review_id"]}_{helpful}', disabled=review['user_id'] == account['user_id'], help='You cannot vote on your own review.' if review['user_id'] == account['user_id'] else None):
                    action(gamer.vote, review['review_id'], helpful)
    return True


def game_form(game=None):
    game = game or {}
    appid = game.get('appid')
    role = auth.identity()['role']
    key = f'game_{appid}_{st.session_state.form_version}'
    with st.form(key):
        data = {}
        data['name'] = st.text_input('Name', value=game.get('name', ''), max_chars=200, key=key+'_name')
        data['short_description'] = st.text_area('Description', value=game.get('short_description') or '', key=key+'_description')
        data['price'] = st.number_input('Price', value=float(game.get('price', 0)), step=0.01, key=key+'_price')
        data['currency'] = st.text_input('Currency', value=game.get('currency', 'USD'), max_chars=3, key=key+'_currency').upper()
        date = st.date_input('Release date', value=game.get('release_date'), key=key+'_date')
        data['release_date'] = date.isoformat() if date else ''
        data['required_age'] = st.number_input('Age', min_value=0, value=int(game.get('required_age') or 0), key=key+'_age')
        data['is_free'] = int(st.checkbox('Free', value=bool(game.get('is_free', False)), key=key+'_free'))
        data['header_image_url'] = st.text_input('Poster URL', value=game.get('header_image_url') or '', key=key+'_poster')
        upload = st.file_uploader('Upload poster', type=['png', 'jpg', 'jpeg'], key=key+'_upload') if role == 'admin' and appid else None
        kinds = list(catalog.KINDS) if role == 'admin' else ['Genre', 'Category', 'Platform', 'Developer']
        for kind in kinds:
            options = {r['id']: r['name'] for r in catalog.reference(kind)}
            selected = [r['id'] for r in catalog.links(appid, kind)] if appid else []
            data['categories' if kind == 'Category' else kind.lower()+'s'] = st.multiselect(kind, options, default=selected, format_func=options.get, key=key+'_'+kind)
        data['new_developer'] = st.text_input('New developer (optional)', max_chars=200, key=key+'_newdev')
        if st.form_submit_button('Save game', key=key+'_submit', type='primary'):
            if not data['name'].strip():
                st.error('Enter a game name.')
            elif data['price'] < 0:
                st.error("Price can't be negative")
            elif len(data['currency']) != 3 or not data['currency'].isalpha():
                st.error('Enter a three-letter currency code.')
            else:
                if data['is_free']:
                    data['price'] = 0
                if upload:
                    try:
                        image = ImageOps.fit(Image.open(upload).convert('RGB'), (460, 215))
                        image.save(config.ROOT / f'app/assets/posters/{appid}.jpg')
                        data['header_image_url'] = ''
                    except Exception:
                        st.error('Choose a valid PNG or JPEG image.')
                        return
                action(admin.save_game if role == 'admin' else publisher.save_game, appid, data)


def chart(rows, x, y, key):
    if rows:
        import plotly.express as px
        frame = pd.DataFrame(rows)
        frame[y] = pd.to_numeric(frame[y])
        figure = px.bar(frame, x=x, y=y, color_discrete_sequence=['#79c6ff'])
        figure.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(figure, key=key, width='stretch')


def store():
    search = st.text_input('Search games', key='store_search')
    genres = {r['id']:r['name'] for r in catalog.reference('Genre')}
    genre = st.selectbox('Genre', [None,*genres], format_func=lambda x: genres.get(x,'All genres'), key='store_genre')
    price = st.selectbox('Price', ['All','Free','Paid'], key='store_price')
    sort = st.selectbox('Sort', ['Name','Price','Newest'], key='store_sort')
    rows = [g for g in catalog.games() if g['is_active'] and search.lower() in g['name'].lower()]
    if genre:
        rows = [g for g in rows if genre in [r['id'] for r in catalog.links(g['appid'],'Genre')]]
    if price != 'All':
        rows = [g for g in rows if bool(g['is_free']) == (price == 'Free')]
    if sort == 'Price':
        rows.sort(key=lambda g:g['price'])
    elif sort == 'Newest':
        rows.sort(key=lambda g:str(g['release_date'] or ''),reverse=True)
    statuses = {g['appid']:g['ownership_status'] for g in gamer.library()} if auth.identity()['role'] == 'gamer' else {}
    grid(paginate(rows,'store'), 'store', statuses=statuses)
