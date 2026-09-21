# CardioTriage — Sistema experto de triaje médico

Aplicación Flask con reglas deterministas de clasificación en cinco niveles, perfiles de administrador y personal de enfermería, y almacenamiento en Supabase.

> Aviso: es un proyecto académico y de apoyo a la priorización. No sustituye protocolos institucionales ni el juicio de profesionales de salud.

## Puesta en marcha

1. Crea un proyecto en Supabase y ejecuta [sql/schema.sql](sql/schema.sql) en el SQL Editor.
2. Copia `.env.example` como `.env` y completa `SUPABASE_URL`, `SUPABASE_SECRET_KEY` y una clave privada de Flask.
3. Instala las dependencias: `python -m pip install -r requirements.txt`.
4. Inicia: `python app.py` y abre `http://127.0.0.1:5000`.

El registro valida la clave académica `admin123` mediante modal, tal como fue solicitado. En un entorno real debe cambiarse por un mecanismo de permisos del servidor.

## Seguridad y roles

- Las contraseñas usan hashes PBKDF2 de Werkzeug; nunca se guardan reversiblemente.
- Los antecedentes, alergias, medicamentos y observaciones se cifran con `cryptography.Fernet` antes de llegar a Supabase.
- La sesión expira tras 10 minutos y la interfaz avisa a los 8 minutos; “Mantener activa” reinicia el periodo.
- El personal captura datos, recibe el triaje y asigna doctor/consultorio. El administrador consulta y exporta registros seleccionados o todos en Excel/PDF.

Las reglas están identificadas con el encabezado `DICCIONARIO DE REGLAS DE TRIAJE` en [app.py](app.py), y se evalúan desde Rojo hasta Azul.
