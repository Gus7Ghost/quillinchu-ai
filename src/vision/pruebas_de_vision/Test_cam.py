import cv2

# Sustituye con la IP que te da la app en tu celular
# No olvides mantener el '/video' al final
CAM_URL = "http://192.168.0.77:8080/video"

print("📡 Conectando a la cámara del celular...")
cap = cv2.VideoCapture(CAM_URL)

if not cap.isOpened():
    print("❌ No se pudo conectar. Verifica que la laptop y el celular estén en el mismo WiFi.")
    exit()

print("✅ ¡Conectado con éxito! Presiona 'q' para salir.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Muestra el video de tu teléfono en tu Lenovo
    cv2.imshow("Prueba Redmi 13 - Quillinchu AI", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()