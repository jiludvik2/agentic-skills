export const unusedExport = "this is never imported anywhere";

export function formatDate(date: Date): string {
  console.log("formatting"); // intentional console.log for ESLint
  return date.toISOString().split("T")[0];
}

export function add(a: number, b: number): number {
  return a + b;
}
