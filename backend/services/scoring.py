def calcular_prioridad(tipo, zona_tipo):

    score = {
        "fuga":10,
        "corte":7,
        "medidor":3
    }.get(tipo,3)

    score += {
        "hospital":6,
        "escuela":4,
        "urbana":2
    }.get(zona_tipo,0)

    if score >= 15:
        return "alta"

    if score >= 8:
        return "media"

    return "baja"