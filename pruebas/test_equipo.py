"""Pruebas del equipo: una por cada regla de REGLAS.md + el cableado del agente.

Convención: cuando una regla RECHAZA, además de comprobar el error se comprueba que el
estado NO cambió (ver ``estado``). Los datos de ejemplo están en datos.json (hoy = lunes
2026-03-16 09:00).
"""

import ast
import hashlib
import json

import pytest

import agente as modulo_agente
import dominio
from dominio import ErrorDeNegocio, ServicioGimnasio, cargar_servicio
from herramientas import HERRAMIENTAS

from conftest import llamada, texto

IDS_CLASES = [f"C{n}" for n in range(101, 116)]
IDS_SOCIOS = [f"S00{n}" for n in range(1, 7)]
ESCRITURAS = ["reservar_clase", "cancelar_reserva", "cambiar_plan"]
LECTURAS = ["listar_clases", "ver_clase", "ver_socio", "ver_reservas_socio"]


def estado(servicio):
    """Foto del estado visible: clases, socios y reservas de todos."""
    return (
        [servicio.ver_clase(c) for c in IDS_CLASES],
        [servicio.ver_socio(s) for s in IDS_SOCIOS],
        {s: servicio.reservas_de_socio(s) for s in IDS_SOCIOS},
    )


def datos_base():
    with open(dominio.RUTA_DATOS, encoding="utf-8") as f:
        return json.load(f)


def rechaza(servicio, metodo, *args, match):
    """Comprueba que ``metodo`` falla con ErrorDeNegocio y que el estado queda intacto."""
    antes = estado(servicio)
    with pytest.raises(ErrorDeNegocio, match=match):
        getattr(servicio, metodo)(*args)
    assert estado(servicio) == antes, "un rechazo no debe cambiar nada"


# ======================================================================
# Reservar: R1 a R8
# ======================================================================
def test_reservar_ok_cambia_el_estado(servicio):
    libres = servicio.ver_clase("C114")["lugares_libres"]
    reserva = servicio.reservar_clase("S002", "C114")
    assert reserva == {
        "socio_id": "S002",
        "clase_id": "C114",
        "clase": "Yoga",
        "fecha": "2026-03-16",
        "hora_inicio": "10:00",
    }
    assert servicio.ver_clase("C114")["lugares_libres"] == libres - 1
    assert "C114" in [r["clase_id"] for r in servicio.reservas_de_socio("S002")]


def test_r1_socio_inexistente(servicio):
    rechaza(servicio, "reservar_clase", "S999", "C114", match="No existe el socio")


def test_r1_clase_inexistente(servicio):
    rechaza(servicio, "reservar_clase", "S002", "C999", match="No existe la clase")


def test_r1_los_codigos_no_distinguen_mayusculas_ni_espacios(servicio):
    assert servicio.reservar_clase(" s002 ", " c114 ")["clase_id"] == "C114"


def test_r2_membresia_vencida(servicio):
    rechaza(servicio, "reservar_clase", "S004", "C107", match="venció el 2026-03-01")


def test_r2_el_dia_de_vencimiento_todavia_vale(servicio):
    assert servicio.ver_socio("S005")["vence"] == "2026-03-16"  # vence hoy
    assert servicio.reservar_clase("S005", "C107")["clase_id"] == "C107"


def test_r3_reservas_cerradas_a_menos_de_60_min(servicio):
    rechaza(servicio, "reservar_clase", "S006", "C102", match="ya cerraron")  # empieza en 30 min


def test_r3_con_exactamente_60_min_si_se_puede(servicio):
    assert servicio.reservar_clase("S002", "C114")["clase_id"] == "C114"  # empieza en 60 min


def test_r3_clase_que_ya_paso(servicio):
    rechaza(servicio, "reservar_clase", "S002", "C101", match="ya cerraron")


def test_r4_no_se_reserva_dos_veces(servicio):
    rechaza(servicio, "reservar_clase", "S002", "C103", match="ya tiene reservada la clase")


def test_r5_clase_premium_con_plan_que_no_la_incluye(servicio):
    rechaza(servicio, "reservar_clase", "S001", "C108", match="premium")


def test_r5_plan_premium_si_puede_reservar_premium(servicio):
    assert servicio.reservar_clase("S003", "C108")["clase_id"] == "C108"


def test_r6_traslape_con_otra_reserva(servicio):
    servicio.reservar_clase("S006", "C108")  # Boxeo 20:00-21:00
    rechaza(servicio, "reservar_clase", "S006", "C109", match="se traslapa")  # Zumba 19:30-20:30


def test_r6_terminar_justo_cuando_empieza_otra_no_es_traslape(servicio):
    # S002 tiene Yoga 18:00-19:00 (C103); Pilates C113 empieza a las 19:00.
    assert servicio.reservar_clase("S002", "C113")["clase_id"] == "C113"


def test_r7_limite_semanal_del_plan_basico(servicio):
    # Ana (basico, límite 2) ya tiene C104 y C110 en la semana del 16.
    rechaza(servicio, "reservar_clase", "S001", "C107", match="2 reservas por semana")


def test_r7_la_semana_siguiente_es_otro_conteo(servicio):
    assert servicio.reservar_clase("S001", "C112")["clase_id"] == "C112"  # lunes 23


def test_r7_cancelar_libera_el_limite(servicio):
    servicio.cancelar_reserva("S001", "C104")
    assert servicio.reservar_clase("S001", "C107")["clase_id"] == "C107"


def test_r7_el_limite_sale_del_plan_no_esta_escrito_a_mano():
    datos = datos_base()
    datos["planes"]["premium"]["limite_semanal"] = 2  # María ya tiene 2 esta semana
    servicio = ServicioGimnasio(datos)
    rechaza(servicio, "reservar_clase", "S003", "C108", match="2 reservas por semana")


def test_r8_clase_llena(servicio):
    rechaza(servicio, "reservar_clase", "S006", "C106", match="está llena")


def test_r8_cancelar_libera_un_lugar(servicio):
    servicio.cancelar_reserva("S005", "C106")
    assert servicio.reservar_clase("S006", "C106")["clase_id"] == "C106"


# ======================================================================
# Cancelar: R9 y R10
# ======================================================================
def test_cancelar_ok_cambia_el_estado(servicio):
    libres = servicio.ver_clase("C103")["lugares_libres"]
    servicio.cancelar_reserva("S002", "C103")
    assert servicio.ver_clase("C103")["lugares_libres"] == libres + 1
    assert "C103" not in [r["clase_id"] for r in servicio.reservas_de_socio("S002")]


def test_r9_cancelar_una_reserva_que_no_existe(servicio):
    rechaza(servicio, "cancelar_reserva", "S001", "C111", match="no tiene reservada")


def test_r10_no_se_cancela_a_menos_de_120_min(servicio):
    rechaza(servicio, "cancelar_reserva", "S003", "C102", match="120 minutos")  # empieza en 30 min


def test_r10_con_exactamente_120_min_si_se_puede(servicio):
    assert servicio.cancelar_reserva("S005", "C115")["clase_id"] == "C115"  # empieza en 120 min


# ======================================================================
# Cambiar de plan: R11 a R13
# ======================================================================
def test_cambiar_plan_ok(servicio):
    socio = servicio.cambiar_plan("S001", "plus")
    assert socio["plan"] == "plus" and socio["limite_semanal"] == 4
    assert servicio.ver_socio("S001")["plan"] == "plus"


def test_r11_plan_inexistente(servicio):
    rechaza(servicio, "cambiar_plan", "S001", "oro", match="no existe")


def test_r11_mismo_plan(servicio):
    rechaza(servicio, "cambiar_plan", "S001", "basico", match="ya tiene el plan")


def test_r12_membresia_vencida(servicio):
    rechaza(servicio, "cambiar_plan", "S004", "plus", match="venció")


def test_r13_no_baja_de_plan_con_reservas_premium(servicio):
    rechaza(servicio, "cambiar_plan", "S003", "basico", match="clases premium")


def test_r13_no_baja_de_plan_si_una_semana_excede_el_nuevo_limite(servicio):
    servicio.reservar_clase("S002", "C114")  # ahora Luis tiene 3 en la semana del 16
    rechaza(servicio, "cambiar_plan", "S002", "basico", match="2 reservas por semana")


def test_r13_baja_de_plan_si_cabe(servicio):
    assert servicio.cambiar_plan("S002", "basico")["plan"] == "basico"  # Luis tiene 2 en la semana


# ======================================================================
# Otras garantías del dominio
# ======================================================================
@pytest.mark.parametrize(
    "metodo,args",
    [
        ("reservar_clase", ("S999", "C114")),
        ("reservar_clase", ("S004", "C107")),
        ("reservar_clase", ("S001", "C108")),
        ("reservar_clase", ("S006", "C106")),
        ("cancelar_reserva", ("S003", "C102")),
        ("cancelar_reserva", ("S001", "C111")),
        ("cambiar_plan", ("S003", "basico")),
        ("cambiar_plan", ("S001", "oro")),
    ],
)
def test_ningun_rechazo_cambia_el_estado(servicio, metodo, args):
    rechaza(servicio, metodo, *args, match=".")


def test_listar_clases_solo_futuras_y_ordenadas(servicio):
    ids = [c["id"] for c in servicio.listar_clases()]
    assert "C101" not in ids  # ya pasó
    assert ids[0] == "C102"  # la próxima en empezar
    assert ids == sorted(ids, key=lambda i: (servicio.ver_clase(i)["fecha"], servicio.ver_clase(i)["hora_inicio"]))


def test_listar_clases_filtros(servicio):
    assert {c["id"] for c in servicio.listar_clases(fecha="2026-03-19")} == {"C108", "C109"}
    assert {c["nombre"] for c in servicio.listar_clases(nombre="yoga")} == {"Yoga"}
    with pytest.raises(ErrorDeNegocio, match="AAAA-MM-DD"):
        servicio.listar_clases(fecha="mañana")


def test_cargar_servicio_da_servicios_independientes():
    uno, dos = cargar_servicio(), cargar_servicio()
    uno.reservar_clase("S002", "C114")
    assert dos.ver_clase("C114")["inscritos"] == 0


def test_los_datos_originales_no_se_modifican():
    antes = hashlib.sha256(dominio.RUTA_DATOS.read_bytes()).hexdigest()
    servicio = cargar_servicio()
    servicio.reservar_clase("S002", "C114")
    servicio.cancelar_reserva("S002", "C103")
    assert hashlib.sha256(dominio.RUTA_DATOS.read_bytes()).hexdigest() == antes


def test_hoy_sale_de_datos_json_no_del_reloj(servicio):
    assert str(servicio.hoy) == "2026-03-16"
    # Se revisa el CÓDIGO (no los comentarios): no debe llamarse a today() ni a now().
    arbol = ast.parse((dominio.RUTA_DATOS.parent / "dominio.py").read_text(encoding="utf-8"))
    llamadas = {n.func.attr for n in ast.walk(arbol) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert not llamadas & {"today", "now", "utcnow"}


# ======================================================================
# Cableado del agente (con modelo falso: sin red y sin costo)
# ======================================================================
def mensajes_de_herramienta(resultado):
    return [m.content for m in resultado["messages"] if m.type == "tool"]


def test_las_acciones_con_aprobacion_son_exactamente_las_escrituras():
    assert set(modulo_agente.ACCIONES_CON_APROBACION) == set(ESCRITURAS)
    assert {t.name for t in HERRAMIENTAS} - set(ESCRITURAS) == set(LECTURAS)


@pytest.mark.parametrize(
    "nombre,args",
    [
        ("ver_socio", {"socio_id": "S001"}),
        ("ver_clase", {"clase_id": "C105"}),
        ("ver_reservas_socio", {"socio_id": "S001"}),
        ("listar_clases", {}),
    ],
)
def test_las_lecturas_no_piden_aprobacion(armar, nombre, args):
    _, _, enviar, _ = armar(llamada(nombre, **args), texto("Aquí está."))
    resultado = enviar("consulta")
    assert "__interrupt__" not in resultado
    assert resultado["messages"][-1].content == "Aquí está."
    assert mensajes_de_herramienta(resultado)


@pytest.mark.parametrize(
    "nombre,args",
    [
        ("reservar_clase", {"socio_id": "S002", "clase_id": "C114"}),
        ("cancelar_reserva", {"socio_id": "S002", "clase_id": "C103"}),
        ("cambiar_plan", {"socio_id": "S001", "plan_nuevo": "plus"}),
    ],
)
def test_las_escrituras_esperan_aprobacion_y_no_se_ejecutan_antes(armar, servicio, nombre, args):
    _, _, enviar, _ = armar(llamada(nombre, **args), texto("Hecho."))
    antes = estado(servicio)
    resultado = enviar("haz la operación")
    pendiente = resultado["__interrupt__"][0].value["action_requests"][0]
    assert pendiente["name"] == nombre and pendiente["args"] == args
    assert estado(servicio) == antes, "nada se ejecuta hasta que una persona apruebe"


def test_aprobar_ejecuta_la_escritura(armar, servicio):
    _, _, enviar, reanudar = armar(llamada("reservar_clase", socio_id="S002", clase_id="C114"), texto("Reservada."))
    enviar("reserva yoga a las 10 para S002")
    resultado = reanudar({"type": "approve"})
    assert "__interrupt__" not in resultado
    assert "C114" in [r["clase_id"] for r in servicio.reservas_de_socio("S002")]
    assert resultado["messages"][-1].content == "Reservada."


def test_rechazar_no_ejecuta_y_no_cambia_nada(armar, servicio):
    _, _, enviar, reanudar = armar(llamada("reservar_clase", socio_id="S002", clase_id="C114"), texto("Entendido."))
    antes = estado(servicio)
    enviar("reserva yoga a las 10 para S002")
    resultado = reanudar({"type": "reject", "message": "No, gracias."})
    assert estado(servicio) == antes
    assert resultado["messages"][-1].content == "Entendido."


def test_aunque_la_persona_apruebe_el_dominio_rechaza(armar, servicio):
    """La idea central del parcial: el modelo no es de confianza y las reglas viven en el dominio."""
    _, _, enviar, reanudar = armar(llamada("reservar_clase", socio_id="S001", clase_id="C108"), texto("No se pudo."))
    antes = estado(servicio)
    enviar("reserva boxeo para S001")
    resultado = reanudar({"type": "approve"})  # la persona aprueba por error
    assert estado(servicio) == antes
    assert "NO se hizo la reserva" in mensajes_de_herramienta(resultado)[-1]


def test_las_herramientas_no_lanzan_errores_al_modelo(armar):
    """Un código inventado por el modelo llega como texto, no como excepción."""
    _, _, enviar, _ = armar(llamada("ver_clase", clase_id="C999"), texto("Esa clase no existe."))
    resultado = enviar("dame la clase C999")
    assert "No existe la clase" in mensajes_de_herramienta(resultado)[-1]
    assert resultado["messages"][-1].content == "Esa clase no existe."


def test_memoria_recuerda_dentro_del_mismo_hilo(armar):
    modelo, _, enviar, _ = armar(texto("Hola Ana."), texto("Tu plan es basico."))
    enviar("Soy Ana, mi código es S001")
    enviar("¿y cuál es mi plan?")
    segunda_llamada = modelo.vistos[-1]
    contenidos = [m.content for m in segunda_llamada if m.type == "human"]
    assert contenidos == ["Soy Ana, mi código es S001", "¿y cuál es mi plan?"]


def test_hilos_distintos_no_comparten_memoria(armar, contexto):
    from langgraph.checkpoint.memory import InMemorySaver

    from conftest import ModeloFalso

    modelo = ModeloFalso(respuestas=[texto("uno"), texto("dos")])
    agente = modulo_agente.crear_agente(modelo, InMemorySaver())
    agente.invoke({"messages": [{"role": "user", "content": "primero"}]}, {"configurable": {"thread_id": "A"}}, context=contexto)
    agente.invoke({"messages": [{"role": "user", "content": "segundo"}]}, {"configurable": {"thread_id": "B"}}, context=contexto)
    humanos = [m.content for m in modelo.vistos[-1] if m.type == "human"]
    assert humanos == ["segundo"]


def test_el_modelo_recibe_el_prompt_del_sistema(armar):
    modelo, _, enviar, _ = armar(texto("Hola."))
    enviar("hola")
    primero = modelo.vistos[0][0]
    assert primero.type == "system"
    assert primero.content == modulo_agente.PROMPT_SISTEMA


def test_el_prompt_limita_el_alcance_y_no_contiene_reglas_de_negocio():
    prompt = modulo_agente.PROMPT_SISTEMA
    assert "SOLO" in prompt and "no puedes ayudar" in prompt  # guardrail de fuera de alcance
    for cifra in ("2 reservas", "60 min", "120 min", "4 reservas", "7 reservas"):  # las reglas NO van en el prompt
        assert cifra not in prompt


def test_responder_resuelve_las_aprobaciones_con_la_funcion_decidir(contexto, config):
    from langgraph.checkpoint.memory import InMemorySaver

    from conftest import ModeloFalso

    modelo = ModeloFalso(respuestas=[llamada("cancelar_reserva", socio_id="S002", clase_id="C103"), texto("Cancelada.")])
    agente = modulo_agente.crear_agente(modelo, InMemorySaver())
    respuesta = modulo_agente.responder(
        agente, "cancela mi yoga", config, contexto, decidir=lambda acciones: [{"type": "approve"}]
    )
    assert respuesta == "Cancelada."
    assert contexto.servicio.ver_clase("C103")["inscritos"] == 0


# ======================================================================
# Bonus multiagente (supervisor.py): la aprobación humana se sigue respetando
# ======================================================================
@pytest.fixture
def armar_supervisor(contexto, config):
    """Devuelve (modelos, enviar, reanudar) con un supervisor y sus subagentes guionados."""
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import Command

    from conftest import ModeloFalso
    from supervisor import crear_supervisor

    def _armar(guion_supervisor, guion_gimnasio=(), guion_recomendador=()):
        m_sup = ModeloFalso(respuestas=list(guion_supervisor))
        m_gim = ModeloFalso(respuestas=list(guion_gimnasio) or [texto("-")])
        m_rec = ModeloFalso(respuestas=list(guion_recomendador) or [texto("-")])
        sup = crear_supervisor(m_sup, InMemorySaver(), modelo_gimnasio=m_gim, modelo_recomendador=m_rec)

        def enviar(mensaje):
            return sup.invoke({"messages": [{"role": "user", "content": mensaje}]}, config, context=contexto)

        def reanudar(*decisiones):
            return sup.invoke(Command(resume={"decisions": list(decisiones)}), config, context=contexto)

        return (m_sup, m_gim, m_rec), enviar, reanudar

    return _armar


def test_bonus_el_recomendador_no_tiene_herramientas_de_escritura():
    from supervisor import HERRAMIENTAS_RECOMENDADOR

    nombres = {t.name for t in HERRAMIENTAS_RECOMENDADOR}
    assert nombres and not nombres & set(ESCRITURAS)


def test_bonus_una_escritura_via_supervisor_espera_aprobacion(armar_supervisor, servicio):
    _, enviar, reanudar = armar_supervisor(
        [llamada("agente_gimnasio", solicitud="Reserva C114 para S002"), texto("Quedó reservada.")],
        [llamada("reservar_clase", socio_id="S002", clase_id="C114"), texto("Reserva hecha.")],
    )
    antes = estado(servicio)
    pausa = enviar("reserva yoga de las 10 para S002")
    pendiente = pausa["__interrupt__"][0].value["action_requests"][0]
    assert pendiente["name"] == "reservar_clase" and pendiente["args"] == {"socio_id": "S002", "clase_id": "C114"}
    assert estado(servicio) == antes, "nada se ejecuta antes de aprobar"
    final = reanudar({"type": "approve"})
    assert "C114" in [r["clase_id"] for r in servicio.reservas_de_socio("S002")]
    assert final["messages"][-1].content == "Quedó reservada."


def test_bonus_rechazar_via_supervisor_no_cambia_nada(armar_supervisor, servicio):
    _, enviar, reanudar = armar_supervisor(
        [llamada("agente_gimnasio", solicitud="Reserva C114 para S002"), texto("Entendido, no se reservó.")],
        [llamada("reservar_clase", socio_id="S002", clase_id="C114"), texto("La persona canceló.")],
    )
    antes = estado(servicio)
    enviar("reserva yoga de las 10 para S002")
    reanudar({"type": "reject", "message": "No."})
    assert estado(servicio) == antes


def test_bonus_aunque_apruebe_el_dominio_rechaza(armar_supervisor, servicio):
    _, enviar, reanudar = armar_supervisor(
        [llamada("agente_gimnasio", solicitud="Reserva C108 para S001"), texto("No fue posible.")],
        [llamada("reservar_clase", socio_id="S001", clase_id="C108"), texto("NO se hizo la reserva.")],
    )
    antes = estado(servicio)
    enviar("reserva boxeo para S001")
    reanudar({"type": "approve"})
    assert estado(servicio) == antes


def test_bonus_el_supervisor_deriva_las_recomendaciones_al_recomendador_sin_aprobacion(armar_supervisor, servicio):
    (m_sup, m_gim, m_rec), enviar, _ = armar_supervisor(
        [llamada("agente_recomendador", solicitud="Recomienda clases para S001"), texto("Te sugiero Pilates (C107).")],
        guion_recomendador=[llamada("ver_socio", socio_id="S001"), texto("Pilates C107 va con tu plan.")],
    )
    antes = estado(servicio)
    resultado = enviar("¿qué clase me recomiendas? soy S001")
    assert "__interrupt__" not in resultado
    assert resultado["messages"][-1].content == "Te sugiero Pilates (C107)."
    assert m_rec.indice == 2 and m_gim.indice == 0, "solo trabajó el recomendador"
    assert estado(servicio) == antes
