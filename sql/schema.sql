-- CARDIOTRIAGE: REINICIO TOTAL DE BASE DE DATOS
-- ADVERTENCIA: elimina todos los usuarios, pacientes, triajes, doctores y listas actuales.
-- Ejecutar completo en Supabase > SQL Editor > New query.

drop table if exists triages cascade;
drop table if exists patients cascade;
drop table if exists app_users cascade;
drop table if exists doctors cascade;
drop table if exists lookup_options cascade;

create extension if not exists "uuid-ossp";

create table app_users (
  id uuid primary key default uuid_generate_v4(),
  first_name varchar(25) not null check (first_name ~ '^[A-Za-z]{1,25}$'),
  last_name varchar(25) not null check (last_name ~ '^[A-Za-z]{1,25}$'),
  full_name varchar(51) not null,
  document_type varchar(40) not null,
  -- Aquí se almacena el valor cifrado por cryptography.Fernet, nunca el número plano.
  document_number text not null,
  email varchar(255) not null unique,
  role varchar(10) not null check (role in ('admin', 'personal')),
  password_hash text not null,
  created_at timestamptz not null default now()
);

create table doctors (
  id uuid primary key default uuid_generate_v4(),
  full_name varchar(120) not null unique,
  specialty varchar(100) not null,
  office varchar(30) not null,
  active boolean not null default true
);

create table lookup_options (
  id bigint generated always as identity primary key,
  category varchar(50) not null,
  label varchar(120) not null,
  sort_order integer not null default 0,
  active boolean not null default true,
  unique(category, label)
);

create table patients (
  id uuid primary key default uuid_generate_v4(),
  document text not null,
  full_name varchar(160) not null,
  age integer not null check (age between 0 and 120),
  sex varchar(40) not null,
  weight numeric not null check (weight > 0),
  pregnancy varchar(80),
  allergies text,
  medications text,
  history text,
  suicide_risk varchar(30),
  travel_history varchar(30),
  observations text,
  created_at timestamptz not null default now()
);

create table triages (
  id uuid primary key default uuid_generate_v4(),
  patient_id uuid not null references patients(id),
  staff_id uuid not null references app_users(id),
  doctor_id uuid not null references doctors(id),
  chief_complaint varchar(150) not null,
  symptom_duration varchar(100),
  respiratory_rate numeric,
  spo2 numeric,
  heart_rate numeric,
  systolic numeric,
  diastolic numeric,
  temperature numeric,
  avpu varchar(40),
  pain integer check (pain between 0 and 10),
  color varchar(15) not null,
  level integer not null check (level between 1 and 5),
  response_time varchar(40) not null,
  created_at timestamptz not null default now()
);

insert into doctors (full_name, specialty, office) values
  ('Dra. Laura Mendez', 'Medicina de urgencias', 'Consultorio 101'),
  ('Dr. Andres Rojas', 'Cardiologia', 'Consultorio 102'),
  ('Dra. Valentina Ruiz', 'Medicina interna', 'Consultorio 103'),
  ('Dr. Mateo Castro', 'Traumatologia', 'Consultorio 104'),
  ('Dra. Sofia Herrera', 'Pediatria', 'Consultorio 105'),
  ('Dr. Nicolas Gomez', 'Neurologia', 'Consultorio 106')
on conflict (full_name) do nothing;

insert into lookup_options (category, label, sort_order) values
  ('document_type', 'Cédula de ciudadanía', 1),
  ('document_type', 'Tarjeta de identidad', 2),
  ('document_type', 'Cédula de extranjería', 3),
  ('document_type', 'Pasaporte', 4),
  ('sex', 'Femenino', 1), ('sex', 'Masculino', 2), ('sex', 'Otro / prefiero no indicar', 3),
  ('pregnancy', 'No aplica', 1), ('pregnancy', 'No', 2), ('pregnancy', 'Sí', 3), ('pregnancy', 'Desconoce', 4),
  ('complaint', 'Paro cardiorrespiratorio', 1), ('complaint', 'Dificultad respiratoria grave', 2), ('complaint', 'Shock', 3),
  ('complaint', 'Dolor torácico intenso', 4), ('complaint', 'Síntomas de ACV', 5), ('complaint', 'Trauma grave', 6),
  ('complaint', 'Dolor abdominal intenso', 7), ('complaint', 'Fractura moderada', 8), ('complaint', 'Herida que requiere sutura', 9),
  ('complaint', 'Esguince leve', 10), ('complaint', 'Herida pequeña', 11), ('complaint', 'Vómitos o diarrea leves', 12),
  ('complaint', 'Resfriado común', 13), ('complaint', 'Control de dolor crónico', 14),
  ('duration', 'Menos de 1 hora', 1), ('duration', '1 a 6 horas', 2), ('duration', '6 a 24 horas', 3), ('duration', 'Más de 24 horas', 4),
  ('avpu', 'Alerta', 1), ('avpu', 'Responde a voz', 2), ('avpu', 'Responde a dolor', 3), ('avpu', 'No responde', 4),
  ('allergy', 'Niega alergias conocidas', 1), ('allergy', 'Medicamentos', 2), ('allergy', 'Látex', 3), ('allergy', 'Alimentos', 4), ('allergy', 'Desconoce', 5),
  ('medication', 'No toma medicamentos', 1), ('medication', 'Anticoagulantes', 2), ('medication', 'Antihipertensivos', 3), ('medication', 'Insulina / antidiabéticos', 4), ('medication', 'Otros', 5),
  ('history', 'Sin antecedentes relevantes', 1), ('history', 'Hipertensión', 2), ('history', 'Diabetes', 3), ('history', 'Cardiopatía', 4), ('history', 'Asma / EPOC', 5), ('history', 'Otros', 6),
  ('yes_no', 'No', 1), ('yes_no', 'Sí', 2), ('yes_no', 'Desconoce', 3)
on conflict (category, label) do nothing;

alter table app_users enable row level security;
alter table doctors enable row level security;
alter table lookup_options enable row level security;
alter table patients enable row level security;
alter table triages enable row level security;
