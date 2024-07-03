import tkinter as tk
from tkinter import messagebox
import subprocess
import psutil
import os

# Obtener la ruta del archivo 'app.py'
app_path = os.path.join(os.path.dirname(__file__), 'app', 'app.py')

# Función para encontrar el proceso del servidor Flask
def encontrar_proceso_flask():
    for proceso in psutil.process_iter():
        try:
            if "python" in proceso.name() and app_path in proceso.cmdline():
                return proceso
        except psutil.AccessDenied:
            pass
    return None

# Función para apagar el servidor Flask
def apagar_servidor():
    proceso_flask = encontrar_proceso_flask()
    if proceso_flask:
        try:
            proceso_flask.terminate()
            estado_label.config(text="Estado: Inactivo")
        except psutil.NoSuchProcess:
            pass
    else:
        messagebox.showerror("Error", "El servidor Flask no está en ejecución")

# Función para reiniciar el servidor Flask
def reiniciar_servidor():
    proceso_flask = encontrar_proceso_flask()
    if proceso_flask:
        try:
            proceso_flask.terminate()
            subprocess.Popen(["python", app_path])
            estado_label.config(text="Estado: Activo")
        except psutil.NoSuchProcess:
            pass
    else:
        messagebox.showerror("Error", "El servidor Flask no está en ejecución")

# Función para iniciar el servidor Flask
def iniciar_servidor():
    proceso_flask = encontrar_proceso_flask()
    if not proceso_flask:
        try:
            subprocess.Popen(["python", app_path])
            estado_label.config(text="Estado: Activo")
        except Exception as e:
            messagebox.showerror("Error", f"Error al iniciar el servidor Flask: {e}")
    else:
        messagebox.showinfo("Info", "El servidor Flask ya está en ejecución")

# Crear la ventana
ventana = tk.Tk()
ventana.title("Control del Servidor")

# Etiqueta para mostrar el estado del servidor
estado_label = tk.Label(ventana, text="Estado: Inactivo", font=("Arial", 12))
estado_label.pack(pady=10)

# Botones para controlar el servidor
encender_btn = tk.Button(ventana, text="Encender", command=iniciar_servidor)
encender_btn.pack(pady=5)
apagar_btn = tk.Button(ventana, text="Apagar", command=apagar_servidor)
apagar_btn.pack(pady=5)
reiniciar_btn = tk.Button(ventana, text="Reiniciar", command=reiniciar_servidor)
reiniciar_btn.pack(pady=5)

# Ajustar tamaño de la ventana automáticamente según su contenido
ventana.update_idletasks()  # Actualiza la ventana para calcular el tamaño correcto
width = ventana.winfo_width() + 20  # Ancho de la ventana con un pequeño margen adicional
height = ventana.winfo_height() + 20  # Alto de la ventana con un pequeño margen adicional
ventana.geometry(f"{width}x{height}")  # Establece el tamaño de la ventana

# Ejecutar la aplicación
ventana.mainloop()
