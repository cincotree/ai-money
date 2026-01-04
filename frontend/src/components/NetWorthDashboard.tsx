"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Modal, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/modal";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getBaseHttpUrl } from "@/utils/api";

interface Account {
  id: string;
  name: string;
  account_type: string;
  currency: string;
  description: string | null;
  open_date: string;
  current_balance: number | null;
  is_active: boolean;
}

interface BalanceEntry {
  id: string;
  account_id: string;
  account_name: string;
  account_type: string;
  amount: number;
  currency: string;
  date: string;
}

interface NetWorthSummary {
  currency: string;
  total_assets: number;
  total_liabilities: number;
  net_worth: number;
}

interface NetWorthResponse {
  as_of_date: string;
  by_currency: NetWorthSummary[];
  entries: BalanceEntry[];
}

export function NetWorthDashboard() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [netWorth, setNetWorth] = useState<NetWorthResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAccountModalOpen, setIsAccountModalOpen] = useState(false);
  const [isBalanceModalOpen, setIsBalanceModalOpen] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [newAccountName, setNewAccountName] = useState("");
  const [newAccountCurrency, setNewAccountCurrency] = useState("USD");
  const [newAccountDescription, setNewAccountDescription] = useState("");
  const [balanceAmount, setBalanceAmount] = useState("");
  const [balanceCurrency, setBalanceCurrency] = useState("USD");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const baseUrl = await getBaseHttpUrl();

      const [accountsRes, networthRes] = await Promise.all([
        fetch(`${baseUrl}/api/networth/accounts`),
        fetch(`${baseUrl}/api/networth/summary`),
      ]);

      if (!accountsRes.ok || !networthRes.ok) {
        throw new Error("Failed to fetch data");
      }

      const accountsData = await accountsRes.json();
      const networthData = await networthRes.json();

      setAccounts(accountsData);
      setNetWorth(networthData);
    } catch (err) {
      console.error("Error fetching data:", err);
      setError("Failed to load net worth data. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateAccount = async () => {
    if (!newAccountName.trim()) {
      alert("Account name is required");
      return;
    }

    try {
      const baseUrl = await getBaseHttpUrl();
      const response = await fetch(`${baseUrl}/api/networth/accounts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newAccountName,
          currency: newAccountCurrency,
          description: newAccountDescription || null,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to create account");
      }

      setNewAccountName("");
      setNewAccountCurrency("USD");
      setNewAccountDescription("");
      setIsAccountModalOpen(false);
      await fetchData();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleUpdateBalance = async () => {
    if (!selectedAccount || !balanceAmount) {
      alert("Please enter a balance");
      return;
    }

    try {
      const baseUrl = await getBaseHttpUrl();
      const response = await fetch(`${baseUrl}/api/networth/balances`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          account_id: selectedAccount.id,
          amount: parseFloat(balanceAmount),
          currency: balanceCurrency,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to update balance");
      }

      setBalanceAmount("");
      setBalanceCurrency("USD");
      setSelectedAccount(null);
      setIsBalanceModalOpen(false);
      await fetchData();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const openBalanceModal = (account: Account) => {
    setSelectedAccount(account);
    setBalanceCurrency(account.currency);
    setBalanceAmount(account.current_balance?.toString() || "");
    setIsBalanceModalOpen(true);
  };

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency,
      minimumFractionDigits: 2,
    }).format(amount);
  };

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <p className="text-lg">Loading net worth data...</p>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Net Worth Tracker</h1>
        <Button onClick={() => setIsAccountModalOpen(true)}>
          Add Account
        </Button>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Net Worth Summary</h2>
        {netWorth && netWorth.by_currency.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {netWorth.by_currency.map((summary) => (
              <div key={summary.currency} className="border rounded-lg p-4">
                <div className="text-sm text-gray-500 mb-2">{summary.currency}</div>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Assets:</span>
                    <span className="font-medium text-green-600">
                      {formatCurrency(summary.total_assets, summary.currency)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Liabilities:</span>
                    <span className="font-medium text-red-600">
                      {formatCurrency(summary.total_liabilities, summary.currency)}
                    </span>
                  </div>
                  <div className="border-t pt-2 flex justify-between">
                    <span className="font-semibold">Net Worth:</span>
                    <span
                      className={`font-bold ${
                        summary.net_worth >= 0 ? "text-green-600" : "text-red-600"
                      }`}
                    >
                      {formatCurrency(summary.net_worth, summary.currency)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">
            No net worth data available. Add accounts and set their balances to get started.
          </p>
        )}
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <h2 className="text-xl font-semibold mb-4">Accounts</h2>
          {accounts.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Account Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Currency</TableHead>
                  <TableHead>Current Balance</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {accounts.map((account) => (
                  <TableRow key={account.id}>
                    <TableCell className="font-medium">{account.name}</TableCell>
                    <TableCell>
                      <span
                        className={`px-2 py-1 rounded text-xs ${
                          account.account_type === "Assets"
                            ? "bg-green-100 text-green-800"
                            : "bg-red-100 text-red-800"
                        }`}
                      >
                        {account.account_type}
                      </span>
                    </TableCell>
                    <TableCell>{account.currency}</TableCell>
                    <TableCell>
                      {account.current_balance !== null
                        ? formatCurrency(account.current_balance, account.currency)
                        : "-"}
                    </TableCell>
                    <TableCell className="text-sm text-gray-600">
                      {account.description || "-"}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openBalanceModal(account)}
                      >
                        Set Balance
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-gray-500">
              No accounts yet. Click "Add Account" to create your first account.
            </p>
          )}
        </div>
      </div>

      <Modal open={isAccountModalOpen} onOpenChange={setIsAccountModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add New Account</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                Account Name *
              </label>
              <input
                type="text"
                placeholder="e.g., Assets:Bank:Savings or Liabilities:Loan:Home"
                className="w-full border rounded px-3 py-2"
                value={newAccountName}
                onChange={(e) => setNewAccountName(e.target.value)}
              />
              <p className="text-xs text-gray-500 mt-1">
                Must start with 'Assets:' or 'Liabilities:'
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Currency</label>
              <select
                className="w-full border rounded px-3 py-2"
                value={newAccountCurrency}
                onChange={(e) => setNewAccountCurrency(e.target.value)}
              >
                <option value="USD">USD</option>
                <option value="INR">INR</option>
                <option value="EUR">EUR</option>
                <option value="GBP">GBP</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                Description (Optional)
              </label>
              <textarea
                className="w-full border rounded px-3 py-2"
                rows={3}
                placeholder="Add notes about this account..."
                value={newAccountDescription}
                onChange={(e) => setNewAccountDescription(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAccountModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateAccount}>Create Account</Button>
          </DialogFooter>
        </DialogContent>
      </Modal>

      <Modal open={isBalanceModalOpen} onOpenChange={setIsBalanceModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Set Current Balance: {selectedAccount?.name}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="block text-sm font-medium mb-1">Amount *</label>
              <input
                type="number"
                step="0.01"
                placeholder="0.00"
                className="w-full border rounded px-3 py-2"
                value={balanceAmount}
                onChange={(e) => setBalanceAmount(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Currency</label>
              <select
                className="w-full border rounded px-3 py-2"
                value={balanceCurrency}
                onChange={(e) => setBalanceCurrency(e.target.value)}
              >
                <option value="USD">USD</option>
                <option value="INR">INR</option>
                <option value="EUR">EUR</option>
                <option value="GBP">GBP</option>
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setIsBalanceModalOpen(false);
                setSelectedAccount(null);
              }}
            >
              Cancel
            </Button>
            <Button onClick={handleUpdateBalance}>Update Balance</Button>
          </DialogFooter>
        </DialogContent>
      </Modal>
    </div>
  );
}
