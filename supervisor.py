"""BONUS multiagente: un supervisor que reparte el trabajo entre dos subagentes.

    Usuario ──▶ supervisor ──┬──▶ agente_gimnasio      (el agente del escenario: lee y ESCRIBE, con aprobación)
                             └──▶ agente_recomendador  (solo lee: sugiere clases)

* El supervisor decide a qué subagente derivar (cada subagente es una herramienta suya).
* La aprobación humana se sigue respetando: las escrituras ocurren dentro del agente del
  gimnasio, que conserva su HumanInTheLoopMiddleware; la pausa sube hasta la consola.
* El recomendador NO tiene herramientas de escritura: no puede modificar nada.
* ``crear_agente`` no cambia: este archivo solo lo reutiliza.

Uso:  uv run python parcial2-equipo-77/supervisor.py
"""

from __future__ import annotations

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langgraph.checkpoint.memory import InMemorySaver

from agente import _texto, construir_agente_base, consola
from herramientas import Contexto, listar_clases, ver_clase, ver_reservas_socio, ver_socio

# El recomendador solo recibe lecturas: no tiene forma de modificar datos.
HERRAMIENTAS_RECOMENDADOR = [listar_clases, ver_clase, ver_socio, ver_reservas_socio]

PROMPT_RECOMENDADOR = """Eres un recomendador de clases de un gimnasio. Tu único trabajo es sugerir clases a un socio.

Cómo trabajas:
- Con las herramientas revisa el plan del socio, sus reservas actuales y las clases próximas. Nunca inventes datos.
- Sugiere de 2 a 3 clases que: tengan lugares libres, NO estén ya reservadas por el socio, no se traslapen con \
sus reservas y sean compatibles con su plan (las clases PREMIUM solo con plan premium).
- Si pide algo concreto (por ejemplo "algo relajado" o "cardio"), úsalo para elegir entre las clases disponibles.
- Explica en una línea por qué recomiendas cada una e incluye el código de la clase.
- Tú NO reservas ni modificas nada. Si el socio quiere reservar, dile que lo pida y se hará con aprobación.
- Si te piden algo ajeno al gimnasio, explica amablemente que no puedes ayudar con eso.
"""

PROMPT_SUPERVISOR = """Eres el coordinador del asistente de un gimnasio. No tienes datos propios: delegas en dos especialistas.

- agente_gimnasio: consultar clases, horarios, cupos, planes y reservas, y también reservar, cancelar y cambiar de plan. \
Úsalo para todo lo que sea consultar o modificar.
- agente_recomendador: sugerir qué clases le convienen a un socio. Úsalo cuando pidan recomendaciones o ideas.

Reglas:
- Los especialistas NO ven la conversación: en cada solicitud incluye todos los datos necesarios (código de socio, \
código de clase, fecha, lo que pidió el usuario). Si falta el código del socio, pídelo antes de delegar.
- Después de recomendar, si el usuario elige una clase, delega la reserva en agente_gimnasio. Reservar, cancelar y \
cambiar de plan pasan siempre por una aprobación humana; no pidas confirmación extra por texto.
- Si un especialista dice que una operación fue rechazada ("NO se ..."), explica el motivo con claridad y ofrece una \
alternativa. No repitas la operación.
- Si el usuario se refiere a una opción de forma ambigua y hay varias posibles (por ejemplo "la que me recomendaste" \
después de varias sugerencias), pregunta cuál quiere ANTES de delegar una reserva, cancelación o cambio de plan.
- Cuando un especialista confirme que algo quedó hecho ("Reserva hecha", "Reserva cancelada"), dilo tal cual. No inventes \
pasos ni condiciones extra (por ejemplo "sujeto a aprobación final"): la aprobación de una persona ya ocurrió.
- Responde en español, breve y amable, con base solo en lo que devuelvan los especialistas. No inventes datos.
- Alcance: SOLO asuntos de este gimnasio. Si te piden otra cosa, explica amablemente que no puedes ayudar con eso.
"""


def crear_supervisor(modelo, checkpointer=None, modelo_gimnasio=None, modelo_recomendador=None):
    """Arma el supervisor. Por defecto los tres agentes usan el mismo ``modelo``.

    El agente del gimnasio se crea SIN checkpointer propio para heredar el del supervisor:
    así, cuando pide aprobación, la pausa sube hasta quien llamó al supervisor y se reanuda ahí.
    """
    gimnasio = construir_agente_base(modelo_gimnasio or modelo, checkpointer=None)
    recomendador = create_agent(
        model=modelo_recomendador or modelo,
        tools=HERRAMIENTAS_RECOMENDADOR,
        system_prompt=PROMPT_RECOMENDADOR,
        context_schema=Contexto,
    )

    @tool
    def agente_gimnasio(solicitud: str, runtime: ToolRuntime[Contexto]) -> str:
        """Especialista en operar el gimnasio: consulta clases, horarios, cupos, planes y reservas, y reserva, \
cancela o cambia de plan (las modificaciones esperan aprobación humana).

        Úsalo para consultar o modificar datos. Los especialistas no ven la conversación, así que la solicitud
        debe ser completa y autosuficiente.

        Args:
            solicitud: lo que hay que hacer, con todos los datos (por ejemplo "Reserva la clase C114 para el socio S002").
        """
        resultado = gimnasio.invoke({"messages": [{"role": "user", "content": solicitud}]}, context=runtime.context)
        return _texto(resultado["messages"][-1])

    @tool
    def agente_recomendador(solicitud: str, runtime: ToolRuntime[Contexto]) -> str:
        """Especialista en recomendar clases a un socio según su plan, sus reservas y lo que busca. Solo sugiere:
        no reserva ni modifica nada.

        Args:
            solicitud: qué se necesita, con todos los datos (por ejemplo "Recomienda 2 clases relajadas para el socio S001").
        """
        resultado = recomendador.invoke({"messages": [{"role": "user", "content": solicitud}]}, context=runtime.context)
        return _texto(resultado["messages"][-1])

    return create_agent(
        model=modelo,
        tools=[agente_gimnasio, agente_recomendador],
        system_prompt=PROMPT_SUPERVISOR,
        checkpointer=checkpointer if checkpointer is not None else InMemorySaver(),
        context_schema=Contexto,
    )


if __name__ == "__main__":
    consola(fabrica=crear_supervisor, titulo="gimnasio (supervisor)")
