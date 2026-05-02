const ui = {
  depositsList: document.getElementById("depositsList"),
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
  clearChildren(ui.depositsList);
  clearChildren(ui.transactionsList);
  const transactions = payload.transactions || [];
  const deposits = transactions.filter((tx) => tx.transaction_type === "deposit");
  const outgoing = transactions.filter((tx) => tx.transaction_type !== "deposit");

  if (!transactions.length) {
    ui.depositsList.appendChild(emptyItem("No deposits found yet."));
    ui.transactionsList.appendChild(emptyItem("No transactions found yet."));
    return;
  }

  if (!deposits.length) {
    ui.depositsList.appendChild(emptyItem("No deposits found yet."));
  }

  if (!outgoing.length) {
    ui.transactionsList.appendChild(emptyItem("No transactions found yet."));
  }

  for (const tx of deposits) {
    const detail = `${tx.account_name} · ${formatDateTime(tx.occurred_at)}`;
    ui.depositsList.appendChild(listItem(tx.transaction_name, formatMoney(tx.amount), detail));
  }

  for (const tx of outgoing) {
    const detail = `${tx.account_name} · ${formatDateTime(tx.occurred_at)}`;
    ui.transactionsList.appendChild(listItem(tx.transaction_name, formatMoney(tx.amount), detail));
  }

  capListToVisibleItems(ui.depositsList, 8);
  capListToVisibleItems(ui.transactionsList, 8);
}

function capListToVisibleItems(listNode, visibleCount = 8) {
  if (!listNode) {
    return;
  }

  const items = Array.from(listNode.children);
  listNode.style.maxHeight = "none";

  if (items.length <= visibleCount) {
    return;
  }

  const styles = window.getComputedStyle(listNode);
  const gap = Number.parseFloat(styles.rowGap || styles.gap || "0") || 0;
  const visibleItems = items.slice(0, visibleCount);
  const contentHeight = visibleItems.reduce((sum, item) => sum + item.getBoundingClientRect().height, 0);
  const totalHeight = Math.ceil(contentHeight + gap * Math.max(visibleCount - 1, 0));

  listNode.style.maxHeight = `${totalHeight}px`;
}

function emptyItem(message) {
  const empty = document.createElement("li");
  empty.textContent = message;
  return empty;
}

async function loadTransactions() {
  const payload = await fetch("/api/transactions").then(toJson);
  renderTransactions(payload);
}

loadTransactions().catch((error) => {
  clearChildren(ui.depositsList);
  clearChildren(ui.transactionsList);
  ui.depositsList.appendChild(emptyItem(error.message));
  ui.transactionsList.appendChild(emptyItem(error.message));
});
