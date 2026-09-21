-- Ejecuta este archivo en Supabase > SQL Editor antes de iniciar la aplicación.
create extension if not exists "uuid-ossp";

create table if not exists app_users (
  id uuid primary key default uuid_generate_v4(), full_name text not null, email text unique not null,
  role text not null check (role in ('admin','personal')), password_hash text not null, created_at timestamptz default now()
);
create table if not exists doctors (
  id uuid primary key default uuid_generate_v4(), full_name text not null, specialty text not null,
  office text not null, active boolean default true
);
create table if not exists lookup_options (
  id bigint generated always as identity primary key, category text not null, label text not null,
  sort_order integer default 0, active boolean default true, unique(category,label)
);
create table if not exists patients (
  id uuid primary key default uuid_generate_v4(), document text not null, full_name text not null,
  age integer not null, sex text not null, weight numeric not null, pregnancy text,
  allergies text, medications text, history text, suicide_risk text, travel_history text, observations text,
  created_at timestamptz default now()
);
create table if not exists triages (
  id uuid primary key default uuid_generate_v4(), patient_id uuid references patients(id) not null,
  staff_id uuid references app_users(id) not null, doctor_id uuid references doctors(id) not null,
  chief_complaint text not null, symptom_duration text, respiratory_rate numeric, spo2 numeric,
  heart_rate numeric, systolic numeric, diastolic numeric, temperature numeric, avpu text, pain integer,
  color text not null, level integer not null, response_time text not null, created_at timestamptz default now()
);

insert into doctors(full_name,specialty,office) values
('Dra. Laura Méndez','Medicina de urgencias','Consultorio 101'),
('Dr. Andrés Rojas','Cardiología','Consultorio 102'),
('Dra. Valentina Ruiz','Medicina interna','Consultorio 103'),
('Dr. Mateo Castro','Traumatología','Consultorio 104'),
('Dra. Sofía Herrera','Pediatría','Consultorio 105'),
('Dr. Nicolás Gómez','Neurología','Consultorio 106') on conflict do nothing;

insert into lookup_options(category,label,sort_order) values
('sex','Femenino',1),('sex','Masculino',2),('sex','Otro / prefiero no indicar',3),
('pregnancy','No aplica',1),('pregnancy','No',2),('pregnancy','Sí',3),('pregnancy','Desconoce',4),
('complaint','Paro cardiorrespiratorio',1),('complaint','Dificultad respiratoria grave',2),('complaint','Shock',3),('complaint','Dolor torácico intenso',4),('complaint','Síntomas de ACV',5),('complaint','Trauma grave',6),('complaint','Dolor abdominal intenso',7),('complaint','Fractura moderada',8),('complaint','Herida que requiere sutura',9),('complaint','Esguince leve',10),('complaint','Herida pequeña',11),('complaint','Vómitos o diarrea leves',12),('complaint','Resfriado común',13),('complaint','Control de dolor crónico',14),
('duration','Menos de 1 hora',1),('duration','1 a 6 horas',2),('duration','6 a 24 horas',3),('duration','Más de 24 horas',4),
('avpu','Alerta',1),('avpu','Responde a voz',2),('avpu','Responde a dolor',3),('avpu','No responde',4),
('allergy','Niega alergias conocidas',1),('allergy','Medicamentos',2),('allergy','Látex',3),('allergy','Alimentos',4),('allergy','Desconoce',5),
('medication','No toma medicamentos',1),('medication','Anticoagulantes',2),('medication','Antihipertensivos',3),('medication','Insulina / antidiabéticos',4),('medication','Otros',5),
('history','Sin antecedentes relevantes',1),('history','Hipertensión',2),('history','Diabetes',3),('history','Cardiopatía',4),('history','Asma / EPOC',5),('history','Otros',6),
('yes_no','No',1),('yes_no','Sí',2),('yes_no','Desconoce',3) on conflict do nothing;

-- Mantén estas tablas sin acceso anónimo. El backend usa la service-role key solo en servidor.
alter table app_users enable row level security;
alter table doctors enable row level security;
alter table lookup_options enable row level security;
alter table patients enable row level security;
alter table triages enable row level security;
