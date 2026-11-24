# Gimnasio — reglas del negocio

> **Nota.** Estas son las reglas que implementa `dominio.py`. Las definimos como equipo porque no tuvimos
> acceso al `REGLAS.md` del curso. Los códigos R1–R13 son los mismos que usan las pruebas de
> `pruebas/test_equipo.py` (al menos una prueba por regla).

"Hoy" es fijo y sale de `datos.json` (`ahora`): **lunes 2026-03-16, 09:00**.

## Planes

| Plan    | Reservas por semana | Clases premium |
|---------|---------------------|----------------|
| basico  | 2                   | no             |
| plus    | 4                   | no             |
| premium | 7                   | sí             |

La semana va de **lunes a domingo**.

## Reservar una clase

| # | Regla |
|---|-------|
| R1 | El socio y la clase deben existir. |
| R2 | La membresía debe estar vigente: `vence >= hoy` (el día de vencimiento todavía vale). |
| R3 | Las reservas cierran **60 min** antes del inicio (con exactamente 60 sí se puede). Una clase ya empezada o pasada no se reserva. |
| R4 | No se puede reservar dos veces la misma clase. |
| R5 | Las clases premium solo las pueden reservar socios con plan premium. |
| R6 | No puede traslaparse con otra reserva futura del socio. Terminar justo cuando empieza la otra **no** es traslape. |
| R7 | No se puede superar el límite semanal del plan (cuenta las reservas futuras de la semana de la clase). |
| R8 | La clase debe tener cupo. |

Orden de validación: R1, R2, R3, R4, R5, R6, R7, R8. Si falla una, no cambia nada.

## Cancelar una reserva

| # | Regla |
|---|-------|
| R9 | La reserva debe existir. |
| R10 | Se cancela hasta **120 min** antes del inicio (con exactamente 120 sí se puede). |

## Cambiar de plan

| # | Regla |
|---|-------|
| R11 | El plan nuevo debe existir y ser distinto al actual. |
| R12 | La membresía debe estar vigente. |
| R13 | El plan nuevo debe ser compatible con las reservas futuras: sin clases premium si el plan no las incluye, y ninguna semana por encima del nuevo límite. |

## Datos de ejemplo

Socios: S001 Ana (basico), S002 Luis (plus), S003 María (premium), S004 Carlos (basico, **vencido**),
S005 Sofía (plus, vence **hoy**), S006 Diego (premium).

Casos útiles incluidos en `datos.json`:
- `C102` Spinning premium empieza en 30 min → reservas cerradas (R3) y María no puede cancelar (R10).
- `C114` Yoga empieza en exactamente 60 min → todavía se puede reservar.
- `C115` Zumba empieza en exactamente 120 min → Sofía todavía puede cancelar.
- `C105` Spinning premium con cupo 2 y lleno; `C106` Crossfit con cupo 2 y lleno.
- `C108` Boxeo (20:00-21:00) y `C109` Zumba (19:30-20:30) se traslapan.
- `C103` Yoga (18:00-19:00) y `C113` Pilates (19:00-20:00) no se traslapan.
- Ana (basico) ya tiene 2 reservas en la semana del 16 (`C104`, `C110`): una tercera falla por R7, pero `C112` (semana siguiente) sí.
