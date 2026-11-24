"""Dominio del escenario Gimnasio.

Aquí viven TODAS las reglas del negocio (ver REGLAS.md). Este módulo no sabe nada
de LangChain ni del modelo: recibe argumentos, valida y devuelve datos simples
(dicts y listas). Si una regla no se cumple lanza ``ErrorDeNegocio`` ANTES de
modificar cualquier dato, así un rechazo nunca deja el estado a medias.

El "hoy" sale de ``datos.json`` (campo ``ahora``); nunca se usa ``date.today()``.
"""

from __future__ import annotations

import copy
import json
from datetime import date, datetime, timedelta
from pathlib import Path

ESCENARIO = "gimnasio"
RUTA_DATOS = Path(__file__).with_name("datos.json")

# Minutos de anticipación (ver REGLAS.md R3 y R10)
MIN_ANTICIPACION_RESERVAR = 60
MIN_ANTICIPACION_CANCELAR = 120


class ErrorDeNegocio(Exception):
    """Una regla del negocio no se cumple. El mensaje está pensado para el usuario."""


class ServicioGimnasio:
    """Reservas de clases con cupo, planes y horarios.

    Formas que devuelven los métodos públicos (el contrato):

    * clase  -> {"id", "nombre", "fecha", "hora_inicio", "hora_fin", "duracion_min",
                 "premium", "cupo", "inscritos", "lugares_libres"}
    * socio  -> {"id", "nombre", "plan", "vence", "limite_semanal",
                 "clases_premium", "membresia_vigente"}
    * reserva -> {"socio_id", "clase_id", "clase", "fecha", "hora_inicio"}
    """

    def __init__(self, datos: dict):
        # Copia profunda: el servicio nunca toca el dict original ni el archivo.
        self._planes: dict = copy.deepcopy(datos["planes"])
        self._socios: dict[str, dict] = {s["id"]: copy.deepcopy(s) for s in datos["socios"]}
        self._clases: dict[str, dict] = {c["id"]: copy.deepcopy(c) for c in datos["clases"]}
        self._ahora: datetime = datetime.fromisoformat(datos["ahora"])

    # ------------------------------------------------------------------
    # Hoy (fijo, viene de los datos)
    # ------------------------------------------------------------------
    @property
    def ahora(self) -> datetime:
        return self._ahora

    @property
    def hoy(self) -> date:
        return self._ahora.date()

    # ------------------------------------------------------------------
    # Ayudas privadas
    # ------------------------------------------------------------------
    @staticmethod
    def _normalizar_id(valor: object) -> str:
        return str(valor).strip().upper()

    def _socio(self, socio_id: str) -> dict:
        clave = self._normalizar_id(socio_id)
        if clave not in self._socios:
            raise ErrorDeNegocio(f"No existe el socio '{socio_id}'.")
        return self._socios[clave]

    def _clase(self, clase_id: str) -> dict:
        clave = self._normalizar_id(clase_id)
        if clave not in self._clases:
            raise ErrorDeNegocio(f"No existe la clase '{clase_id}'.")
        return self._clases[clave]

    @staticmethod
    def _inicio(clase: dict) -> datetime:
        return datetime.fromisoformat(f"{clase['fecha']}T{clase['hora_inicio']}")

    def _fin(self, clase: dict) -> datetime:
        return self._inicio(clase) + timedelta(minutes=clase["duracion_min"])

    @staticmethod
    def _lunes(d: date) -> date:
        """Lunes de la semana de ``d`` (la semana va de lunes a domingo)."""
        return d - timedelta(days=d.weekday())

    def _vigente(self, socio: dict) -> bool:
        # El día de vencimiento todavía cuenta como vigente.
        return date.fromisoformat(socio["vence"]) >= self.hoy

    def _plan(self, socio: dict) -> dict:
        return self._planes[socio["plan"]]

    def _clases_del_socio(self, socio_id: str) -> list[dict]:
        return [c for c in self._clases.values() if socio_id in c["inscritos"]]

    def _reservas_futuras(self, socio_id: str) -> list[dict]:
        return [c for c in self._clases_del_socio(socio_id) if self._inicio(c) > self._ahora]

    def _resumen_clase(self, clase: dict) -> dict:
        return {
            "id": clase["id"],
            "nombre": clase["nombre"],
            "fecha": clase["fecha"],
            "hora_inicio": clase["hora_inicio"],
            "hora_fin": self._fin(clase).strftime("%H:%M"),
            "duracion_min": clase["duracion_min"],
            "premium": clase["premium"],
            "cupo": clase["cupo"],
            "inscritos": len(clase["inscritos"]),
            "lugares_libres": clase["cupo"] - len(clase["inscritos"]),
        }

    def _resumen_socio(self, socio: dict) -> dict:
        plan = self._plan(socio)
        return {
            "id": socio["id"],
            "nombre": socio["nombre"],
            "plan": socio["plan"],
            "vence": socio["vence"],
            "limite_semanal": plan["limite_semanal"],
            "clases_premium": plan["clases_premium"],
            "membresia_vigente": self._vigente(socio),
        }

    def _resumen_reserva(self, socio_id: str, clase: dict) -> dict:
        return {
            "socio_id": socio_id,
            "clase_id": clase["id"],
            "clase": clase["nombre"],
            "fecha": clase["fecha"],
            "hora_inicio": clase["hora_inicio"],
        }

    def _reservas_en_semana(self, socio_id: str, lunes: date, excepto: str | None = None) -> int:
        domingo = lunes + timedelta(days=6)
        return sum(
            1
            for c in self._reservas_futuras(socio_id)
            if c["id"] != excepto and lunes <= date.fromisoformat(c["fecha"]) <= domingo
        )

    # ------------------------------------------------------------------
    # Lecturas
    # ------------------------------------------------------------------
    def listar_clases(self, fecha: str | None = None, nombre: str | None = None) -> list[dict]:
        """Clases que AÚN NO han empezado, ordenadas por fecha y hora.

        ``fecha`` (AAAA-MM-DD) filtra por día; ``nombre`` filtra por texto contenido
        en el nombre (sin distinguir mayúsculas). Devuelve una lista de "clase".
        """
        if fecha:
            try:
                date.fromisoformat(fecha)
            except ValueError:
                raise ErrorDeNegocio(f"La fecha '{fecha}' no es válida; usa el formato AAAA-MM-DD.")
        resultado = []
        for c in self._clases.values():
            if self._inicio(c) <= self._ahora:
                continue
            if fecha and c["fecha"] != fecha:
                continue
            if nombre and nombre.strip().lower() not in c["nombre"].lower():
                continue
            resultado.append(c)
        resultado.sort(key=self._inicio)
        return [self._resumen_clase(c) for c in resultado]

    def ver_clase(self, clase_id: str) -> dict:
        """Detalle de una clase (aunque ya haya empezado). Devuelve una "clase"."""
        return self._resumen_clase(self._clase(clase_id))

    def ver_socio(self, socio_id: str) -> dict:
        """Datos del socio y de su plan. Devuelve un "socio"."""
        return self._resumen_socio(self._socio(socio_id))

    def reservas_de_socio(self, socio_id: str) -> list[dict]:
        """Reservas FUTURAS del socio, ordenadas por fecha y hora. Lista de "reserva"."""
        socio = self._socio(socio_id)
        clases = sorted(self._reservas_futuras(socio["id"]), key=self._inicio)
        return [self._resumen_reserva(socio["id"], c) for c in clases]

    # ------------------------------------------------------------------
    # Escrituras (primero se validan TODAS las reglas, después se cambia el estado)
    # ------------------------------------------------------------------
    def reservar_clase(self, socio_id: str, clase_id: str) -> dict:
        """Reserva un lugar. Devuelve una "reserva". Reglas R1 a R8 de REGLAS.md."""
        socio = self._socio(socio_id)  # R1
        clase = self._clase(clase_id)  # R1
        plan = self._plan(socio)

        # R2: membresía vigente
        if not self._vigente(socio):
            raise ErrorDeNegocio(
                f"La membresía de {socio['nombre']} venció el {socio['vence']}; debe renovarla para reservar."
            )

        # R3: la reserva cierra 60 min antes del inicio
        minutos_para_inicio = (self._inicio(clase) - self._ahora).total_seconds() / 60
        if minutos_para_inicio < MIN_ANTICIPACION_RESERVAR:
            raise ErrorDeNegocio(
                f"Las reservas de {clase['nombre']} ({clase['id']}) ya cerraron: "
                f"se pueden hacer hasta {MIN_ANTICIPACION_RESERVAR} minutos antes del inicio."
            )

        # R4: no duplicar
        if socio["id"] in clase["inscritos"]:
            raise ErrorDeNegocio(f"{socio['nombre']} ya tiene reservada la clase {clase['id']}.")

        # R5: clases premium solo con plan que las incluya
        if clase["premium"] and not plan["clases_premium"]:
            raise ErrorDeNegocio(
                f"{clase['nombre']} es una clase premium y el plan {socio['plan']} no la incluye."
            )

        # R6: sin traslape con otra reserva (terminar justo cuando empieza otra NO es traslape)
        inicio, fin = self._inicio(clase), self._fin(clase)
        for otra in self._reservas_futuras(socio["id"]):
            if inicio < self._fin(otra) and self._inicio(otra) < fin:
                raise ErrorDeNegocio(
                    f"La clase {clase['id']} se traslapa con {otra['nombre']} ({otra['id']}), "
                    f"que ya tiene reservada el {otra['fecha']} a las {otra['hora_inicio']}."
                )

        # R7: límite semanal del plan (semana de lunes a domingo, la de la clase)
        lunes = self._lunes(date.fromisoformat(clase["fecha"]))
        usadas = self._reservas_en_semana(socio["id"], lunes)
        if usadas >= plan["limite_semanal"]:
            raise ErrorDeNegocio(
                f"El plan {socio['plan']} permite {plan['limite_semanal']} reservas por semana "
                f"y {socio['nombre']} ya tiene {usadas} en la semana del {lunes.isoformat()}."
            )

        # R8: cupo
        if len(clase["inscritos"]) >= clase["cupo"]:
            raise ErrorDeNegocio(f"La clase {clase['id']} ({clase['nombre']}) está llena.")

        # Todas las reglas pasaron: ahora sí se cambia el estado.
        clase["inscritos"].append(socio["id"])
        return self._resumen_reserva(socio["id"], clase)

    def cancelar_reserva(self, socio_id: str, clase_id: str) -> dict:
        """Cancela una reserva. Devuelve la "reserva" cancelada. Reglas R9 y R10."""
        socio = self._socio(socio_id)  # R1
        clase = self._clase(clase_id)  # R1

        # R9: debe existir la reserva
        if socio["id"] not in clase["inscritos"]:
            raise ErrorDeNegocio(f"{socio['nombre']} no tiene reservada la clase {clase['id']}.")

        # R10: se cancela hasta 120 min antes (una clase ya empezada tampoco se cancela)
        minutos_para_inicio = (self._inicio(clase) - self._ahora).total_seconds() / 60
        if minutos_para_inicio < MIN_ANTICIPACION_CANCELAR:
            raise ErrorDeNegocio(
                f"Ya no se puede cancelar {clase['id']}: debe hacerse al menos "
                f"{MIN_ANTICIPACION_CANCELAR} minutos antes del inicio."
            )

        clase["inscritos"].remove(socio["id"])
        return self._resumen_reserva(socio["id"], clase)

    def cambiar_plan(self, socio_id: str, plan_nuevo: str) -> dict:
        """Cambia el plan del socio. Devuelve el "socio" actualizado. Reglas R11 a R13."""
        socio = self._socio(socio_id)  # R1
        plan_nuevo = str(plan_nuevo).strip().lower()

        # R11: el plan existe y es distinto al actual
        if plan_nuevo not in self._planes:
            validos = ", ".join(self._planes)
            raise ErrorDeNegocio(f"El plan '{plan_nuevo}' no existe. Planes disponibles: {validos}.")
        if plan_nuevo == socio["plan"]:
            raise ErrorDeNegocio(f"{socio['nombre']} ya tiene el plan {plan_nuevo}.")

        # R12: membresía vigente
        if not self._vigente(socio):
            raise ErrorDeNegocio(
                f"La membresía de {socio['nombre']} venció el {socio['vence']}; debe renovarla antes de cambiar de plan."
            )

        # R13: el plan nuevo debe ser compatible con las reservas futuras que ya tiene
        destino = self._planes[plan_nuevo]
        futuras = self._reservas_futuras(socio["id"])
        if not destino["clases_premium"]:
            premium = [c["id"] for c in futuras if c["premium"]]
            if premium:
                raise ErrorDeNegocio(
                    f"No se puede pasar a {plan_nuevo}: tiene reservas de clases premium "
                    f"({', '.join(premium)}). Debe cancelarlas primero."
                )
        por_semana: dict[date, int] = {}
        for c in futuras:
            lunes = self._lunes(date.fromisoformat(c["fecha"]))
            por_semana[lunes] = por_semana.get(lunes, 0) + 1
        for lunes, cantidad in sorted(por_semana.items()):
            if cantidad > destino["limite_semanal"]:
                raise ErrorDeNegocio(
                    f"No se puede pasar a {plan_nuevo}: permite {destino['limite_semanal']} reservas "
                    f"por semana y {socio['nombre']} tiene {cantidad} en la semana del {lunes.isoformat()}."
                )

        socio["plan"] = plan_nuevo
        return self._resumen_socio(socio)


def cargar_servicio(ruta: str | Path | None = None) -> ServicioGimnasio:
    """Crea un servicio NUEVO con los datos de ``ruta`` (por defecto, el datos.json de esta carpeta).

    Cada llamada devuelve un servicio independiente: lo que se escriba en uno no
    aparece en otro, y el archivo nunca se modifica.
    """
    with open(ruta or RUTA_DATOS, encoding="utf-8") as archivo:
        return ServicioGimnasio(json.load(archivo))
