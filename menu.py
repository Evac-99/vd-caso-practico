import streamlit as st

country = st.Page("spain.py", title="España", icon="🇪🇸")
region = st.Page("andalucia.py", title="Andalucía", icon="🏞️")

pg = st.navigation({"Dashboards":[country, region]})

pg.run()
