import pandas as pd
import numpy as np
import sqlalchemy as sql
import pyodbc
import locale
from decouple import config
import re

pd.options.display.float_format = lambda x: '{:,.2f}'.format(x)

#locale.setlocale(locale=locale.LC_ALL, category='es_ES')

SERVIDOR = config("SERVIDOR")
SERVIDOR_PLUS = config("SERVIDOR_PLUS")
SERVIDOR_REFUERZO = config("SERVIDOR_REFUERZO")

engine: sql.Engine = sql.create_engine(f"mssql+pyodbc://{SERVIDOR}/Liquidacion?"
                           f"driver=ODBC+Driver+17+for+SQL+Server")
engine_plus: sql.Engine = sql.create_engine(f"mssql+pyodbc://{SERVIDOR_PLUS}/" 
                        f"Liquidacion?driver=ODBC+Driver+17+for+SQL+Server")
engine_refuerzo: sql.Engine = sql.create_engine(f"mssql+pyodbc://"
    f"{SERVIDOR_REFUERZO}/Liquidacion?driver="
    f"ODBC+Driver+17+for+SQL+Server""")

class PlanillaLiquidacion:
    def __init__(self, liquidacion: str ):
        self.engine = engine
        
        """ el formato de la liquidacion debe ser yyyy-mm siendo mm posible tomar
        los valores 13 y 14 para el aguinaldo """
        pattern = r'\d{4}-\d{2}|13|14'
        if not re.match(pattern, liquidacion):
            raise ValueError("El formato de la liquidacion debe ser yyyy-mm")
        
        self.liquidacion = liquidacion

    def obtener_datos_liquidacion(self) -> pd.DataFrame:
        cons_creditos: pd.DataFrame = f"""SELECT L.PLLA, L.ORDEN, L.AFILIADO, SUM(MONTO) AS CREDITOS
        FROM [{self.liquidacion}].dbo.Liquidacion L
        INNER JOIN [{self.liquidacion}].dbo.Codigos C ON C.CODIGO=L.CODIGO
        WHERE C.TIPO='C'
        GROUP BY L.PLLA, L.ORDEN, L.AFILIADO"""

        creditos: pd.DataFrame = pd.read_sql(cons_creditos, engine)
        cons_beneficios: str = f"""SELECT DL.CONTROL, DL.PLLA, DL.ORDEN, DL.AFILIADO, D.SEXO,
            DL.BENEFICIO, B.DETALLE AS BENEFICIO_TIPO, B.TIPO,
            R.DETALLE AS REPARTICION, R.TIPOREPARTICION, L.LOCALIDAD, FNAC 
            FROM DATOSAFILIADO D  
            LEFT OUTER JOIN BENEFICIO B ON B.COD=D.COD_BENEFICIO
            LEFT OUTER JOIN REPARTICION R ON R.COD=D.LETRA
            LEFT OUTER JOIN LOCALIDADES L ON D.CODLOCALIDAD=L.CODLOCALIDAD
            INNER JOIN [{self.liquidacion}].dbo.DatosAfiliado DL on DL.CONTROL=D.CONTROL"""

        beneficios: pd.DataFrame = pd.read_sql(cons_beneficios, engine)
        brutos: pd.DataFrame = beneficios.merge(
            creditos, on=["PLLA", "ORDEN", "AFILIADO"], how="left"
        ).fillna(0.0)

        brutos["BRUTO"] = brutos["BENEFICIO"] + brutos["CREDITOS"]
        return brutos
        
        
    
    def obtener_datos_plus(self) -> pd.DataFrame:
        cons_creditos_plus = f"""SELECT L.PLLA, L.ORDEN, L.AFILIADO, SUM(MONTO) AS CREDITOS
        FROM [{self.liquidacion}].dbo.Liquidacion L
        INNER JOIN Codigos C ON C.CODIGO=L.CODIGO
        WHERE C.TIPO='C'
        GROUP BY L.PLLA, L.ORDEN, L.AFILIADO"""

        creditos_plus = pd.read_sql(cons_creditos_plus, engine_plus)
        cons_beneficios_plus = f"""SELECT D.CONTROL, D.PLLA, D.ORDEN, D.AFILIADO, D.SEXO,
        DL.BENEFICIO, B.DETALLE AS BENEFICIO_TIPO, B.TIPO, R.DETALLE AS REPARTICION, 
        R.TIPOREPARTICION FROM DATOSAFILIADO D 
        LEFT OUTER JOIN BENEFICIO B ON B.COD=COD_BENEFICIO 
        LEFT OUTER JOIN REPARTICION R ON R.COD=LETRA
        INNER JOIN [{self.liquidacion}].dbo.DatosAfiliado DL on DL.CONTROL=D.CONTROL"""

        beneficios_plus: pd.DataFrame = pd.read_sql(cons_beneficios_plus, engine_plus)
        brutos_plus: pd.DataFrame = beneficios_plus.merge(
            creditos_plus, on=["PLLA", "ORDEN", "AFILIADO"], how="left"
        ).fillna(0.0)

        brutos_plus["BRUTO"] = brutos_plus["BENEFICIO"] + brutos_plus["CREDITOS"]
        return brutos_plus
        
    def obtener_datos_extra(self) -> pd.DataFrame:
        cons_creditos_refuerzo: str = f"""SELECT L.PLLA, L.ORDEN, L.AFILIADO, SUM(MONTO) AS CREDITOS
        FROM [{self.liquidacion}].dbo.Liquidacion L
        INNER JOIN Codigos C ON C.CODIGO=L.CODIGO
        WHERE C.TIPO='C'
        GROUP BY L.PLLA, L.ORDEN, L.AFILIADO"""

        creditos_refuerzo: pd.DataFrame = pd.read_sql(
            cons_creditos_refuerzo, engine_refuerzo
        )
        cons_beneficios_refuerzo: str = f"""SELECT D.CONTROL, D.PLLA, D.ORDEN, D.AFILIADO, 
        D.SEXO, DL.BENEFICIO, B.DETALLE AS BENEFICIO_TIPO, B.TIPO,
        R.DETALLE AS REPARTICION 
        FROM DATOSAFILIADO D 
        LEFT OUTER JOIN BENEFICIO B ON B.COD=COD_BENEFICIO
        LEFT OUTER JOIN REPARTICION R ON R.COD=LETRA
        INNER JOIN [{self.liquidacion}].dbo.DatosAfiliado DL on DL.CONTROL=D.CONTROL"""

        beneficios_refuerzo: pd.DataFrame = pd.read_sql(
            cons_beneficios_refuerzo, engine_refuerzo
        )
        brutos_refuerzo: pd.DataFrame = beneficios_refuerzo.merge(
            creditos_refuerzo, on=["PLLA", "ORDEN", "AFILIADO"], how="left"
        ).fillna(0.0)

        brutos_refuerzo["BRUTO"] = (
            brutos_refuerzo["BENEFICIO"] + brutos_refuerzo["CREDITOS"]
        )
        
        return brutos_refuerzo

