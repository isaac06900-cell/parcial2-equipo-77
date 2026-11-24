"""Ayudas compartidas por las pruebas: servicio nuevo, modelo falso y helpers del agente.

El modelo falso nos deja probar el cableado del agente (aprobar, rechazar, memoria) sin
gastar dinero y de forma determinista: devuelve respuestas guionadas, en orden.
"""

import sys
import uuid
from pathlib import Path

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from pydantic import Field

# Las pruebas importan los módulos por nombre (dominio, herramientas, agente).
CARPETA = Path(__file__).resolve().parent.parent
if str(CARPETA) not in sys.path:
    sys.path.insert(0, str(CARPETA))

from agente import crear_agente  # noqa: E402
from herramientas import Contexto, cargar_servicio  # noqa: E402


class ModeloFalso(BaseChatModel):
    """Chat model que responde con mensajes guionados y recuerda lo que recibió."""

    respuestas: list = Field(default_factory=list)
    vistos: list = Field(default_factory=list)  # una lista de mensajes por cada llamada al modelo
    indice: int = 0

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.vistos.append(list(messages))
        mensaje = self.respuestas[min(self.indice, len(self.respuestas) - 1)]
        self.indice += 1
        return ChatResult(generations=[ChatGeneration(message=mensaje)])

    def bind_tools(self, tools, **kwargs):
        return self  # no hace falta enlazar nada: las llamadas ya vienen guionadas

    @property
    def _llm_type(self) -> str:
        return "modelo-falso"


def llamada(nombre: str, **args) -> AIMessage:
    """Mensaje del modelo que pide ejecutar una herramienta."""
    return AIMessage(content="", tool_calls=[{"name": nombre, "args": args, "id": f"call_{uuid.uuid4().hex[:8]}"}])


def texto(contenido: str) -> AIMessage:
    """Mensaje final del modelo, sin herramientas."""
    return AIMessage(content=contenido)


@pytest.fixture
def servicio():
    """Servicio nuevo con los datos originales en cada prueba."""
    return cargar_servicio()


@pytest.fixture
def contexto(servicio):
    return Contexto(servicio=servicio)


@pytest.fixture
def config():
    return {"configurable": {"thread_id": f"prueba-{uuid.uuid4().hex[:8]}"}}


@pytest.fixture
def armar(contexto, config):
    """Devuelve (modelo, agente, enviar): ``enviar`` manda un mensaje y regresa el resultado crudo."""

    def _armar(*respuestas):
        modelo = ModeloFalso(respuestas=list(respuestas))
        agente = crear_agente(modelo, InMemorySaver())

        def enviar(mensaje):
            return agente.invoke({"messages": [{"role": "user", "content": mensaje}]}, config, context=contexto)

        def reanudar(*decisiones):
            return agente.invoke(Command(resume={"decisions": list(decisiones)}), config, context=contexto)

        return modelo, agente, enviar, reanudar

    return _armar
