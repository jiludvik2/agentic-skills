// Intentional duplicate of utils.ts for jscpd detection
export const unusedExport2 = "this is never imported anywhere";

export function formatDate2(date: Date): string {
  console.log("formatting");
  return date.toISOString().split("T")[0];
}

export function add2(a: number, b: number): number {
  return a + b;
}
