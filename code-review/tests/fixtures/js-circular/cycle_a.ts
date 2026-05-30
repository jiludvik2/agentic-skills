import { banana } from "./cycle_b";

export function apple(): number {
  return banana() + 1;
}
