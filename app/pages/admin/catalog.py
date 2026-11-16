import pandas as pd
import streamlit as st
from app import auth, ui
from app.services import catalog, gamer, publisher, admin
account = auth.require_role('admin')
ui.page_header('Catalog Data', 'Genres, platforms, and studios')
for tab,kind in zip(st.tabs(list(catalog.KINDS)),catalog.KINDS):
    with tab:
        rows=catalog.reference(kind)
        ui.table(rows,'catalog_'+kind)
        options={r['id']:r['name'] for r in rows}
        identifier=st.selectbox(kind,[None,*options],format_func=lambda x:options.get(x,'Add new'),key='catalog_select_'+kind)
        key=f'catalog_{kind}_{identifier}_{st.session_state.form_version}'
        with st.form(key):
            name=st.text_input('Name',value=options.get(identifier,''),max_chars=50 if kind=='Platform' else 100 if kind in ('Genre','Category') else 200,key=key+'_name')
            if st.form_submit_button('Save',key=key+'_save'):
                ui.action(admin.catalog_save,kind,identifier,name)
        if st.button('Delete',key='catalog_delete_'+kind,disabled=identifier is None,help='Select an entry first.' if identifier is None else None):
            ui.confirm_dialog('Delete this catalog entry?',admin.catalog_delete,kind,identifier)
