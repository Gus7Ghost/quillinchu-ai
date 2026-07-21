# 001 · Detección y Tracking

**Estado:** completado

## Qué hace

El sistema recibe de forma continua el flujo de video transmitido por el dron (DJI Air 2S) a través de la red local. A partir de esa imagen, identifica automáticamente a las personas detectando sus cabezas y les asigna un identificador único (ID) que sirve para seguirlas ininterrumpidamente a medida que se mueven, extrayendo las coordenadas espaciales sin interrumpir el resto de las funciones operativas de la estación terrena.

## Por qué

Es el pilar fundamental de la autonomía de Quillinchu AI. Sin la capacidad de aislar y "anclar" la mirada sobre un objetivo en tiempo real, el dron no puede navegar autónomamente. Adicionalmente, el enfocarse específicamente en la detección de la cabeza (y no en el cuerpo completo) es un paso estratégico y vital que permitirá que la futura estimación matemática de distancia no sufra distorsiones críticas por ángulos de visión cenitales u oblicuos.

## Criterios de aceptación

_Condiciones verificables que deben cumplirse para dar la feature por terminada. Redacta cada una de forma que se pueda comprobar con un sí/no. Marca `[x]` al cumplirse._

### Comportamiento observable y comprobable
- [x] ¿El flujo de video se lee y decodifica correctamente desde el puerto UDP 5600 de Rosetta Drone sin depender de una cámara web conectada localmente por USB?
- [x] ¿El sistema dibuja con precisión cajas delimitadoras (bounding boxes) alrededor de las cabezas detectadas en el cuadro de video en vivo?
- [x] ¿El sistema asigna y renderiza en pantalla un identificador numérico persistente sobre la cabeza del objetivo mientras este permanezca en el campo de visión?

### Caso límite o de error contemplado
- [x] ¿El algoritmo de tracking (Deep SORT) es capaz de retener y recuperar el mismo ID único del objetivo si este sufre una oclusión temporal corta (pérdida visual menor a 1 segundo o $30\text{ frames}$)?

### Requisito de calidad
- [x] ¿El procesamiento visual expone los datos de salida (ID, bbox, timestamp) en una estructura de colas asíncrona no bloqueante que no interfiere con el lazo de navegación?
- [x] ¿La tasa de procesamiento (FPS) del pipeline de visión se mantiene de manera constante por encima de los 15 Hz en la laptop de desarrollo del laboratorio sin presentar congelamientos ni retraso acumulado por buffer?

## Fuera de alcance

_Lo que esta feature NO incluye, para evitar que crezca. Si algo se difiere, enlaza a dónde (roadmap/backlog)._

- La conversión del tamaño de las cajas delimitadoras a distancias métricas estimadas. (Se abordará posteriormente en **[002 · Estimación de Distancia](../002%20-%20estimacion%20de%20distancia/)**).
- La emisión y cálculo de velocidades o comandos de dirección para que el dron persiga a la persona detectada. (Se abordará posteriormente en **[003 · Control de Vuelo PID](../003%20-%20control%20de%20vuelo%20pid/)**).