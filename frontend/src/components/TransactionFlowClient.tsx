"use client";

import { useAgentWorkflow } from "@/hooks/useAgentworkflow";
import { Button } from "@/components/ui/button";
import { Modal, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/modal";
import { LoadingIcon } from '@/components/LoadingIcon';
import { useEffect, useState, useRef } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import ExpenseCalendar from "@/components/CalendarView"
import { getBaseHttpUrl } from "@/utils/api";

export function TransactionFlowClient() {
  const [isMounted, setIsMounted] = useState(false);
  const [uploadErrorMessage, setuploadErrorMessage] = useState<string | null>(null);
  const [beancountFilepath, setBeancountFilepath] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);


  const {
    isConnected,
    currentState,
    progress,
    categories,
    transactions,
    pendingTransactions,
    submitFeedback,
    rectifyTransaction,
    initializeConnection,
    setCategories,
    setTransactions
  } = useAgentWorkflow();

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files) return;
    const file = files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const baseUrl = await getBaseHttpUrl();
      const response = await fetch(`${baseUrl}/api/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("File upload failed");
      }

      const data = await response.json();
      setBeancountFilepath(data.beancount_filepath);
      setCategories(data.categories);
      setTransactions(data.transactions);
    } catch (error) {
      console.error("Error uploading file:", error);
      setuploadErrorMessage("Error uploading file");
    }
  };

  useEffect(() => {
    setIsMounted(true);
    if (pendingTransactions.length > 0) {
      setIsModalOpen(true);
    }
  }, [pendingTransactions]);

  // Don't render anything until the component is mounted
  if (!isMounted) {
    return null;
  }

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  return (
    <div className="p-4">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        className="hidden"
      />
      {fileInputRef.current?.files?.[0] ? (
        <div className="mb-4 text-xs">
          <p className="text-sky-600 pb-5 pr-5 float-left">
            Uploaded File: <span className="font-mono">{fileInputRef.current.files[0].name}</span>
          </p>
          {beancountFilepath && (
            <p className="text-sky-600 pb-5 float-left">
              Beancount Filepath: <span className="font-mono">{beancountFilepath}</span>
            </p>
          )}
          <div className="text-xs font-mono float-right">
            {isConnected ? "🟢 Connected" : "⚪ Disconnected"}
            {isConnected && (
              <div className="inline-block float-right pl-2">
                <LoadingIcon width={14} height={14} className="text-green-500" />
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="place-items-center">
          <div>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
            >
              Upload Statement
            </button>
          </div>
        </div>
      )}

      {uploadErrorMessage && (
        <div className="mb-4">
          <p className="text-red-600">{uploadErrorMessage}</p>
        </div>
      )}

      {beancountFilepath && (
        <div className="mb-4 clear-both">
          {!isConnected && currentState !== "completed" && (
            <button
              onClick={() => beancountFilepath && initializeConnection(beancountFilepath)}
              className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded"
            >
              Categorize Expenses
            </button>
          )}
          {currentState === "completed" && (
            <div className="place-items-center pt-5">
              <h3 className="text-2xl text-green-500 font-extrabold">
                Categorization is complete 🎉
              </h3>
            </div>
          )}

          {isConnected && (
            <div className="pt-10">
              <div className="w-full bg-gray-200 rounded-full h-4 mb-2">
                <div
                  className="bg-green-500 h-4 rounded-full transition-all duration-500"
                  style={{
                    width: progress ? `${(progress.processed / progress.total) * 100}%` : '0%',
                  }}
                ></div>
              </div>
              <div className="text-sky-600 font-bold pt-5">
                All transactions: {progress ? progress.total : <LoadingIcon width={14} height={14} className="text-sky-600 inline-block" />} | Categorized transactions: {progress ? progress.processed : <LoadingIcon width={14} height={14} className="text-sky-600 inline-block" />}
              </div>
            </div>
          )}

          <Modal open={isModalOpen} onOpenChange={setIsModalOpen}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>🤖 Review and update transaction categories</DialogTitle>
                <p className="pb-3 text-m text-gray-600">
                  Teach the AI agent! Provide categories to the agent for the following transactions </p>
              </DialogHeader>
              <hr />
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="font-bold">Date</TableHead>
                      <TableHead className="font-bold">Expense</TableHead>
                      <TableHead className="font-bold">Amount</TableHead>
                      <TableHead className="font-bold">Assessed Category</TableHead>
                      <TableHead className="font-bold">Assessed Vendor</TableHead>
                      <TableHead className="font-bold">Rectified Category</TableHead>
                      <TableHead className="font-bold">Rectified Vendor</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {pendingTransactions.map((txn) => (
                      <TableRow key={txn.id}>
                        <TableCell>{txn.date}</TableCell>
                        <TableCell className="break-words max-w-[200px]">
                          {txn.vendor}
                        </TableCell>
                        <TableCell>{txn.amount}</TableCell>
                        <TableCell>{txn.assessed_category}</TableCell>
                        <TableCell>{txn.assessed_vendor}</TableCell>
                        <TableCell>
                          <select
                            id={`category-${txn.id}`}
                            className="rounded-md border border-gray-300 p-2 text-sm w-full"
                            value={txn.rectified_category}
                            required={true}
                            onChange={(e) => {
                              rectifyTransaction({
                                ...txn,
                                rectified_category: e.target.value,
                              });
                            }}
                          >
                            <option value=""></option>
                            {categories.map((category) => (
                              <option key={category} value={category}>
                                {category.replace("Expenses:", "")}
                              </option>
                            ))}
                          </select>
                        </TableCell>
                        <TableCell>
                          <input
                            id={`vendor-${txn.id}`}
                            type="text"
                            className="rounded-md border border-gray-300 p-2 text-sm w-full"
                            defaultValue={
                              txn.rectified_vendor || txn.assessed_vendor
                            }
                            onChange={(e) => {
                              rectifyTransaction({
                                ...txn,
                                rectified_vendor: e.target.value,
                              });
                            }}
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <DialogFooter>
                <div className="float-right pr-3">
                  <Button
                    onClick={() => {
                      submitFeedback(pendingTransactions);
                      handleCloseModal();
                    }}
                    className="bg-green-500 hover:bg-green-700 text-white font-bold p-4 rounded"
                  >
                    Submit
                  </Button>
                </div>
              </DialogFooter>
            </DialogContent>
          </Modal>
          <ExpenseCalendar categories={categories} expenses={transactions || []} />
        </div>
      )}
    </div>
  );
}
