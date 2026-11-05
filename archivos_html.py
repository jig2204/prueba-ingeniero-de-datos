from argparse import ArgumentParser
from base64 import b64encode
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
import json
import mimetypes


EXTENSIONES_HTML = {".html", ".htm"}


class ProcesadorImagenesHTML(HTMLParser):
    """
    Procesa las etiquetas <img> de un documento HTML y reemplaza
    las imágenes locales por su representación en Base64.
    """

    def __init__(self, ruta_html):
        super().__init__(convert_charrefs=False)

        self.ruta_html = Path(ruta_html).resolve()
        self.contenido_salida = []
        self.imagenes_exitosas = []
        self.imagenes_fallidas = []

    def handle_decl(self, decl):
        self.contenido_salida.append(f"<!{decl}>")

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "img":
            attrs = self._procesar_imagen(attrs)

        self.contenido_salida.append(
            self._construir_etiqueta_inicio(tag, attrs)
        )

    def handle_startendtag(self, tag, attrs):
        if tag.lower() == "img":
            attrs = self._procesar_imagen(attrs)

        etiqueta = self._construir_etiqueta_inicio(tag, attrs)

        if etiqueta.endswith(">"):
            etiqueta = etiqueta[:-1] + " />"

        self.contenido_salida.append(etiqueta)

    def handle_endtag(self, tag):
        self.contenido_salida.append(f"</{tag}>")

    def handle_data(self, data):
        self.contenido_salida.append(data)

    def handle_entityref(self, name):
        self.contenido_salida.append(f"&{name};")

    def handle_charref(self, name):
        self.contenido_salida.append(f"&#{name};")

    def handle_comment(self, data):
        self.contenido_salida.append(f"<!--{data}-->")

    def handle_pi(self, data):
        self.contenido_salida.append(f"<?{data}>")

    def handle_unknown_decl(self, data):
        self.contenido_salida.append(f"<![{data}]>")

    def obtener_html(self):
        """
        Devuelve el documento HTML procesado.
        """

        return "".join(self.contenido_salida)

    def _procesar_imagen(self, attrs):
        """
        Busca el atributo src de una etiqueta <img> y reemplaza
        la ruta local por una URI Base64.
        """

        nuevos_atributos = []
        src_encontrado = False

        for nombre, valor in attrs:
            if nombre.lower() != "src":
                nuevos_atributos.append((nombre, valor))
                continue

            src_encontrado = True

            if not valor:
                self.imagenes_fallidas.append({
                    "imagen": None,
                    "error": "El atributo src está vacío."
                })

                nuevos_atributos.append((nombre, valor))
                continue

            src_original = valor.strip()

            try:
                src_base64 = self._convertir_src_a_base64(src_original)

                nuevos_atributos.append((nombre, src_base64))

            except Exception as error:
                self.imagenes_fallidas.append({
                    "imagen": src_original,
                    "archivo_html": str(self.ruta_html),
                    "error": str(error)
                })

                # Se conserva la ruta original en caso de error
                nuevos_atributos.append((nombre, valor))

        if not src_encontrado:
            self.imagenes_fallidas.append({
                "imagen": None,
                "archivo_html": str(self.ruta_html),
                "error": "La etiqueta <img> no contiene el atributo src."
            })

        return nuevos_atributos

    def _convertir_src_a_base64(self, src):
        """
        Convierte una imagen local en una URI Base64.
        """

        src_minuscula = src.lower()

        if src_minuscula.startswith("data:"):
            self.imagenes_exitosas.append({
                "imagen": src[:50] + "...",
                "estado": "La imagen ya estaba codificada en Base64."
            })

            return src

        if src_minuscula.startswith(
            ("http://", "https://", "//", "ftp://")
        ):
            raise ValueError(
                "La imagen es remota. Solo se procesan imágenes locales."
            )

        ruta_imagen = self._resolver_ruta_imagen(src)

        if not ruta_imagen.exists():
            raise FileNotFoundError(
                f"No se encontró la imagen: {ruta_imagen}"
            )

        if not ruta_imagen.is_file():
            raise ValueError(
                f"La ruta no corresponde a un archivo: {ruta_imagen}"
            )

        tipo_mime, _ = mimetypes.guess_type(ruta_imagen.name)

        if tipo_mime is None:
            tipo_mime = "application/octet-stream"

        contenido_binario = ruta_imagen.read_bytes()

        contenido_base64 = b64encode(
            contenido_binario
        ).decode("ascii")

        self.imagenes_exitosas.append({
            "imagen": src,
            "ruta_resuelta": str(ruta_imagen),
            "tipo_mime": tipo_mime
        })

        return f"data:{tipo_mime};base64,{contenido_base64}"

    def _resolver_ruta_imagen(self, src):
        """
        Obtiene la ruta local de la imagen respecto al archivo HTML.
        Elimina fragmentos y parámetros de consulta.
        """

        ruta_url = urlparse(src).path
        ruta_limpia = unquote(ruta_url)

        # Corrige rutas HTML que usan barras de Windows
        ruta_limpia = ruta_limpia.replace("\\", "/")

        ruta_imagen = Path(ruta_limpia)

        if ruta_imagen.is_absolute():
            return ruta_imagen.resolve()

        return (self.ruta_html.parent / ruta_imagen).resolve()

    @staticmethod
    def _construir_etiqueta_inicio(tag, attrs):
        """
        Reconstruye una etiqueta HTML conservando sus atributos.
        """

        atributos_formateados = []

        for nombre, valor in attrs:
            if valor is None:
                atributos_formateados.append(nombre)
            else:
                valor_seguro = escape(
                    str(valor),
                    quote=True
                )

                atributos_formateados.append(
                    f'{nombre}="{valor_seguro}"'
                )

        if atributos_formateados:
            atributos = " ".join(atributos_formateados)
            return f"<{tag} {atributos}>"

        return f"<{tag}>"


def obtener_archivos_html(archivos=None, directorios=None):
    """
    Recibe archivos HTML o directorios y crea una lista única.

    Los directorios se recorren de manera recursiva, incluyendo
    todos sus subdirectorios.
    """

    archivos_encontrados = set()

    for archivo in archivos or []:
        ruta = Path(archivo).expanduser().resolve()

        if ruta.is_file() and ruta.suffix.lower() in EXTENSIONES_HTML:
            archivos_encontrados.add(ruta)

    for directorio in directorios or []:
        ruta_directorio = Path(directorio).expanduser().resolve()

        if not ruta_directorio.is_dir():
            continue

        for ruta in ruta_directorio.rglob("*"):
            if (
                ruta.is_file()
                and ruta.suffix.lower() in EXTENSIONES_HTML
                and not ruta.stem.endswith("_base64")
            ):
                archivos_encontrados.add(ruta.resolve())

    return sorted(archivos_encontrados)


def construir_ruta_salida(ruta_html):
    """
    Genera una ruta diferente para no reemplazar el HTML original.

    Ejemplo:
        pagina.html -> pagina_base64.html
    """

    return ruta_html.with_name(
        f"{ruta_html.stem}_base64{ruta_html.suffix}"
    )


def procesar_archivo_html(ruta_html):
    """
    Procesa un archivo HTML y genera una copia con sus imágenes
    codificadas en Base64.
    """

    ruta_html = Path(ruta_html).resolve()

    resultado = {
        "archivo_html": str(ruta_html),
        "archivo_salida": None,
        "estado": "fallido",
        "imagenes_exitosas": [],
        "imagenes_fallidas": []
    }

    try:
        contenido = ruta_html.read_text(
            encoding="utf-8",
            errors="replace"
        )

        parser = ProcesadorImagenesHTML(ruta_html)
        parser.feed(contenido)
        parser.close()

        ruta_salida = construir_ruta_salida(ruta_html)

        ruta_salida.write_text(
            parser.obtener_html(),
            encoding="utf-8"
        )

        resultado["archivo_salida"] = str(ruta_salida)
        resultado["estado"] = "procesado"
        resultado["imagenes_exitosas"] = parser.imagenes_exitosas
        resultado["imagenes_fallidas"] = parser.imagenes_fallidas

    except Exception as error:
        resultado["error_archivo_html"] = str(error)

    return resultado


def procesar_html(archivos=None, directorios=None):
    """
    Ejecuta el procesamiento de todos los archivos encontrados.
    """

    archivos_html = obtener_archivos_html(
        archivos=archivos,
        directorios=directorios
    )

    resultados = []

    for ruta_html in archivos_html:
        resultado = procesar_archivo_html(ruta_html)
        resultados.append(resultado)

    return {
        "total_archivos_html": len(archivos_html),
        "total_archivos_procesados": sum(
            resultado["estado"] == "procesado"
            for resultado in resultados
        ),
        "total_imagenes_exitosas": sum(
            len(resultado["imagenes_exitosas"])
            for resultado in resultados
        ),
        "total_imagenes_fallidas": sum(
            len(resultado["imagenes_fallidas"])
            for resultado in resultados
        ),
        "resultados": resultados
    }


def guardar_reporte(resultado, ruta_reporte):
    """
    Guarda el resultado general en un archivo JSON.
    """

    ruta_reporte = Path(ruta_reporte).expanduser().resolve()

    ruta_reporte.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    ruta_reporte.write_text(
        json.dumps(
            resultado,
            indent=4,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )


def main():
    parser = ArgumentParser(
        description=(
            "Convierte a Base64 las imágenes locales asociadas "
            "a uno o varios archivos HTML."
        )
    )

    parser.add_argument(
        "--archivos",
        nargs="*",
        default=[],
        help="Listado de archivos HTML individuales."
    )

    parser.add_argument(
        "--directorios",
        nargs="*",
        default=[],
        help="Directorios que serán recorridos recursivamente."
    )

    parser.add_argument(
        "--reporte",
        default="resultado_procesamiento.json",
        help="Ruta donde se guardará el reporte JSON."
    )

    argumentos = parser.parse_args()

    if not argumentos.archivos and not argumentos.directorios:
        parser.error(
            "Debe indicar por lo menos un archivo o un directorio."
        )

    resultado = procesar_html(
        archivos=argumentos.archivos,
        directorios=argumentos.directorios
    )

    guardar_reporte(
        resultado,
        argumentos.reporte
    )

    print(
        json.dumps(
            resultado,
            indent=4,
            ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()