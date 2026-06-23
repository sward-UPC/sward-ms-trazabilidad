"""Serializers/helpers de mapeo del adaptador de entrada HTTP.

Traducen objetos del dominio/aplicación a las estructuras que devuelven los
handlers, manteniendo las rutas delgadas.
"""


def _serializar_preferencias(pref) -> dict:
    return {
        "por_tipo": pref.por_tipo,
        "tipo_fuerte": pref.tipo_fuerte,
        "tipo_debil": pref.tipo_debil,
        "engagement_por_tipo": pref.engagement_por_tipo,
        "formato_mas_consumido": pref.formato_mas_consumido,
        "recursos_vistos": pref.recursos_vistos,
    }
