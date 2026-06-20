import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

async function loadArtifactTool() {
  if (process.env.CODEX_NODE_MODULES) {
    const modulePath = path.join(
      process.env.CODEX_NODE_MODULES,
      "@oai", "artifact-tool", "dist", "artifact_tool.mjs",
    );
    return import(pathToFileURL(modulePath).href);
  }
  return import("@oai/artifact-tool");
}

const { Presentation, PresentationFile } = await loadArtifactTool();

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROOT, "reports", "CacheSage-UC-defense-demo-NSFC.pptx");
const WORK = process.env.CACHESAGE_PPT_WORK || path.join(process.env.TEMP || ".", "cachesage-ppt-nsfc");
const PREVIEW = path.join(WORK, "preview");
const LAYOUT = path.join(WORK, "layout");
const BACKGROUND = path.join(ROOT, "assets", "defense-background.png");

const rtl = JSON.parse(await fs.readFile(path.join(ROOT, "reports", "rtl-functional-coverage.json"), "utf8"));
const py = JSON.parse(await fs.readFile(path.join(ROOT, "reports", "sample-run-seed11.json"), "utf8"));
const reviewRows = (await fs.readFile(path.join(ROOT, "review_journal.jsonl"), "utf8"))
  .split(/\r?\n/).filter(Boolean).map(line => JSON.parse(line));
const bgBytes = await readImageBlob(BACKGROUND);

const codeSummary = rtl.artifacts.rtl_code_coverage.summary;
const failures = rtl.scoreboard.failures.length;
const uncovered = rtl.coverpoints.filter(point => !point.covered).map(point => point.id);
const FONT = "Microsoft YaHei";
const MONO = "Cascadia Mono";
const C = {
  navy: "#061A3A", deep: "#0B2452", blue: "#145DA0", cyan: "#23C8E8",
  teal: "#18B7A0", green: "#42D392", gold: "#F4BE4F", orange: "#F18F4B",
  red: "#F46D75", white: "#FFFFFF", paper: "#F4F8FD", ink: "#10233F",
  muted: "#AFC4DF", pale: "#DDE9F6", line: "#5B83B8",
};

async function readImageBlob(imagePath) {
  const bytes = await fs.readFile(imagePath);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

function shape(slide, geometry, left, top, width, height, fill = "none", line = "none", radius = undefined) {
  return slide.shapes.add({
    geometry,
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: line, width: line === "none" ? 0 : 1 },
    ...(radius ? { borderRadius: radius } : {}),
  });
}

function text(slide, value, left, top, width, height, size = 18, color = C.white, bold = false, align = "left", font = FONT) {
  const item = shape(slide, "textbox", left, top, width, height);
  item.text = String(value);
  item.text.style = { fontSize: size, color, bold, typeface: font, alignment: align };
  return item;
}

function rule(slide, left, top, width, height = 2, fill = C.cyan) {
  return shape(slide, "rect", left, top, width, height, fill);
}

function addBackground(slide, shade = 52) {
  slide.images.add({
    blob: bgBytes,
    contentType: "image/png",
    alt: "蓝色建筑仰视背景",
    fit: "cover",
    position: { left: 0, top: 0, width: 1280, height: 720 },
  });
  shape(slide, "rect", 0, 0, 1280, 720, `${C.navy}/${shade}`);
}

function addChrome(slide, section, title, page, options = {}) {
  const { shade = 58, titleSize = 34, subtitle = "" } = options;
  addBackground(slide, shade);
  text(slide, section, 68, 34, 300, 24, 13, C.cyan, true);
  text(slide, title, 68, 70, 1080, 52, titleSize, C.white, true);
  rule(slide, 68, 137, 1144, 2, "#7ECBE0/70");
  if (subtitle) text(slide, subtitle, 70, 145, 1030, 28, 16, C.pale);
  text(slide, String(page).padStart(2, "0"), 1160, 674, 52, 20, 12, C.pale, true, "right");
  text(slide, "CacheSage-UC · NutShell Cache 自动化验证", 68, 674, 520, 20, 12, C.muted);
}

function panel(slide, left, top, width, height, options = {}) {
  const { fill = "#F7FAFE/94", line = "#A9C7E5/75", radius = "rounded-sm" } = options;
  return shape(slide, "roundRect", left, top, width, height, fill, line, radius);
}

function darkPanel(slide, left, top, width, height, options = {}) {
  const { fill = "#081D43/88", line = "#6EA4D2/55" } = options;
  return panel(slide, left, top, width, height, { fill, line });
}

function label(slide, value, left, top, width, color = C.cyan) {
  rule(slide, left, top + 3, 4, 24, color);
  text(slide, value, left + 14, top, width - 14, 30, 18, C.ink, true);
}

function metric(slide, left, top, width, value, title, color = C.cyan, dark = true) {
  const p = dark ? darkPanel(slide, left, top, width, 112) : panel(slide, left, top, width, 112);
  text(slide, value, left + 18, top + 14, width - 36, 44, 34, color, true);
  text(slide, title, left + 18, top + 68, width - 36, 28, 15, dark ? C.pale : "#47627F");
  return p;
}

function smallTag(slide, value, left, top, width, color = C.teal) {
  panel(slide, left, top, width, 30, { fill: `${color}/16`, line: `${color}/65` });
  text(slide, value, left + 8, top + 5, width - 16, 20, 13, color, true, "center");
}

function arrow(slide, left, top, width, height, color = C.cyan) {
  shape(slide, "rightArrow", left, top, width, height, `${color}/75`, "none");
}

function cover(p) {
  const s = p.slides.add(); addBackground(s, 47);
  text(s, "UCAgent · NutShell Cache 验证赛题", 72, 52, 600, 28, 16, C.cyan, true);
  rule(s, 72, 96, 110, 4, C.gold);
  text(s, "CacheSage-UC", 72, 145, 760, 76, 54, C.white, true);
  text(s, "面向真实 RTL 的自动化验证与人工复核闭环", 74, 232, 860, 46, 28, C.pale, false);
  text(s, "从可运行原型走向可度量、可复核、可复现的 Cache 验证证据链", 74, 292, 900, 34, 18, C.muted);
  const values = [
    [`${rtl.coverage.covered}/${rtl.coverage.total}`, "真实 RTL 功能覆盖点", C.green],
    [`${rtl.scoreboard.comparisons} / ${failures}`, "Scoreboard 比较 / 失败", C.cyan],
    [`${codeSummary.percent.toFixed(2)}%`, "Verilator 代码覆盖率", C.gold],
    [String(rtl.run.transactions), "真实 DUT 事务", C.white],
  ];
  values.forEach((item, i) => metric(s, 72 + i * 285, 395, 260, item[0], item[1], item[2]));
  text(s, "GitLink · python123/cachesage-uc", 74, 642, 420, 22, 14, C.muted);
  text(s, "GitHub · python123-ops/CacheSage-UC", 500, 642, 450, 22, 14, C.muted);
  text(s, "2026", 1138, 642, 70, 22, 14, C.pale, true, "right");
}

function rationale(p) {
  const s = p.slides.add(); addChrome(s, "01 立项依据", "Cache 验证的难点不在激励数量，而在结果是否可信", 2,
    { subtitle: "真实 RTL、独立判定与可追溯证据必须同时成立" });
  panel(s, 68, 195, 430, 408, { fill: "#F7FAFE/95" });
  label(s, "研究对象", 94, 222, 220);
  text(s, "NutShell Cache", 94, 267, 350, 42, 30, C.ink, true);
  text(s, "64-bit 数据通路\n8-bit byte mask\n64-byte cache line\n128 sets · 4 ways", 96, 330, 330, 170, 21, "#395775", false);
  smallTag(s, "replacement", 94, 532, 122, C.blue);
  smallTag(s, "coherence", 228, 532, 112, C.teal);
  smallTag(s, "stall / reset", 352, 532, 116, C.orange);
  const drivers = [
    ["场景复杂", "hit / miss、mask、替换、写回与 probe 交织", C.cyan],
    ["模型同源", "DUT 与参考模型复用同一路径时可能同步出错", C.gold],
    ["证据割裂", "smoke、功能覆盖和代码覆盖若混写便失去解释力", C.green],
  ];
  drivers.forEach((d, i) => {
    const y = 196 + i * 136;
    darkPanel(s, 542, y, 668, 112);
    text(s, `0${i + 1}`, 566, y + 22, 54, 44, 26, d[2], true);
    text(s, d[0], 632, y + 17, 150, 32, 21, C.white, true);
    text(s, d[1], 632, y + 54, 540, 36, 17, C.pale);
  });
  text(s, "研究判断：覆盖率必须绑定真实 DUT 可观察事件，并由独立 Scoreboard 给出可解释结论。",
    544, 616, 660, 34, 18, C.white, true);
}

function problem(p) {
  const s = p.slides.add(); addChrome(s, "01 立项依据", "从“跑通 smoke”到“形成可信验证闭环”仍有三道门槛", 3);
  arrow(s, 376, 319, 70, 34, C.cyan); arrow(s, 806, 319, 70, 34, C.cyan);
  const cols = [
    ["激励可达", "约束随机必须打到\n同 set 压力、dirty victim、\nmask 组合与一致性 probe", "Generator / CRV", C.cyan],
    ["判定独立", "不能让驱动错误同时污染\nDUT 与 reference model，\n需独立 byte-mask 语义", "Reference / Scoreboard", C.gold],
    ["证据可审计", "每个覆盖点要能反查\nseed、事务、总线事件、\n波形和人工修正记录", "Coverage / Journal", C.green],
  ];
  cols.forEach((c, i) => {
    const x = 68 + i * 430;
    panel(s, x, 205, 360, 360, { fill: "#F8FBFF/95" });
    text(s, `0${i + 1}`, x + 24, 226, 60, 42, 27, c[3], true);
    text(s, c[0], x + 24, 283, 300, 38, 25, C.ink, true);
    rule(s, x + 24, 337, 78, 3, c[3]);
    text(s, c[1], x + 24, 366, 310, 116, 18, "#425E7B");
    smallTag(s, c[2], x + 24, 510, 300, c[3]);
  });
  darkPanel(s, 68, 590, 1144, 58, { fill: "#071A3D/92" });
  text(s, "本项目的核心不是增加一套测试脚本，而是把激励、判定、覆盖与复核组织成同一证据链。",
    92, 606, 1096, 28, 18, C.white, true, "center");
}

function contributions(p) {
  const s = p.slides.add(); addChrome(s, "02 研究方案", "三项人工定制把通用原型改造成真实 RTL 验证系统", 4);
  const items = [
    ["协议参数重构", "按真实 DUT 固定 64-bit data、8-bit mask、64B line、128 sets、4 ways", "避免 Python 快速模型参数污染 RTL 场景", C.cyan],
    ["独立判定链路", "显式构造 SimpleBus 请求，独立 Reference Memory 按 byte mask 更新", "消除驱动与参考模型同源漏检", C.gold],
    ["事件化覆盖模型", "36 个覆盖点只由 response、memory、victim、probe 等真实事件命中", "覆盖率具备来源、分母和失败门槛", C.green],
  ];
  items.forEach((item, i) => {
    const y = 190 + i * 140;
    panel(s, 68, y, 1144, 116, { fill: "#F8FBFF/95" });
    text(s, `贡献 ${i + 1}`, 92, y + 16, 104, 24, 14, item[3], true);
    text(s, item[0], 92, y + 48, 230, 36, 23, C.ink, true);
    rule(s, 338, y + 20, 2, 76, "#B7CCE3");
    text(s, item[1], 368, y + 18, 500, 70, 17, "#3D5B79");
    panel(s, 890, y + 18, 292, 78, { fill: `${item[3]}/12`, line: `${item[3]}/55` });
    text(s, item[2], 910, y + 30, 252, 52, 16, C.ink, true);
  });
  text(s, "完成标准", 72, 626, 100, 24, 15, C.cyan, true);
  text(s, "RTL functional coverage ≥ 90% 且 Scoreboard failure = 0", 190, 622, 650, 30, 19, C.white, true);
}

function architecture(p) {
  const s = p.slides.add(); addChrome(s, "02 研究方案", "端到端链路将激励、RTL 行为与判定证据闭环", 5);
  const xs = [72, 264, 456, 648, 840, 1032];
  for (let i = 0; i < xs.length - 1; i++) arrow(s, xs[i] + 150, 279, 42, 28, i < 2 ? C.cyan : C.teal);
  const nodes = [
    ["Generator", "directed + CRV\nseed 11 / 29 / 73", C.cyan],
    ["SimpleBus Driver", "address · size · cmd\nmask · data", C.cyan],
    ["Picker DUT", "NutShell Cache RTL\nVerilator", C.gold],
    ["Monitor", "response · memory\nvictim · probe", C.teal],
    ["Scoreboard", "独立 byte-mask\nreference", C.green],
    ["Coverage", "36 points\nsource trace", C.green],
  ];
  nodes.forEach((n, i) => {
    darkPanel(s, xs[i], 228, 160, 132, { fill: "#071C42/92", line: `${n[2]}/70` });
    text(s, n[0], xs[i] + 12, 248, 136, 28, 18, C.white, true, "center");
    rule(s, xs[i] + 48, 286, 64, 3, n[2]);
    text(s, n[1], xs[i] + 10, 305, 140, 45, 13, C.pale, false, "center");
  });
  panel(s, 72, 412, 746, 184, { fill: "#F7FAFE/95" });
  label(s, "可观察事件", 96, 434, 180);
  const events = ["read / write", "refill", "writeback", "victim way", "coherence probe", "io_empty"];
  events.forEach((event, i) => smallTag(s, event, 96 + (i % 3) * 228, 486 + Math.floor(i / 3) * 52, 205,
    [C.blue, C.cyan, C.orange, C.gold, C.teal, C.green][i]));
  darkPanel(s, 850, 412, 342, 184, { fill: "#071C42/94" });
  text(s, "判定门槛", 878, 436, 250, 30, 19, C.cyan, true);
  text(s, `覆盖点 ≥ 33 / 36\nScoreboard failure = 0\n每个命中保留 source trace`, 878, 486, 282, 92, 18, C.white, true);
}

function scenarios(p) {
  const s = p.slides.add(); addChrome(s, "02 研究方案", "场景矩阵同时覆盖数据、替换、一致性与时序风险", 6);
  const rows = [
    ["数据路径", "read/write hit · miss/refill · read-after-write", "5 类", C.cyan],
    ["写掩码", "full · low/high partial · sparse mask", "4 类", C.blue],
    ["替换策略", "4-way fill · same-set pressure · clean/dirty eviction", "9 类", C.gold],
    ["一致性", "probe miss · clean/dirty hit · data return · reaccess", "7 类", C.teal],
    ["时序控制", "memory latency · reset recovery · io_empty · backpressure", "11 类", C.green],
  ];
  panel(s, 68, 188, 830, 430, { fill: "#F7FAFE/96" });
  rows.forEach((row, i) => {
    const y = 212 + i * 76;
    text(s, row[0], 94, y + 10, 120, 28, 18, C.ink, true);
    rule(s, 222, y + 14, 3, 24, row[3]);
    text(s, row[1], 244, y + 9, 500, 32, 16, "#45627F");
    smallTag(s, row[2], 770, y + 7, 92, row[3]);
    if (i < rows.length - 1) rule(s, 94, y + 56, 768, 1, "#C8D8E9");
  });
  darkPanel(s, 932, 188, 280, 274, { fill: "#071C42/94" });
  text(s, "真实 RTL 覆盖", 958, 218, 228, 28, 18, C.pale, true, "center");
  text(s, `${rtl.coverage.covered}/${rtl.coverage.total}`, 958, 270, 228, 72, 50, C.green, true, "center");
  text(s, `${rtl.coverage.percent.toFixed(2)}%`, 958, 346, 228, 42, 28, C.cyan, true, "center");
  text(s, "门槛：33/36", 958, 406, 228, 24, 15, C.muted, false, "center");
  panel(s, 932, 484, 280, 134, { fill: "#FFF8E8/96", line: "#F4BE4F/80" });
  text(s, "保留真实缺口", 956, 504, 230, 26, 17, "#9A6410", true);
  text(s, uncovered.join("\n"), 956, 542, 230, 60, 14, "#7C5A20", false, "left", MONO);
}

function linuxFlow(p) {
  const s = p.slides.add(); addChrome(s, "03 实测结果", "Linux 工具链已经完成 Picker—Toffee—Verilator 实测闭环", 7);
  darkPanel(s, 68, 190, 626, 394, { fill: "#04152F/95", line: "#6EA4D2/65" });
  text(s, "Ubuntu 24.04 / WSL2", 92, 212, 340, 28, 16, C.cyan, true, "left", MONO);
  const commands = [
    "$ make gen_dut",
    "[100%] Built target UT_Cache",
    "$ python scripts/run_rtl_regression.py",
    "directed-complete transactions=16",
    "seed-11/29/73 progress=128/128",
    "PASSED  RTL 34/36  Scoreboard 0",
  ];
  commands.forEach((line, i) => text(s, line, 92, 262 + i * 42, 570, 28, 16,
    i === 5 ? C.green : (i === 1 ? C.gold : C.pale), i === 5, "left", MONO));
  const steps = [
    ["01", "锁定上游", "commit cdc9ef7", C.blue],
    ["02", "Picker export", "DUT + FST + coverage", C.cyan],
    ["03", "Toffee 回归", "directed + 3 seeds", C.teal],
    ["04", "证据导出", "JSON / Markdown / manifest", C.green],
  ];
  steps.forEach((step, i) => {
    const y = 190 + i * 100;
    panel(s, 738, y, 474, 78, { fill: "#F7FAFE/96" });
    text(s, step[0], 760, y + 17, 48, 34, 22, step[3], true);
    text(s, step[1], 824, y + 13, 170, 28, 18, C.ink, true);
    text(s, step[2], 824, y + 43, 340, 22, 14, "#4C6884");
    if (i < steps.length - 1) rule(s, 782, y + 78, 2, 22, `${step[3]}/65`);
  });
  text(s, `真实 DUT 事务 ${rtl.run.transactions} 条`, 742, 610, 230, 28, 18, C.white, true);
  text(s, "构建与测试均 exit 0", 984, 610, 224, 28, 18, C.green, true, "right");
}

function coverage(p) {
  const s = p.slides.add(); addChrome(s, "03 实测结果", "三类覆盖率分栏度量，功能覆盖与代码覆盖不混写", 8);
  panel(s, 68, 188, 742, 414, { fill: "#F7FAFE/96" });
  s.charts.add("bar", {
    position: { left: 104, top: 236, width: 666, height: 312 },
    categories: ["Python functional", "RTL functional", "RTL code"],
    series: [{ name: "覆盖率", values: [py.coverage.percent, rtl.coverage.percent, codeSummary.percent], fill: C.blue }],
    hasLegend: false,
    dataLabels: { showValue: true, position: "outEnd" },
    xAxis: { minimumScale: 0, maximumScale: 100 },
    yAxis: { majorGridlines: { style: "solid", fill: "#D5E2EF", width: 1 } },
  });
  metric(s, 850, 188, 362, `${py.coverage.covered}/${py.coverage.total}`, "Python harness functional coverage", C.green);
  metric(s, 850, 318, 362, `${rtl.coverage.covered}/${rtl.coverage.total}`, "真实 RTL functional coverage", C.cyan);
  metric(s, 850, 448, 362, `${codeSummary.covered_points}/${codeSummary.total_points}`, "Verilator code coverage", C.gold);
  darkPanel(s, 68, 620, 1144, 42, { fill: "#071A3D/92" });
  text(s, `Scoreboard：${rtl.scoreboard.comparisons} 次独立比较，${failures} 个失败；功能覆盖达成门槛并保留 ${uncovered.length} 个未命中点。`,
    88, 630, 1104, 24, 16, C.white, true, "center");
}

function faults(p) {
  const s = p.slides.add(); addChrome(s, "03 实测结果", "故障注入用于证明验证环境能检错，而不是制造漂亮数字", 9);
  const rows = [
    ["drop_dirty_writeback", "脏行未写回", "final memory mismatch", C.red],
    ["ignore_write_mask", "忽略 byte mask", "masked data mismatch", C.orange],
    ["stuck_replacement", "替换状态停滞", "victim memory mismatch", C.gold],
    ["refill_shift", "refill beat 偏移", "alignment mismatch", C.cyan],
    ["unstable_under_stall", "stall 期间不稳定", "response mismatch", C.teal],
  ];
  panel(s, 68, 188, 850, 414, { fill: "#F7FAFE/96" });
  text(s, "故障模式", 94, 208, 280, 24, 15, "#5A7694", true);
  text(s, "注入行为", 400, 208, 210, 24, 15, "#5A7694", true);
  text(s, "确定性判定", 650, 208, 230, 24, 15, "#5A7694", true);
  rows.forEach((row, i) => {
    const y = 246 + i * 66;
    text(s, row[0], 94, y + 12, 286, 26, 15, C.ink, true, "left", MONO);
    text(s, row[1], 400, y + 12, 220, 26, 16, "#46627F");
    smallTag(s, row[2], 646, y + 7, 236, row[3]);
    if (i < rows.length - 1) rule(s, 94, y + 54, 788, 1, "#CDDCEB");
  });
  darkPanel(s, 952, 188, 260, 252, { fill: "#071C42/94" });
  text(s, "5 / 5", 976, 222, 212, 66, 46, C.green, true, "center");
  text(s, "注入故障均被检出", 976, 298, 212, 30, 17, C.pale, true, "center");
  rule(s, 1004, 350, 156, 3, C.gold);
  text(s, "deterministic seed\n可重放失败摘要\n关联 artifact", 976, 374, 212, 74, 15, C.white, false, "center");
  panel(s, 952, 468, 260, 134, { fill: "#FFF8E8/96", line: "#F4BE4F/75" });
  text(s, "证据边界", 976, 488, 210, 26, 17, "#9A6410", true);
  text(s, "不声称真实 NutShell RTL\n存在对应缺陷", 976, 530, 210, 52, 16, "#725329", true);
}

function collaboration(p) {
  const s = p.slides.add(); addChrome(s, "04 协同复核", "UCAgent 提供构建速度，人工复核决定验证结论是否可信", 10);
  const cases = [
    ["RV-006", "参数重构", "32-bit 快速模型不能直接映射真实 DUT", C.blue],
    ["RV-007", "证据纠偏", "smoke 通过不能替代 RTL functional coverage", C.cyan],
    ["RV-008", "场景扩展", "加入 victim、memory 与 coherence probe", C.teal],
    ["RV-009", "驱动重写", "发现 data / size 位置参数错位与同源漏检", C.gold],
    ["RV-010", "约束修正", "读取 RTL 断言，移除 DCache 非法 flush", C.green],
  ];
  rule(s, 114, 274, 1010, 4, "#85B6D9/80");
  cases.forEach((item, i) => {
    const x = 78 + i * 228;
    shape(s, "ellipse", x + 84, 254, 38, 38, item[3], C.white);
    text(s, String(i + 1), x + 91, 261, 24, 22, 14, C.navy, true, "center");
    darkPanel(s, x, 316, 206, 200, { fill: "#071C42/93", line: `${item[3]}/70` });
    text(s, item[0], x + 16, 334, 80, 22, 14, item[3], true, "left", MONO);
    text(s, item[1], x + 16, 370, 170, 30, 19, C.white, true);
    rule(s, x + 16, 412, 58, 3, item[3]);
    text(s, item[2], x + 16, 434, 174, 66, 14, C.pale);
  });
  panel(s, 68, 550, 1144, 86, { fill: "#F7FAFE/96" });
  label(s, "记录结构", 92, 568, 130);
  text(s, `共 ${reviewRows.length} 条记录：草案摘要 → 人工发现 → 风险判断 → 代码修正 → 指标变化 → 命令与产物`,
    230, 566, 946, 34, 17, C.ink, true);
  text(s, "重建记录与同步记录明确区分，避免事后包装成实时发现。", 230, 602, 946, 24, 15, "#56718D");
}

function reproducibility(p) {
  const s = p.slides.add(); addChrome(s, "04 工程基础", "代码、报告、覆盖率与复核记录可以双向反查", 11);
  const chain = [
    ["源代码", "src/ · integration/", C.blue], ["运行证据", "JSON · FST · coverage.dat", C.cyan],
    ["复核记录", "review_journal.jsonl", C.gold], ["正式材料", "PDF · PPTX", C.green],
  ];
  for (let i = 0; i < 3; i++) arrow(s, 322 + i * 290, 270, 50, 30, chain[i][2]);
  chain.forEach((item, i) => {
    const x = 68 + i * 290;
    darkPanel(s, x, 222, 254, 126, { fill: "#071C42/93", line: `${item[2]}/70` });
    text(s, item[0], x + 18, 244, 218, 30, 20, C.white, true, "center");
    rule(s, x + 78, 286, 98, 3, item[2]);
    text(s, item[1], x + 16, 306, 222, 26, 14, C.pale, false, "center", MONO);
  });
  panel(s, 68, 398, 546, 218, { fill: "#F7FAFE/96" });
  label(s, "复现命令", 94, 420, 160);
  text(s, "$ python scripts/run_rtl_regression.py\n$ python -m unittest discover -s tests -v\n$ python scripts/build_verification_pdf.py",
    94, 468, 486, 112, 16, C.ink, false, "left", MONO);
  panel(s, 650, 398, 562, 218, { fill: "#F7FAFE/96" });
  label(s, "交付完整性", 676, 420, 180);
  const deliverables = ["Apache-2.0 license", "锁定 upstream commit", "全量自动化测试", "双远端同步"];
  deliverables.forEach((item, i) => {
    shape(s, "ellipse", 680 + (i % 2) * 250, 476 + Math.floor(i / 2) * 58, 12, 12, C.green);
    text(s, item, 702 + (i % 2) * 250, 468 + Math.floor(i / 2) * 58, 216, 28, 15, C.ink, true);
  });
}

function conclusion(p) {
  const s = p.slides.add(); addBackground(s, 49);
  text(s, "05 总结", 72, 44, 200, 24, 14, C.cyan, true);
  text(s, "CacheSage-UC 已形成真实 RTL 驱动、独立判定与人工复核闭环", 72, 92, 1090, 62, 36, C.white, true);
  text(s, "阶段结果由可复现命令和仓库证据支撑，未覆盖点与证据边界同样公开。", 74, 165, 980, 34, 18, C.pale);
  const cards = [
    [`${rtl.coverage.covered}/${rtl.coverage.total}`, "RTL 功能覆盖点", `达到 ${rtl.coverage.percent.toFixed(2)}%`, C.green],
    [String(rtl.scoreboard.comparisons), "独立 Scoreboard 比较", `${failures} 个失败`, C.cyan],
    [String(rtl.run.transactions), "真实 DUT 事务", "directed + seeds 11/29/73", C.gold],
  ];
  cards.forEach((item, i) => {
    const x = 72 + i * 382;
    darkPanel(s, x, 270, 350, 196, { fill: "#071C42/92", line: `${item[3]}/75` });
    text(s, item[0], x + 24, 296, 302, 64, 46, item[3], true, "center");
    text(s, item[1], x + 24, 372, 302, 30, 18, C.white, true, "center");
    text(s, item[2], x + 24, 420, 302, 24, 15, C.muted, false, "center");
  });
  darkPanel(s, 72, 512, 1132, 88, { fill: "#071A3D/93" });
  text(s, "验证边界", 96, 532, 110, 28, 17, C.gold, true);
  text(s, `${uncovered.join("、")} 尚未命中；注入故障仅证明环境检错能力，不代表真实 RTL 缺陷。`,
    218, 528, 956, 38, 16, C.white, true);
  text(s, "谢谢", 72, 640, 180, 32, 22, C.white, true);
  text(s, "CacheSage-UC · 可度量、可复核、可复现", 760, 642, 444, 24, 15, C.pale, false, "right");
}

async function writeBlob(file, blob) {
  await fs.writeFile(file, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await fs.mkdir(PREVIEW, { recursive: true });
  await fs.mkdir(LAYOUT, { recursive: true });
  const p = Presentation.create({ slideSize: { width: 1280, height: 720 } });
  [cover, rationale, problem, contributions, architecture, scenarios, linuxFlow, coverage, faults,
    collaboration, reproducibility, conclusion].forEach(fn => fn(p));

  for (const [i, slide] of p.slides.items.entries()) {
    const stem = `slide-${String(i + 1).padStart(2, "0")}`;
    await writeBlob(path.join(PREVIEW, `${stem}.png`), await p.export({ slide, format: "png", scale: 1 }));
    await fs.writeFile(path.join(LAYOUT, `${stem}.json`), await (await slide.export({ format: "layout" })).text());
  }
  await writeBlob(path.join(WORK, "montage.webp"), await p.export({ format: "webp", montage: true, scale: 1 }));
  await (await PresentationFile.exportPptx(p)).save(OUT);
  console.log(JSON.stringify({ output: OUT, slides: p.slides.items.length, preview: PREVIEW, montage: path.join(WORK, "montage.webp") }));
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
