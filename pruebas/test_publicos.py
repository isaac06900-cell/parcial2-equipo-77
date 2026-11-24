"""Pruebas públicas del CONTRATO (nombres y formas que no se pueden cambiar).

⚠️ Este archivo es un sustituto: no teníamos el test_publicos.py oficial del profe.
Cuando lo consigan, reemplácenlo por el original y NO lo modifiquen (-5 puntos).
"""

import inspect

import agente
import dominio
import herramientas

HERRAMIENTAS_ESPERADAS = {
    "listar_clases",
    "ver_clase",
    "ver_socio",
    "ver_reservas_socio",
    "reservar_clase",
    "cancelar_reserva",
    "cambiar_plan",
}


def test_nombres_del_contrato_en_herramientas():
    assert herramientas.ESCENARIO == "gimnasio"
    assert issubclass(herramientas.ErrorDeNegocio, Exception)
    assert callable(herramientas.cargar_servicio)
    assert herramientas.Contexto(servicio=herramientas.cargar_servicio()).servicio is not None
    assert isinstance(herramientas.HERRAMIENTAS, list)


def test_cargar_servicio_acepta_ruta_opcional():
    parametros = inspect.signature(dominio.cargar_servicio).parameters
    assert list(parametros) == ["ruta"]
    assert parametros["ruta"].default is None


def test_nombres_de_las_herramientas():
    nombres = {t.name for t in herramientas.HERRAMIENTAS}
    assert nombres == HERRAMIENTAS_ESPERADAS


def test_cada_herramienta_tiene_descripcion_util():
    for t in herramientas.HERRAMIENTAS:
        assert len(t.description) > 60, f"{t.name} necesita una descripción más clara"


def test_parametros_de_las_herramientas():
    esperados = {
        "listar_clases": {"fecha", "nombre"},
        "ver_clase": {"clase_id"},
        "ver_socio": {"socio_id"},
        "ver_reservas_socio": {"socio_id"},
        "reservar_clase": {"socio_id", "clase_id"},
        "cancelar_reserva": {"socio_id", "clase_id"},
        "cambiar_plan": {"socio_id", "plan_nuevo"},
    }
    for t in herramientas.HERRAMIENTAS:
        # "runtime" lo inyecta LangChain: el modelo no lo ve.
        assert set(t.args) == esperados[t.name], t.name


def test_metodos_del_servicio():
    servicio = dominio.cargar_servicio()
    for nombre in (
        "listar_clases",
        "ver_clase",
        "ver_socio",
        "reservas_de_socio",
        "reservar_clase",
        "cancelar_reserva",
        "cambiar_plan",
    ):
        assert callable(getattr(servicio, nombre)), nombre


def test_nombres_del_contrato_en_agente():
    assert isinstance(agente.PROMPT_SISTEMA, str) and agente.PROMPT_SISTEMA.strip()
    assert agente.ACCIONES_CON_APROBACION
    parametros = inspect.signature(agente.crear_agente).parameters
    assert list(parametros) == ["modelo", "checkpointer"]
    assert parametros["checkpointer"].default is None


def test_las_acciones_con_aprobacion_son_las_escrituras():
    assert set(agente.ACCIONES_CON_APROBACION) == {"reservar_clase", "cancelar_reserva", "cambiar_plan"}
