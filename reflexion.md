# Reflexión

> Los puntos 1 (el resultado de la prueba final) y 4 dependen de ustedes: llénenlos. Los puntos 2 y 3 son
> un borrador basado en lo que de verdad pasó al construir el proyecto; ajústenlo con sus palabras y
> quiten lo que no les haya pasado.

## 1. Un caso en que el modelo eligió mal una herramienta o inventó un dato, y qué cambiamos

Al probar el supervisor con el modelo real (`gemini-3.5-flash-lite`) vimos dos fallos en la misma conversación.
El recomendador sugirió tres clases (C113, C107 y C110) y el usuario escribió «Resérvame la que me recomendaste»:

1. **Eligió sin preguntar.** La referencia era ambigua (había tres opciones) y el agente reservó la primera
   (`reservar_clase(socio_id='S002', clase_id='C113')`) en lugar de preguntar cuál quería.
2. **Inventó un paso que no existe.** Después de la reserva dijo que «queda sujeta a la aprobación final del
   gimnasio». No hay ninguna aprobación posterior: la única es la de la persona en la consola, que ya había
   ocurrido, y la reserva ya estaba hecha.

**Qué cambiamos.** Agregamos dos reglas a `PROMPT_SISTEMA` (`agente.py`) y a `PROMPT_SUPERVISOR` (`supervisor.py`):
(a) si el usuario se refiere a una opción de forma ambigua y hay varias posibles, preguntar cuál quiere
*antes* de reservar, cancelar o cambiar algo; (b) cuando una herramienta confirme que algo quedó hecho,
decirlo tal cual sin inventar pasos o condiciones extra. Lo resolvimos en el prompt porque es un problema de
comportamiento conversacional y no una regla del negocio: las reglas siguen estando solo en `dominio.py`.

Aun así, el primer fallo muestra para qué sirve la aprobación humana: la consola mostró exactamente qué acción
iba a ejecutarse (`clase_id='C113'`), así que la persona pudo verla antes de decir que sí.

**Resultado tras el cambio.** Repetimos la misma conversación (S002, «recomiéndame una clase relajada», «Resérvame la que me recomendaste»). Esta vez el supervisor **no eligió por su cuenta**: volvió a listar las tres opciones (C113, C107 y C110) y preguntó cuál quería. Cuando la persona contestó «La de Pilates del miércoles», la consola mostró `reservar_clase(clase_id='C107', socio_id='S002')`, que coincide con lo que se pidió, y tras aprobar, el agente confirmó solo lo que ocurrió («Reserva hecha: S002 en Pilates (C107)...») sin agregar la «aprobación final». Los dos fallos desaparecieron en esta corrida.

Hay que ser prudentes con la conclusión: fue **una sola** conversación y el modelo no es determinista, así que no demuestra que el problema esté resuelto, solo que el cambio de prompt lo corrigió en este caso. Por eso las reglas del negocio siguen en `dominio.py` y no en el prompt: el prompt mejora la conversación, pero lo que garantiza que no se rompa una regla es el código y la aprobación humana. Si volviera a fallar, probaríamos un modelo más grande o agregar un ejemplo concreto al prompt.

## 2. Una regla que nos costó implementar y cómo la probamos

**R6 (traslape) y su borde.** Lo difícil no fue detectar dos clases a la misma hora, sino decidir
qué pasa cuando una termina justo cuando empieza la otra (Yoga 18:00-19:00 y Pilates 19:00-20:00).
Decidimos que **no** es traslape y lo expresamos con desigualdades estrictas
(`inicio < fin_otra and inicio_otra < fin`). Lo probamos con los dos lados del borde:
`test_r6_traslape_con_otra_reserva` (Boxeo 20:00 contra Zumba 19:30) y
`test_r6_terminar_justo_cuando_empieza_otra_no_es_traslape` (C103 y C113).

**Probar los rechazos.** Para cada regla que rechaza, la prueba no solo espera `ErrorDeNegocio`:
compara una foto del estado (clases, socios y reservas) antes y después, porque el requisito es
que un rechazo no cambie nada. Por eso `dominio.py` valida todo primero y recién después modifica.

**Una prueba que no probaba lo que creíamos.** Para comprobar nuestras pruebas rompimos las reglas
a propósito (por ejemplo, desactivar R4) y vimos si alguna prueba fallaba. Con R4 desactivada la
prueba seguía pasando: la reserva repetida caía en la regla del traslape, cuyo mensaje también
dice "ya tiene reservada". Corregimos la prueba para exigir el mensaje exacto de R4.

## 3. Qué pasaría si las reglas estuvieran solo en el prompt

- **El modelo no es de confianza.** Un prompt es una petición, no una garantía: el modelo puede
  ignorarlo, interpretarlo mal o ser convencido por el usuario. Con las reglas en `dominio.py`
  dejan de depender de lo que el modelo "decida" obedecer.
- **La aprobación humana no basta.** Una persona puede aprobar por error. Lo comprobamos en
  `test_aunque_la_persona_apruebe_el_dominio_rechaza`: se aprueba una reserva premium para un socio
  básico y el estado no cambia.
- **No se pueden probar.** Las pruebas llaman al dominio y al agente con un modelo falso, que
  nunca lee el prompt. Reglas solo en el prompt no tendrían una sola prueba determinista, y un cambio
  de modelo o de redacción las rompería sin avisar.
- **Costo y deriva.** Reglas como "máximo 2 reservas por semana" exigen contar reservas reales; el
  modelo solo vería lo que cupo en la conversación y podría contar mal. Además, cada regla escrita
  en el prompt alarga el prompt en todas las llamadas.

Por eso el prompt solo orienta (tono, uso de herramientas, alcance) y hay una prueba
(`test_el_prompt_limita_el_alcance_y_no_contiene_reglas_de_negocio`) que vigila que no se cuelen
cifras de las reglas.

## 4. Qué hizo cada integrante

| Integrante | Qué hizo |
|------------|----------|
| Isaac Jasiel Herrera Avila | Capa del agente: `agente.py` (prompt, aprobación humana con `HumanInTheLoopMiddleware`, memoria con `thread_id`, consola con `--guardar`) y el bonus `supervisor.py`. Configuró Gemini, grabó las cuatro conversaciones reales, detectó y corrigió los dos fallos del supervisor y redactó `conversaciones.md` y `reflexion.md`. |
| Andrew Neftali Chaidez Lopez | Capa del dominio: `dominio.py` (reglas R1–R13 y `ErrorDeNegocio`, validando antes de modificar el estado), `datos.json`, `REGLAS.md` y las pruebas por regla de `pruebas/test_equipo.py`, incluida la comprobación con mutaciones. |
| Alan Jesus Aguilar Verdugo | Capa de herramientas: `herramientas.py` (las 7 herramientas, `Contexto`, traducción de `ErrorDeNegocio` a texto) y `pruebas/conftest.py` (modelo falso) junto con `pruebas/test_publicos.py`, que prueban las herramientas y el agente sin red ni modelo real. |
