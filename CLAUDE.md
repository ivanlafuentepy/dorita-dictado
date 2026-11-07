# DORITA DICTADO — reglas del proyecto

Dictado por voz en la bandeja de Windows (`dictado.py`): click en el ícono, Groq Whisper
transcribe y pega donde está el cursor. Cómo se instala y se usa: `README.md`.

## Reglas

- **Lo que se corta o actúa solo (por tiempo) no pega donde está el cursor**: deja el texto
  en el portapapeles y avisa en la bandeja. El auto-pegado es solo para cuando Iván para la
  grabación con el click. (07/11/2026: corte automático a los 3 min, `MAX_GRABACION_SEG`.
  Un mic olvidado pegaría minutos de charla en el chat abierto; tirarlo perdería un dictado
  largo de verdad.)
