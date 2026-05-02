const ui = {
  actionForm: document.getElementById("accountActionForm"),
  actionSelect: document.getElementById("accountAction"),
  addFields: document.getElementById("addFields"),
  deleteFields: document.getElementById("deleteFields"),
  submitActionBtn: document.getElementById("submitActionBtn"),
  actionMessage: document.getElementById("actionMessage"),
  manageTotalBalance: document.getElementById("manageTotalBalance"),
  manageAccountsList: document.getElementById("manageAccountsList"),
  manageHistoryList: document.getElementById("manageHistoryList"),
  newAccountName: document.getElementById("newAccountName"),
  newStartingBalance: document.getElementById("newStartingBalance"),
  newAccountNote: document.getElementById("newAccountNote"),
  deleteAccountId: document.getElementById("deleteAccountId"),
  deleteReason: document.getElementById("deleteReason"),
  deleteConfirm: document.getElementById("deleteConfirm"),
};

function formatMoney(value) {
  const parsed = Number.parseFloat(String(value ?? "0"));
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(Number.isFinite(parsed) ? parsed : 0);
}

function formatDateTime(value) {
  if (!value) {
    return "Unknown time";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Unknown time";
  }

  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}

function normalizeMoneyInput(value, { allowNegative = false } = {}) {
  const hasLeadingMinus = allowNegative && value.trimStart().startsWith("-");
  const cleaned = value.replace(/[^\d.]/g, "");
  const [whole, ...decimalParts] = cleaned.split(".");
  const decimals = decimalParts.join("").slice(0, 2);
  const unsigned = decimalParts.length ? `${whole}.${decimals}` : whole;
  return `${hasLeadingMinus ? "-" : ""}${unsigned}`;
}

function parseMoney(value, { allowNegative = false } = {}) {
  const trimmed = value.trim();
  const pattern = allowNegative ? /^-?\d+(\.\d{1,2})?$/ : /^\d+(\.\d{1,2})?$/;
  if (!pattern.test(trimmed)) {
    return Number.NaN;
  }

  return Number.parseFloat(trimmed);
}

function clearChildren(node) {
  while (node.firstChild) {
    node.removeChild(node.firstChild);
  }
}

function csrfHeaders() {
  const token = document.querySelector('meta[name="csrf-token"]')?.content || "";
  return token ? { "X-CSRF-Token": token } : {};
}

async function toJson(response) {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.error || "Request failed");
  }
  return body;
}

function showMessage(text, type = "") {
  ui.actionMessage.textContent = text;
  ui.actionMessage.classList.remove("success", "error");
  if (type) {
    ui.actionMessage.classList.add(type);
  }
}

function listItem(title, value, detail) {
  const li = document.createElement("li");

  const top = document.createElement("div");
  top.className = "item-top";

  const strong = document.createElement("strong");
  strong.textContent = title;

  const amount = document.createElement("span");
  amount.textContent = value;

  top.appendChild(strong);
  top.appendChild(amount);

  const sub = document.createElement("div");
  sub.className = "item-sub";
  sub.textContent = detail;

  li.appendChild(top);
  li.appendChild(sub);
  return li;
}

function renderAccountSummaries(summary) {
  clearChildren(ui.manageAccountsList);
  clearChildren(ui.deleteAccountId);

  ui.manageTotalBalance.textContent = formatMoney(summary.total_balance);

  const accounts = summary.accounts || [];
  if (!accounts.length) {
    const empty = document.createElement("li");
    empty.textContent = "No accounts available.";
    ui.manageAccountsList.appendChild(empty);

    const option = document.createElement("option");
    option.textContent = "No account available";
    option.value = "";
    ui.deleteAccountId.appendChild(option);
    return;
  }

  for (const account of accounts) {
    const details = `Starting Balance: ${formatMoney(account.starting_balance)}`;
    ui.manageAccountsList.appendChild(listItem(account.name, formatMoney(account.current_balance), details));

    const option = document.createElement("option");
    option.value = String(account.id);
    option.textContent = `${account.name} (${formatMoney(account.current_balance)})`;
    ui.deleteAccountId.appendChild(option);
  }
}

function renderHistory(eventsPayload) {
  clearChildren(ui.manageHistoryList);

  const events = eventsPayload.events || [];
  if (!events.length) {
    const empty = document.createElement("li");
    empty.textContent = "No account activity logged yet.";
    ui.manageHistoryList.appendChild(empty);
    return;
  }

  for (const event of events) {
    const title = `${event.account_name} ${event.action}`;
    const notePart = event.note ? ` · ${event.note}` : "";
    const detail = `${formatDateTime(event.created_at)}${notePart}`;
    ui.manageHistoryList.appendChild(listItem(title, formatMoney(event.account_balance), detail));
  }
}

function syncActionView() {
  const isCreate = ui.actionSelect.value === "create";

  ui.addFields.classList.toggle("hidden", !isCreate);
  ui.deleteFields.classList.toggle("hidden", isCreate);
  ui.submitActionBtn.textContent = isCreate ? "Create Account" : "Delete Account";
}

function payloadForCreate() {
  const name = ui.newAccountName.value.trim();
  const startingBalance = parseMoney(ui.newStartingBalance.value, { allowNegative: true });
  const note = ui.newAccountNote.value.trim();

  if (!name) {
    throw new Error("Account name is required.");
  }
  if (!Number.isFinite(startingBalance)) {
    throw new Error("Starting balance must be a valid number.");
  }

  return {
    name,
    starting_balance: startingBalance.toFixed(2),
    note,
  };
}

function payloadForDelete() {
  const accountId = Number.parseInt(ui.deleteAccountId.value, 10);
  const reason = ui.deleteReason.value.trim();

  if (!Number.isInteger(accountId) || accountId < 1) {
    throw new Error("Choose an account to delete.");
  }
  if (!ui.deleteConfirm.checked) {
    throw new Error("Confirm deletion before continuing.");
  }

  return {
    accountId,
    body: {
      confirm: true,
      reason,
    },
  };
}

async function loadPageData() {
  const [summaryResult, historyResult] = await Promise.allSettled([
    fetch("/api/accounts/summary").then(toJson),
    fetch("/api/accounts/history?limit=50").then(toJson),
  ]);

  if (summaryResult.status === "fulfilled") {
    renderAccountSummaries(summaryResult.value);
  } else {
    throw summaryResult.reason;
  }

  if (historyResult.status === "fulfilled") {
    renderHistory(historyResult.value);
  } else {
    renderHistory({ events: [] });
  }
}

async function handleSubmit(event) {
  event.preventDefault();
  showMessage("");

  try {
    if (ui.actionSelect.value === "create") {
      const body = payloadForCreate();
      await fetch("/api/accounts", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...csrfHeaders() },
        body: JSON.stringify(body),
      }).then(toJson);

      ui.newAccountName.value = "";
      ui.newStartingBalance.value = "";
      ui.newAccountNote.value = "";
      showMessage("Account created.", "success");
    } else {
      const { accountId, body } = payloadForDelete();
      await fetch(`/api/accounts/${accountId}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json", ...csrfHeaders() },
        body: JSON.stringify(body),
      }).then(toJson);

      ui.deleteReason.value = "";
      ui.deleteConfirm.checked = false;
      showMessage("Account deleted.", "success");
    }

    await loadPageData();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

ui.actionSelect.addEventListener("change", syncActionView);
ui.actionForm.addEventListener("submit", handleSubmit);
ui.newStartingBalance.addEventListener("input", () => {
  const cleaned = normalizeMoneyInput(ui.newStartingBalance.value, { allowNegative: true });
  if (ui.newStartingBalance.value !== cleaned) {
    ui.newStartingBalance.value = cleaned;
  }
});

syncActionView();
loadPageData().catch((error) => {
  showMessage(error.message, "error");
});
