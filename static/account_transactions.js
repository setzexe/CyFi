const ui = {
  accountTitle: document.getElementById("accountTitle"),
  accountBalance: document.getElementById("accountBalance"),
  accountTransactionsList: document.getElementById("accountTransactionsList"),
};

function formatMoney(value) {
  const parsed = Number.parseFloat(String(value ?? "0"));
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(Number.isFinite(parsed) ? parsed : 0);
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
  clearChildren(ui.accountTransactionsList);

  if (payload.account) {
    ui.accountTitle.textContent = payload.account.name;
    ui.accountBalance.textContent = formatMoney(payload.account.current_balance);
  }

  const transactions = payload.transactions || [];
  if (!transactions.length) {
    const empty = document.createElement("li");
    empty.textContent = "No transactions found for this account yet.";
    ui.accountTransactionsList.appendChild(empty);
    return;
  }

  for (const tx of transactions) {
    const notePart = tx.note ? ` · ${tx.note}` : "";
    const detail = `${tx.category} · ${tx.transaction_type}${notePart}`;
    ui.accountTransactionsList.appendChild(listItem(tx.transaction_name, formatMoney(tx.amount), detail));
  }
}

async function loadAccountTransactions() {
  const accountId = Number.parseInt(window.CYFI_ACCOUNT_ID, 10);
  if (!Number.isInteger(accountId) || accountId < 1) {
    throw new Error("Invalid account id");
  }

  const payload = await fetch(`/api/accounts/${accountId}/transactions`).then(toJson);
  renderTransactions(payload);
}

loadAccountTransactions().catch((error) => {
  clearChildren(ui.accountTransactionsList);
  const failed = document.createElement("li");
  failed.textContent = error.message;
  ui.accountTransactionsList.appendChild(failed);
});
