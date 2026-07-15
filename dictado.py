"""
Dorita Dictado — Transcribe voz al portapapeles + auto-paste, con icono en bandeja.

Uso: CLICK IZQUIERDO en el icono de la bandeja para grabar; click de nuevo para
parar y transcribir. El resultado se pega solo donde tengas el cursor.
El icono cambia de color: azul = listo, rojo = grabando, amarillo = transcribiendo.

Click derecho en el icono para el menu (grabar/parar, estado, salir).

Nota: el atajo de teclado Ctrl+Espacio quedo DESACTIVADO (disparaba el mic solo
cuando pynput perdia el release de Ctrl). La funcion `hotkey_listener` sigue en el
codigo pero no se arranca — el control es 100% por click del icono.
"""
import io
import os
import sys
import wave
import time
import ctypes
import threading

import numpy as np
import sounddevice as sd
import pyperclip
from pynput import keyboard
from pynput.keyboard import Controller, Key
from PIL import Image, ImageDraw
import pystray
from dotenv import load_dotenv
from groq import Groq


load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    sys.exit("ERROR: falta GROQ_API_KEY en .env")

client = Groq(api_key=GROQ_API_KEY)

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dictado.log")


def log(mensaje: str) -> None:
    """Bitacora minima en disco — pythonw no tiene consola y los crashes
    quedaban invisibles (el proceso murio el 13/07 sin dejar rastro)."""
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {mensaje}\n")
    except OSError:
        pass


SAMPLE_RATE = 16000
CHANNELS = 1
VK_CONTROL = 0x11  # Ctrl (cualquiera de las dos) para GetAsyncKeyState
MODEL = "whisper-large-v3"
LANG = "es"

COLOR_IDLE = "#3b82f6"     # azul
COLOR_REC = "#ef4444"      # rojo
COLOR_PROC = "#eab308"     # amarillo

ESTADO_IDLE = "Listo"
ESTADO_REC = "Grabando..."
ESTADO_PROC = "Transcribiendo..."

estado_actual = ESTADO_IDLE
grabando = False
audio_buffer: list = []
ultimo_toggle = 0.0
lock = threading.Lock()
kb_controller = Controller()
tray_icon: pystray.Icon = None
stream: sd.InputStream = None


def crear_icono(color: str) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Circulo de fondo
    d.ellipse([4, 4, 60, 60], fill=color)
    # Cuerpo del microfono (rectangulo redondeado)
    d.rounded_rectangle([26, 16, 38, 38], radius=6, fill="white")
    # Base/arco del mic
    d.arc([20, 28, 44, 50], start=0, end=180, fill="white", width=3)
    # Soporte vertical
    d.line([32, 44, 32, 52], fill="white", width=3)
    # Base horizontal
    d.line([24, 52, 40, 52], fill="white", width=3)
    return img


ICONO_IDLE = crear_icono(COLOR_IDLE)
ICONO_REC = crear_icono(COLOR_REC)
ICONO_PROC = crear_icono(COLOR_PROC)


def cambiar_estado(nuevo_estado: str) -> None:
    global estado_actual
    estado_actual = nuevo_estado
    if tray_icon is None:
        return
    if nuevo_estado == ESTADO_REC:
        tray_icon.icon = ICONO_REC
    elif nuevo_estado == ESTADO_PROC:
        tray_icon.icon = ICONO_PROC
    else:
        tray_icon.icon = ICONO_IDLE
    tray_icon.title = f"Dorita Dictado — {nuevo_estado}"


def callback(indata, frames, time_info, status):
    if grabando:
        audio_buffer.append(indata.copy())


def transcribir(audio_np: np.ndarray) -> str:
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes((audio_np * 32767).astype(np.int16).tobytes())
    wav_io.seek(0)

    resp = client.audio.transcriptions.create(
        file=("audio.wav", wav_io.read()),
        model=MODEL,
        language=LANG,
    )
    return resp.text.strip()


def auto_pegar() -> None:
    time.sleep(0.1)
    with kb_controller.pressed(Key.ctrl):
        kb_controller.press("v")
        kb_controller.release("v")


def procesar_audio() -> None:
    """Corre en thread aparte para no bloquear el listener."""
    if not audio_buffer:
        cambiar_estado(ESTADO_IDLE)
        return

    cambiar_estado(ESTADO_PROC)
    audio = np.concatenate(audio_buffer, axis=0).flatten()

    try:
        texto = transcribir(audio)
        if texto:
            pyperclip.copy(texto)
            auto_pegar()
    except Exception as e:
        # Silencio en background — opcionalmente notificar via tray
        log(f"error transcripcion: {e!r}")
        if tray_icon:
            tray_icon.notify(f"Error: {str(e)[:80]}", "Dorita Dictado")

    cambiar_estado(ESTADO_IDLE)


def abrir_stream() -> None:
    """Abre el microfono. Solo se llama al empezar a grabar."""
    global stream
    stream = sd.InputStream(
        callback=callback, channels=CHANNELS, samplerate=SAMPLE_RATE
    )
    stream.start()


def cerrar_stream() -> None:
    """Cierra el microfono. Asi audiodg no consume CPU en reposo."""
    global stream
    if stream is not None:
        stream.stop()
        stream.close()
        stream = None


def toggle() -> None:
    global grabando, audio_buffer, ultimo_toggle

    with lock:
        ahora = time.time()
        if ahora - ultimo_toggle < 0.3:
            return
        ultimo_toggle = ahora

        if not grabando:
            audio_buffer = []
            grabando = True
            abrir_stream()
            cambiar_estado(ESTADO_REC)
            return

        grabando = False
        cerrar_stream()

    threading.Thread(target=procesar_audio, daemon=True).start()


def hotkey_listener() -> None:
    """Ctrl+Espacio. NO usa GlobalHotKeys: su tracking interno se desincroniza si
    pierde un release (ventanas elevadas, cambios de foco) y la barra sola
    disparaba el mic. Aca se consulta el estado FISICO de Ctrl con GetAsyncKeyState
    recien en el momento de apretar espacio — no hay estado que se pueda pegar."""
    espacio_abajo = False

    def ctrl_fisico() -> bool:
        return bool(ctypes.windll.user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)

    def on_press(key):
        nonlocal espacio_abajo
        if key == keyboard.Key.space:
            if espacio_abajo:  # autorepeat de Windows al mantener apretada la barra
                return
            espacio_abajo = True
            if ctrl_fisico():
                toggle()

    def on_release(key):
        nonlocal espacio_abajo
        if key == keyboard.Key.space:
            espacio_abajo = False

    try:
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()
    except Exception as e:
        log(f"CRASH listener: {e!r}")
        raise


def toggle_click(icon=None, item=None) -> None:
    """Handler del click del icono y del item del menu (pystray pasa (icon, item))."""
    toggle()


def texto_item_grabar(item) -> str:
    return "⏹  Detener grabacion" if grabando else "🎙  Grabar"


def salir(icon, item) -> None:
    log("salida por menu Salir")
    cerrar_stream()
    icon.stop()
    os._exit(0)


def asegurar_instancia_unica() -> None:
    """Si ya hay un dictado corriendo, salir en silencio. Evita dobles toggles
    cuando conviven el arranque automatico (shell:startup) y uno lanzado a mano."""
    ctypes.windll.kernel32.CreateMutexW(None, False, "DoritaDictadoMutex")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        sys.exit(0)


def main() -> None:
    global tray_icon

    asegurar_instancia_unica()
    log("arranque OK — control por click del icono")

    # El hotkey de teclado quedo desactivado (disparos fantasma). Control por click.
    menu = pystray.Menu(
        # default=True: se dispara con CLICK IZQUIERDO simple sobre el icono.
        pystray.MenuItem(texto_item_grabar, toggle_click, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(lambda item: f"Estado: {estado_actual}", lambda: None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Salir", salir),
    )

    tray_icon = pystray.Icon(
        "dorita-dictado",
        ICONO_IDLE,
        f"Dorita Dictado — {ESTADO_IDLE}",
        menu=menu,
    )
    try:
        tray_icon.run()
    except Exception as e:
        log(f"CRASH tray: {e!r}")
        raise
    log("salida normal (menu Salir o cierre del tray)")


if __name__ == "__main__":
    main()
