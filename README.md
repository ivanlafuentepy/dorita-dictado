# Dorita Dictado

Transcripción de voz al portapapeles en español usando **Groq Whisper Large v3**. Dictás en cualquier app de Windows (VS Code, WhatsApp Web, Word, navegador, terminal) y el texto se pega automáticamente donde tengas el cursor.

Mucho mejor que el dictado nativo de Windows (Win+H) — sobre todo en español rioplatense.

> Autor: **Iván Lafuente** — Salsa Soul Studio / Curso IA
> Licencia: MIT (ver [LICENSE](LICENSE))

---

## Cómo funciona

1. Apretás `Ctrl+Shift+Espacio` → empieza a grabar (ícono en bandeja se pone rojo)
2. Hablás
3. Apretás `Ctrl+Shift+Espacio` de nuevo → para, transcribe, pega solo
4. Listo — el texto aparece donde tenías el cursor

El audio **nunca se guarda en disco**. Vive en memoria, va a Groq, se descarta.

---

## ⚠️ Requisitos previos (hacelos primero o nada funciona)

### 1. Python 3.10 o superior instalado

Verificar si ya lo tenés:
```bash
python --version
```

Si no:
- Descargá de [python.org/downloads](https://www.python.org/downloads/)
- En el instalador, **tildá la casilla "Add Python to PATH"** (abajo, en la primera pantalla). Sin esto el programa no arranca.
- Click "Install Now"
- Cerrá y abrí una terminal nueva, verificá con `python --version`

### 2. Cuenta en Groq + API key

**Qué es Groq:** servicio que corre Whisper (el mejor modelo de transcripción del mundo). Tier gratis generoso para uso personal.

**Crear cuenta (5 min):**
1. Andá a [console.groq.com](https://console.groq.com)
2. "Sign In" → "Continue with Google" (no pide tarjeta)

**Generar la key (1 min):**
1. Menú izquierdo → **"API Keys"**
2. Click **"Create API Key"** → ponele un nombre
3. **Copiá la key que aparece** (`gsk_...`) — esta ventana se cierra y NO la vas a ver de nuevo
4. Pegala en un Bloc de notas seguro

> ⚠️ La API key es como una contraseña. No la subas a GitHub ni la compartas. Si la perdés, generá otra desde la misma página y revocá la vieja.

### 3. Windows 10 u 11

(Mac y Linux funcionan con cambios menores — abrí un issue si te interesa)

---

## Instalación (primera vez)

### Paso 1 — Bajar el proyecto

Opción A: con git
```bash
git clone https://github.com/ivanlafuentepy/dorita-dictado.git
```

Opción B: sin git → descargar el ZIP de GitHub y descomprimir donde quieras (por ejemplo `C:\Users\TU_USUARIO\Documents\dorita-dictado`)

### Paso 2 — Configurar tu API key

1. Abrí la carpeta del proyecto en el explorador
2. Copiá el archivo `.env.example` y renombrá la copia a `.env`
3. Abrí el `.env` con el Bloc de notas
4. Pegá tu key después del `=`, queda así:
   ```
   GROQ_API_KEY=gsk_TU_KEY_AQUI
   ```
5. Guardá y cerrá

### Paso 3 — Instalar dependencias

Doble click en `arrancar.bat`. La primera vez:
- Crea un entorno virtual de Python
- Descarga e instala las 7 librerías que necesita (tarda ~2 minutos)
- Abre el programa

Si todo salió bien, va a aparecer un **círculo azul con un micrófono** en la bandeja del sistema (al lado del reloj, abajo a la derecha).

### Paso 4 — Probar

1. Abrí cualquier app donde quieras dictar (VS Code, navegador, WhatsApp Web, lo que sea)
2. Hacé click donde quieras que aparezca el texto (caja de mensaje, editor, etc.)
3. Apretá `Ctrl+Shift+Espacio` — el ícono se pone rojo
4. Decí algo en voz alta: *"hola, esta es una prueba de dictado"*
5. Apretá `Ctrl+Shift+Espacio` de nuevo — el ícono se pone amarillo, después vuelve a azul
6. El texto aparece automáticamente donde tenías el cursor

---

## Arrancar automático con Windows (recomendado)

Para que el dictado esté disponible siempre que prendas la PC, sin tener que ejecutar el `.vbs` manualmente:

1. Apretá `Win + R` (tecla Windows + R)
2. Escribí `shell:startup` y dale Enter — se abre la carpeta de inicio de Windows
3. Andá a la carpeta del proyecto
4. Click derecho en `arrancar.vbs` → "Copiar"
5. Volvé a la carpeta de inicio y hacé click derecho → **"Pegar acceso directo"**

Próxima vez que prendas la PC, el ícono azul aparece solo en la bandeja, listo para usar.

---

## Uso diario

### Para dictar

- Cursor donde quieras escribir
- `Ctrl+Shift+Espacio`
- Hablás
- `Ctrl+Shift+Espacio`
- Texto pegado automáticamente

### Para ver el estado

Hover sobre el ícono en la bandeja → te dice "Listo" / "Grabando..." / "Transcribiendo..."

### Estados visuales del ícono

| Color | Significa |
|---|---|
| 🔵 Azul | Listo, esperando que apretes la hotkey |
| 🔴 Rojo | Grabando — hablá |
| 🟡 Amarillo | Procesando — esperá 1-2 segundos |

### Para cerrar el programa

Click derecho en el ícono de la bandeja → "Salir"

---

## Costo

Groq tiene tier gratuito generoso. Para uso personal (dictado de notas, mensajes, code) normalmente **no cuesta nada**.

Si llegás a pagar, Whisper Large v3 en Groq cuesta ~$0.04 USD por hora de audio. Una hora dictando = 4 centavos de dólar.

---

## Cómo personalizar

Editá `dictado.py` con cualquier editor:

| Qué cambiar | Línea | Valor por default |
|---|---|---|
| Hotkey | `HOTKEY = "<ctrl>+<shift>+<space>"` | Ctrl+Shift+Espacio |
| Idioma | `LANG = "es"` | Español. Para inglés: `"en"` |
| Modelo | `MODEL = "whisper-large-v3"` | El mejor de Groq |

Después de editar, cerrá el programa (click derecho en ícono → Salir) y arrancalo de nuevo con el `.vbs`.

### Hotkeys alternativos

Si `Ctrl+Shift+Espacio` choca con otra app:
- `<f12>` — tecla F12 sola
- `<ctrl>+<alt>+d` — Ctrl + Alt + D
- `<ctrl>+<shift>+v` — Ctrl + Shift + V

---

## Problemas comunes

### "No aparece el ícono en la bandeja"
- Click en la flechita ▲ al lado del reloj para expandir íconos ocultos
- Si no está ahí, abrí el Administrador de Tareas y buscá `pythonw.exe` — si no está corriendo, doble click otra vez en `arrancar.vbs`

### "La hotkey no responde"
- Otra app está usando la misma combinación. Cambiá el hotkey en `dictado.py`
- Reiniciá el programa después de cambiar

### "El mic no graba nada"
- Configuración → Sistema → Sonido → verificá que el micrófono predeterminado sea el correcto
- Permisos: Configuración → Privacidad → Micrófono → activar "Permitir que las aplicaciones de escritorio accedan al micrófono"

### "Pega texto en inglés"
- Revisá que `LANG = "es"` esté en `dictado.py` línea 36

### "Error de API key"
- Verificá que el `.env` tenga la línea `GROQ_API_KEY=gsk_...` sin espacios ni comillas
- Probá generar una key nueva en Groq y reemplazar

---

## Tecnologías usadas

- **Python 3.10+** — runtime
- **[Groq](https://groq.com) Whisper Large v3** — transcripción (rapidísima, excelente en español)
- **[pynput](https://pypi.org/project/pynput/)** — hotkeys globales en Windows sin admin
- **[sounddevice](https://pypi.org/project/sounddevice/)** — captura de audio del mic
- **[pystray](https://pypi.org/project/pystray/) + [Pillow](https://pypi.org/project/Pillow/)** — ícono en bandeja del sistema
- **[pyperclip](https://pypi.org/project/pyperclip/)** — manejo de portapapeles

---

## Estructura del proyecto

```
dorita-dictado/
├── dictado.py          ← código principal (~190 líneas)
├── arrancar.bat        ← launcher con consola (debugging)
├── arrancar.vbs        ← launcher silencioso (uso normal)
├── requirements.txt    ← dependencias
├── .env.example        ← plantilla de config
├── LICENSE             ← MIT
└── README.md           ← este archivo
```

---

## Créditos

Hecho por **Iván Lafuente** como herramienta del [Curso IA](https://github.com/ivanlafuentepy/cursos-ia) para emprendedores y dueños de negocio.

Si te sirve, ⭐ el repo. Si encontrás un bug o querés mejorarlo, abrí un issue o PR.
