const form = document.querySelector("#form");
const file = document.querySelector("#image");
const text = document.querySelector("#text");
const status = document.querySelector("#status");
let previewUrl;
let recordId = crypto.randomUUID();
form.addEventListener("input", () => { recordId = crypto.randomUUID(); });
function renderProgress(items) {
  const container = document.querySelector("#progress");
  container.replaceChildren();
  for (const item of items) {
    const row = document.createElement("div");
    row.className = "progress-item";
    const icon = document.createElement("span");
    icon.textContent = item.category === "연애" ? "♥" : item.icon;
    icon.style.color = item.color;
    icon.style.opacity = item.level ? String(0.4 + item.level * 0.2) : "0.15";
    icon.style.fontSize = (28 + item.level * 8) + "px";
    const label = document.createElement("span");
    label.textContent = item.category + " · " + item.count + "회 · Lv." + item.level;
    row.append(icon, label);
    container.append(row);
  }
}
fetch("/api/progress").then(r => { if (!r.ok) throw new Error(); return r.json(); })
  .then(data => renderProgress(data.progress))
  .catch(() => { document.querySelector("#progress").textContent = "누적 기록을 불러오지 못했어요. 새로고침해 주세요."; });
function clearPreview() {
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = undefined;
  document.querySelector("#preview").removeAttribute("src");
  document.querySelector("#preview-box").hidden = true;
}
file.addEventListener("change", () => {
  clearPreview();
  if (!file.files[0]) return;
  if (file.files[0].size > 10 * 1024 * 1024) {
    status.textContent = "이미지는 10MB 이하로 올려 주세요.";
    status.className = "error";
    file.value = "";
    return;
  }
  previewUrl = URL.createObjectURL(file.files[0]);
  document.querySelector("#preview").src = previewUrl;
  document.querySelector("#preview-box").hidden = false;
});
document.querySelector("#remove").addEventListener("click", () => {
  recordId = crypto.randomUUID();
  file.value = "";
  clearPreview();
});
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  status.className = "";
  document.querySelector("#result").hidden = true;
  if (!text.value.trim() && !file.files[0]) {
    status.textContent = "글 또는 이미지를 하나 이상 입력해 주세요.";
    status.className = "error";
    return;
  }
  const body = new FormData();
  body.append("record_id", recordId);
  body.append("text", text.value.trim());
  if (file.files[0]) body.append("image", file.files[0]);
  document.querySelector("#inputs").disabled = true;
  form.setAttribute("aria-busy", "true");
  status.textContent = "기록을 읽고 키워드를 찾고 있어요…";
  try {
    const response = await fetch("/api/keywords", { method: "POST", body, signal: AbortSignal.timeout(90000) });
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "입력 형식을 확인해 주세요.");
    const tags = document.querySelector("#keywords");
    tags.replaceChildren();
    for (const keyword of result.keywords) {
      const tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = "#" + keyword;
      tags.append(tag);
    }
    if (!result.keywords.length) tags.textContent = "뚜렷한 키워드를 찾지 못했어요.";
    document.querySelector("#summary").textContent = result.summary;
    document.querySelector("#category").textContent = result.category || "분류 보류";
    document.querySelector("#reason").textContent = result.category_reason;
    document.querySelector("#review").hidden = !result.needs_review;
    const effect = result.character_effect;
    document.querySelector("#evidence").textContent = "분류 근거 키워드: " + (result.category_keywords.join(", ") || "없음");
    document.querySelector("#effect-icon").textContent = effect ? effect.icon : "";
    document.querySelector("#effect-icon").setAttribute("aria-label", effect ? effect.name : "효과 없음");
    document.querySelector("#effect-name").textContent = result.awarded ? result.category + " +1 누적!" : (effect ? "이미 반영된 기록입니다. 중복으로 누적하지 않았어요." : "분류를 확정할 수 없어 누적하지 않았어요.");
    renderProgress(result.progress);
    document.querySelector("#result").hidden = false;
    status.textContent = "분석이 완료되었어요.";
  } catch (error) {
    status.className = "error";
    status.textContent = error.name === "TimeoutError" ? "응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요." : (error instanceof TypeError ? "서버 연결을 확인하고 다시 시도해 주세요." : error.message);
  } finally {
    document.querySelector("#inputs").disabled = false;
    form.setAttribute("aria-busy", "false");
  }
});
