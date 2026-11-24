# Conversaciones con el modelo real

Cuatro conversaciones copiadas de la consola (`python agente.py --guardar`), con el modelo real `gemini-3.5-flash-lite`. En el gimnasio, "hoy" es lunes 2026-03-16, 09:00.

## 1. Escritura aprobada, de punta a punta (buscar → proponer → aprobar → confirmar)

Luis (`S002`) busca clases de yoga, pide una reserva, la persona la aprueba con `s` y el agente confirma. Al final consulta sus reservas y aparece la nueva.

```text
Asistente del escenario 'gimnasio'. Escribe 'salir' para terminar.

Tú: Hola, soy S002. ¿Qué clases de yoga hay hoy?
Asistente del escenario 'gimnasio'. Escribe 'salir' para terminar.

Tú: Hola, soy S002. ¿Qué clases de yoga hay hoy?

Asistente: Hola. Hoy lunes tenemos dos clases de yoga disponibles:

- **C114**: de 10:00 a 11:00 (12 lugares libres)
- **C103**: de 18:00 a 19:00 (11 lugares libres)

¿Te gustaría reservar alguna de ellas?

Tú: Resérvame la de las 10

⚠️  El agente quiere ejecutar una acción que modifica datos:
    reservar_clase(clase_id='C114', socio_id='S002')
    ¿Aprobar? [s/n]: S

Asistente: He registrado tu reserva para la clase de yoga de las 10:00 (C114). ¡Te esperamos!

Tú: ¿Qué reservas tengo ahora?

Asistente: Actualmente tienes tres reservas futuras:

1. **Yoga** (C114) - Hoy a las 10:00
2. **Yoga** (C103) - Hoy a las 18:00
3. **Crossfit** (C106) - Miércoles 18 de marzo a las 06:00

¿Te puedo ayudar con algo más?

Tú: salir
```

## 2. Escritura rechazada por una regla del dominio, y cómo se lo explicó el agente

Ana (`S001`, plan básico) pide Pilates. La persona **aprobó** la acción y aun así el dominio la rechazó por el límite semanal del plan (R7). El agente explicó el motivo y ofreció alternativas.

```text
Asistente del escenario 'gimnasio'. Escribe 'salir' para terminar.

Tú: Soy S001, resérvame Pilates del miércoles

⚠️  El agente quiere ejecutar una acción que modifica datos:
    reservar_clase(socio_id='S001', clase_id='C107')
    ¿Aprobar? [s/n]: S

Asistente: No fue posible realizar la reserva para la clase de Pilates del miércoles (C107). Ana Torres cuenta con el plan básico, el cual permite un máximo de 2 reservas por semana, y ya alcanzó ese límite para esta semana. 

Si deseas cambiar de plan o cancelar alguna de tus reservas actuales para liberar espacio, avísame.

Tú: salir
```

## 3. La memoria: una pregunta que solo se entiende por el mensaje anterior

«¿Y cuál es la más tarde?» y «¿Y a qué hora termina?» solo se entienden por los mensajes anteriores del mismo hilo (`thread_id`).

```text
Asistente del escenario 'gimnasio'. Escribe 'salir' para terminar.

Tú: ¿Qué clases hay mañana?

Asistente: Mañana, martes 17 de marzo, tenemos programadas las siguientes clases:

- **C105: Spinning [PREMIUM]** | 07:00 - 07:45 | Estado: LLENA
- **C104: Zumba** | 19:00 - 20:00 | 19 lugares disponibles (de 20)

¿Te gustaría reservar un lugar para alguna de ellas? Recuerda que necesitaré tu código de socio.

Tú: ¿Y cuál es la más tarde?

Asistente: La clase más tarde programada para mañana (martes 17 de marzo) es:

- **C104: Zumba** | 19:00 - 20:00 | 19 lugares disponibles

¿Te gustaría que te reserve un lugar en esta clase?

Tú: ¿Y a qué hora termina?

Asistente: La clase de Zumba (C104) de mañana termina a las **20:00**. 

¿Te gustaría que te reserve un lugar o tienes alguna otra duda?

Tú: salir
```

## 4. Una pregunta fuera de alcance

El agente rechazó con amabilidad una receta y una pregunta de deportes, y ofreció lo que sí puede hacer en el gimnasio.

```text
Asistente del escenario 'gimnasio'. Escribe 'salir' para terminar.

Tú: ¿Me das una receta de lasaña?

Asistente: Hola. Solo puedo ayudarte con asuntos del gimnasio, como consultar clases, horarios, cupos, planes o gestionar reservas. 

Si te interesa, puedo mostrarte las clases disponibles para hoy o para los próximos días. ¿Hay algo de eso en lo que te pueda ayudar?

Tú: ¿Quién ganó el partido de ayer?

Asistente: Lo siento, no tengo información sobre deportes ni noticias. Solo puedo ayudarte con los servicios del gimnasio, como consultar clases, cupos, reservas o los detalles de tu membresía. 

¿Te gustaría que revisemos las clases disponibles para hoy?

Tú: salir
```
