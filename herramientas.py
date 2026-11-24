"""Herramientas (@tool) del agente de Gimnasio.

Esta capa SOLO adapta: recibe los argumentos que eligió el modelo, llama al servicio
de ``dominio.py`` y devuelve texto. No contiene reglas del negocio.

Reglas de oro de esta capa:
* Una herramienta nunca lanza errores al modelo: captura ``ErrorDeNegocio`` y
  devuelve el mensaje como texto para que el agente se lo explique al usuario.
* Las de lectura no piden aprobación; las de escritura sí (se configura en agente.py).
"""

from __future__ import annotations

from dataclasses import dataclass

from langchain.tools import ToolRuntime, tool

from dominio import (  # noqa: F401  (se re-exportan: el contrato las pide aquí)
    ESCENARIO,
    ErrorDeNegocio,
    ServicioGimnasio,
    cargar_servicio,
)

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


@dataclass
class Contexto:
    """Lo que el agente necesita en cada ejecución pero que NO debe ver el modelo."""

    servicio: ServicioGimnasio


# ----------------------------------------------------------------------
# Formato de las respuestas (texto claro para el modelo)
# ----------------------------------------------------------------------
def _encabezado_fecha(servicio: ServicioGimnasio) -> str:
    ahora = servicio.ahora
    return f"Fecha y hora actuales del gimnasio: {DIAS[ahora.weekday()]} {ahora:%Y-%m-%d %H:%M}."


def _linea_clase(c: dict) -> str:
    premium = " [PREMIUM]" if c["premium"] else ""
    libres = f"{c['lugares_libres']} lugar(es) libre(s) de {c['cupo']}" if c["lugares_libres"] else "LLENA"
    return (
        f"- {c['id']}: {c['nombre']}{premium}, {c['fecha']} de {c['hora_inicio']} a {c['hora_fin']}, {libres}"
    )


# ----------------------------------------------------------------------
# Lecturas (sin aprobación)
# ----------------------------------------------------------------------
@tool
def listar_clases(runtime: ToolRuntime[Contexto], fecha: str | None = None, nombre: str | None = None) -> str:
    """Lista las clases del gimnasio que todavía NO han empezado, con su cupo disponible.

    Úsala para saber qué clases hay, qué día y a qué hora, si son premium y si tienen lugares.
    También sirve para saber qué día es hoy: el resultado siempre trae la fecha y hora actuales.

    Args:
        fecha: día a consultar en formato AAAA-MM-DD (por ejemplo 2026-03-17). Si el usuario dice
            "mañana" o "el viernes", calcula la fecha a partir de la fecha actual. Opcional.
        nombre: parte del nombre de la clase (por ejemplo "yoga" o "spinning"). Opcional.
    """
    servicio = runtime.context.servicio
    try:
        clases = servicio.listar_clases(fecha=fecha, nombre=nombre)
    except ErrorDeNegocio as error:
        return f"No se pudo listar: {error}"
    encabezado = _encabezado_fecha(servicio)
    if not clases:
        return f"{encabezado}\nNo hay clases próximas con esos criterios."
    return encabezado + "\n" + "\n".join(_linea_clase(c) for c in clases)


@tool
def ver_clase(runtime: ToolRuntime[Contexto], clase_id: str) -> str:
    """Muestra el detalle de UNA clase: horario, cupo, lugares libres y si es premium.

    Úsala cuando el usuario ya mencionó un código de clase (por ejemplo "C105") y quieres
    confirmar sus datos antes de proponer una reserva o cancelación.

    Args:
        clase_id: código de la clase, como "C105". No lo inventes: sale de listar_clases.
    """
    servicio = runtime.context.servicio
    try:
        clase = servicio.ver_clase(clase_id)
    except ErrorDeNegocio as error:
        return f"No se pudo consultar: {error}"
    return _encabezado_fecha(servicio) + "\n" + _linea_clase(clase)


@tool
def ver_socio(runtime: ToolRuntime[Contexto], socio_id: str) -> str:
    """Muestra los datos de un socio: nombre, plan, vencimiento de la membresía y límites del plan.

    Úsala antes de proponer una reserva o un cambio de plan para conocer el plan del socio.

    Args:
        socio_id: código del socio, como "S001". Si el usuario no lo ha dado, pídeselo; no lo inventes.
    """
    servicio = runtime.context.servicio
    try:
        socio = servicio.ver_socio(socio_id)
    except ErrorDeNegocio as error:
        return f"No se pudo consultar: {error}"
    estado = "vigente" if socio["membresia_vigente"] else "VENCIDA"
    premium = "incluye clases premium" if socio["clases_premium"] else "no incluye clases premium"
    return (
        f"{socio['id']}: {socio['nombre']}, plan {socio['plan']} "
        f"({socio['limite_semanal']} reservas por semana, {premium}). "
        f"Membresía {estado}, vence el {socio['vence']}."
    )


@tool
def ver_reservas_socio(runtime: ToolRuntime[Contexto], socio_id: str) -> str:
    """Lista las reservas FUTURAS de un socio (clase, fecha y hora).

    Úsala para saber qué tiene reservado un socio, por ejemplo antes de cancelar o de revisar
    si una nueva reserva se traslapa.

    Args:
        socio_id: código del socio, como "S001".
    """
    servicio = runtime.context.servicio
    try:
        reservas = servicio.reservas_de_socio(socio_id)
    except ErrorDeNegocio as error:
        return f"No se pudo consultar: {error}"
    if not reservas:
        return f"El socio {socio_id} no tiene reservas futuras."
    lineas = [f"- {r['clase_id']}: {r['clase']}, {r['fecha']} a las {r['hora_inicio']}" for r in reservas]
    return f"Reservas futuras de {socio_id}:\n" + "\n".join(lineas)


# ----------------------------------------------------------------------
# Escrituras (el agente exige aprobación humana antes de ejecutarlas)
# ----------------------------------------------------------------------
@tool
def reservar_clase(runtime: ToolRuntime[Contexto], socio_id: str, clase_id: str) -> str:
    """ESCRIBE: reserva un lugar para un socio en una clase. Requiere aprobación humana.

    Úsala solo cuando el usuario pidió reservar y ya tienes un socio_id y un clase_id reales
    (obtén el clase_id con listar_clases). Un rechazo del sistema significa que una regla no se
    cumple (cupo, plan, traslape, límite semanal, membresía...): explícaselo al usuario, no insistas.

    Args:
        socio_id: código del socio, como "S001".
        clase_id: código de la clase, como "C105".
    """
    try:
        r = runtime.context.servicio.reservar_clase(socio_id, clase_id)
    except ErrorDeNegocio as error:
        return f"NO se hizo la reserva: {error}"
    return f"Reserva hecha: {r['socio_id']} en {r['clase']} ({r['clase_id']}), {r['fecha']} a las {r['hora_inicio']}."


@tool
def cancelar_reserva(runtime: ToolRuntime[Contexto], socio_id: str, clase_id: str) -> str:
    """ESCRIBE: cancela la reserva de un socio en una clase. Requiere aprobación humana.

    Úsala solo cuando el usuario pidió cancelar y sabes con certeza qué clase (revisa con
    ver_reservas_socio si hay duda). Si el sistema la rechaza, explica el motivo.

    Args:
        socio_id: código del socio, como "S001".
        clase_id: código de la clase a cancelar, como "C105".
    """
    try:
        r = runtime.context.servicio.cancelar_reserva(socio_id, clase_id)
    except ErrorDeNegocio as error:
        return f"NO se canceló: {error}"
    return f"Reserva cancelada: {r['socio_id']} en {r['clase']} ({r['clase_id']}), {r['fecha']} a las {r['hora_inicio']}."


@tool
def cambiar_plan(runtime: ToolRuntime[Contexto], socio_id: str, plan_nuevo: str) -> str:
    """ESCRIBE: cambia el plan de un socio (basico, plus o premium). Requiere aprobación humana.

    Úsala solo cuando el usuario pidió cambiar de plan. Si el sistema la rechaza, explica el motivo
    (por ejemplo, tiene reservas premium que debe cancelar antes de bajar de plan).

    Args:
        socio_id: código del socio, como "S001".
        plan_nuevo: uno de "basico", "plus" o "premium".
    """
    try:
        s = runtime.context.servicio.cambiar_plan(socio_id, plan_nuevo)
    except ErrorDeNegocio as error:
        return f"NO se cambió el plan: {error}"
    return f"Plan actualizado: {s['nombre']} ({s['id']}) ahora tiene el plan {s['plan']}."


HERRAMIENTAS = [
    listar_clases,
    ver_clase,
    ver_socio,
    ver_reservas_socio,
    reservar_clase,
    cancelar_reserva,
    cambiar_plan,
]
