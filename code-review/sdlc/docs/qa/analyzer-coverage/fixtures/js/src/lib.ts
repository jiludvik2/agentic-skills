export function usedExport(): number {
  return 1;
}

// Never imported anywhere -> knip "unused export".
export function unusedExport(): number {
  return 2;
}
