import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="Tablero PPB", layout="wide")
st.title("📊 Tablero de Seguimiento - Política Pública de la Bicicleta")

# -----------------------------------------------------------------------------
# 1. CARGA Y LIMPIEZA DE DATOS
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    archivo = "interfaz web_tablero.xlsx"
    df_seg = pd.read_excel(archivo, sheet_name="Seguimiento_ppb")
    df_mapa = pd.read_excel(archivo, sheet_name="mapa_ppb")
    
    # Limpiamos espacios en los nombres de las columnas
    df_seg.columns = df_seg.columns.str.strip()
    df_mapa.columns = df_mapa.columns.str.strip()
    
    # Limpiamos espacios y aseguramos que la primera letra sea mayúscula (Ej: "Avance", "Meta")
    if 'VARIABLE' in df_seg.columns:
        df_seg['VARIABLE'] = df_seg['VARIABLE'].astype(str).str.strip().str.capitalize()
        
    return df_seg, df_mapa

try:
    df_seg, df_mapa = load_data()
except FileNotFoundError:
    st.error("No se encontró el archivo 'interfaz web_tablero.xlsx'.")
    st.stop()

# -----------------------------------------------------------------------------
# 2. FILTROS
# -----------------------------------------------------------------------------
item_seleccionado = st.selectbox("📌 Selecciona el ITEM:", df_seg['ITEM'].unique())

st.sidebar.header("Filtros Temporales")
anios_disponibles = sorted(df_seg['AÑO'].dropna().unique())
anio_seleccionado = st.sidebar.multiselect("📅 Selecciona el AÑO:", anios_disponibles, default=anios_disponibles)

# Aplicar filtros
df_filtrado = df_seg[df_seg['ITEM'] == item_seleccionado]
if anio_seleccionado:
    df_filtrado = df_filtrado[df_filtrado['AÑO'].isin(anio_seleccionado)]

# Cuadro de VIGENCIA
if 'VIGENCIA' in df_filtrado.columns and not df_filtrado.empty:
    vigencias = df_filtrado['VIGENCIA'].dropna().unique()
    if len(vigencias) > 0:
        st.info(f"**Vigencia actual del ITEM seleccionado:** {vigencias[0]}")

st.markdown("---")

# -----------------------------------------------------------------------------
# SECCIÓN 1: AVANCE FÍSICO
# -----------------------------------------------------------------------------
st.subheader("📈 Avance Físico vs Meta")

if 'VARIABLE' in df_filtrado.columns and 'VALOR' in df_filtrado.columns:
    # Agrupar y pivotear
    df_agrupado = df_filtrado.groupby(['AÑO', 'VARIABLE'])['VALOR'].sum().reset_index()
    df_pivot = df_agrupado.pivot(index='AÑO', columns='VARIABLE', values='VALOR').fillna(0).reset_index()
    
    # Asegurar que las columnas existan con la primera mayúscula
    if 'Avance' not in df_pivot.columns: df_pivot['Avance'] = 0
    if 'Meta' not in df_pivot.columns: df_pivot['Meta'] = 0

    col1, col2 = st.columns(2)

    with col1:
        # Gráfico de barras
        fig_barras = go.Figure()
        fig_barras.add_trace(go.Bar(x=df_pivot['AÑO'], y=df_pivot['Avance'], name='Avance', marker_color='#2CA02C'))
        fig_barras.add_trace(go.Bar(x=df_pivot['AÑO'], y=df_pivot['Meta'], name='Meta', marker_color='#1F77B4'))
        fig_barras.update_layout(barmode='group', xaxis_title="Año", yaxis_title="Valor Físico")
        st.plotly_chart(fig_barras, use_container_width=True)

    with col2:
        # Gráfico de líneas (% Avance)
        df_pivot['% Avance'] = np.where(df_pivot['Meta'] == 0, 0, df_pivot['Avance'] / df_pivot['Meta'])
        fig_lineas = px.line(df_pivot, x='AÑO', y='% Avance', markers=True)
        fig_lineas.update_traces(line_color='#FF7F0E')
        fig_lineas.update_layout(yaxis_tickformat='.1%')
        st.plotly_chart(fig_lineas, use_container_width=True)

    # Gráficos Apilados
    st.markdown("### 📊 Desglose de Totales por Periodo")
    col3, col4 = st.columns(2)

    def crear_grafico_apilado(df_pivoteado, anio_inicio, anio_fin, titulo):
        df_periodo = df_pivoteado[(df_pivoteado['AÑO'] >= anio_inicio) & (df_pivoteado['AÑO'] <= anio_fin)].copy()
        if df_periodo.empty: return None, 0
        
        df_melted = df_periodo.melt(id_vars=['AÑO'], value_vars=['Avance', 'Meta'], var_name='Indicador', value_name='Valor')
        fig = px.bar(df_melted, x='Indicador', y='Valor', color='AÑO', barmode='stack', title=titulo)
        
        pct_total = (df_periodo['Avance'].sum() / df_periodo['Meta'].sum()) if df_periodo['Meta'].sum() > 0 else 0
        return fig, pct_total

    with col3:
        fig_25, pct_25 = crear_grafico_apilado(df_pivot, 2021, 2025, "Contribución 2021-2025")
        if fig_25:
            st.plotly_chart(fig_25, use_container_width=True)
            st.success(f"**% de avance respecto a la meta (2025):** {pct_25:.2%}")

    with col4:
        fig_39, pct_39 = crear_grafico_apilado(df_pivot, 2021, 2039, "Contribución 2021-2039")
        if fig_39:
            st.plotly_chart(fig_39, use_container_width=True)
            st.info(f"**% de avance respecto a la meta final (2039):** {pct_39:.2%}")

st.markdown("---")

# -----------------------------------------------------------------------------
# SECCIÓN 2: EJECUCIÓN FINANCIERA
# -----------------------------------------------------------------------------
st.subheader("💰 Ejecución Financiera")

if 'VARIABLE' in df_filtrado.columns and 'COSTO' in df_filtrado.columns:
    df_costo = df_filtrado.groupby(['AÑO', 'VARIABLE'])['COSTO'].sum().reset_index()
    df_costo_pivot = df_costo.pivot(index='AÑO', columns='VARIABLE', values='COSTO').fillna(0).reset_index()
    
    if 'Avance' not in df_costo_pivot.columns: df_costo_pivot['Avance'] = 0
    if 'Meta' not in df_costo_pivot.columns: df_costo_pivot['Meta'] = 0

    df_costo_pivot.rename(columns={'Avance': 'Costo Ejecutado', 'Meta': 'Costo Estimado'}, inplace=True)
    df_costo_pivot['% Ejecución'] = np.where(df_costo_pivot['Costo Estimado'] == 0, 0, df_costo_pivot['Costo Ejecutado'] / df_costo_pivot['Costo Estimado'])

    col5, col6 = st.columns(2)
    
    with col5:
        fig_costo_bar = go.Figure()
        fig_costo_bar.add_trace(go.Bar(x=df_costo_pivot['AÑO'], y=df_costo_pivot['Costo Ejecutado'], name='Costo Ejecutado', marker_color='#8C564B'))
        fig_costo_bar.add_trace(go.Bar(x=df_costo_pivot['AÑO'], y=df_costo_pivot['Costo Estimado'], name='Costo Estimado', marker_color='#E377C2'))
        fig_costo_bar.update_layout(barmode='group', xaxis_title="Año", yaxis_title="Costo")
        st.plotly_chart(fig_costo_bar, use_container_width=True)

    with col6:
        fig_costo_line = px.line(df_costo_pivot, x='AÑO', y='% Ejecución', markers=True)
        fig_costo_line.update_traces(line_color='#D62728')
        fig_costo_line.update_layout(yaxis_tickformat='.1%')
        st.plotly_chart(fig_costo_line, use_container_width=True)

st.markdown("---")

# -----------------------------------------------------------------------------
# SECCIÓN 3: MAPA / LOCALIDADES
# -----------------------------------------------------------------------------
st.subheader("📍 Mapa de Presencia Territorial por Localidades")

# Usaremos un bloque para cargar el GeoJSON local de las localidades
@st.cache_data
def obtener_geojson():
    import json
    # Lee el archivo local que está en la misma carpeta
    archivo_geojson = "Loca_project_2.json"
    try:
        with open(archivo_geojson, "r", encoding="utf-8") as f:
            geojson_data = json.load(f)
        return geojson_data
    except FileNotFoundError:
        st.warning(f"No se encontró el archivo '{archivo_geojson}'. Asegúrate de que esté en la misma carpeta que app.py.")
        return None
    except Exception as e:
        st.warning(f"Error al leer el GeoJSON: {e}")
        return None

geojson_bogota = obtener_geojson()

df_mapa_filtrado = df_mapa[df_mapa['ITEM'] == item_seleccionado].copy()

if geojson_bogota and not df_mapa_filtrado.empty and 'LOCALIDAD' in df_mapa_filtrado.columns:
    
    # 1. Creamos una lista con todas las localidades oficiales de Bogotá
    todas_localidades = [
        "USAQUEN", "CHAPINERO", "SANTA FE", "SAN CRISTOBAL", "USME", "TUNJUELITO", 
        "BOSA", "KENNEDY", "FONTIBON", "ENGATIVA", "SUBA", "BARRIOS UNIDOS", 
        "TEUSAQUILLO", "LOS MARTIRES", "ANTONIO NARIÑO", "PUENTE ARANDA", 
        "LA CANDELARIA", "RAFAEL URIBE URIBE", "CIUDAD BOLIVAR", "SUMAPAZ"
    ]
    
    # 2. Creamos un DataFrame base con todas las localidades de Bogotá en "Sin presencia"
    df_presencia = pd.DataFrame({'LOCALIDAD_OFICIAL': todas_localidades})
    df_presencia['Presencia'] = "Sin presencia"
    
    # 3. Normalizamos las localidades de tu Excel para cruzarlas correctamente (quitamos tildes)
    df_mapa_filtrado['Loc_Norm'] = (df_mapa_filtrado['LOCALIDAD']
                                    .astype(str)
                                    .str.strip()
                                    .str.upper()
                                    .str.normalize('NFKD')
                                    .str.encode('ascii', errors='ignore')
                                    .str.decode('utf-8')) 
    
    localidades_con_presencia = df_mapa_filtrado['Loc_Norm'].unique()
    
    # 4. Marcamos con "Presencia Activa" las localidades que están en tu Excel filtrado
    df_presencia.loc[df_presencia['LOCALIDAD_OFICIAL'].isin(localidades_con_presencia), 'Presencia'] = "Presencia Activa"
    
    # 5. Creamos el mapa coroplético (de polígonos) usando tu llave LocNombre
    fig_mapa_poligonos = px.choropleth_mapbox(
        df_presencia,
        geojson=geojson_bogota,
        locations="LOCALIDAD_OFICIAL",
        featureidkey="properties.LocNombre", # <--- Conectado a tu variable LocNombre
        color="Presencia",
        color_discrete_map={"Presencia Activa": "#2CA02C", "Sin presencia": "#E5ECF6"}, # Verde y Gris claro
        mapbox_style="carto-positron",
        center={"lat": 4.6097, "lon": -74.0817},
        zoom=9.5,
        opacity=0.6,
        height=550,
        labels={"Presencia": "Estado"},
        title="Localidades con presencia para el ITEM seleccionado"
    )
    
    fig_mapa_poligonos.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
    st.plotly_chart(fig_mapa_poligonos, use_container_width=True)
    
else:
    # Alternativa si falla la carga del GeoJSON o no hay datos
    st.info("No se pudo generar el mapa de polígonos. Asegúrate de tener el archivo 'Loca_project_2.json' en la misma carpeta que el código o que el ítem tenga localidades asociadas.")