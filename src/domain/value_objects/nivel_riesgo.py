from enum import StrEnum


class NivelRiesgo(StrEnum):
    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"
    CRITICO = "critico"

    @staticmethod
    def por_puntaje(puntaje: float, total_interacciones: int = 1) -> "NivelRiesgo":
        """Regla de negocio ÚNICA para derivar el nivel de riesgo desde el puntaje.

        Es la fuente de verdad del dominio: la usan tanto el recálculo de progreso
        de un estudiante como la sincronización masiva del LMS, para que no
        existan umbrales divergentes en distintas capas.
        """
        if puntaje < 40 or total_interacciones == 0:
            return NivelRiesgo.CRITICO
        if puntaje < 60:
            return NivelRiesgo.ALTO
        if puntaje < 75:
            return NivelRiesgo.MEDIO
        return NivelRiesgo.BAJO


class TipoInteraccion(StrEnum):
    RESPUESTA = "respuesta"
    VISTA = "vista"
    DESCARGA = "descarga"
    COMPLETADO = "completado"
