export function computeStatistics(values: number[]): Record<string, number> {
  const count = values.length;
  const total = values.reduce((acc, v) => acc + v, 0);
  const mean = count === 0 ? 0 : total / count;
  const sorted = [...values].sort((a, b) => a - b);
  const median = count === 0 ? 0 : sorted[Math.floor(count / 2)];
  const max = count === 0 ? 0 : sorted[count - 1];
  const min = count === 0 ? 0 : sorted[0];
  return { count, total, mean, median, max, min };
}
