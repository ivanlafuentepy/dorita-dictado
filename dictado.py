"""
Dorita Dictado — Transcribe voz al portapapeles + auto-paste, con icono en bandeja.

Uso: CLICK IZQUIERDO en el icono de la bandeja para grabar; click de nuevo para
parar y transcribir. El resultado se pega solo donde tengas el cursor.
El icono cambia de color: azul = listo, rojo = grabando, amarillo = transcribiendo.

Click derecho en el icono para el menu (grabar/parar, estado, salir).

Corte automatico: si la grabacion sigue prendida a los 3 minutos, se apaga sola,
transcribe y deja el texto SOLO en el portapapeles (no lo pega), con un aviso.
Asi un mic olvidado no pega minutos de charla donde este el cursor, y un dictado
largo de verdad no se pierde (Ctrl+V a mano).

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
from ctypes import wintypes
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
MAX_GRABACION_SEG = 180  # 3 min: pasado esto la grabacion se apaga sola

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
# Sube en cada grabacion: el temporizador de corte solo actua si sigue siendo
# la misma grabacion que lo arranco (parar y volver a grabar reinicia los 3 min).
sesion_grabacion = 0
lock = threading.Lock()
kb_controller = Controller()
tray_icon: pystray.Icon = None
stream: sd.InputStream = None

# --- Foco: donde pegar el texto -----------------------------------------
# Al hacer click en el icono de la bandeja, el foco del teclado se va de la
# caja donde estabas escribiendo (VS Code, WhatsApp, etc.) hacia la barra de
# tareas → el Ctrl+V automatico se pierde. Solucion: un poller recuerda la
# ultima ventana "real" con foco mientras NO grabamos, y antes de pegar le
# devolvemos el foco a esa ventana.
user32 = ctypes.windll.user32
ventana_objetivo = None  # HWND donde pegar la transcripcion
_CLASES_SHELL = {
    "Shell_TrayWnd", "Shell_SecondaryTrayWnd", "TrayNotifyWnd",
    "NotifyIconOverflowWindow", "Windows.UI.Core.CoreWindow",
    "WorkerW", "Progman", "Button",
}


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


def _nombre_clase(hwnd) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _es_ventana_valida(hwnd) -> bool:
    """True si es una ventana donde tiene sentido pegar texto (no la barra de
    tareas, ni el menu inicio, ni nuestra propia ventana oculta del tray)."""
    if not hwnd or not user32.IsWindowVisible(hwnd):
        return False
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == os.getpid():
        return False
    return _nombre_clase(hwnd) not in _CLASES_SHELL


def _recordar_ventana_activa() -> None:
    """Corre en background: mientras estamos en reposo, guarda la ultima ventana
    real con foco. Cuando el usuario hace click en el icono para grabar, esa
    ventana ya quedo guardada (el filtro ignora la barra de tareas)."""
    global ventana_objetivo
    while True:
        try:
            if not grabando and estado_actual == ESTADO_IDLE:
                hwnd = user32.GetForegroundWindow()
                if _es_ventana_valida(hwnd):
                    ventana_objetivo = hwnd
        except Exception as e:
            log(f"poller ventana: {e!r}")
        time.sleep(0.25)


def _traer_al_frente(hwnd) -> bool:
    """Devuelve el foco a hwnd. Usa AttachThreadInput como fallback si Windows
    bloquea el SetForegroundWindow directo (foreground lock)."""
    if not hwnd or not user32.IsWindow(hwnd):
        return False
    try:
        if user32.IsIconic(hwnd):            # minimizada → restaurar
            user32.ShowWindow(hwnd, 9)       # SW_RESTORE
        if user32.SetForegroundWindow(hwnd):
            return True
        # Fallback: adjuntar el input del hilo en foreground al de la ventana
        hilo_fg = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
        hilo_obj = user32.GetWindowThreadProcessId(hwnd, None)
        user32.AttachThreadInput(hilo_fg, hilo_obj, True)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.AttachThreadInput(hilo_fg, hilo_obj, False)
        return True
    except Exception as e:
        log(f"no pude restaurar foco: {e!r}")
        return False


def auto_pegar() -> None:
    # Devolver el foco a la caja donde estabas escribiendo ANTES de pegar,
    # si no el Ctrl+V se manda a la barra de tareas y no pega nada.
    if _traer_al_frente(ventana_objetivo):
        time.sleep(0.15)
    else:
        time.sleep(0.1)
    with kb_controller.pressed(Key.ctrl):
        kb_controller.press("v")
        kb_controller.release("v")


def procesar_audio(pegar: bool = True) -> None:
    """Corre en thread aparte para no bloquear el listener.
    pegar=False (corte automatico): deja el texto en el portapapeles y avisa."""
    if not audio_buffer:
        cambiar_estado(ESTADO_IDLE)
        return

    cambiar_estado(ESTADO_PROC)
    audio = np.concatenate(audio_buffer, axis=0).flatten()

    try:
        texto = transcribir(audio)
        if texto:
            pyperclip.copy(texto)
            if pegar:
                auto_pegar()
        if not pegar and tray_icon:
            aviso = ("el texto quedo copiado, Ctrl+V para pegarlo" if texto
                     else "no se escucho nada")
            tray_icon.notify(f"Se apago solo a los 3 min — {aviso}", "Dorita Dictado")
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
    global grabando, audio_buffer, ultimo_toggle, sesion_grabacion

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
            sesion_grabacion += 1
            corte = threading.Timer(MAX_GRABACION_SEG, auto_apagar,
                                    args=(sesion_grabacion,))
            corte.daemon = True
            corte.start()
            return

        grabando = False
        cerrar_stream()

    threading.Thread(target=procesar_audio, daemon=True).start()


def auto_apagar(sesion: int) -> None:
    """Lo dispara el temporizador a los MAX_GRABACION_SEG. Si esa grabacion
    sigue prendida, la corta y transcribe sin pegar (solo portapapeles)."""
    global grabando

    with lock:
        if not grabando or sesion != sesion_grabacion:
            return  # ya la paraste a mano, o es otra grabacion
        grabando = False
        cerrar_stream()

    log(f"corte automatico a los {MAX_GRABACION_SEG}s")
    threading.Thread(target=procesar_audio, args=(False,), daemon=True).start()


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

    # Recuerda la ventana donde pegar (el click en el icono roba el foco).
    threading.Thread(target=_recordar_ventana_activa, daemon=True).start()

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
