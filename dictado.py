"""
Dorita Dictado — Transcribe voz al portapapeles + auto-paste, con icono en bandeja.

Hotkey: Ctrl+Shift+Espacio (apretar para grabar, apretar de nuevo para parar).
Resultado se pega automaticamente donde tengas el cursor.

Click derecho en el icono de la bandeja para ver estado y salir.
"""
import io
import os
import sys
import wave
import time
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

SAMPLE_RATE = 16000
CHANNELS = 1
HOTKEY = "<ctrl>+<shift>+<space>"
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
    with keyboard.GlobalHotKeys({HOTKEY: toggle}) as h:
        h.join()


def salir(icon, item) -> None:
    cerrar_stream()
    icon.stop()
    os._exit(0)


def main() -> None:
    global tray_icon

    threading.Thread(target=hotkey_listener, daemon=True).start()

    menu = pystray.Menu(
        pystray.MenuItem("Dorita Dictado", lambda: None, enabled=False),
        pystray.MenuItem(lambda item: f"Estado: {estado_actual}", lambda: None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Hotkey: Ctrl+Shift+Espacio", lambda: None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Salir", salir),
    )

    tray_icon = pystray.Icon(
        "dorita-dictado",
        ICONO_IDLE,
        f"Dorita Dictado — {ESTADO_IDLE}",
        menu=menu,
    )
    tray_icon.run()


if __name__ == "__main__":
    main()
