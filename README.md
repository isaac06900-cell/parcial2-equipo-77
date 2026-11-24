# Parcial 2 — Agente de LangChain: Gimnasio

## 1. Integrantes

| Integrante | Matrícula | Rol |
|------------|-----------|-----|
| Isaac Jasiel Herrera Avila | 24040275 | Agente |
| Andrew Neftali Chaidez Lopez | 24040127 | Dominio |
| Alan Jesus Aguilar Verdugo | 24040737 | Herramientas |

## 2. Escenario elegido

**Gimnasio** — reservas de clases con cupo, planes y horarios. Un agente de recepción que consulta
clases y socios, y propone reservas, cancelaciones y cambios de plan. Toda escritura espera la
aprobación de una persona. Las reglas están en [`REGLAS.md`](REGLAS.md) y se implementan **solo**
en `dominio.py`.

```
Usuario ──▶ agente.py ──▶ modelo ──▶ herramientas.py ──▶ dominio.py ──▶ datos
            (compone)     (decide)   (adapta, valida)     (REGLAS)
               ▲                           │
               └── aprobación humana ◀─────┘  (solo las escrituras)
```

| Archivo | Qué hace |
|---------|----------|
| `dominio.py` | Reglas R1–R13. Lanza `ErrorDeNegocio` **antes** de cambiar cualquier dato. Sin LangChain. |
| `herramientas.py` | 4 lecturas y 3 escrituras (`@tool`). Capturan `ErrorDeNegocio` y devuelven el mensaje como texto. |
| `agente.py` | Prompt, `ACCIONES_CON_APROBACION`, `crear_agente`, memoria y consola. |
| `supervisor.py` | Bonus multiagente (ver sección 4). |
| `pruebas/` | `test_publicos.py` (contrato), `test_equipo.py` (una prueba por regla + agente) y `conftest.py`. |

## 3. Cómo correr las pruebas y la consola

Desde la carpeta `clase-langchain-agentes` (con el entorno de la clase 0 instalado):

```bash
uv run pytest parcial2-equipo-77/pruebas          # no usa red ni modelo real
uv run python parcial2-equipo-77/agente.py        # consola con el modelo real
uv run python parcial2-equipo-77/agente.py --guardar conv.txt   # además copia la conversación a un archivo
uv run python parcial2-equipo-77/supervisor.py    # consola del bonus
```

La clave del proveedor del modelo va **solo** en un archivo `.env` junto a estos archivos (no se
entrega). El modelo se elige con la variable `MODELO` del mismo `.env`, por ejemplo
`MODELO=openai:gpt-4o-mini`; si no existe se usa ese valor.

En la consola, cada escritura muestra la acción pendiente y pregunta `¿Aprobar? [s/n]`.
Las lecturas no preguntan nada.

## 4. Qué agregamos más allá de lo pedido

- **Bonus multiagente (`supervisor.py`).** Un supervisor con dos subagentes como herramientas:
  `agente_gimnasio` (el agente del escenario, con su aprobación humana) y `agente_recomendador`
  (solo lecturas: no puede escribir). La pausa de aprobación del subagente sube hasta la consola.
  `crear_agente` no cambió.
- **Pruebas del agente con un modelo falso** (`conftest.py`): aprobar, rechazar, memoria por
  `thread_id`, "aunque la persona apruebe, el dominio rechaza", lecturas sin aprobación.
- **Comprobación de las pruebas con mutaciones:** rompimos cada regla a propósito y verificamos que
  alguna prueba fallara (así se detectó una prueba débil de R4).
- **`--guardar`** en la consola para copiar las conversaciones tal cual a `conversaciones.md`.

### Conversación de ejemplo con el supervisor

Conversación real con `python supervisor.py` (modelo `gemini-3.5-flash-lite`), después de ajustar los prompts. El recomendador propone clases, el supervisor pregunta cuál quiere la persona y la reserva pasa por la aprobación humana antes de ejecutarse:

```text
Asistente del escenario 'gimnasio (supervisor)'. Escribe 'salir' para terminar.

Tú: Soy S002, recomiéndame una clase relajada para esta semana

Asistente: ¡Hola, Luis! Con base en tu plan **Plus** y tus reservas actuales, aquí tienes algunas opciones relajadas para esta semana:

*   **C113 (Pilates)**: Lunes 16 de marzo de 19:00 a 20:00 (10 lugares libres).
*   **C107 (Pilates)**: Miércoles 18 de marzo de 18:00 a 19:00 (10 lugares libres).
*   **C110 (Yoga)**: Viernes 20 de marzo de 08:00 a 09:00 (11 lugares libres).

¿Te gustaría que reserve alguna de ellas para ti?

Tú: Resérvame la que me recomendaste

Asistente: Para poder hacer la reserva, ¿podrías indicarme exactamente cuál de las clases prefieres? Te recuerdo las opciones que te recomendé:

* **C113** (Pilates - Lunes 16 de marzo, 19:00 a 20:00)
* **C107** (Pilates - Miércoles 18 de marzo, 18:00 a 19:00)
* **C110** (Yoga - Viernes 20 de marzo, 08:00 a 09:00) 

Dime el código de la que deseas y con gusto la reservo.

Tú: La de Pilates del miércoles

⚠️  El agente quiere ejecutar una acción que modifica datos:
    reservar_clase(clase_id='C107', socio_id='S002')
    ¿Aprobar? [s/n]: s

Asistente: Reserva hecha: S002 en Pilates (C107), 2026-03-18 a las 18:00.

Tú: salir
```
