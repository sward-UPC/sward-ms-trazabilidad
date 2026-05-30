from enum import StrEnum


class NivelRiesgo(StrEnum):
    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"
    CRITICO = "critico"


class TipoInteraccion(StrEnum):
    RESPUESTA = "respuesta"
    VISTA = "vista"
    DESCARGA = "descarga"
    COMPLETADO = "completado"
