import { apple } from "./cycle_a";

export function banana(): number {
  return (apple ? 1 : 0) + 2;
}
