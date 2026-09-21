import base64
import hashlib
import logging
import io
import os
import re
from datetime import datetime, timedelta, timezone
from functools import wraps

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from supabase import create_client
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
# Algunos entornos de desarrollo inyectan este proxy local de descarte. No existe
# un servidor en 127.0.0.1:9, por lo que impediría la conexión HTTPS a Supabase.
# No se eliminan proxies reales configurados por el usuario.
for proxy_name in ("ALL_PROXY", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "http_proxy", "https_proxy"):
    if os.getenv(proxy_name, "").rstrip("/") == "http://127.0.0.1:9":
        os.environ.pop(proxy_name, None)
app = Flask(__name__)
app.config.update(SECRET_KEY=os.getenv("FLASK_SECRET_KEY", "cambia-esta-clave-en-produccion"), PERMANENT_SESSION_LIFETIME=timedelta(minutes=10))
key = os.getenv("FERNET_KEY") or base64.urlsafe_b64encode(hashlib.sha256(app.config["SECRET_KEY"].encode()).digest()).decode()
box = Fernet(key.encode())
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_KEY", "")
supabase = create_client(os.getenv("SUPABASE_URL", ""), SUPABASE_KEY) if os.getenv("SUPABASE_URL") else None

# ===================== DICCIONARIO DE REGLAS DE TRIAJE =====================
# 1. MEMORIA DE TRABAJO (Base de hechos)
# Los hechos se crean con los datos que la enfermera registra en el formulario.
# 2. BASE DE REGLAS Y MOTOR DE INFERENCIA ESTÁTICO
# Las reglas se evalúan de arriba hacia abajo: la primera coincidencia tiene prioridad.
# Es una ayuda académica de priorización, no sustituye el juicio clínico.
def motor_evaluacion_triaje(hechos):
    """Clasifica hechos clínicos con reglas deterministas y precedencia explícita."""

    # Hechos disponibles: identificación, edad, sexo, peso, embarazo, motivo,
    # duración, signos vitales, AVPU, dolor, alergias, medicamentos,
    # antecedentes, riesgo suicida, viajes y observaciones. Los datos que no
    # son alarmas aisladas se usan como contexto en reglas combinadas.

    # Regla de triaje ROJO / Nivel I: amenaza vital inmediata (máxima precedencia)
    if (hechos["avpu"] == "No responde" or hechos["spo2"] < 85 or
            hechos["systolic"] < 80 or hechos["respiratory_rate"] < 8 or
            hechos["respiratory_rate"] > 35 or
            hechos["chief_complaint"] in {"Paro cardiorrespiratorio", "Dificultad respiratoria grave", "Shock"}):
        return {"color": "Rojo", "level": 1, "wait": "Atención inmediata"}

    # Regla de triaje NARANJA / Nivel II: posible deterioro rápido
    if (hechos["avpu"] == "Responde a dolor" or hechos["spo2"] < 90 or
            hechos["systolic"] < 90 or hechos["heart_rate"] > 140 or
            hechos["pain"] >= 9 or
            (hechos["pregnancy"] == "Sí" and hechos["chief_complaint"] == "Dolor abdominal intenso") or
            hechos["suicide_risk"] == "Sí" or
            (hechos["medications"] == "Anticoagulantes" and hechos["chief_complaint"] in {"Trauma grave", "Herida que requiere sutura"}) or
            (hechos["age"] < 1 and hechos["temperature"] >= 38) or
            hechos["chief_complaint"] in {"Dolor torácico intenso", "Síntomas de ACV", "Trauma grave"}):
        return {"color": "Naranja", "level": 2, "wait": "≤ 10 minutos"}

    # Regla de triaje AMARILLO / Nivel III: urgencia estable
    if (hechos["temperature"] >= 39 or hechos["pain"] >= 6 or
            (hechos["travel_history"] == "Sí" and hechos["temperature"] >= 38) or
            (hechos["history"] in {"Cardiopatía", "Asma / EPOC"} and hechos["spo2"] <= 92) or
            (hechos["age"] <= 5 and hechos["temperature"] >= 38) or
            hechos["chief_complaint"] in {"Dolor abdominal intenso", "Fractura moderada", "Herida que requiere sutura"}):
        return {"color": "Amarillo", "level": 3, "wait": "≤ 30–60 minutos"}

    # Regla de triaje VERDE / Nivel IV: atención menos urgente
    if hechos["chief_complaint"] in {"Esguince leve", "Herida pequeña", "Vómitos o diarrea leves"}:
        return {"color": "Verde", "level": 4, "wait": "≈ 120 minutos"}

    # Regla por defecto (fallback): triaje AZUL / Nivel V
    return {"color": "Azul", "level": 5, "wait": "180–240 minutos"}

def db():
    if not supabase:
        raise RuntimeError("Configura SUPABASE_URL y SUPABASE_SERVICE_KEY en .env")
    return supabase

def registration_error_message(error):
    """Convierte errores frecuentes de Supabase en mensajes útiles y seguros."""
    detail = str(error).lower()
    app.logger.exception("Error durante el registro", exc_info=error)
    if "app_users" in detail and ("does not exist" in detail or "relation" in detail):
        return "La tabla app_users no existe todavía. Ejecuta sql/schema.sql en Supabase SQL Editor."
    if "duplicate" in detail or "unique" in detail or "23505" in detail:
        return "Este correo ya está registrado. Inicia sesión o usa otro correo."
    if "connect" in detail or "name or service not known" in detail or "getaddrinfo" in detail:
        return "No se pudo conectar con Supabase. Verifica SUPABASE_URL y que el proyecto esté activo."
    if "permission" in detail or "row-level security" in detail or "401" in detail or "403" in detail:
        return "Supabase rechazó el acceso. Verifica que SUPABASE_SECRET_KEY sea la clave sb_secret vigente."
    return "No fue posible registrar el usuario. Revisa la consola de Python para ver el error técnico."

def encrypt(value):
    return box.encrypt((value or "").encode()).decode()

def decrypt(value):
    return box.decrypt(value.encode()).decode() if value else ""

def current_user():
    return {"id": session.get("user_id"), "name": session.get("user_name"), "role": session.get("role")}

def login_required(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                abort(403)
            return fn(*args, **kwargs)
        return wrapped
    return decorator

@app.before_request
def session_timeout():
    if session.get("user_id"):
        last = session.get("last_activity", 0)
        if datetime.now(timezone.utc).timestamp() - last > 600:
            session.clear(); flash("La sesión expiró por inactividad.", "error")
            return redirect(url_for("login"))
        session["last_activity"] = datetime.now(timezone.utc).timestamp()
        session.permanent = True

@app.route("/")
def index():
    return redirect(url_for("dashboard")) if session.get("user_id") else redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            record = db().table("app_users").select("*").eq("email", request.form["email"].lower()).single().execute().data
            if not check_password_hash(record["password_hash"], request.form["password"]): raise ValueError
            session.clear(); session.permanent = True
            session.update(user_id=record["id"], user_name=record["full_name"], role=record["role"], last_activity=datetime.now(timezone.utc).timestamp())
            return redirect(url_for("dashboard"))
        except Exception:
            flash("Correo o contraseña inválidos.", "error")
    return render_template("auth.html", mode="login")

@app.route("/register", methods=["GET", "POST"])
def register():
    document_types = db().table("lookup_options").select("label").eq("category", "document_type").eq("active", True).order("sort_order").execute().data
    if request.method == "POST":
        if request.form.get("super_password") != "admin123":
            return jsonify(ok=False, message="Clave de superadministrador incorrecta."), 403
        try:
            first_name = request.form.get("first_name", "")
            last_name = request.form.get("last_name", "")
            document_type = request.form.get("document_type", "")
            document_number = request.form.get("document_number", "")
            if not re.fullmatch(r"[A-Za-z]{1,25}", first_name) or not re.fullmatch(r"[A-Za-z]{1,25}", last_name):
                return jsonify(ok=False, message="El primer nombre y el primer apellido solo admiten letras sin espacios (máximo 25)."), 400
            if not re.fullmatch(r"[0-9]{5,25}", document_number):
                return jsonify(ok=False, message="El número de documento debe contener entre 5 y 25 dígitos."), 400
            if document_type not in {item["label"] for item in document_types}:
                return jsonify(ok=False, message="Selecciona un tipo de documento válido."), 400
            user = db().table("app_users").insert({
                "first_name": first_name, "last_name": last_name,
                "full_name": f"{first_name} {last_name}",
                "document_type": document_type, "document_number": encrypt(document_number),
                "email": request.form["email"].lower(), "role": request.form["role"],
                "password_hash": generate_password_hash(request.form["password"])
            }).execute().data[0]
            # El usuario recién validado queda autenticado inmediatamente.
            session.clear(); session.permanent = True
            session.update(user_id=user["id"], user_name=user["full_name"], role=user["role"], last_activity=datetime.now(timezone.utc).timestamp())
            return jsonify(ok=True, redirect=url_for("dashboard"))
        except Exception as error:
            return jsonify(ok=False, message=registration_error_message(error)), 400
    return render_template("auth.html", mode="register", document_types=document_types)

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("login"))

@app.route("/keep-alive", methods=["POST"])
@login_required()
def keep_alive():
    session["last_activity"] = datetime.now(timezone.utc).timestamp(); return jsonify(ok=True)

@app.route("/dashboard")
@login_required()
def dashboard():
    if current_user()["role"] == "admin":
        rows = db().table("triages").select("*, doctors(full_name, office)").order("created_at", desc=True).execute().data
        return render_template("admin_dashboard.html", triages=rows)
    options = db().table("lookup_options").select("category,label").eq("active", True).order("sort_order").execute().data
    groups = {}
    for item in options: groups.setdefault(item["category"], []).append(item["label"])
    doctors = db().table("doctors").select("id,full_name,office").eq("active", True).execute().data
    return render_template("staff_dashboard.html", options=groups, doctors=doctors)

@app.route("/api/triages", methods=["POST"])
@login_required("personal")
def save_triage():
    form = request.get_json()
    try:
        values = {k: float(form[k]) for k in ("spo2", "systolic", "respiratory_rate", "heart_rate", "temperature", "pain")}
        values["pain"] = int(values["pain"])
        # Memoria de trabajo: incluye todos los hechos recolectados por enfermería.
        values.update({
            "document": form["document"], "full_name": form["full_name"], "age": int(form["age"]),
            "sex": form["sex"], "weight": float(form["weight"]), "pregnancy": form.get("pregnancy"),
            "chief_complaint": form["chief_complaint"], "symptom_duration": form["symptom_duration"],
            "diastolic": float(form["diastolic"]), "avpu": form["avpu"],
            "allergies": form.get("allergies"), "medications": form.get("medications"),
            "history": form.get("history"), "suicide_risk": form.get("suicide_risk"),
            "travel_history": form.get("travel_history"), "observations": form.get("observations")
        })
        result = motor_evaluacion_triaje(values)
        sensitive = {"allergies": form.get("allergies"), "medications": form.get("medications"), "history": form.get("history"), "observations": form.get("observations")}
        patient = {"document": form["document"], "full_name": form["full_name"], "age": int(form["age"]), "sex": form["sex"], "weight": float(form["weight"]), "pregnancy": form.get("pregnancy"), "suicide_risk": form.get("suicide_risk"), "travel_history": form.get("travel_history"), **{k: encrypt(v) for k,v in sensitive.items()}}
        patient_row = db().table("patients").insert(patient).execute().data[0]
        triage_columns = ("chief_complaint", "symptom_duration", "respiratory_rate", "spo2", "heart_rate", "systolic", "diastolic", "temperature", "avpu", "pain")
        data = {key: values[key] for key in triage_columns}
        data.update({"doctor_id": form["doctor_id"], "patient_id": patient_row["id"], "staff_id": current_user()["id"], "level": result["level"], "color": result["color"], "response_time": result["wait"]})
        saved = db().table("triages").insert(data).execute().data[0]
        doctor = db().table("doctors").select("full_name,office").eq("id", form["doctor_id"]).single().execute().data
        return jsonify(ok=True, triage=result, doctor=doctor, time=datetime.now().strftime("%I:%M %p"), id=saved["id"])
    except (KeyError, ValueError):
        return jsonify(ok=False, message="Revisa los campos obligatorios y los signos vitales."), 400

@app.route("/reports/<format>")
@login_required("admin")
def report(format):
    ids = [i for i in request.args.get("ids", "").split(",") if i]
    doctor_id = request.args.get("doctor")
    query = db().table("triages").select("*, patients(full_name,document,age), doctors(full_name,office)").order("created_at", desc=True)
    if ids: query = query.in_("id", ids)
    if doctor_id: query = query.eq("doctor_id", doctor_id)
    rows = query.execute().data
    columns = ["Paciente", "Documento", "Edad", "Triaje", "Prioridad", "Doctor", "Consultorio", "Registro"]
    values = [[r["patients"]["full_name"], r["patients"]["document"], r["patients"]["age"], r["color"], f"Nivel {r['level']}", r["doctors"]["full_name"], r["doctors"]["office"], r["created_at"][:16]] for r in rows]
    if format == "excel":
        book=Workbook(); sheet=book.active; sheet.title="Triajes"; sheet.append(columns)
        for line in values: sheet.append(line)
        out=io.BytesIO(); book.save(out); out.seek(0)
        return send_file(out, as_attachment=True, download_name="triajes.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    if format == "pdf":
        out=io.BytesIO(); doc=SimpleDocTemplate(out, pagesize=letter); table=Table([columns]+values, repeatRows=1)
        table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#4f87bd")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.25,colors.grey),("FONTSIZE",(0,0),(-1,-1),7)])); doc.build([table]); out.seek(0)
        return send_file(out, as_attachment=True, download_name="triajes.pdf", mimetype="application/pdf")
    abort(404)

if __name__ == "__main__": app.run(debug=True)
