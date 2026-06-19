import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

async function loadArtifactTool() {
  if (process.env.CODEX_NODE_MODULES) {
    const modulePath = path.join(
      process.env.CODEX_NODE_MODULES,
      "@oai", "artifact-tool", "dist", "artifact_tool.mjs"
    );
    return import(pathToFileURL(modulePath).href);
  }
  return import("@oai/artifact-tool");
}

const { Presentation, PresentationFile } = await loadArtifactTool();

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/(.:)/, "$1")), "..");
const OUT = path.join(ROOT, "reports", "CacheSage-UC-defense-demo.pptx");
const WORK = process.env.CACHESAGE_PPT_WORK || path.join(process.env.TEMP || ".", "cachesage-ppt");
const PREVIEW = path.join(WORK, "preview");
const LAYOUT = path.join(WORK, "layout");

const C = {
  ink: "#0B1220", panel: "#121D30", paper: "#F4F7FB", white: "#F8FAFC",
  muted: "#94A3B8", cyan: "#22D3EE", green: "#34D399", amber: "#F59E0B",
  red: "#FB7185", line: "#26364F", darkText: "#172033"
};
const FONT = "Microsoft YaHei";

function box(slide, left, top, width, height, fill = C.panel, line = C.line, radius = "rounded-sm") {
  return slide.shapes.add({ geometry: "roundRect", position: { left, top, width, height }, fill,
    line: { style: "solid", fill: line, width: 1 }, borderRadius: radius });
}

function text(slide, value, left, top, width, height, size = 20, color = C.white, bold = false) {
  const shape = slide.shapes.add({ geometry: "textbox", position: { left, top, width, height },
    fill: "none", line: { style: "solid", fill: "none", width: 0 } });
  shape.text = value;
  shape.text.style = { fontSize: size, color, bold, typeface: FONT };
  return shape;
}

function base(slide, kicker, title, page, light = false) {
  slide.background.fill = light ? C.paper : C.ink;
  text(slide, kicker, 64, 34, 340, 24, 13, light ? "#087A8C" : C.cyan, true);
  text(slide, title, 64, 66, 1040, 58, 34, light ? C.darkText : C.white, true);
  const rule = slide.shapes.add({ geometry: "rect", position: { left: 64, top: 132, width: 1152, height: 2 }, fill: light ? "#C8D3E1" : C.line, line: { style: "solid", fill: "none", width: 0 } });
  text(slide, String(page).padStart(2, "0"), 1160, 676, 54, 20, 12, light ? "#64748B" : C.muted, true);
  return rule;
}

function metric(slide, left, top, value, label, accent = C.green, width = 250) {
  box(slide, left, top, width, 116);
  text(slide, value, left + 18, top + 13, width - 36, 52, 38, accent, true);
  text(slide, label, left + 18, top + 73, width - 36, 26, 16, C.muted, false);
}

function bullet(slide, value, left, top, width, color = C.white, size = 18) {
  slide.shapes.add({ geometry: "ellipse", position: { left, top: top + 8, width: 8, height: 8 }, fill: C.cyan,
    line: { style: "solid", fill: "none", width: 0 } });
  text(slide, value, left + 18, top, width - 18, 54, size, color, false);
}

function cover(p) {
  const s = p.slides.add(); s.background.fill = C.ink;
  text(s, "UCAGENT / NUTSHELL CACHE", 68, 52, 420, 28, 14, C.cyan, true);
  text(s, "CacheSage-UC", 68, 132, 700, 78, 58, C.white, true);
  text(s, "真实 RTL 自动化验证与人工复核证据", 68, 218, 800, 54, 28, C.muted, false);
  metric(s, 68, 342, "34/36", "RTL 功能覆盖点", C.green, 252);
  metric(s, 340, 342, "199 / 0", "Scoreboard 比较 / 失败", C.cyan, 286);
  metric(s, 646, 342, "61.00%", "Verilator 代码覆盖率", C.amber, 280);
  metric(s, 946, 342, "421", "真实 DUT 事务", C.white, 252);
  text(s, "GitLink: python123/cachesage-uc    GitHub: python123-ops/CacheSage-UC", 68, 620, 900, 28, 16, C.muted);
  text(s, "2026-06-19", 1080, 620, 120, 28, 14, C.muted, true);
}

function architecture(p) {
  const s = p.slides.add(); base(s, "VERIFICATION ARCHITECTURE", "覆盖命中必须来自真实 DUT 可观察事件", 2);
  const names = [
    ["Generator / CRV", "directed + seeds 11/29/73"], ["SimpleBus Driver", "64-bit data / 8-bit mask"],
    ["Picker DUT", "NutShell Cache RTL"], ["Monitor", "response / memory / victim / probe"],
    ["Scoreboard", "独立 byte-mask reference"], ["Coverage", "36 points + source trace"]
  ];
  names.forEach((n, i) => { const x = 70 + (i % 3) * 400, y = 180 + Math.floor(i / 3) * 190; box(s, x, y, 330, 112);
    text(s, n[0], x + 20, y + 18, 290, 30, 21, C.white, true); text(s, n[1], x + 20, y + 58, 290, 32, 16, C.muted); });
  text(s, "驱动", 416, 224, 60, 22, 13, C.cyan, true); text(s, "观测", 816, 224, 60, 22, 13, C.cyan, true);
  text(s, "判定", 416, 414, 60, 22, 13, C.cyan, true); text(s, "归档", 816, 414, 60, 22, 13, C.cyan, true);
  box(s, 70, 592, 1130, 54, "#17263C", C.line);
  text(s, "未命中：rtl_input_backpressure、rtl_response_backpressure。保持缺口，不人工补点。", 92, 607, 1086, 26, 17, C.amber, true);
}

function linuxFlow(p) {
  const s = p.slides.add(); base(s, "LINUX EXECUTION", "Picker、Toffee、Verilator 已形成端到端实测链", 3, true);
  const steps = [["1", "锁定上游", "commit cdc9ef7"], ["2", "Picker export", "make gen_dut / exit 0"],
    ["3", "Toffee 回归", "directed + 3 seeds"], ["4", "证据导出", "JSON / FST / coverage.dat"]];
  steps.forEach((a, i) => { const x = 68 + i * 298; box(s, x, 190, 260, 136, "#FFFFFF", "#CBD5E1");
    text(s, a[0], x + 18, 205, 38, 42, 30, "#0891B2", true); text(s, a[1], x + 66, 207, 170, 32, 21, C.darkText, true);
    text(s, a[2], x + 22, 264, 216, 34, 16, "#64748B"); });
  metric(s, 68, 410, "24.04", "Ubuntu / WSL2 实测环境", "#0891B2", 270);
  metric(s, 358, 410, "1.47 s", "421 条 RTL 回归", "#16A34A", 250);
  metric(s, 628, 410, "219100 B", "FST 波形", "#D97706", 250);
  metric(s, 898, 410, "3621619 B", "coverage.dat", "#7C3AED", 300);
  text(s, "复现入口：python scripts/run_rtl_regression.py", 70, 584, 800, 34, 21, C.darkText, true);
}

function coverage(p) {
  const s = p.slides.add(); base(s, "MEASURED COVERAGE", "三类覆盖率分栏，含义与分母不混写", 4);
  s.charts.add("bar", { position: { left: 70, top: 178, width: 670, height: 390 },
    categories: ["Python functional", "RTL functional", "RTL code"],
    series: [{ name: "覆盖率", values: [100, 94.44, 61], fill: C.cyan }], hasLegend: false,
    dataLabels: { showValue: true, position: "outEnd" }, xAxis: { minimumScale: 0, maximumScale: 100 },
    yAxis: { majorGridlines: { style: "solid", fill: C.line, width: 1 } } });
  metric(s, 790, 180, "23/23", "Python harness", C.green, 390);
  metric(s, 790, 316, "34/36", "真实 RTL functional", C.cyan, 390);
  metric(s, 790, 452, "898/1454", "Verilator code coverage", C.amber, 390);
  text(s, "Scoreboard：199 次读数据比较，0 个失败", 790, 600, 390, 30, 18, C.white, true);
}

function scenarios(p) {
  const s = p.slides.add(); base(s, "SCENARIO MATRIX", "替换、写回和一致性均由总线事件闭环", 5, true);
  const rows = [
    ["数据路径", "read/write hit · miss/refill · read-after-write", "已覆盖"],
    ["写掩码", "full · low/high partial · sparse mask", "已覆盖"],
    ["替换策略", "4-way fill · clean/dirty eviction · victim onehot", "已覆盖"],
    ["一致性", "probe miss · clean/dirty hit · 8-beat data return", "已覆盖"],
    ["时序", "memory latency · reset recovery · io_empty", "已覆盖"],
    ["反压", "input wait · response wait", "2 点未覆盖"]
  ];
  rows.forEach((r, i) => { const y = 168 + i * 78; box(s, 68, y, 1130, 62, i === 5 ? "#FFF7ED" : "#FFFFFF", i === 5 ? "#F59E0B" : "#CBD5E1");
    text(s, r[0], 88, y + 16, 150, 30, 18, C.darkText, true); text(s, r[1], 252, y + 16, 700, 30, 17, "#475569");
    text(s, r[2], 986, y + 16, 184, 30, 17, i === 5 ? "#B45309" : "#15803D", true); });
}

function faults(p) {
  const s = p.slides.add(); base(s, "FAULT INJECTION", "5 类注入错误均触发确定性、可解释失败", 6);
  const rows = [["drop_dirty_writeback", "脏行未写回", "memory mismatch"], ["ignore_write_mask", "忽略字节掩码", "masked data mismatch"],
    ["stuck_replacement", "替换路固定", "victim memory mismatch"], ["refill_shift", "refill beat 偏移", "alignment mismatch"],
    ["unstable_under_stall", "stall 期间数据变化", "response mismatch"]];
  rows.forEach((r, i) => { const y = 170 + i * 88; box(s, 70, y, 1110, 66); text(s, r[0], 92, y + 17, 330, 28, 18, C.cyan, true);
    text(s, r[1], 438, y + 17, 300, 28, 18, C.white); text(s, r[2], 780, y + 17, 370, 28, 17, C.red, true); });
  text(s, "边界：这些结果证明验证环境能检错，不等同于确认真实 NutShell RTL 存在对应缺陷。", 72, 630, 1110, 30, 16, C.muted);
}

function collaboration(p) {
  const s = p.slides.add(); base(s, "UCAgent + HUMAN REVIEW", "草案速度由 UCAgent 提供，验证可信度由人工复核闭环", 7, true);
  const rows = [["RV-006", "参数沿用 Python 模型", "按 64-bit / 8-mask / 64B / 128-set / 4-way 重构"],
    ["RV-007", "smoke 被误当作功能覆盖", "36 点仅由真实 DUT 事件命中"],
    ["RV-008", "只做简单 read/write", "加入 memory、victim、coherence probe"],
    ["RV-009", "复用上游 block_write", "发现 data/size 位置参数错位，改用显式协议驱动"],
    ["RV-010", "通用 flush 假设", "读取 RTL 断言，改为合法 io_empty 观测"]];
  rows.forEach((r, i) => { const y = 166 + i * 94; text(s, r[0], 70, y + 18, 96, 28, 17, "#0891B2", true);
    box(s, 170, y, 420, 66, "#FFFFFF", "#CBD5E1"); text(s, r[1], 190, y + 18, 380, 30, 17, C.darkText);
    box(s, 620, y, 578, 66, i >= 3 ? "#ECFDF5" : "#F8FAFC", i >= 3 ? "#34D399" : "#CBD5E1");
    text(s, r[2], 642, y + 14, 530, 40, 16, C.darkText, i >= 3); });
}

function packageSlide(p) {
  const s = p.slides.add(); base(s, "REPRODUCIBLE PACKAGE", "报告、代码、记录和命令可以相互反查", 8);
  metric(s, 70, 170, "PDF", "13 页验证报告", C.green, 250); metric(s, 340, 170, "PPTX", "8 页答辩演示", C.cyan, 250);
  metric(s, 610, 170, "JSONL", "10 条协同记录", C.amber, 250); metric(s, 880, 170, "JSON", "逐覆盖点来源", C.white, 300);
  bullet(s, "python scripts/run_rtl_regression.py", 82, 360, 520, C.white, 20);
  bullet(s, "python -m unittest discover -s tests -v", 82, 430, 520, C.white, 20);
  bullet(s, "python scripts/build_verification_pdf.py", 82, 500, 520, C.white, 20);
  box(s, 650, 350, 530, 230, "#17263C", C.line);
  text(s, "仓库证据入口", 680, 374, 450, 30, 21, C.cyan, true);
  text(s, "reports/rtl-functional-coverage.json\ndocs/ucagent-collaboration.md\nintegration/nutshell/test_rtl_regression.py\nreview_journal.jsonl", 680, 424, 450, 128, 18, C.white);
  text(s, "未覆盖点与大型本地产物同样被明确记录。", 70, 632, 800, 28, 17, C.muted);
}

async function writeBlob(file, blob) { await fs.writeFile(file, new Uint8Array(await blob.arrayBuffer())); }

async function main() {
  await fs.mkdir(PREVIEW, { recursive: true }); await fs.mkdir(LAYOUT, { recursive: true });
  const p = Presentation.create({ slideSize: { width: 1280, height: 720 } });
  [cover, architecture, linuxFlow, coverage, scenarios, faults, collaboration, packageSlide].forEach(fn => fn(p));
  for (const [i, slide] of p.slides.items.entries()) {
    const stem = `slide-${String(i + 1).padStart(2, "0")}`;
    await writeBlob(path.join(PREVIEW, `${stem}.png`), await p.export({ slide, format: "png", scale: 1 }));
    await fs.writeFile(path.join(LAYOUT, `${stem}.json`), await (await slide.export({ format: "layout" })).text());
  }
  await writeBlob(path.join(WORK, "montage.webp"), await p.export({ format: "webp", montage: true, scale: 1 }));
  await (await PresentationFile.exportPptx(p)).save(OUT);
  console.log(JSON.stringify({ output: OUT, slides: p.slides.items.length, preview: PREVIEW }));
}

main().catch(error => { console.error(error); process.exitCode = 1; });
