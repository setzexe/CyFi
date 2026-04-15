const ui = {
  transactionsList: document.getElementById("transactionsList"),
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

function clearChildren(node) {
  while (node.firstChild) {
    node.removeChild(node.firstChild);
  }
}

async function toJson(response) {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.error || "Request failed");
  }
  return body;
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

function renderTransactions(payload) {
  clearChildren(ui.transactionsList);
  const transactions = payload.transactions || [];

  if (!transactions.length) {
    const empty = document.createElement("li");
    empty.textContent = "No transactions found yet.";
    ui.transactionsList.appendChild(empty);
    return;
  }

  for (const tx of transactions) {
    const detail = `${tx.account_name} · ${formatDateTime(tx.occurred_at)}`;
    ui.transactionsList.appendChild(listItem(tx.transaction_name, formatMoney(tx.amount), detail));
  }
}

async function loadTransactions() {
  const payload = await fetch("/api/transactions").then(toJson);
  renderTransactions(payload);
}

loadTransactions().catch((error) => {
  clearChildren(ui.transactionsList);
  const failed = document.createElement("li");
  failed.textContent = error.message;
  ui.transactionsList.appendChild(failed);
});
