const ui = {
  refreshBtn: document.getElementById("refreshBtn"),
  form: document.getElementById("txnForm"),
  formMessage: document.getElementById("formMessage"),
  accountId: document.getElementById("accountId"),
  transactionType: document.getElementById("transactionType"),
  recurringDateRow: document.getElementById("recurringDateRow"),
  recurringDueDate: document.getElementById("recurringDueDate"),
  transactionName: document.getElementById("transactionName"),
  amount: document.getElementById("amount"),
  category: document.getElementById("category"),
  note: document.getElementById("note"),
  totalBalance: document.getElementById("totalBalance"),
  accountsList: document.getElementById("accountsList"),
  recentList: document.getElementById("recentList"),
  billsList: document.getElementById("billsList"),
  removeRecurringBillId: document.getElementById("removeRecurringBillId"),
  removeRecurringBillBtn: document.getElementById("removeRecurringBillBtn"),
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
    return "Unknown date";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Unknown date";
  }

  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}

function normalizeMoneyInput(value) {
  const cleaned = value.replace(/[^\d.]/g, "");
  const [whole, ...decimalParts] = cleaned.split(".");
  const decimals = decimalParts.join("").slice(0, 2);
  return decimalParts.length ? `${whole}.${decimals}` : whole;
}

function parseMoney(value) {
  const trimmed = value.trim();
  if (!/^\d+(\.\d{1,2})?$/.test(trimmed)) {
    return Number.NaN;
  }

  return Number.parseFloat(trimmed);
}

function clearChildren(node) {
  while (node.firstChild) {
    node.removeChild(node.firstChild);
  }
}

function showMessage(text, type = "") {
  ui.formMessage.textContent = text;
  ui.formMessage.classList.remove("success", "error");
  if (type) {
    ui.formMessage.classList.add(type);
  }
}

async function toJson(response) {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.error || "Request failed");
  }
  return body;
}

function listItem(title, value, detail, options = {}) {
  const li = document.createElement("li");

  const top = document.createElement("div");
  top.className = "item-top";

  const strong = document.createElement("strong");
  if (options.titleHref) {
    const link = document.createElement("a");
    link.className = "item-link";
    link.href = options.titleHref;
    link.textContent = title;
    strong.appendChild(link);
  } else {
    strong.textContent = title;
  }

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

function renderAccounts(summary) {
  clearChildren(ui.accountsList);
  clearChildren(ui.accountId);

  ui.totalBalance.textContent = formatMoney(summary.total_balance);

  const accounts = summary.accounts || [];
  if (!accounts.length) {
    const empty = document.createElement("li");
    empty.textContent = "No accounts yet. Add one in the database first.";
    ui.accountsList.appendChild(empty);

    const option = document.createElement("option");
    option.textContent = "No account available";
    option.value = "";
    ui.accountId.appendChild(option);
    return;
  }

  for (const account of accounts) {
    const details = `Starting Balance: ${formatMoney(account.starting_balance)}`;
    const href = `/accounts/${account.id}/transactions`;
    ui.accountsList.appendChild(listItem(account.name, formatMoney(account.current_balance), details, { titleHref: href }));

    const option = document.createElement("option");
    option.value = String(account.id);
    option.textContent = `${account.name} (${formatMoney(account.current_balance)})`;
    ui.accountId.appendChild(option);
  }
}

function renderRecent(payload) {
  clearChildren(ui.recentList);
  const transactions = payload.transactions || [];

  if (!transactions.length) {
    const empty = document.createElement("li");
    empty.textContent = "No recent transactions yet.";
    ui.recentList.appendChild(empty);
    return;
  }

  for (const tx of transactions) {
    const detail = `${tx.account_name} · ${formatDateTime(tx.occurred_at)}`;
    ui.recentList.appendChild(listItem(tx.transaction_name, formatMoney(tx.amount), detail));
  }
}

function renderBills(payload, recurringPayload) {
  clearChildren(ui.billsList);
  clearChildren(ui.removeRecurringBillId);

  const bills = payload.bills || [];
  const recurringBills = recurringPayload.bills || [];

  if (!bills.length) {
    const empty = document.createElement("li");
    empty.textContent = "No upcoming bills found.";
    ui.billsList.appendChild(empty);
  }

  for (const bill of bills) {
    const detail = `Due ${bill.next_due_date} · in ${bill.days_until_due} day(s)`;
    ui.billsList.appendChild(listItem(bill.name, formatMoney(bill.amount), detail));
  }

  if (!recurringBills.length) {
    const noneOption = document.createElement("option");
    noneOption.value = "";
    noneOption.textContent = "No recurring bills available";
    ui.removeRecurringBillId.appendChild(noneOption);
    ui.removeRecurringBillBtn.disabled = true;
    return;
  }

  for (const bill of recurringBills) {
    const option = document.createElement("option");
    option.value = String(bill.id);
    option.textContent = `${bill.name} (${formatMoney(bill.amount)})`;
    ui.removeRecurringBillId.appendChild(option);
  }

  ui.removeRecurringBillBtn.disabled = false;
}

async function loadDashboard() {
  try {
    const [summary, recent, bills, recurringBills] = await Promise.all([
      fetch("/api/accounts/summary").then(toJson),
      fetch("/api/transactions/recent?limit=5").then(toJson),
      fetch("/api/bills/upcoming?days=45").then(toJson),
      fetch("/api/bills/recurring").then(toJson),
    ]);

    renderAccounts(summary);
    renderRecent(recent);
    renderBills(bills, recurringBills);
  } catch (error) {
    showMessage(error.message, "error");
  }
}

function validateForm() {
  const accountId = Number.parseInt(ui.accountId.value, 10);
  const transactionName = ui.transactionName.value.trim();
  const category = ui.category.value.trim();
  const amount = parseMoney(ui.amount.value);

  if (!Number.isInteger(accountId) || accountId < 1) {
    throw new Error("Pick a valid account.");
  }
  if (!transactionName) {
    throw new Error("Transaction name is required.");
  }
  if (!category) {
    throw new Error("Category is required.");
  }
  if (!Number.isFinite(amount) || amount <= 0) {
    throw new Error("Amount must be greater than 0.");
  }

  const payload = {
    account_id: accountId,
    transaction_name: transactionName,
    amount: amount.toFixed(2),
    category,
    transaction_type: ui.transactionType.value,
    note: ui.note.value.trim(),
  };

  if (ui.transactionType.value === "recurring") {
    const dueDateInput = ui.recurringDueDate.value.trim();
    if (!dueDateInput) {
      throw new Error("Recurring bills require a due date.");
    }

    const parsed = new Date(`${dueDateInput}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) {
      throw new Error("Due date must be valid and formatted as YYYY-MM-DD.");
    }

    payload.recurring_due_date = dueDateInput;
  }

  return payload;
}

async function handleSubmit(event) {
  event.preventDefault();
  showMessage("");

  let payload;
  try {
    payload = validateForm();
  } catch (error) {
    showMessage(error.message, "error");
    return;
  }

  try {
    await fetch("/api/transactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(toJson);

    ui.form.reset();
    syncRecurringFields();
    showMessage("Saved and refreshed.", "success");
    await loadDashboard();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

function syncRecurringFields() {
  const isRecurring = ui.transactionType.value === "recurring";
  ui.recurringDateRow.classList.toggle("hidden", !isRecurring);
}

async function handleRemoveRecurringBill() {
  const billId = Number.parseInt(ui.removeRecurringBillId.value, 10);
  if (!Number.isInteger(billId) || billId < 1) {
    showMessage("Select a recurring bill to remove.", "error");
    return;
  }

  try {
    await fetch(`/api/bills/${billId}`, {
      method: "DELETE",
    }).then(toJson);

    showMessage("Recurring bill removed.", "success");
    await loadDashboard();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

ui.refreshBtn.addEventListener("click", loadDashboard);
ui.form.addEventListener("submit", handleSubmit);
ui.transactionType.addEventListener("change", syncRecurringFields);
ui.amount.addEventListener("input", () => {
  const cleaned = normalizeMoneyInput(ui.amount.value);
  if (ui.amount.value !== cleaned) {
    ui.amount.value = cleaned;
  }
});
ui.removeRecurringBillBtn.addEventListener("click", handleRemoveRecurringBill);

syncRecurringFields();
loadDashboard();
