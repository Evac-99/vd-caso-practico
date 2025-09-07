import streamlit as st
import pandas as pd
import math
from pathlib import Path
import altair as alt

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='Incendios forestales en España',
    page_icon=':earth_americas:', # This is an emoji shortcode. Could be a URL too.
    layout='wide', 
    initial_sidebar_state='expanded'
)

# -----------------------------------------------------------------------------
# Declare some useful functions.

@st.cache_data
def get_incendios_data():
    """Grab GDP data from a CSV file.

    This uses caching to avoid having to read the file every time. If we were
    reading from an HTTP endpoint instead of a file, it's a good idea to set
    a maximum age to the cache with the TTL argument: @st.cache_data(ttl='1d')
    """

    # Instead of a CSV on disk, you could read from an HTTP endpoint here too.
    DATA_FILENAME = Path(__file__).parent/'data/incendios.csv'
    df = pd.read_csv(DATA_FILENAME)

    MIN_YEAR = 1961
    MAX_YEAR = 2016

    return df



def fires_per_reg_barchart(input_df):
    data = input_df.groupby(['comunidad', 'anio']).size().reset_index(name='total').sort_values(by='total', ascending=False)
    data = data[(data.anio >= from_year) & (data.anio <= to_year)]

    chart = alt.Chart(data).transform_aggregate(
        total='sum(total)',
        groupby=['comunidad']
    ).mark_bar().encode(
        x=alt.X('comunidad:N', sort='-y', title='Comunidad Autónoma', axis=alt.Axis(labelAngle=-30)),
        y=alt.Y('total:Q', title='Número total de incendios'),
        tooltip=['total']
    ).properties(
        width=800,
        height=500,
        title='Número total de incendios por Comunidad Autónoma'
    )
    return chart




def fires_per_5year(input_df): 
    data = input_df.loc[(incendios.anio >= 1970) & (incendios.anio <= 2014), :].groupby(['anio']).agg(
        total=('perdidassuperficiales', 'sum'),
        count=('perdidassuperficiales', 'size')
    ).reset_index().sort_values(by='total', ascending=False)

    data['rango_5_anios'] = data['anio'].apply(lambda x: f"{x - (x % 5)}-{x - (x % 5) + 4}")
    data = data[(data.anio >= from_year) & (data.anio <= to_year)]


    data_grouped = data.groupby('rango_5_anios').agg(
        total=('total', 'sum'),
        count=('count', 'sum')
    ).reset_index().sort_values(by='rango_5_anios')


    base = alt.Chart(data_grouped).encode(
        x=alt.X('rango_5_anios:O', title='Rango de años')
    )

    bar = base.mark_bar(color='#6BAED6').encode(
        y=alt.Y('count:Q', title='Número de hectáreas quemadas')
    )

    line = base.mark_line(color='purple', strokeWidth=3).encode(
        y=alt.Y('total:Q', title='Número total de incendios')
    )

    chart = alt.layer(bar, line).resolve_scale(
        y='independent'
    ).properties(
        width=800,
        height=500,
        title='Superficie total perdida y número de incendios por rango de 5 años'
    )

    return chart


incendios = get_incendios_data()


with st.sidebar: 
    st.title("Filtros")
    min_value = incendios['anio'].min()
    max_value = incendios['anio'].max()

    from_year, to_year = st.slider(
        'Ano ',
        min_value=min_value,
        max_value=max_value,
        value=[min_value, max_value])

# -----------------------------------------------------------------------------
# Draw the actual page

# Set the title that appears at the top of the page.
'''
# :earth_americas: GDP dashboard

Browse GDP data from the [World Bank Open Data](https://data.worldbank.org/) website. As you'll
notice, the data only goes to 2022 right now, and datapoints for certain years are often missing.
But it's otherwise a great (and did I mention _free_?) source of data.
'''

# Add some spacing
''
''




st.altair_chart(fires_per_reg_barchart(incendios))

st.altair_chart(fires_per_5year(incendios))



# Filter the data
filtered_gdp_df = gdp_df[
    (gdp_df['Country Code'].isin(selected_countries))
    & (gdp_df['Year'] <= to_year)
    & (from_year <= gdp_df['Year'])
]

st.header('GDP over time', divider='gray')

''

st.line_chart(
    filtered_gdp_df,
    x='Year',
    y='GDP',
    color='Country Code',
)

''
''


first_year = gdp_df[gdp_df['Year'] == from_year]
last_year = gdp_df[gdp_df['Year'] == to_year]

st.header(f'GDP in {to_year}', divider='gray')

''

cols = st.columns(4)

for i, country in enumerate(selected_countries):
    col = cols[i % len(cols)]

    with col:
        first_gdp = first_year[first_year['Country Code'] == country]['GDP'].iat[0] / 1000000000
        last_gdp = last_year[last_year['Country Code'] == country]['GDP'].iat[0] / 1000000000

        if math.isnan(first_gdp):
            growth = 'n/a'
            delta_color = 'off'
        else:
            growth = f'{last_gdp / first_gdp:,.2f}x'
            delta_color = 'normal'

        st.metric(
            label=f'{country} GDP',
            value=f'{last_gdp:,.0f}B',
            delta=growth,
            delta_color=delta_color
        )
