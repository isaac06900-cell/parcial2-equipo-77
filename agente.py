"""Composición del agente de Gimnasio y consola.

Esta capa SOLO compone: junta el prompt, las herramientas, la aprobación humana y la
memoria. Las reglas del negocio no están aquí ni en el prompt: viven en dominio.py.

Uso:  uv run python parcial2-equipo-77/agente.py
La clave del modelo va en un archivo .env (que NO se entrega), nunca en el código.
"""

from __future__ import annotations

import os
import uuid

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from herramientas import ESCENARIO, HERRAMIENTAS, Contexto, cargar_servicio

PROMPT_SISTEMA = """Eres el asistente de recepción de un gimnasio. Ayudas a consultar clases, \
horarios, cupos, planes y reservas de los socios, y a proponer reservas, cancelaciones y cambios de plan.

Cómo trabajas:
- Responde siempre en español, breve y amable.
- Los datos salen SOLO de las herramientas. Nunca inventes clases, horarios, cupos, planes ni códigos. \
Si no sabes algo, consúltalo con una herramienta.
- Para saber qué día es hoy, llama a listar_clases: el resultado trae la fecha y hora actuales. \
Con eso calcula expresiones como "mañana" o "el viernes".
- Si falta el código del socio (por ejemplo S001) o de la clase (por ejemplo C105), pídelo o búscalo; no lo adivines. \
Si el usuario nombra una clase sin código, usa listar_clases para encontrar el código.
- Antes de proponer una reserva, consulta la clase y el socio para revisar que todo tenga sentido.
- Reservar, cancelar y cambiar de plan modifican datos: cuando lo pida el usuario, llama a la herramienta \
correspondiente y el sistema le pedirá aprobación a una persona. No le pidas confirmación extra por texto.
- Si el sistema rechaza una operación (la herramienta responde "NO se ..."), explica el motivo con claridad y \
sin tecnicismos, y ofrece una alternativa si la hay (otra clase, otro horario, otro plan). No repitas la operación.
- Si el usuario rechaza una acción, acéptalo y pregunta si necesita otra cosa.
- Cuando una herramienta confirme que algo quedó hecho ("Reserva hecha", "Reserva cancelada", "Plan actualizado"), \
dilo tal cual. No inventes pasos ni condiciones extra (por ejemplo "sujeto a aprobación final"): la aprobación de una \
persona ya ocurrió antes de ejecutar la acción.
- Si el usuario se refiere a una opción de forma ambigua y hay varias posibles (por ejemplo "la que me recomendaste" \
después de varias sugerencias), pregunta cuál quiere ANTES de reservar, cancelar o cambiar algo.

Alcance: SOLO atiendes asuntos de este gimnasio (clases, reservas, planes y socios). Si te piden otra cosa \
(recetas, política, tareas, programación, etc.), explica amablemente que no puedes ayudar con eso y ofrece \
lo que sí puedes hacer.
"""

# Escrituras: TODAS esperan aprobación humana. Las lecturas no están aquí.
ACCIONES_CON_APROBACION = {
    "reservar_clase": {"allowed_decisions": ["approve", "reject"]},
    "cancelar_reserva": {"allowed_decisions": ["approve", "reject"]},
    "cambiar_plan": {"allowed_decisions": ["approve", "reject"]},
}


def construir_agente_base(modelo, checkpointer=None):
    """Compone el agente tal cual: prompt + herramientas + aprobación humana.

    Con ``checkpointer=None`` el agente NO crea memoria propia (si va dentro de otro
    agente, hereda la del padre). Lo usa ``crear_agente`` y también el bonus (supervisor.py).
    """
    return create_agent(
        model=modelo,
        tools=HERRAMIENTAS,
        system_prompt=PROMPT_SISTEMA,
        middleware=[HumanInTheLoopMiddleware(interrupt_on=ACCIONES_CON_APROBACION)],
        checkpointer=checkpointer,
        context_schema=Contexto,
    )


def crear_agente(modelo, checkpointer=None):
    """Arma el agente. ``modelo`` es un chat model (o su nombre); ``checkpointer`` guarda la memoria.

    La aprobación humana necesita un checkpointer para poder pausar y reanudar; si no se
    pasa uno se usa uno en memoria, así el agente nunca queda sin poder pedir aprobación.
    """
    return construir_agente_base(modelo, checkpointer if checkpointer is not None else InMemorySaver())


# ----------------------------------------------------------------------
# Consola
# ----------------------------------------------------------------------
def pedir_decisiones(acciones: list[dict], entrada=input, salida=print) -> list[dict]:
    """Muestra cada acción pendiente y pregunta a la persona si la aprueba."""
    decisiones = []
    for accion in acciones:
        salida("\n⚠️  El agente quiere ejecutar una acción que modifica datos:")
        salida(f"    {accion['name']}({', '.join(f'{k}={v!r}' for k, v in accion['args'].items())})")
        respuesta = entrada("    ¿Aprobar? [s/n]: ").strip().lower()
        if respuesta in ("s", "si", "sí", "y", "yes"):
            decisiones.append({"type": "approve"})
        else:
            decisiones.append({"type": "reject", "message": "La persona rechazó esta acción. No la ejecutes."})
    return decisiones


def _texto(mensaje) -> str:
    contenido = mensaje.content
    if isinstance(contenido, list):
        return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in contenido)
    return str(contenido)


def responder(agente, texto: str, config: dict, contexto: Contexto, decidir=pedir_decisiones) -> str:
    """Envía un mensaje y resuelve todas las aprobaciones pendientes. Devuelve el texto final."""
    resultado = agente.invoke({"messages": [{"role": "user", "content": texto}]}, config, context=contexto)
    while resultado.get("__interrupt__"):
        peticion = resultado["__interrupt__"][0].value
        decisiones = decidir(peticion["action_requests"])
        resultado = agente.invoke(Command(resume={"decisions": decisiones}), config, context=contexto)
    return _texto(resultado["messages"][-1])


def consola(fabrica=crear_agente, titulo: str = ESCENARIO) -> None:
    """Consola interactiva. ``fabrica(modelo, checkpointer)`` arma el agente (el bonus pasa la suya).

    Con ``--guardar archivo.txt`` copia la conversación completa (mensajes, aprobaciones y
    respuestas) a ese archivo, para pegarla después en conversaciones.md.
    """
    import sys

    from dotenv import load_dotenv
    from langchain.chat_models import init_chat_model

    load_dotenv()
    destino = sys.argv[sys.argv.index("--guardar") + 1] if "--guardar" in sys.argv else None
    registro = open(destino, "a", encoding="utf-8") if destino else None

    def mostrar(linea: str = "") -> None:
        print(linea)
        if registro:
            registro.write(linea + "\n")

    def preguntar(pregunta: str) -> str:
        respuesta = input(pregunta)
        if registro:
            registro.write(pregunta + respuesta + "\n")
        return respuesta

    nombre_modelo = os.getenv("MODELO", "openai:gpt-4o-mini")  # cambia el proveedor en .env: MODELO=...
    agente = fabrica(init_chat_model(nombre_modelo), InMemorySaver())
    contexto = Contexto(servicio=cargar_servicio())
    config = {"configurable": {"thread_id": f"consola-{uuid.uuid4().hex[:8]}"}}
    decidir = lambda acciones: pedir_decisiones(acciones, entrada=preguntar, salida=mostrar)  # noqa: E731

    mostrar(f"Asistente del escenario '{titulo}'. Escribe 'salir' para terminar.\n")
    try:
        while True:
            try:
                texto = preguntar("Tú: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if texto.lower() in ("salir", "exit", "quit"):
                break
            if not texto:
                continue
            mostrar(f"\nAsistente: {responder(agente, texto, config, contexto, decidir)}\n")
    finally:
        if registro:
            registro.close()


if __name__ == "__main__":
    consola()
