import streamlit as st
import pandas as pd
import math
from pathlib import Path
import altair as alt
import json

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
def get_data_from_csv(file_path):
    DATA_FILENAME = file_path   
    df = pd.read_csv(DATA_FILENAME)

    return df




def fires_per_reg_barchart(input_df):
    data = input_df.groupby(['comunidad', 'anio']).size().reset_index(name='total').sort_values(by='total', ascending=False)
    data = data[(data.anio >= from_year) & (data.anio <= to_year)]

    chart = alt.Chart(data).transform_aggregate(
        total='sum(total)',
        groupby=['comunidad']
    ).mark_bar(color=colores[0]).encode(
        x=alt.X('comunidad:N', sort='-y', title='Comunidad Autónoma', axis=alt.Axis(labelAngle=-90, labelLimit=0)),
        y=alt.Y('total:Q', title='Número total de incendios'),
        tooltip=[
            alt.Tooltip("total", title="Nº incendios")  
        ]
    ).properties(
        height=500
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

    bar = base.mark_bar().transform_calculate(Variable = '"NDVI"').encode(
        y=alt.Y('count:Q', title='Número de hectáreas quemadas'),
        color=alt.Color('Variable:N', scale=alt.Scale(range=colores_reversed))
    )

    line = base.mark_line(strokeWidth=3, point=alt.OverlayMarkDef(filled=False, fill="white")).transform_calculate(Variable = '"Número de incendios"').encode(
        y=alt.Y('total:Q', title='Número de incendios'),
        color=alt.Color('Variable:N', scale=alt.Scale(range=colores_reversed))
    )

    hover = alt.selection_point(
        fields=["rango_5_anios"], nearest=False, on="pointermove", empty="none"
    )

    selector = base.mark_rect(opacity=0).encode(
        opacity=alt.value(0),
        tooltip=[
            alt.Tooltip('rango_5_anios:O', title='Rango años'),
            alt.Tooltip('count:Q', title='Hectáreas quemadas'),
            alt.Tooltip('total:Q', title='Número de incendios')
        ]
    ).add_params(hover)

    chart = alt.layer(bar, line, selector).resolve_scale(
        y='independent'
    ).properties(
        height=500
    )

    return chart


def fires_per_year(input_df): 
    data = input_df[(input_df.anio >= from_year) & (input_df.anio <= to_year)].groupby(['anio']).agg(
        total=('perdidassuperficiales', 'sum'),
        count=('perdidassuperficiales', 'size')
    ).reset_index().sort_values(by='total', ascending=False)

    base = alt.Chart(data).encode(
        x=alt.X('anio:O', title='Año')
    )

    numero = base.mark_bar(color=colores[0]).encode(
        y=alt.Y('count:Q', title='Número total de incendios')
    ).properties(height=250, width=800)


    ha = base.mark_bar(color=colores[1],strokeWidth=3).encode(
        y=alt.Y('total:Q', title='Número de hectáreas quemadas')
    ).properties(height=250)

    hover = alt.selection_point(
        fields=["anio"], nearest=False, on="pointermove", empty="none"
    )

    selector = base.mark_rect(opacity=0).encode(
        opacity=alt.value(0),
        tooltip=[
            alt.Tooltip('anio:O', title='Año'),
            alt.Tooltip('count:Q', title='Número de incendios'),
            alt.Tooltip('total:Q', title='Hectáreas quemadas')
        ]
    ).add_params(hover)

    points_numero = base.mark_point(color=colores[0]).encode(
        y=alt.Y('count:Q'),
        opacity=alt.condition(hover, alt.value(1), alt.value(0))
    )
    points_ha = base.mark_point(color= colores[1]).encode(
        y=alt.Y('total:Q'),
        opacity=alt.condition(hover, alt.value(1), alt.value(0))
    )
    rule = base.mark_rule(color='gray').encode(
        opacity=alt.condition(hover, alt.value(0.4), alt.value(0))
    )



    chart = alt.vconcat(
        alt.layer(numero, selector, points_numero, rule),
        alt.layer(ha, selector, points_ha, rule)
    ).resolve_scale(
        x='shared',
        y='independent'
    )
    return chart


def bubbles(input_df):
    data = input_df[(input_df.anio >= from_year) & (input_df.anio <= to_year)]
    max_y = data.groupby('comunidad_y')['count'].sum().max()

    base = alt.Chart(data).transform_aggregate(
        total_incendios='sum(count)',
        total_hectareas='sum(total)',
        ndvi='mean(ndvi_mean)',
        groupby=['comunidad_y']
    )
    bubbles = base.mark_circle(opacity=0.75).encode(
        x=alt.X('ndvi:Q', title='NVDI'),
        y=alt.Y('total_incendios:Q', title='Número total de incendios'),
        size=alt.Size('total_hectareas:Q', title='Hectáreas quemadas', legend=None, scale=alt.Scale(range=[200, 4500])),
        color=alt.Color('comunidad_y:N', title='Comunidad', scale=alt.Scale(scheme='category20')),
        tooltip=[
            alt.Tooltip('comunidad_y:N', title='Comunidad'),
            alt.Tooltip('total_incendios:Q', title='Total incendios'),
            alt.Tooltip('total_hectareas:Q', title='Total hectáreas'),
            alt.Tooltip('ndvi:Q', title='NDVI medio', format='.2f')
    ]
    )

    dummies = base.transform_calculate(
        ndvi_boost='datum.ndvi * 1.1',
        incendios_boost='datum.total_incendios * 1.1'
    ).mark_circle(opacity=0).encode(
        x='ndvi_boost:Q',
        y='incendios_boost:Q'
    )

    chart = (bubbles + dummies).properties(
        height=500,     
        title=alt.TitleParams(
            '*Tamaño de las burbujas determinado por el número de hectáreas quedadas',
            color='darkgray',
            baseline='bottom',
            orient='bottom',
            anchor='end', 
            fontWeight = 'normal'
        )
)
    return chart    


def serious_fires_ndvi(ndvi, fires):
    selector = alt.selection_point(
        fields=["mesdeteccion"], 
        nearest=True, 
        on="mouseover", 
        empty="none"
    )

    chart_incendios = (
        alt.Chart(fires[fires.perdidassuperficiales > 500])
        .transform_calculate(Variable = '"Número de incendios"')
        .mark_line(strokeWidth=3,point=alt.OverlayMarkDef(filled=False, fill="white"))
        .encode(
            x=alt.X("mesdeteccion:O", sort=meses_ordenados, title="Mes"),
            y=alt.Y("count():Q", title="Número de incendios graves"), 
            color=alt.Color('Variable:N', scale=alt.Scale(range=colores_reversed))
        )
    )

    chart_ndvi = (
        alt.Chart(ndvi) 
        .transform_calculate(Variable = '"NDVI"')
        .mark_line(strokeWidth=3,point=alt.OverlayMarkDef(filled=False, fill="white"))
        .encode(
            x=alt.X("mesdeteccion:O", sort=meses_ordenados, title="Mes"),
            y=alt.Y("NDVI:Q", title="NDVI"),
            color = alt.Color('Variable:N', scale=alt.Scale(range=colores_reversed))
        )
    )

    puntos = (
        alt.Chart(fires[fires.perdidassuperficiales > 500].merge(ndvi, on="mesdeteccion"))
        .mark_circle(size=0, opacity=0) 
        .encode(
            x=alt.X("mesdeteccion:O", sort=meses_ordenados),
            tooltip=[
                alt.Tooltip("mesdeteccion:O", title="Mes"),
                alt.Tooltip("count():Q", title="Incendios graves"),
                alt.Tooltip("NDVI:Q", title="NDVI")
            ]
        )
        .add_params(selector)
    )

    combined_chart = alt.layer(
        chart_incendios,
        chart_ndvi,
        puntos
    ).resolve_scale(
        x="shared",
        y="independent"
    ).properties(
        height=500, 
        title=alt.TitleParams(
            '*El filtrado de años no aplica a este gráfico',
            color='darkgray',
            baseline='bottom',
            orient='bottom',
            anchor='end', 
            fontWeight = 'normal'
        )
    ).configure_legend(
        titleFontSize=14,
        labelFontSize=12,
        orient='bottom'
    )


    return combined_chart



def previous_ndvi(input_df):
    data = input_df[(input_df.anio >= from_year) & (input_df.anio <= to_year)].groupby(["fortnight", "anio", "provincia"]).agg({
        "NDVI_previo": ["mean"],
        "perdidassuperficiales": ["sum", "mean", "max"],
        "geometry": "count"
    }).reset_index().copy()

    data.columns = [
        "_".join(col).strip("_") if isinstance(col, tuple) else col
        for col in data.columns
    ]

    data = data.rename(columns={"geometry_count": "n_incendios"})

    scatter = alt.Chart(data).mark_circle(size=100).encode(
        x=alt.X('n_incendios:Q', title='Número de incendios'),
        y=alt.Y('perdidassuperficiales_sum:Q', title='Hectáreas quemadas'),
        color=alt.Color('NDVI_previo_mean:Q', title='NDVI medio', scale=alt.Scale(scheme='viridis')),
        tooltip=[
            alt.Tooltip('provincia:N', title='Comunidad'),
            alt.Tooltip('n_incendios:Q', title='Nº incendios'),
            alt.Tooltip('perdidassuperficiales_sum:Q', title= 'Hectáreas quemadas'),
            alt.Tooltip('NDVI_previo_mean:Q', title= 'NDVI previo')
        ]
    ).properties(height=500)

    return scatter


incendios = get_data_from_csv('data/incendios.csv')
incendios_ndvi = get_data_from_csv('data/merged_data.csv')
ndvi_mensual = get_data_from_csv('data/NDVI_mensual.csv' )
incendios_ndvi_previo = get_data_from_csv('data/NDVI_previo_incendios.csv')

colores = ["#CA694B","#88BB75"]
colores_reversed = ["#88BB75","#CA694B"]
meses_ordenados = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

with st.sidebar: 
    st.title("Filtros")
    min_value = incendios['anio'].min()
    max_value = incendios['anio'].max()

    from_year, to_year = st.slider(
        'Ano ',
        min_value=min_value,
        max_value=max_value,
        value=[min_value, max_value]
    )

# -----------------------------------------------------------------------------
# Draw the actual page

# Set the title that appears at the top of the page.
'''
# Dashboard incendios España
'''

st.markdown("## Incidencios por comunidad autónoma")

row1 = st.columns((1, 1), gap='large')
with row1[0]:
    st.subheader("Número de incendios")
    st.altair_chart(fires_per_reg_barchart(incendios), use_container_width=True)

with row1[1]:
    st.subheader("NDVI, Número de incendios y hectáreas quemadas")
    st.altair_chart(bubbles(incendios_ndvi), use_container_width=True)

st.divider()
st.markdown("## 📆 Hectáreas quemadas y número de incendios anuales")

row2 = st.columns((1, 1), gap='large')

if row2[0].button("Rangos de 5 años", width="stretch"):
    st.altair_chart(fires_per_5year(incendios), use_container_width=True)

if row2[1].button("Anual", width="stretch"):
    st.altair_chart(fires_per_year(incendios), use_container_width=True)




st.divider()
st.markdown("## NDVI medio y previo")

row3 = st.columns((1, 1), gap='large')


with row3[0]:
    st.subheader("NDVI medio mensual y número de grandes incendios forestales")
    st.altair_chart(serious_fires_ndvi(ndvi_mensual, incendios), use_container_width=True)


with row3[1]:
    st.subheader("Relación NDVI previo a los incendios con el número de incendios y su severidad")
    st.altair_chart(previous_ndvi(incendios_ndvi_previo), use_container_width=True)
