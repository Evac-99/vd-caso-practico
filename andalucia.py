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



def plot_ica_pies(input_df):
    niveles = ['Buena','Razonablemente buena', 'Regular', 'Desfavorable', 'Muy desfavorable', 'Extremadamente desfavorable']
    colores=['#38A2CE', '#32B15E', '#F1E549', '#F28C28', '#D53441', '#A52DA4']

    agg = input_df[(input_df.anio >= from_year) & (input_df.anio <= to_year)].groupby(['Incendio', 'label']).size().reset_index(name='count')

    agg['porcentaje'] = 100 * agg['count'] / agg.groupby('Incendio')['count'].transform('sum')
    agg['label'] = pd.Categorical(agg['label'], categories=niveles, ordered=True)
    agg['label_orden'] = agg['label'].cat.codes

    agg = agg.sort_values(['Incendio', 'label_orden']).reset_index(drop=True)

    pie = alt.Chart(agg).mark_arc(innerRadius=130, opacity=1).encode(
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
        ],
        facet=alt.Facet("Incendio:N", title='¿Hubo incendio?')
    ).properties(
        title="Distribución de calidad del aire en días con vs sin incendio"
        , width=600,
        height=200
    )

    return pie 


def plot_graph_contaminant_lines(incendios, contaminante, nombre_contaminante): 
    df_incendios = incendios[(incendios.anio >= from_year)&(incendios.anio <= to_year)]
    df_contaminante = contaminante[(contaminante['AÑO'] >= from_year)&(contaminante['AÑO'] <= to_year)]
    df_incendios['perdidassuperficiales_suavizada'] = df_incendios['perdidassuperficiales'].rolling(30,  min_periods=1).mean()
    df_contaminante['contaminante_suavizado'] = df_contaminante['VALOR_MEDIO'].rolling(30,  min_periods=1).mean()


    line_incendios = alt.Chart(df_incendios).mark_line(color="purple").encode(
        x="fecha:T",
        y=alt.Y("perdidassuperficiales_suavizada:Q", axis=alt.Axis(title="Superficie quemada (ha)")),
        tooltip=["fecha","perdidassuperficiales_suavizada"]
    )

    line_contaminant = alt.Chart(df_contaminante).mark_line(color="steelblue").encode(
        x="FECHA:T",
        y=alt.Y("contaminante_suavizado:Q", axis=alt.Axis(title={nombre_contaminante})),
        tooltip=["FECHA","contaminante_suavizado"]
    )

    lineas = alt.layer(line_incendios, line_contaminant).resolve_scale(
        y='independent'
    ).properties(
        title=f"Evolución de incendios vs {nombre_contaminante}",
        width=1000
    )

    return lineas

def plot_graph_contaminant_boxes(incendios, bandas, df_contaminante, nombre_contaminante): 
    
    data = incendios[(incendios.anio >= from_year)&(incendios.anio <= to_year)].groupby(['fecha'])['perdidassuperficiales'].sum().reset_index()
    contaminante = df_contaminante.groupby(['FECHA'])['VALOR_MEDIO'].mean().reset_index()
    contaminante['anio'] = contaminante['FECHA'].astype('datetime64[ns]').dt.year
    contaminante[(contaminante.anio >= from_year)&(contaminante.anio <= to_year)]
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
                range=['#1f77b4', 'purple']
            ))
    ).properties(
        width=300,
        height=300,
        title='Comparación de superficie total vs total incendios por comunidad'
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
            title='Rangos ' + nombre_contaminante
        )
    )


    chart = alt.layer(background, boxplot).resolve_scale(
        y='shared',
        color='independent'
    ).properties(
        width=300,
        height=300,
        title='Comparación de superficie total vs total incendios por comunidad'
    )
    return chart


incendios = get_data_from_csv('data/dias_incendio_andalucia.csv')
incendios['anio'] = incendios['fecha'].astype('datetime64[ns]').dt.year


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
    'PM 2,5': pm25, 
    'PM 10':pm10
}

with st.sidebar: 
    st.title("Filtros")
    nombre_contaminante = st.selectbox("Contaminante", contaminantes.keys() )
    
    df = contaminantes[nombre_contaminante]
    min_value = df['AÑO'].min()
    max_value = df['AÑO'].max()

    from_year, to_year = st.slider(
        'Año *',
        min_value=min_value,
        max_value=max_value,
        value=[min_value, max_value])
    '''
    *La información del año es recalculada cada vez que se cambia de contaminante debido a los distintos horizontes temporales de los contaminantes.
    '''

# -----------------------------------------------------------------------------
# Draw the actual page

# Set the title that appears at the top of the page.
'''
# Andalucía
'''




row1 = st.columns((1, 1), gap='medium')
row2 = st.columns((1, 3), gap='medium')


with row1[0]:
    st.altair_chart(plot_ica_pies(ica))



with row2[0]:
    st.altair_chart(plot_graph_contaminant_boxes(incendios, bandas, contaminantes[nombre_contaminante], nombre_contaminante))

with row2[1]:    
    st.altair_chart(plot_graph_contaminant_lines(incendios, contaminantes[nombre_contaminante], nombre_contaminante))



