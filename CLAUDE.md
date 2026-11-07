# DORITA DICTADO — reglas del proyecto

Dictado por voz en la bandeja de Windows (`dictado.py`): click en el ícono, Groq Whisper
transcribe y pega donde está el cursor. Cómo se instala y se usa: `README.md`.

## Reglas

- **Este repo se usa en dos PCs (2PC y mini PC): `git pull` antes de tocar y push al terminar.**
  Estuvieron separadas de junio a noviembre de 2026 (la 2PC con 11 commits sin subir, la mini PC
  con 5); se unieron el 07/11 (`4c0c6d8`). Lo propio de una PC va por configuración que se
  apaga sola en la otra, como `MIC_NAME`: si no encuentra el DRELANMIC usa el mic de Windows.

- **Lo que se corta o actúa solo (por tiempo) no pega donde está el cursor**: deja el texto
  en el portapapeles y avisa en la bandeja. El auto-pegado es solo para cuando Iván para la
  grabación con el click. (07/11/2026: corte automático a los 3 min, `MAX_GRABACION_SEG`.
  Un mic olvidado pegaría minutos de charla en el chat abierto; tirarlo perdería un dictado
  largo de verdad.)
