"""Lectura y busqueda por palabras en las politicas Markdown del curso."""

from pathlib import Path
import re
import unicodedata

from .schemas import FragmentoPolitica

RUTA_DOCUMENTOS = Path(__file__).resolve().parent / "documentos"
ARCHIVOS_POLITICAS = ("envios.md", "devoluciones.md", "atencion.md")
PALABRAS_VACIAS = set(
    "a al algo ante con cual cuales cuando de del debe deben el ella en es esta "
    "este esto ha hay la las lo los me mi mis no o para pedido pedidos por puedo "
    "que quiero se si sin sobre su sus tiene tienen un una unos unas y yo como "
    "cual cuanto donde son ser saber informacion politica politicas".split()
)


def palabras(texto: str) -> set[str]:
    """Normaliza mayusculas y tildes y descarta palabras poco informativas."""
    normalizado = unicodedata.normalize("NFD", texto.lower())
    sin_tildes = "".join(
        caracter for caracter in normalizado
        if unicodedata.category(caracter) != "Mn"
    )
    return set(re.findall(r"[a-z0-9]+", sin_tildes)) - PALABRAS_VACIAS


def cargar_fragmentos() -> list[FragmentoPolitica]:
    """Lee los tres archivos conocidos y separa sus secciones de nivel ##."""
    fragmentos = []
    for nombre in ARCHIVOS_POLITICAS:
        contenido = (RUTA_DOCUMENTOS / nombre).read_text(encoding="utf-8")
        secciones = re.split(r"^## +(.+)$", contenido, flags=re.MULTILINE)
        if len(secciones) == 1:
            raise ValueError(f"La politica {nombre} no contiene secciones.")
        for indice in range(1, len(secciones), 2):
            seccion = secciones[indice].strip()
            texto = secciones[indice + 1].strip()
            if not seccion or not texto:
                raise ValueError(f"La politica {nombre} contiene una seccion vacia.")
            fragmentos.append(FragmentoPolitica(
                archivo=f"documentos/{nombre}", seccion=seccion, texto=texto,
            ))
    return fragmentos


def buscar_fragmentos(consulta: str) -> list[FragmentoPolitica]:
    """Ordena coincidencias: dos puntos por palabra del titulo y uno del texto."""
    terminos = palabras(consulta)
    puntuados = []
    for fragmento in cargar_fragmentos():
        puntos = (
            2 * len(terminos & palabras(fragmento.seccion))
            + len(terminos & palabras(fragmento.texto))
        )
        if puntos:
            puntuados.append((puntos, fragmento))
    # sorted conserva el orden de lectura cuando hay empate.
    puntuados.sort(key=lambda resultado: resultado[0], reverse=True)
    return [fragmento for _, fragmento in puntuados[:3]]
