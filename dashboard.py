import streamlit as st
import pandas as pd
import sqlalchemy as sql
import pyodbc 
import datetime as dt
from tempfile import _TemporaryFileWrapper
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.colors import Colormap
import planilla_liquidacion
from locale import setlocale, LC_NUMERIC

setlocale(LC_NUMERIC, "es_AR.UTF-8")

st.set_page_config(
    page_title="IPS - Haberes previsionales",          # Título de la pestaña del navegador
    page_icon="ips.ico",           # Ícono de la pestaña (emoji o archivo .png/.jpg/.ico)
    layout="wide",        # "centered" (default) o "wide"
    initial_sidebar_state="auto",  # "auto" (default), "expanded" o "collapsed"
    menu_items={"About": "Aplicación desarrollada por el Departamento de Sistemas del IPS."}  ,
    
)


engine: sql.Engine = sql.create_engine("mssql+pyodbc://IPSBD/Liquidacion?"
                           "driver=ODBC+Driver+17+for+SQL+Server")

liqs  = pd.read_sql("""SELECT NAME FROM SYS.DATABASES WHERE NAME LIKE
                    '[0-9][0-9][0-9][0-9]-[0-9][0-9]' order by create_date  desc""", engine)

container = st.container()

st.sidebar.image("resources\logo_IPS_header.png")
# Buscar la liquidacion del mes actual o la ultima menor al mes 13 (1º SAC) o 14 (2º SAC)

# Seleccionar la liquidacion actual por defecto
liq_sel = st.sidebar.selectbox(
    "Seleccione liquidación",
    liqs, 
    format_func=lambda x: ("1º SAC" if x[-2:] == "13" else "2º SAC" if x[-2:] == "14" 
                           else x[-2:]) + "/" + x[0:4],
    width=150,
    
)

# liq_sql en formato en variable nombre_liq, ej: "Sep de 2024"
nombre_liq = ("1º SAC" if liq_sel[-2:] == "13" else "2º SAC" if liq_sel[-2:] == "14" else liq_sel[-2:]) + "/" + liq_sel[0:4]

st.title("Análisis de Haberes Previsionales - " + nombre_liq)

plla_haberes = planilla_liquidacion.PlanillaLiquidacion(liq_sel).obtener_datos_liquidacion()
plla_plus = planilla_liquidacion.PlanillaLiquidacion(liq_sel).obtener_datos_plus()
plla_refuerzo = planilla_liquidacion.PlanillaLiquidacion(liq_sel).obtener_datos_extra()


# NORMALIZACION DE DATOS DEL DATAFRAME

plla_haberes["TIPO"] = plla_haberes.apply(
    lambda x: "Ret Pol."
    if x["REPARTICION"] in ("Retiro Policial", "Retiro Carcelario")
    else "Pensiones"
    if x["TIPO"] == "pen"
    else "Jubilaciones",
    axis=1,
)

plla_haberes["FNAC"] = pd.to_datetime(
    plla_haberes["FNAC"], format="%d/%m/%Y", errors="coerce"
)
plla_haberes["EDAD"] = pd.to_datetime("today") - plla_haberes["FNAC"]
plla_haberes["EDAD"] = plla_haberes["EDAD"].dt.days / 365

plla_haberes["SEXO"] = plla_haberes.apply(
    lambda x: "Masculino"
    if x["SEXO"] == "M"
    else "Femenino"
    if x["SEXO"] == "F"
    else x["SEXO"],
    axis=1,
)

plla_haberes["LOCALIDAD"] = plla_haberes["LOCALIDAD"].apply(
    lambda x: "SIN LOCALIDAD" if x == 0 else x
)
plla_haberes["LOCALIDAD"] = plla_haberes["LOCALIDAD"].apply(
    lambda x: "SAN LUIS\nDEL PALMAR" if x == "SAN LUIS DEL PALMAR" else x
)

plla_haberes["TIPOREPARTICION"] = plla_haberes["TIPOREPARTICION"].replace({
    "AGUAS": "Aguas",
    "NO": "Org.Desc.",
    "MG": "Adm. Central",
    "SP": "Salud Pública",
    "AC": "Adm. Central",
    "Legisladores": "P. Legislativo",
    "DOC": "Docente",
    "JUPOLICIA": "Policia",
    "MOVILIDADES": "Otras leyes",
    "Cautelares": "Otras leyes",
    "Certificado": "Otras leyes",
    "Especial": "Otras leyes",
})

tabResumen, tabReparticion, tabLocalidad = st.tabs(["Resumen General", "Análisis por Repartición", "Análisis por Localidad"])

with tabResumen:
   
    # Formateo de columnas
    col1, col2, col3  = st.columns(3, vertical_alignment="top", gap="small",)

    # GRAFICA COSTO TOTAL
    costos: dict = {
        "Haberes": plla_haberes["BRUTO"].sum(),
        "Plus Unificado" : plla_plus["BRUTO"].sum(),
        "Plus Refuerzo" : plla_refuerzo["BRUTO"].sum(),
    }

    fig, ax = plt.subplots(figsize=(4, 4), tight_layout=True)

    sector, textos, autotextos = plt.pie(
        costos.values(),
        autopct=lambda p: f"{p:.2f}%\n(${p * sum(costos.values()) / 1e8:.0f}M)",
        shadow=False, startangle=90, labels=["Haberes", "Plus\nUnificado", "Plus\nRefuerzo"],
        labeldistance=1.3, pctdistance=0.84, textprops={"fontsize": 10})

    for autotext in autotextos:
        autotext.set_color("white")
        # autotext.set_weight('bold')

    centre_circle = plt.Circle((0, 0), 0.70, fc="white")
    fig = plt.gcf()
    fig.gca().add_artist(centre_circle)
    ax.text(0, 0, "Costo\nTotal\n" + f"{sum(costos.values()) / 1e6:.0f} M",
        ha="center", va="center", fontsize=14,fontweight="bold")

    plt.tight_layout()
    plt.rcParams["savefig.dpi"] = 1200

    col1.pyplot(fig)
    # st.dataframe(costos, column_config={"value": st.column_config.NumberColumn(
    #     "Valores", format="accounting", help="Haberes")}, )
            

    # CANTIDAD POR SEXO Y TIPO GENERAL

    cmap: plt.Colormap = plt.get_cmap("Pastel1")
    colores: list[tuple[float, float, float, float]] = [cmap(i) for i in range(3)]

    fig, axs = plt.subplots(figsize=(4, 4))

    cant_por_sexo = plla_haberes.groupby("SEXO")["SEXO"].count()

    cant_por_sexo.plot.pie(
        ax=axs,y="BRUTO",autopct=lambda p: f"{p:.2f}%\n ({p * len(plla_haberes) / 100:.0f})",
        label="",colors=["#ff91af", "#9fc5e8"],pctdistance=0.85)

    centre_circle = plt.Circle((0, 0), 0.70, fc="white")
    axs.add_artist(centre_circle)
    axs.text(0,0,"Beneficios\n" + f"({len(plla_haberes):.0f})",ha="center",
        va="center", fontsize=12, fontweight="bold")


    col2.pyplot(fig)
    # exp = st.expander("Datos")
    # exp.dataframe(cant_por_sexo, column_config={"value": st.column_config.NumberColumn(
    #     "Valores", format="accounting", help="Haberes")})


    fig, axs = plt.subplots(figsize=(4, 4))

    brutos_por_tipo_cuenta = plla_haberes.groupby("TIPO")["CONTROL"].count()

    brutos_por_tipo_cuenta = brutos_por_tipo_cuenta.reset_index().rename(columns={"CONTROL": "CUENTA"})
    brutos_por_tipo_cuenta = brutos_por_tipo_cuenta.set_index("TIPO")

    brutos_por_tipo_cuenta.plot.pie(ax=axs,y="CUENTA",colors=colores,autopct=lambda p: f"{p:.2f}% ({p * len(plla_haberes) / 100:.0f})",
                                    label="",pctdistance=0.85)
    plt.legend().remove()
    centre_circle = plt.Circle((0, 0), 0.70, fc="white")
    axs.add_artist(centre_circle)
    axs.text(0,0,"Beneficios\n" + f"({len(plla_haberes):.0f})",ha="center",
             va="center",fontsize=12,fontweight="bold")

    plt.tight_layout()
    plt.rcParams["savefig.dpi"] = 1200


    col3.pyplot(fig)
    # exp = st.expander("Datos")
    # exp.dataframe(brutos_por_tipo_cuenta, column_config={"value": st.column_config.NumberColumn(
    #     "Valores", format="accounting", help="Haberes")})

with tabReparticion:
    col1, col2, col3 = st.columns(3, vertical_alignment="top", gap="small")

    # POR REPARTICION - BRUTO Y CANTIDAD
    pastel1: Colormap = plt.get_cmap("Pastel1")
    pastel2: Colormap = plt.get_cmap("Pastel2")

    colores: list[tuple[float, float, float, float]] = [cmap(i) for i in range(pastel1.N-1)] + \
        [pastel2(i) for i in range(pastel2.N)]

    fig, axs = plt.subplots(figsize=(4,4), tight_layout=True)

    # Obtener las 10 primeras reparticiones con mayor BRUTO
    top_10_reparticiones_bruto = plla_haberes.groupby("TIPOREPARTICION")["BRUTO"].\
        sum().nlargest(10).index

    # Calcular el total del BRUTO del resto de las reparticiones
    resto_reparticiones_bruto: pd.DataFrame = plla_haberes[~plla_haberes['TIPOREPARTICION']\
        .isin(top_10_reparticiones_bruto)]

    otras = "Otras: " + " - ".join(resto_reparticiones_bruto['TIPOREPARTICION'].unique().tolist()) 

    # Calcular el total del BRUTO del resto de las reparticiones
    total_resto_reparticiones_bruto = resto_reparticiones_bruto['BRUTO'].sum()

    # Crear los datos para el gráfico de pastel
    data_top_10_bruto = plla_haberes.loc[plla_haberes['TIPOREPARTICION'].\
        isin(values=top_10_reparticiones_bruto), ["TIPOREPARTICION", "BRUTO"]]

    # Concatenar las series
    data_top_10_bruto.loc[len(data_top_10_bruto)] = ["Otras", \
        total_resto_reparticiones_bruto]

    data_top_10_bruto_grp: pd.DataFrame = data_top_10_bruto.groupby("TIPOREPARTICION").sum("BRUTO")

    fig, axs = plt.subplots(figsize=(4,4), tight_layout=True)

    sectores, textos, autos = plt.pie(data_top_10_bruto_grp["BRUTO"], \
        labels=data_top_10_bruto_grp.index,  autopct="%1.2f%%", startangle=135,
        pctdistance=0.85, colors=colores[:11], textprops={'fontsize': 7}, 
        wedgeprops={'width': 0.5}, counterclock=False)

    for i, aut in enumerate(iterable=autos):
            aut.set_fontsize(fontsize=7)

    centre_circle = plt.Circle((0,0),0.70,fc='white')
    axs.add_artist(centre_circle)
    axs.text(0, 0, 'Haber\nBruto\nTotal\n' 
                f'({sum(plla_haberes["BRUTO"])/1e6:.0f} M)', 
                ha='center', va='center', fontsize=12, fontweight='bold')

    axs.legend().set_visible(False)

    col1.pyplot(fig)
    
    # Obtener las 10 primeras reparticiones con mayor cantidad
    top_10_reparticiones_cantidad = plla_haberes.groupby("TIPOREPARTICION").count() \
        .nlargest(n=10, columns="CONTROL").index

    resto_reparticiones_cantidad = plla_haberes[~plla_haberes['TIPOREPARTICION']\
        .isin(top_10_reparticiones_cantidad)]

    # Calcular el total del BRUTO del resto de las reparticiones
    total_resto_reparticiones = resto_reparticiones_cantidad.count()["CONTROL"].sum()

    # Crear los datos para el gráfico de pastel
    data_top_10: pd.DataFrame = plla_haberes.loc[plla_haberes['TIPOREPARTICION'].\
        isin(top_10_reparticiones_bruto), ["TIPOREPARTICION", "CONTROL"]]

    data_top_10_grp = data_top_10.groupby("TIPOREPARTICION").count()["CONTROL"]

    # Concatenar las series
    data_top_10_grp = pd.concat( [data_top_10_grp, \
        pd.Series(data={"Otras": total_resto_reparticiones})] )

    data_top_10_grp = data_top_10_grp.sort_index()  

    fig, axs = plt.subplots(figsize=(4,4), tight_layout=True)

    sectores, textos, autos = axs.pie(x=data_top_10_grp, 
            labels=data_top_10_grp.index, autopct=lambda p:f'{p:.2f}%', 
            shadow=False, startangle=135, explode=[0.01] * len(data_top_10_grp), 
            pctdistance=0.85, colors=colores[:11], counterclock=False,
            textprops={"fontsize": 7, "color": "black"})

    for i, aut in enumerate(autos):
        if data_top_10_grp.iloc[i] / data_top_10_grp.sum() < 0.05:
            if ((i % 2) == 0):
                x, y = aut.get_position()
                aut.set_position((x * 0.95, y * 0.95)) 
                
    for i, texto in enumerate(textos):
        if data_top_10_grp.iloc[i] / data_top_10_grp.sum() < 0.05:
            if ((i % 2) == 0):
                x, y = texto.get_position()
                texto.set_position((x * 1, y * 0.95)) 

    centre_circle = plt.Circle((0,0),radius=0.70,fc='white')
    axs.add_artist(centre_circle)
    axs.text(0, 0, 'Beneficios\n' f'({len(plla_haberes):.0f})', ha='center', 
                va='center', fontsize=12, fontweight='bold')

    axs.legend().set_visible(False)

    plt.legend().set_visible(False)
    plt.rcParams['savefig.dpi'] = 1200 

    # Ajustar el layout para reducir el espacio entre los gráficos de pastel
    plt.subplots_adjust(wspace=0, hspace=5)

    col2.pyplot(fig)
    exp = st.expander("Datos")
    exp.dataframe(data_top_10_grp, column_config={
        "0": st.column_config.NumberColumn(label="Valores", format="%d")} )
