import React, { useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { Table, message } from "antd";
import { Pie } from 'react-chartjs-2';
import { ArcElement } from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

interface Expense {
  date: string;
  amount: number;
  category: string;
}


interface ExpenseCalendarProps {
  expenses?: Transaction[];
  categories: string[];
}

const ExpenseCalendar: React.FC<ExpenseCalendarProps> = ({ expenses, categories }) => {
  const [loading, setLoading] = useState(false);
  const [currentDate, setCurrentDate] = useState<Date>(new Date());
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

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
        },
    ];

    const getTotalByCategory = (expenses: Transaction[]) => {
        const totals: { [key: string]: number } = {};
        categories.forEach(category => {
            totals[category] = 0;
        });

        expenses.forEach(transaction => {
            if (totals.hasOwnProperty(transaction.rectified_category)) {
                totals[transaction.rectified_category] += parseFloat(transaction.amount);
            }
        });

        return totals;
    };
  const totals = getTotalByCategory(expenses);

  const getDaysInMonth = (date: Date): number => {
    return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
  };

  const getFirstDayOfMonth = (date: Date): number => {
    return new Date(date.getFullYear(), date.getMonth(), 1).getDay();
  };

  const getDailyExpenses = (dateStr: string) => {
    const totals: { [key: string]: number } = {};

    categories.forEach(category => {
        totals[category] = 0;
    });
    const dayExpenses = expenses.filter(exp => exp.date === dateStr);
    console.log(dayExpenses)
    dayExpenses.forEach(transaction => {
        if (totals.hasOwnProperty(transaction.to_account)) {
            totals[transaction.to_account] += parseFloat(transaction.amount);
        }
    });

    return {
      labels: categories.map(category => category.replace("Expenses:", "")),
      datasets: [{
        label: 'Expenses by Category',
        data: categories.map(category => totals[category]),
        backgroundColor: 'rgba(75, 192, 192, 0.6)',
        borderColor: 'rgba(75, 192, 192, 1)',
        borderWidth: 1,
      }],
    };
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top' as const },
      title: {
        display: true,
        text: selectedDate ? `Daily Expenses - ${selectedDate}` : '',
      },
    },
  };


const renderTable = (dateStr : string) => {
    const dayExpenses = expenses.filter(exp => exp.date === dateStr);
    return (<div className="mt-8 overflow-x-auto">
      <h1 className="text-xl font-bold mb-4 p-3">Transactions</h1>
                    <Table
                        dataSource={dayExpenses}
                        columns={columns}
                        rowKey="id"
                        loading={loading}
                        pagination={{ defaultPageSize: 10 }}
                        size="middle"
                        scroll={{ x: true }}
                    />
    </div>)
  };
  const renderCalendar = () => {
    const daysInMonth = getDaysInMonth(currentDate);
    const firstDay = getFirstDayOfMonth(currentDate);
    const days: JSX.Element[] = [];

    for (let i = 0; i < firstDay; i++) {
      days.push(<div key={`empty-${i}`} className="p-2 border bg-gray-50"></div>);
    }

    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      const dayExpenses = expenses.filter(exp => exp.date === dateStr);
      const totalAmount = dayExpenses.reduce((sum, exp) => sum + exp.amount, 0);

      days.push(
        <div
          key={day}
          className={`p-2 border min-h-24 hover:bg-gray-50 cursor-pointer ${
   dateStr === selectedDate ? 'bg-blue-100' : ''
 }`}
          onClick={() => setSelectedDate(dateStr)}
        >
          <div className="font-semibold">{day}</div>
          {totalAmount > 0 && (
            <div className="mt-1 text-sm">
              <div className="text-green-600">$ {totalAmount.toFixed(2)}</div>
            </div>
          )}
        </div>
      );
    }

    return days;
  };

  return (
      <div className="p-4">
    <div className="flex gap-4">
      <div className="w-3/5">
        <div className="flex justify-between items-center mb-4">
          <button onClick={() => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1))}
            className="px-4 py-2 bg-blue-500 text-white rounded">
            Previous
          </button>
          <h2 className="text-xl font-bold">
            {currentDate.toLocaleString('default', { month: 'long', year: 'numeric' })}
          </h2>
          <button onClick={() => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1))}
            className="px-4 py-2 bg-blue-500 text-white rounded">
            Next
          </button>
        </div>
        <div className="grid grid-cols-7 gap-0">
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
            <div key={day} className="p-2 text-center font-bold bg-gray-100 border">
              {day}
            </div>
          ))}
          {renderCalendar()}
        </div>
      </div>
      <div className="w-2/5">
        {selectedDate ? (
          <div className="h-full min-h-96 p-4 border rounded-lg bg-white">
            <Bar data={getDailyExpenses(selectedDate)} options={chartOptions} />
          </div>
        ) : (
          <div className="h-full min-h-96 p-4 border rounded-lg bg-white flex items-center justify-center text-gray-500">
            Select a date to view expenses
          </div>
        )}
      </div>
    </div>
    {selectedDate ? ( renderTable(selectedDate)) :( <div className="h-full min-h-96 p-4 border rounded-lg bg-white flex items-center justify-center text-gray-500">
            Select a date to view expenses
          </div>)}
    </div>
  );
};

export default ExpenseCalendar;