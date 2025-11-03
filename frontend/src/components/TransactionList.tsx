"use client";

import { Table } from "antd";
import { Bar } from 'react-chartjs-2';
import { Chart, CategoryScale, LinearScale, BarElement } from 'chart.js';
import ChartDataLabels from 'chartjs-plugin-datalabels';
Chart.register(CategoryScale, LinearScale, BarElement, ChartDataLabels);


import { Transaction } from "@/hooks/useAgentworkflow";

// Currency symbol mapping
const CURRENCY_SYMBOLS: { [key: string]: string } = {
    "USD": "$",
    "AED": "AED",
    "EUR": "€",
    "GBP": "£",
    "INR": "₹",
    "JPY": "¥",
    "CNY": "¥",
};

export default function TransactionsPage({ transactions, categories, currency = "USD" }: { transactions: Transaction[], categories: string[], currency?: string }) {
    const currencySymbol = CURRENCY_SYMBOLS[currency] || currency;

    const columns = [
        {
            title: "Date",
            dataIndex: "date",
            key: "date",
            width: 150,
            sorter: (a: Transaction, b: Transaction) =>
                new Date(a.date).getTime() - new Date(b.date).getTime(),
        },
        {
            title: "Payee",
            dataIndex: "payee",
            key: "payee",
            width: 300,
        },
        {
            title: "From account",
            dataIndex: "from_account",
            key: "from_account",
            width: 300,
        },
        {
            title: "To account",
            dataIndex: "to_account",
            key: "to_account",
            width: 300,
        },
        {
            title: "Amount",
            dataIndex: "display_amount",
            key: "display_amount",
            width: 300,
            render: (text: string, record: Transaction) => {
                // Extract the numeric value from display_amount (remove $ or other symbols)
                const numericValue = text.replace(/[^0-9.-]/g, '');
                return (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
                        <span style={{ fontSize: '10px', color: '#888', marginBottom: '2px' }}>{currencySymbol}</span>
                        <span style={{ fontWeight: 500 }}>{numericValue}</span>
                    </div>
                );
            },
        },
    ];

    const getTotalByCategory = (transactions: Transaction[]) => {
        const totals: { [key: string]: number } = {};
        categories.forEach(category => {
            totals[category] = 0;
        });

        let unmatchedTotal = 0;
        let matchedTotal = 0;

        transactions.forEach(transaction => {
            const amount = parseFloat(transaction.amount);
            if (!isNaN(amount)) {
                const absAmount = Math.abs(amount);
                if (totals.hasOwnProperty(transaction.to_account)) {
                    totals[transaction.to_account] += absAmount;
                    matchedTotal += absAmount;
                } else {
                    unmatchedTotal += absAmount;
                    console.log('Unmatched transaction:', {
                        to_account: transaction.to_account,
                        amount: absAmount,
                        date: transaction.date,
                        payee: transaction.payee
                    });
                }
            }
        });

        console.log('Category Totals:', totals);
        console.log('Categories:', categories);
        console.log('Matched total:', matchedTotal);
        console.log('Unmatched total:', unmatchedTotal);
        console.log('Sample transactions:', transactions.slice(0, 5));

        return totals;
    };
    const totals = getTotalByCategory(transactions);
    const chart_data = {
        labels: categories.map(category => category.replace("Expenses:", "")),
        datasets: [
            {
                label: 'Total Value',
                data: categories.map(category => totals[category]),
                backgroundColor: 'rgba(75, 192, 192, 0.6)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1,
            },
        ],
    };
    const chart_options = {
        responsive: true,
        plugins: {
            datalabels: {
                anchor: "end" as const,
                align: "end" as const,
                formatter: (value: number) => {
                    // Small currency on top, larger amount below
                    return [currencySymbol, value.toFixed(2)];
                },
                font: (context: any) => {
                    // Make the first line (currency) smaller
                    const line = context.dataset.datalabels?.[context.dataIndex] || 0;
                    return {
                        size: 8, // Smaller size for currency
                        weight: 'normal' as const
                    };
                },
                textAlign: 'center' as const,
                color: (context: any) => {
                    // Make currency slightly gray
                    return '#666';
                },
            },
        },
        scales: {
            y: {
                beginAtZero: true,
                grace: '7%',
                ticks: {
                    callback: function (tickValue: number | string) {
                        return `${currencySymbol} ${tickValue}`;
                    },
                },
            },
        },
    };

    // Calculate total expenses amount (only transactions with to_account starting with "Expenses:")
    const totalExpensesAmount = transactions.reduce((sum, txn) => {
        if (txn.to_account && txn.to_account.startsWith('Expenses:')) {
            const amount = parseFloat(txn.amount || '0');
            return sum + (isNaN(amount) ? 0 : Math.abs(amount));
        }
        return sum;
    }, 0);

    return (
        <div className="p-4">
            <div className="flex">
                <div className="w-7/12 p-4">
                    <h1 className="text-xl font-bold mb-4 p-3">Transactions</h1>
                    <Table
                        dataSource={transactions}
                        columns={columns}
                        rowKey="id"
                        pagination={{ defaultPageSize: 10 }}
                        size="middle"
                        scroll={{ x: true }}
                    />
                </div>
                <div className="w-5/12 p-4">
                    <div className="flex justify-between items-center mb-4 p-3">
                        <h2 className="text-xl font-bold">Expenses by Category</h2>
                        <div className="text-right">
                            <div className="text-xs text-gray-500 uppercase tracking-wide">Total Expenses</div>
                            <div className="text-2xl font-bold text-blue-600">
                                {currencySymbol} {totalExpensesAmount.toFixed(2)}
                            </div>
                        </div>
                    </div>
                    <Bar data={chart_data} options={chart_options} className="pt-5" />
                </div>
            </div>
        </div>
    );
}
