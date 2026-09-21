# Clasificación Experta-Triage Medico

Aplicación Flask con reglas deterministas de clasificación en cinco niveles, perfiles de administrador y personal de enfermería, y almacenamiento en Supabase.

## Puesta en marcha

1. Instala las dependencias: `python -m pip install -r requirements.txt`.
2. Inicia: `python app.py` y abre `http://127.0.0.1:5000`.

El registro valida la clave super admin es  `admin123` por el momento qeumada en el codigo 
## Seguridad y roles

- Las contraseñas usan hashes PBKDF2 de Werkzeug; nunca se guardan reversiblemente.
- Los antecedentes, alergias, medicamentos y observaciones se cifran con `cryptography.Fernet` antes de llegar a Supabase.
- La sesión expira tras 10 minutos y la interfaz avisa a los 8 minutos; “Mantener activa” reinicia el periodo.
- El personal captura datos, recibe el triaje y asigna doctor/consultorio. El administrador consulta y exporta registros seleccionados o todos en Excel/PDF.

