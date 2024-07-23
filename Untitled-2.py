
### EJEMPLO 


import matplotlib.pyplot as plt
import pandas as pd
import tempfile
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

# Suponiendo que `brutos` es tu DataFrame
brutos = pd.DataFrame({
    'SEXO': ['M', 'F', 'M', 'F', 'M'],
    'REPARTICION': ['Retiro Policial', 'Retiro Carcelario', 'Otra', 'Otra', 'Otra'],
    'TIPO': ['jub', 'pen', 'jub', 'jub', 'pen'],
    'BRUTO': [1000, 2000, 3000, 4000, 5000]
})

fig, axs = plt.subplots(2, 1, figsize=(4, 8))

brutos["SEXO"] = brutos.apply(lambda x: "Masculino" if x["SEXO"] == "M" else "Femenino" if x["SEXO"] == "F" else x["SEXO"], axis=1)
brutos.groupby("SEXO")["SEXO"].count().plot.pie(ax=axs[0], autopct="%1.1f%%", label='', colors=["#ff91af","#9fc5e8"])
axs[0].set_title("Beneficios por sexo", fontdict={'family': 'Arial', 'size': 14, 'weight': 'bold', 'style': 'normal'})

# Añadir el círculo blanco al primer gráfico de pastel
centre_circle = plt.Circle((0, 0), 0.70, fc='white')
axs[0].add_artist(centre_circle)

# Función para calcular los porcentajes
def make_autopct(values):
    def my_autopct(pct):
        total = sum(values)
        val = int(round(pct*total/100.0))
        return '{p:.1f}% ({v:d})'.format(p=pct,v=val)
    return my_autopct

brutos["JPR"] = brutos.apply(lambda x: "Retiros" if x["REPARTICION"] in ("Retiro Policial", "Retiro Carcelario") else "Pensiones" if x["TIPO"]=='pen' else 'Jubilaciones', axis=1)
brutos.groupby("JPR").count().plot.pie(ax=axs[1], y="BRUTO", autopct=make_autopct(brutos["JPR"].value_counts()), label='')
plt.legend().remove()
axs[1].set_title('Beneficios por Tipo', fontdict={'family': 'Arial', 'size': 14, 'weight': 'bold', 'style': 'normal'})

# Añadir el círculo blanco al segundo gráfico de pastel
centre_circle = plt.Circle((0, 0), 0.70, fc='white')
axs[1].add_artist(centre_circle)

# Añadir el logotipo en la esquina superior derecha
logo_path = 'ruta_a_tu_imagen.png'  # Reemplaza con la ruta a tu imagen
logo = plt.imread(logo_path)
imagebox = OffsetImage(logo, zoom=0.1)  # Ajusta el zoom según sea necesario

# Ajustar la posición del logotipo (coordenadas en fracción del gráfico)
ab = AnnotationBbox(imagebox, (1, 1), xycoords='axes fraction', box_alignment=(1, 1), frameon=False)
axs[0].add_artist(ab)

plt.tight_layout()

temp_pie_beneficios_sexo_tipo = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
plt.savefig(temp_pie_beneficios_sexo_tipo.name)
plt.show()
plt.close()
