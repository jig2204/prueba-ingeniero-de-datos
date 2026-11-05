import pandas as pd
import re
from datetime import datetime

#1. Ejercicio Conceptual de Creación de Dataset de Números de Teléfono de Clientes
base_tel = pd.read_csv("base_telefonos.csv", sep=";")

def validacion(celular):

    if pd.isna(celular):
        return "NULO"

    celular = str(celular)

    if len(celular) != 10:
        return "NO CUMPLE LONGITUD"

    if re.search(r"[a-zA-Z]", celular):
        return "CONTIENE LETRAS"

    if not celular.startswith("3"):
        return "NO ES DE COLOMBIA"

    return "VALIDO"

base_tel["validacion_tel"] = base_tel["celular"].apply(validacion)

registos = (base_tel["id"].count())

dupli = base_tel.duplicated(subset=["celular"]).sum() 

cel_null = base_tel["celular"].isnull().sum()

base_tel["celular"] = base_tel["celular"].fillna("0").astype(str).str.replace(".0","",regex=False)

base_tel["celular"] = base_tel["celular"].astype(str)

base_tel = base_tel.drop_duplicates()

cel_extrangero = (base_tel["validacion_tel"].str.count("NO ES DE COLOMBIA")).sum()

cel_str = (base_tel["celular"].str.contains(r"[a-zA-Z]",na=False).sum()) 

cel_len_m10 =  (base_tel["celular"].str.len()!= 10).sum()

valida_null = base_tel["celular"].isnull().sum()

tel_validos = (base_tel["validacion_tel"].str.count("VALIDO")).sum()

print("1️⃣ . Ejercicio Conceptual de Creación de Dataset de Números de Teléfono de Clientes")
print("--"*30)
print("📂 Validacion de registros del dataset de entrada:")
print(f"    Cantidad de registros telefonicos:  {registos}/")
print(f"    Registros duplicados de cel:        {dupli}")
print(f"    Registros nulos:                    {cel_null}")
print(f"    Registros con celulares con letras: {cel_str}")
print(f"    Registros que no cumplen  logitud:  {cel_len_m10}")
print(f"    Registros extranjeros:              {cel_extrangero}")
print("--"*30)
print("Se procede a eliminar duplicados y a general los dataset para gestion y validacion:")
datos_validos = base_tel[base_tel["validacion_tel"] == "VALIDO"]
datos_validos.to_csv("base_tel_validos_gest.csv")
print(" ✅ Dataset para la gestion: base_tel_validos_gest.csv ")
print("--"*30)
print("Se genera el dataset de informacion que no cumple para la gestion y se proceda a validar actulizacion de datos")
datos_errados = base_tel[base_tel["validacion_tel"] != "VALIDO"]
datos_errados.to_csv("base_tel_errados.csv")
print(" ⚠️  Dataset para la validacion y actualizacion de datos: base_tel_errados.csv")
print("--"*30)
print("--"*30)

##2. Ejercicio Conceptual de KPI's
print("2️⃣ . Ejercicio Conceptual de KPI's")
print("--"*30)
print(" 📋 Se crea dataset de reportes de ejecución para seguimiento y validación de la calidad de datos")
print("     DATASET Auditoria_datos.csv")
auditoria = pd.DataFrame({
    "fecha_ejecucion"   : [datetime.now()],
    "total_registros"   : [registos],
    "telefonos_validos" : [tel_validos],
    "telefonos_null"    : [cel_null],
    "telef_con_letras"  : [cel_str],
    "tel_extranero"    : [cel_extrangero],
    "porcentaje_Validos": [(tel_validos/registos)*100],
    "porcentaje_rechazados" : [((registos - tel_validos)/registos)*100]
})

auditoria.to_csv("Auditoria_datos.csv",mode="a", index=False,header=False)

vali_auditoria = pd.read_csv("Auditoria_datos.csv", sep=",")

vali_auditoria = vali_auditoria[["fecha_ejecucion","porcentaje_Validos","porcentaje_rechazados"]]
print("REGISTROS DE EJECUCION:")
print(vali_auditoria)
