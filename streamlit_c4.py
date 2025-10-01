# ---
# lambda-test: false  # auxiliary-file
# ---
# ## Demo Streamlit application.
#
# This application is the example from https://docs.streamlit.io/library/get-started/create-an-app.
#
# Streamlit is designed to run its apps as Python scripts, not functions, so we separate the Streamlit
# code into this module, away from the Modal application code.

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
import os
from dotenv import load_dotenv
from supabase import create_client, Client
    
    
def get_client() -> Client:
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in .env")
    return create_client(url, key)

def main():

    supabase = get_client()

    st.title("🍥 Top 10 Animes")
    st.subheader("Disclaimer: this data was webscraped from MyAnimeList and not based on personal opinion.")

    # 'top_anime' table
    @st.cache_data
    def load_data(nrows=None):
        query = supabase.table("top_anime").select("*")
        if nrows:  
            query = query.limit(nrows)
        response = query.execute()
        return pd.DataFrame(response.data)
    

    data_load_state = st.text("Loading data...")
    animeData = load_data(1000)
    data_load_state.text("Done! (using st.cache_data)")
    if st.checkbox("Show raw game data"):
        st.subheader("Raw data:")    
        st.write(animeData)
        
    st.subheader("🏆 Anime Ratings Distribution")
    st.markdown("The chart below shows the distribution of anime ratings on a scale from 1 to 10.")
    animeData["jitter"] = np.random.uniform(-0.3, 0.3, size=len(animeData))


    dot_plot = (
        alt.Chart(animeData)
        .mark_circle(size=60, opacity=0.6)
    .encode(
            x=alt.X(
                "score:Q",
                title="Rating",
                scale=alt.Scale(domain=[9, 9.4]), 
                axis=alt.Axis(values=np.arange(9, 9.4, 0.005))  
            ),
            y=alt.Y("jitter:Q", title="", axis=None),
            tooltip=["title", "score"]
        )
        .properties(width=700, height=400)
    )

    st.altair_chart(dot_plot, use_container_width=True)
    
    st.subheader("⏰ Anime Release Timeline")
    st.markdown("The lines shows the span of years during which the anime aired, and dots represent anime that aired within a single year.")
    rules = (
        alt.Chart(animeData[animeData["start_year"] != animeData["end_year"]])
        .mark_rule(size=4)
        .encode(
            x=alt.X("start_year:Q", title="Year", scale=alt.Scale(domain=[1985, 2025])),
            x2="end_year:Q",
            y=alt.Y("title:N", title="Anime Title"),
            tooltip=["title", "start_year", "end_year"]
        )
    )

    points = (
        alt.Chart(animeData[animeData["start_year"] == animeData["end_year"]])
        .mark_point(size=80, shape="circle")
        .encode(
            x="start_year:Q",
            y="title:N",
            tooltip=["title", "start_year", "end_year"]
        )
    )

    timeline = (rules + points).properties(width=700, height=400)
    st.altair_chart(timeline, use_container_width=True)

    

if __name__ == "__main__":
    main()