const API = "/api/pacientes";

const $ = (id) => document.getElementById(id);
const campos = ["nome", "data_nascimento", "telefone", "cpf", "operadora", "carteirinha", "validade_carteirinha"];

const form = $("form");
const tbody = $("tbody");
const busca = $("busca");
const status = $("status");
const btnExcluir = $("btn-excluir");
const btnLimpar = $("btn-limpar");
const indicador = $("indicador");
const indicadorTexto = $("indicador-texto");

let pacientes = [];

function lerForm() {
  const dados = {};
  for (const c of campos) dados[c] = $(c).value.trim();
  dados.id = $("id").value || null;
  return dados;
}

function preencher(p) {
  $("id").value = p.id;
  for (const c of campos) $(c).value = p[c] ?? "";
  btnExcluir.hidden = false;
  marcarStatus("");
}

function limpar() {
  form.reset();
  $("id").value = "";
  btnExcluir.hidden = true;
  marcarStatus("");
  document.querySelectorAll("tr.selecionado").forEach((tr) => tr.classList.remove("selecionado"));
}

function marcarStatus(texto, tipo = "") {
  status.textContent = texto;
  status.className = "status" + (tipo ? " " + tipo : "");
}

function aplicarMascaraCPF(v) {
  const d = v.replace(/\D/g, "").slice(0, 11);
  if (d.length <= 3) return d;
  if (d.length <= 6) return `${d.slice(0, 3)}.${d.slice(3)}`;
  if (d.length <= 9) return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6)}`;
  return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`;
}

function aplicarMascaraTelefone(v) {
  const d = v.replace(/\D/g, "").slice(0, 11);
  if (d.length <= 2) return d;
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
}

function aplicarMascaraData(v) {
  const d = v.replace(/\D/g, "").slice(0, 8);
  if (d.length <= 2) return d;
  if (d.length <= 4) return `${d.slice(0, 2)}/${d.slice(2)}`;
  return `${d.slice(0, 2)}/${d.slice(2, 4)}/${d.slice(4)}`;
}

$("cpf").addEventListener("input", (e) => (e.target.value = aplicarMascaraCPF(e.target.value)));
$("telefone").addEventListener("input", (e) => (e.target.value = aplicarMascaraTelefone(e.target.value)));
$("data_nascimento").addEventListener("input", (e) => (e.target.value = aplicarMascaraData(e.target.value)));
$("validade_carteirinha").addEventListener("input", (e) => (e.target.value = aplicarMascaraData(e.target.value)));

async function chamarAPI(url, opts = {}) {
  const resp = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  indicador.classList.toggle("erro", !resp.ok && resp.status >= 500);
  indicadorTexto.textContent = resp.ok ? "Conectado ao banco local" : "Erro de comunicação";
  if (resp.status === 204) return null;
  const dados = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(dados.erro || `Erro ${resp.status}`);
  return dados;
}

async function carregar() {
  try {
    const q = busca.value.trim();
    pacientes = await chamarAPI(API + (q ? `?q=${encodeURIComponent(q)}` : ""));
    renderizar();
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6" class="vazio">${escaparHtml(e.message)}</td></tr>`;
  }
}

function escaparHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );
}

function rotuloValidade(p) {
  if (!p.validade_carteirinha) return "—";
  if (p.dias_para_vencer == null) return p.validade_carteirinha;
  if (p.dias_para_vencer < 0) return `${p.validade_carteirinha} (vencido)`;
  if (p.dias_para_vencer <= 30) return `${p.validade_carteirinha} (${p.dias_para_vencer}d)`;
  return p.validade_carteirinha;
}

function renderizar() {
  if (!pacientes.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="vazio">Nenhum paciente encontrado.</td></tr>`;
    return;
  }
  tbody.innerHTML = pacientes
    .map((p) => {
      const cls = p.situacao === "vencido" ? "vencido" : p.situacao === "a_vencer" ? "avencer" : "";
      return `<tr data-id="${p.id}" class="${cls}">
        <td>${escaparHtml(p.nome)}</td>
        <td>${escaparHtml(p.cpf)}</td>
        <td>${escaparHtml(p.telefone)}</td>
        <td>${escaparHtml(p.operadora || "—")}</td>
        <td>${escaparHtml(p.carteirinha || "—")}</td>
        <td>${escaparHtml(rotuloValidade(p))}</td>
      </tr>`;
    })
    .join("");
}

tbody.addEventListener("click", (ev) => {
  const tr = ev.target.closest("tr[data-id]");
  if (!tr) return;
  document.querySelectorAll("tr.selecionado").forEach((t) => t.classList.remove("selecionado"));
  tr.classList.add("selecionado");
  const p = pacientes.find((x) => String(x.id) === tr.dataset.id);
  if (!p) return;
  preencher(p);
  if (p.situacao === "vencido") {
    marcarStatus("⚠ Carteirinha vencida — solicite nova autorização.", "erro");
  } else if (p.situacao === "a_vencer") {
    marcarStatus(`⚠ Carteirinha vence em ${p.dias_para_vencer} dia(s).`, "aviso");
  }
});

busca.addEventListener("input", () => {
  clearTimeout(busca._t);
  busca._t = setTimeout(carregar, 150);
});

btnLimpar.addEventListener("click", limpar);

btnExcluir.addEventListener("click", async () => {
  const id = $("id").value;
  if (!id) return;
  if (!confirm("Remover este paciente do banco local? Esta ação não pode ser desfeita.")) return;
  try {
    await chamarAPI(`${API}/${id}`, { method: "DELETE" });
    limpar();
    marcarStatus("Paciente removido.", "ok");
    carregar();
  } catch (e) {
    marcarStatus(e.message, "erro");
  }
});

form.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const dados = lerForm();
  const id = dados.id;
  delete dados.id;
  try {
    if (id) {
      await chamarAPI(`${API}/${id}`, { method: "PUT", body: JSON.stringify(dados) });
      marcarStatus("Cadastro atualizado.", "ok");
    } else {
      await chamarAPI(API, { method: "POST", body: JSON.stringify(dados) });
      marcarStatus("Paciente cadastrado com sucesso.", "ok");
      limpar();
    }
    carregar();
  } catch (e) {
    marcarStatus(e.message, "erro");
  }
});

carregar();
