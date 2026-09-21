const $ = (s) => document.querySelector(s);
document
  .querySelectorAll("[data-close]")
  .forEach(
    (b) => (b.onclick = () => b.closest(".modal").classList.remove("show")),
  );
const register = $("#registerForm");
if (register) {
  register.onsubmit = (e) => {
    e.preventDefault();
    $("#superModal").classList.add("show");
  };
  $("#confirmRegister").onclick = async () => {
    const data = new FormData(register);
    data.append("super_password", $("#superPassword").value);
    const res = await fetch("/register", { method: "POST", body: data }),
      out = await res.json();
    if (out.ok) {
      $("#superModal").classList.remove("show");
      $("#successModal").classList.add("show");
      setTimeout(() => {
        location.href = out.redirect;
      }, 1500);
    } else $("#registerError").textContent = out.message;
  };
}
const triageForm = $("#triageForm");
if (triageForm)
  triageForm.onsubmit = async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(triageForm));
    const res = await fetch("/api/triages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
      out = await res.json();
    if (!out.ok) return alert(out.message);
    $("#resultTitle").textContent =
      `Triaje ${out.triage.color} · Nivel ${out.triage.level}`;
    $("#resultColor").className =
      `color-pill ${out.triage.color.toLowerCase()}`;
    $("#resultColor").textContent = out.triage.wait;
    $("#resultDetails").textContent =
      "La prioridad se calculó con las reglas del diccionario clínico.";
    $("#office").textContent = out.doctor.office;
    $("#doctor").textContent = out.doctor.full_name;
    $("#time").textContent = out.time;
    $("#resultModal").classList.add("show");
    triageForm.reset();
  };
const all = $("#selectAll");
if (all)
  all.onchange = () =>
    document
      .querySelectorAll(".row-select")
      .forEach((x) => (x.checked = all.checked));
document.querySelectorAll("[data-report]").forEach(
  (b) =>
    (b.onclick = () => {
      const ids = [...document.querySelectorAll(".row-select:checked")].map(
        (x) => x.value,
      );
      location.href = `/reports/${b.dataset.report}?ids=${ids.join(",")}`;
    }),
);
let warned = false;
if ($("#timeoutModal"))
  setInterval(
    () => {
      if (!warned) {
        warned = true;
        $("#timeoutModal").classList.add("show");
      }
    },
    8 * 60 * 1000,
  );
if ($("#keepActive"))
  $("#keepActive").onclick = async () => {
    await fetch("/keep-alive", { method: "POST" });
    warned = false;
    $("#timeoutModal").classList.remove("show");
  };
