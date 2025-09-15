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
def get_data_from_csv(file_path):
    """Grab GDP data from a CSV file.

    This uses caching to avoid having to read the file every time. If we were
    reading from an HTTP endpoint instead of a file, it's a good idea to set
    a maximum age to the cache with the TTL argument: @st.cache_data(ttl='1d')
    """

    # Instead of a CSV on disk, you could read from an HTTP endpoint here too.
    DATA_FILENAME = file_path   
    df = pd.read_csv(DATA_FILENAME)
    return df

def format_nombre_contaminante(contaminante):
    if contaminante == 'PM10': 
        return 'PM 10'
    elif contaminante == 'PM25': 
        return 'PM 2,5'
    else: 
        return contaminante

def plot_ica_pies(input_df):
    niveles = ['Buena','Razonablemente buena', 'Regular', 'Desfavorable', 'Muy desfavorable', 'Extremadamente desfavorable']
    colores = ['#38A2CE', '#32B15E', '#F1E549', '#F28C28', '#D53441', '#A52DA4']

    agg = input_df[(input_df.anio >= from_year) & (input_df.anio <= to_year)] \
        .groupby(['Incendio', 'label']).size().reset_index(name='count')

    agg['porcentaje'] = 100 * agg['count'] / agg.groupby('Incendio')['count'].transform('sum')
    agg['label'] = pd.Categorical(agg['label'], categories=niveles, ordered=True)
    agg['label_orden'] = agg['label'].cat.codes
    agg = agg.sort_values(['Incendio', 'label_orden']).reset_index(drop=True)

    base = alt.Chart(agg).mark_arc(innerRadius=80, opacity=1).encode(
        theta=alt.Theta(field="count", type="quantitative"),
        color=alt.Color(
            "label:N",
            title="Calidad del aire",
            scale=alt.Scale(domain=niveles, range=colores),
            sort=niveles
        ),
        order=alt.Order('label_orden:Q'),
        tooltip=[
            alt.Tooltip('label:N', title='Nivel de calidad'),
            alt.Tooltip('count:Q', title='Cantidad'),
            alt.Tooltip('porcentaje:Q', format='.1f', title='Porcentaje (%)')
        ]
    ).properties(
        height=250
    )

    pie = base.facet(
        column=alt.Facet("Incendio:N", title="¿Hubo incendio?"),
    ).configure_legend(
        orient='bottom',
        direction='horizontal',
        columnPadding=20,
        columns=3,
        labelLimit=0   
    )

    return pie



def plot_graph_contaminant_boxes(incendios, bandas, df_contaminante, nombre_contaminante): 
    
    data = incendios[(incendios.anio >= from_year)&(incendios.anio <= to_year)].groupby(['fecha'])['perdidassuperficiales'].sum().reset_index()
    contaminante = df_contaminante[(df_contaminante['AÑO'] >= from_year)&(df_contaminante['AÑO'] <= to_year)].groupby(['FECHA', 'AÑO'])['VALOR_MEDIO'].mean().reset_index()
    bandas_filtradas = bandas[bandas['contaminante'] == nombre_contaminante]


    max_valor = contaminante['VALOR_MEDIO'].max()
    max_band = math.ceil((max_valor + 10) / 10) * 10

    bandas_filtradas = bandas_filtradas[bandas_filtradas['min'] <= max_valor]
    bandas_filtradas.loc[bandas_filtradas.index[-1], 'max'] = max_band
    
    boxplot = alt.Chart(contaminante).transform_lookup(
        lookup='FECHA',
        from_=alt.LookupData(data, key='fecha', fields=['perdidassuperficiales'])
    ).transform_calculate(
            Incendio = "datum.perdidassuperficiales>0 ? 'Si':'No'"
    ).mark_boxplot(size=50).encode(
        x=alt.X('Incendio:N', title='¿Hubo incendio?'),
        y=alt.Y('VALOR_MEDIO:Q', title='NO2 media'),
        color=alt.Color('Incendio:N', legend=None,        scale=alt.Scale(
                domain=['No', 'Si'],
                range=["#668F58","#994E38"]
            ))
    )

    background = alt.Chart(bandas_filtradas).mark_rect(opacity=0.25).encode(
        y='min:Q',
        y2='max:Q',
        color=alt.Color(
            'label:N',
            scale=alt.Scale(
                domain=bandas_filtradas['label'].tolist(),
                range=bandas_filtradas['color'].tolist()
            ),
            title='Rangos ' + format_nombre_contaminante(nombre_contaminante)
        )
    )


    chart = alt.layer(background, boxplot).resolve_scale(
        y='shared',
        color='independent'
    ).properties(
        height=390, 
        padding={"bottom": 30}  
    ).configure_legend(
        labelLimit=0    
    )
    return chart


def plot_fire_NDVI_monthly(incendios, ndvi): 
    incendios_andalucia = incendios[(incendios.comunidad == 'Andalucia')&(incendios.perdidassuperficiales > 500)]
    
    ndvi['mesdeteccion'] = ndvi['mes'].apply(lambda x: meses_ordenados[x-1])
    incendios_andalucia_agregado = incendios_andalucia.groupby('mesdeteccion')['anio'].count().reindex(meses_ordenados, fill_value=0).reset_index(name="numero")

    df = pd.merge(ndvi, incendios_andalucia_agregado, on="mesdeteccion", how='left')

    chart_incendios = (
        alt.Chart(df)
        .mark_line(color=colores[0],point=alt.OverlayMarkDef(filled=False, fill="white"))
        .transform_calculate(Variable = '"Incendios graves"')
        .encode(
            x=alt.X("mesdeteccion:O", sort=meses_ordenados, title="Mes"),
            y=alt.Y("numero:Q", title="Número de incendios graves"),
            tooltip=[
                alt.Tooltip("mesdeteccion:O", title="Mes"),
                alt.Tooltip("numero:Q", title="Incendios graves"),
                alt.Tooltip("ndvi_mean:Q", title="NDVI")
            ],
            color=alt.Color('Variable:N', scale=alt.Scale(range=colores))
        )
    )

    chart_ndvi = (
        alt.Chart(df)
        .mark_line(color=colores[1], point=alt.OverlayMarkDef(filled=False, fill="white"))
        .transform_calculate(Variable = '"NDVI"')
        .encode(
            x=alt.X("mesdeteccion:O", sort=meses_ordenados, title="Mes"),
            y=alt.Y("ndvi_mean:Q", title="NDVI"), 
            tooltip=[
                alt.Tooltip("mesdeteccion:O", title="Mes"),
                alt.Tooltip("numero:Q", title="Incendios graves"),
                alt.Tooltip("ndvi_mean:Q", title="NDVI")
            ],
            color=alt.Color('Variable:N', scale=alt.Scale(range=colores))
        )
    )

    combined_chart = alt.layer(
        chart_incendios,
        chart_ndvi, 
    ).resolve_scale(
        x='shared',
        y='independent'
    ).properties(height=500).configure_legend(
        titleFontSize=14,
        labelFontSize=12,
        orient='bottom'
    )

    return combined_chart



def plot_fire_contaminant_monthly(incendios, contaminante, nombre_contaminante):
    data = incendios[(incendios.comunidad == 'Andalucia')&(incendios.perdidassuperficiales > 500)]
    incendios_andalucia_agregado = data.groupby('mesdeteccion')['anio'].count().reindex(meses_ordenados, fill_value=0).reset_index(name="numero")

    contaminante = contaminante.groupby('MES')['VALOR_FINAL'].mean()
    contaminante.index = meses_ordenados
    contaminante = contaminante.reset_index().rename(columns={'index': 'mesdeteccion'})
    
    df = pd.merge(contaminante, incendios_andalucia_agregado, on="mesdeteccion", how='left')


    chart_incendios = alt.Chart(df).mark_line( point=alt.OverlayMarkDef(filled=False, fill="white")
        ).transform_calculate(
            Variable = '"Incendios graves"'
        ).encode(
        x=alt.X('mesdeteccion:O', sort=meses_ordenados, title='Mes'),
        y=alt.Y('numero:Q', title='Número de incendios graves'),
        tooltip=[
                alt.Tooltip("mesdeteccion:O", title="Mes"),
                alt.Tooltip("numero:Q", title="Incendios graves"),
                alt.Tooltip("VALOR_FINAL:Q", title="NDVI")
            ],
            color=alt.Color('Variable:N', scale=alt.Scale(range=colores)) 
    )

    chart_ndvi = alt.Chart(df).mark_line(point=alt.OverlayMarkDef(filled=False, fill="white")
        ).transform_calculate(
            Variable = f'"{nombre_contaminante}"'
        ).encode(
        x=alt.X('mesdeteccion:N', sort=meses_ordenados, title='Mes'),
        y=alt.Y('VALOR_FINAL:Q', title=format_nombre_contaminante(nombre_contaminante)),
        tooltip=[
                alt.Tooltip("mesdeteccion:O", title="Mes"),
                alt.Tooltip("numero:Q", title="Incendios graves"),
                alt.Tooltip("VALOR_FINAL:Q", title="NDVI")
            ],
        color=alt.Color('Variable:N', scale=alt.Scale(range=colores))
    )


    combined_chart = alt.layer(
        chart_incendios,
        chart_ndvi
    ).resolve_scale(
        x='shared',
        y='independent'
    ).properties(height=500).configure_legend(
        titleFontSize=14,
        labelFontSize=12,
        orient='bottom'
    )


    return combined_chart

meses_ordenados = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

incendios = get_data_from_csv('data/dias_incendio_andalucia.csv')
incendios['anio'] = incendios['fecha'].astype('datetime64[ns]').dt.year

incendios_orig = get_data_from_csv('data/incendios.csv')
ndvi_andalucia = get_data_from_csv('data/NDVI_andalucia_mensual.csv')
colores = ["#CA694B","#88BB75"]

ica = get_data_from_csv('data/df_ica_diario.csv')
bandas = get_data_from_csv('data/bandas_contaminantes.csv')
o3 = get_data_from_csv('data/o3.csv')
so2 = get_data_from_csv('data/so2.csv')
no2 = get_data_from_csv('data/no2.csv')
pm25 = get_data_from_csv('data/pm25.csv')
pm10 = get_data_from_csv('data/pm10.csv')

contaminantes = {
    'O3': o3,
    'SO2':so2,
    'NO2':no2, 
    'PM25': pm25, 
    'PM10':pm10
}



with st.sidebar: 
    st.title("Filtros")
    nombre_contaminante = st.selectbox("Contaminante", contaminantes.keys(), index=4)
    
    df = contaminantes[nombre_contaminante]
    min_value = df['AÑO'].min()
    max_value = df['AÑO'].max()

    from_year, to_year = st.slider(
        'Año *',
        min_value=min_value,
        max_value=max_value,
        value=[min_value, max_value],
        disabled=True)
    '''
    *La información del año es recalculada cada vez que se cambia de contaminante debido a los distintos horizontes temporales de los contaminantes.
    '''

# -----------------------------------------------------------------------------
# Draw the actual page

# Set the title that appears at the top of the page.
st.title("📊 Incendios forestales en Andalucía")
st.markdown("## 🌍 Comparación días incendio durante el periodo completo")

row1 = st.columns((4,3), gap='large')
with row1[0]:
    st.subheader("Distribución calidad aire")
    st.altair_chart(plot_ica_pies(ica), use_container_width=True)

with row1[1]:
    st.subheader(f"Valores contaminante {format_nombre_contaminante(nombre_contaminante)}")
    st.altair_chart(plot_graph_contaminant_boxes(
        incendios, bandas, contaminantes[nombre_contaminante], nombre_contaminante
    ), use_container_width=True)

st.divider()
st.markdown("## 📆 Datos mensuales")

row2 = st.columns((1, 1), gap='large')
with row2[0]:
    st.subheader("NDVI medio mensual")
    st.altair_chart(plot_fire_NDVI_monthly(incendios_orig, ndvi_andalucia), use_container_width=True)

with row2[1]:
    st.subheader(f"{format_nombre_contaminante(nombre_contaminante)} medio mensual")
    st.altair_chart(plot_fire_contaminant_monthly(
        incendios_orig, contaminantes[nombre_contaminante], nombre_contaminante
    ), use_container_width=True)