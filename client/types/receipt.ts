export type ReceiptStatus = "PENDING" | "PROCESSING" | "READY" | "FAILED";

export type Receipt = {
  id: number;
  merchant_name?: string;
  total_amount?: string;
  purchase_date?: string;
  status: ReceiptStatus;
};
