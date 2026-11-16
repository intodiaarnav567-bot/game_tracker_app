import pandas as pd
import streamlit as st
from app import auth, ui
from app.services import catalog, gamer, publisher, admin
account = auth.require_role('gamer')
ui.page_header('Profile', 'Your profile and activity')
profile = gamer.profile()
ui.metrics([('Level', profile['user_level'] or 0)])
with st.form('profile_form'):
    username = st.text_input('Username',value=profile['username'],max_chars=100,key='profile_username')
    url = st.text_input('Profile URL',value=profile['profile_url'] or '',max_chars=500,key='profile_url')
    if st.form_submit_button('Save profile',key='profile_save',type='primary'):
        ui.action(gamer.update_profile,username,url)
st.subheader('Purchase history')
ui.table(gamer.purchases(),'profile_purchases')
st.subheader('Your reviews')
reviews = [r for r in catalog.reviews() if r['user_id']==account['user_id']]
for review in ui.paginate(reviews,'profile_reviews'):
    game = next(g for g in catalog.games() if g['appid']==review['appid'])
    st.write(game['name'])
    ui.review_form(game,review)
