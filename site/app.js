// Página de demonstração do faturapt: o Python corre no browser com o Pyodide, e as
// fotografias são lidas com o zxing-wasm. Nada é enviado para nenhum servidor.
import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs";

const ZXING_URL = "https://cdn.jsdelivr.net/npm/zxing-wasm@3.1.4/dist/es/reader/index.js";

// Os quatro exemplos das especificações técnicas da AT (versão 1.0, ponto 5).
const EXAMPLES = [
  {
    label: "Fatura (três espaços fiscais)",
    text:
      "A:123456789*B:999999990*C:PT*D:FT*E:N*F:20191231*G:FT AB2019/0035*H:CSDF7T5H-0035" +
      "*I1:PT*I2:12000.00*I3:15000.00*I4:900.00*I5:50000.00*I6:6500.00*I7:80000.00*I8:18400.00" +
      "*J1:PT-AC*J2:10000.00*J3:25000.56*J4:1000.02*J5:75000.00*J6:6750.00*J7:100000.00*J8:18000.00" +
      "*K1:PT-MA*K2:5000.00*K3:12500.00*K4:625.00*K5:25000.00*K6:3000.00*K7:40000.00*K8:8800.00" +
      "*L:100.00*M:25.00*N:64000.02*O:513600.58*P:100.00*Q:kLp0*R:9999" +
      "*S:TB;PT00000000000000000000000;513500.58",
  },
  {
    label: "Fatura simplificada",
    text:
      "A:123456789*B:999999990*C:PT*D:FS*E:N*F:20190812*G:FS CDVF/12345*H:CDF7T5HD-12345" +
      "*I1:PT*I7:0.65*I8:0.15*N:0.15*O:0.80*Q:YhGV*R:9999*S:NU;0.80",
  },
  {
    label: "Fatura pró-forma",
    text:
      "A:500000000*B:123456789*C:PT*D:PF*E:N*F:20190123*G:PF G2019CB/145789*H:HB6FT7RV-145789" +
      "*I1:PT*I2:12345.34*I3:12532.65*I4:751.96*I5:52789.00*I6:6862.57*I7:32425.69*I8:7457.91" +
      "*N:15072.44*O:125165.12*Q:r/fY*R:9999",
  },
  {
    label: "Guia de transporte",
    text:
      "A:500000000*B:123456789*C:PT*D:GT*E:N*F:20190720*G:GT G234CB/50987*H:GTVX4Y8B-50987" +
      "*I1:0*N:0.00*O:0.00*Q:5uIg*R:9999",
  },
  {
    label: "Com problemas",
    text:
      "A:123456789*B:999999990*C:PT*D:FS*E:N*F:20190812*G:FS CDVF/12345*H:CDF7T5HD-12346" +
      "*I1:PT*I7:0.65*I8:0.15*N:0.15*O:0.90*Q:YhGV*R:9999",
  },
];

const FISCAL_SPACES = { PT: "Continente", "PT-AC": "Açores", "PT-MA": "Madeira" };

const $ = (id) => document.getElementById(id);
const status = $("status");
let analyse = null; // a função Python, quando o Pyodide estiver pronto

// --- Arranque ----------------------------------------------------------------------------

async function start() {
  for (const example of EXAMPLES) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = example.label;
    button.disabled = true;
    button.addEventListener("click", () => {
      $("qr-text").value = example.text;
      show(example.text, "o exemplo");
    });
    $("examples").append(button);
  }
  $("text-form").addEventListener("submit", (event) => {
    event.preventDefault();
    show($("qr-text").value, "o texto");
  });
  $("qr-photo").addEventListener("change", readPhoto);
  $("camera-start").addEventListener("click", startCamera);
  $("camera-stop").addEventListener("click", () => {
    stopCamera();
    status.textContent = "Câmara parada.";
    $("camera-start").focus();
  });
  // Sem câmara acessível (ou fora de HTTPS), o botão não aparece.
  if (!navigator.mediaDevices?.getUserMedia) {
    $("camera-start").hidden = true;
    $("camera-hint").hidden = true;
  }
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stopCamera();
  });

  try {
    const pyodide = await loadPyodide();
    const [wheel, bridge] = await Promise.all([
      fetch("faturapt.whl").then(okOrThrow).then((r) => r.arrayBuffer()),
      fetch("demo.py").then(okOrThrow).then((r) => r.text()),
    ]);
    pyodide.unpackArchive(wheel, "wheel");
    pyodide.runPython(bridge);
    analyse = pyodide.globals.get("analyse");
  } catch (error) {
    status.textContent = `Não foi possível carregar o Python no browser: ${error.message}`;
    return;
  }
  for (const control of document.querySelectorAll("button, input")) control.disabled = false;
  status.textContent = "Pronto. Cola o texto do QR, escolhe um exemplo, usa a câmara ou uma fotografia.";
}

function okOrThrow(response) {
  if (!response.ok) throw new Error(`${response.url}: ${response.status}`);
  return response;
}

// --- Fotografia --------------------------------------------------------------------------

async function readPhoto(event) {
  const file = event.target.files[0];
  if (!file) return;
  status.textContent = "A procurar o código QR na fotografia…";
  try {
    const { readBarcodes } = await import(ZXING_URL);
    const codes = await readBarcodes(file, { formats: ["QRCode"], tryHarder: true });
    const texts = codes.filter((code) => code.isValid).map((code) => code.text);
    if (texts.length === 0) {
      showError("Não encontrei nenhum código QR na fotografia. Tenta com o QR maior e nítido.");
      return;
    }
    // Pode haver outros QR na fotografia (um site, uma promoção): fica o primeiro da fatura.
    const text = texts.find((t) => !JSON.parse(analyse(t)).error) ?? texts[0];
    $("qr-text").value = text;
    show(text, "a fotografia");
  } catch (error) {
    showError(`Não foi possível ler a fotografia: ${error.message}`);
  } finally {
    event.target.value = "";
  }
}

// --- Câmara ------------------------------------------------------------------------------

let camera = null; // { stream, timer } enquanto a câmara está ligada
const SCAN_INTERVAL_MS = 200;

async function startCamera() {
  if (camera) return;
  // Enquanto o browser pergunta se pode usar a câmara, o botão fica desativado.
  $("camera-start").disabled = true;
  status.textContent = "A pedir acesso à câmara…";
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    });
  } catch (error) {
    status.textContent = cameraError(error);
    return;
  } finally {
    $("camera-start").disabled = false;
  }
  camera = { stream, timer: null };
  const video = $("camera-video");
  try {
    const { readBarcodes } = await import(ZXING_URL);
    video.srcObject = stream;
    await video.play();
    $("camera-start").hidden = true;
    $("camera-hint").hidden = true;
    $("camera-panel").hidden = false;
    $("camera-stop").focus();
    status.textContent = "Aponta a câmara ao código QR da fatura…";
    scanLoop(stream, video, readBarcodes);
  } catch (error) {
    stopCamera();
    status.textContent = `Não foi possível usar a câmara: ${error.message}`;
  }
}

function scanLoop(stream, video, readBarcodes) {
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d", { willReadFrequently: true });
  let warned = false;
  const scan = async () => {
    if (camera?.stream !== stream) return; // a câmara foi parada entretanto
    try {
      if (video.videoWidth) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0);
        const frame = context.getImageData(0, 0, canvas.width, canvas.height);
        const codes = await readBarcodes(frame, { formats: ["QRCode"], maxNumberOfSymbols: 4 });
        const texts = codes.filter((code) => code.isValid).map((code) => code.text);
        const invoice = texts.find((t) => !JSON.parse(analyse(t)).error);
        if (invoice && camera?.stream === stream) {
          stopCamera();
          $("qr-text").value = invoice;
          show(invoice, "o QR pela câmara");
          return;
        }
        if (texts.length > 0 && !warned) {
          warned = true;
          status.textContent = "Encontrei um código QR, mas não é de uma fatura. Aponta ao QR da fatura.";
        }
      }
    } catch (error) {
      stopCamera();
      showError(`Não foi possível ler a imagem da câmara: ${error.message}`);
      return;
    }
    if (camera?.stream === stream) camera.timer = setTimeout(scan, SCAN_INTERVAL_MS);
  };
  scan();
}

function stopCamera() {
  if (!camera) return;
  clearTimeout(camera.timer);
  for (const track of camera.stream.getTracks()) track.stop();
  camera = null;
  $("camera-video").srcObject = null;
  $("camera-panel").hidden = true;
  if (navigator.mediaDevices?.getUserMedia) {
    $("camera-start").hidden = false;
    $("camera-hint").hidden = false;
  }
}

function cameraError(error) {
  switch (error.name) {
    case "NotAllowedError":
    case "SecurityError":
      return "Sem autorização para usar a câmara. Podes dá-la nas definições do browser, ou escolher uma fotografia.";
    case "NotFoundError":
    case "OverconstrainedError":
      return "Não encontrei nenhuma câmara neste aparelho. Podes escolher uma fotografia.";
    case "NotReadableError":
      return "A câmara está a ser usada por outra aplicação.";
    default:
      return `Não foi possível abrir a câmara: ${error.message}`;
  }
}

// --- Resultado ---------------------------------------------------------------------------

function show(text, source) {
  if (!analyse) return;
  const data = JSON.parse(analyse(text.trim()));
  $("result-card").hidden = false;
  $("raw-json").textContent = JSON.stringify(data, null, 2);
  $("version").textContent = data.version ? `faturapt ${data.version}.` : "";
  if (data.error) {
    showError(`Não é um código QR de fatura: ${data.error}`);
    return;
  }
  status.textContent = `Li ${source}.`;
  showVerdict(data.problems);
  showDetails(data);
  $("result-title").focus({ preventScroll: true });
}

function showError(message) {
  $("result-card").hidden = false;
  $("details").replaceChildren();
  const verdict = $("verdict");
  verdict.className = "verdict error";
  verdict.replaceChildren(el("p", message));
  status.textContent = message;
}

function showVerdict(problems) {
  const verdict = $("verdict");
  if (problems.length === 0) {
    verdict.className = "verdict ok";
    verdict.replaceChildren(el("p", "Tudo certo: os NIFs, o ATCUD e as contas batem certo."));
    return;
  }
  verdict.className = "verdict warn";
  const title = problems.length === 1 ? "1 problema" : `${problems.length} problemas`;
  verdict.replaceChildren(
    el("p", `${title} (a fatura lê-se, mas há algo que não bate certo):`),
    el("ul", ...problems.map((p) => el("li", p))),
  );
}

function showDetails(data) {
  const issuer = data.issuer_type ? `${data.issuer_nif} (${data.issuer_type})` : data.issuer_nif;
  const buyer = data.is_final_consumer
    ? `${data.buyer_nif} (consumidor final)`
    : `${data.buyer_nif} (${data.buyer_country})`;
  const type = data.document_type_name
    ? `${data.document_type_name} (${data.document_type})`
    : data.document_type;
  const rows = [
    ["Emitente (NIF)", issuer],
    ["Adquirente (NIF)", buyer],
    ["Documento", `${type} ${data.document_id}`],
    ["Estado", data.document_status],
    ["Data", formatDate(data.document_date)],
    ["ATCUD", data.atcud],
    ["Total de impostos", euros(data.total_taxes)],
    ["Total", euros(data.total)],
  ];
  if (data.non_taxable) rows.push(["Não sujeito a IVA", euros(data.non_taxable)]);
  if (data.stamp_duty) rows.push(["Imposto do selo", euros(data.stamp_duty)]);
  if (data.withholding) rows.push(["Retenção na fonte", euros(data.withholding)]);
  rows.push(["Certificado", `n.º ${data.certificate}, hash ${data.hash_chars}`]);
  if (data.other_info) rows.push(["Outras informações", data.other_info]);

  const list = el("dl", ...rows.flatMap(([term, value]) => [el("dt", term), el("dd", value)]));
  $("details").replaceChildren(list, ...vatTable(data.taxes));
}

function vatTable(taxes) {
  if (taxes.length === 0) return [el("h3", "IVA"), el("p", "Documento sem IVA.")];
  const columns = [
    ["Isento", "exempt_base"],
    ["Reduzida", "reduced_base", "reduced_vat"],
    ["Intermédia", "intermediate_base", "intermediate_vat"],
    ["Normal", "normal_base", "normal_vat"],
  ];
  const header = el(
    "tr",
    el("th", "Espaço fiscal", { scope: "col" }),
    ...columns.map(([name]) => el("th", name, { scope: "col" })),
  );
  const body = taxes.map((tax) =>
    el(
      "tr",
      el("th", FISCAL_SPACES[tax.fiscal_space] ?? tax.fiscal_space, { scope: "row" }),
      ...columns.map(([, base, vat]) => {
        if (tax[base] == null) return el("td", "—");
        if (!vat) return el("td", euros(tax[base]));
        return el("td", euros(tax[base]), el("span", `IVA ${euros(tax[vat] ?? "0.00")}`, { class: "vat" }));
      }),
    ),
  );
  const table = el("table", el("thead", header), el("tbody", ...body));
  table.setAttribute("aria-label", "IVA por espaço fiscal e taxa: base tributável e imposto");
  // Em ecrãs estreitos a tabela tem scroll: a zona recebe o foco para se ler pelo teclado.
  const wrap = el("div", table, { class: "table-wrap", tabindex: "0", role: "region" });
  wrap.setAttribute("aria-label", "IVA por espaço fiscal (com scroll horizontal)");
  return [el("h3", "IVA por espaço fiscal"), wrap];
}

// --- Utilitários -------------------------------------------------------------------------

/** Cria um elemento; o texto entra sempre como texto, nunca como HTML. */
function el(tag, ...children) {
  const node = document.createElement(tag);
  for (const child of children) {
    if (child instanceof Node) node.append(child);
    else if (typeof child === "string") node.append(child);
    else if (child) for (const [name, value] of Object.entries(child)) node.setAttribute(name, value);
  }
  return node;
}

const euroFormat = new Intl.NumberFormat("pt-PT", { style: "currency", currency: "EUR" });

function euros(amount) {
  return euroFormat.format(Number(amount));
}

function formatDate(iso) {
  const [year, month, day] = iso.split("-");
  return `${day}/${month}/${year}`;
}

$("result-title").tabIndex = -1;
start();
