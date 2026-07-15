# 001 · Detección y Tracking

**Estado:** en curso

## Qué hace

El sistema recibe de forma continua el flujo de video transmitido por el dron (DJI Air 2S) a través de la red local. A partir de esa imagen, identifica automáticamente a las personas detectando sus cabezas y les asigna un identificador único (ID) que sirve para seguirlas ininterrumpidamente a medida que se mueven, extrayendo las coordenadas sin interrumpir el resto de las funciones operativas de la estación.

## Por qué

Es el pilar fundamental de la autonomía de Quillinchu AI. Sin la capacidad de aislar y "anclar" la mirada sobre un objetivo en tiempo real, el dron no puede navegar autónomamente. Adicionalmente, el enfocarse específicamente en la detección de la cabeza (y no en el cuerpo completo) es un paso estratégico y vital que permitirá que la futura estimación matemática de distancia no sufra distorsiones críticas por ángulos de visión cenitales.

## Criterios de aceptación

_Condiciones verificables que deben cumplirse para dar la feature por terminada. Redacta cada una de forma que se pueda comprobar con un sí/no. Marca `[x]` al cumplirse._

- [ ] El video se lee correctamente a través del stream de red UDP (`udp://127.0.0.1:5600`) de Rosetta Drone, descartándose dependencias a dispositivos USB locales.
- [ ] El sistema dibuja cajas delimitadoras precisas sobre las cabezas detectadas en el cuadro de video.
- [ ] El sistema mantiene un identificador numérico persistente e inmutable sobre el objetivo mientras permanezca visible.
- [ ] El procesamiento visual expone los resultados (ID, caja, timestamp) en una estructura de datos asíncrona que puede leerse sin causar pausas.
- [ ] La tasa general de procesamiento del video se mantiene estrictamente por encima de los 15 fotogramas por segundo (> 15 Hz) sin presentar retraso de buffer acumulado (tiempo real efectivo).

## Fuera de alcance

_Lo que esta feature NO incluye, para evitar que crezca. Si algo se difiere, enlaza a dónde (roadmap/backlog)._

- La conversión del tamaño de las cajas delimitadoras a distancias métricas estimadas. (Se abordará posteriormente en **[002 · Estimación de Distancia](../002%20-%20estimacion%20de%20distancia/)**).
- La emisión y cálculo de velocidades o comandos de dirección para que el dron persiga a la persona detectada. (Se abordará posteriormente en **[003 · Control de Vuelo PID](../003%20-%20control%20de%20vuelo%20pid/)**).
