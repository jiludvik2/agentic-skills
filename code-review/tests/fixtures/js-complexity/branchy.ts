// Fixture for jscomplexity-ts-t1 (ADR-0022 follow-up): a TypeScript function carrying
// type annotations the default ESLint parser (espree) cannot parse, branchy enough that
// the vendored `complexity` rule (threshold 0) reports it once @typescript-eslint/parser
// is wired into the config — the TypeScript counterpart of branchy.js.
interface Flags {
  a: boolean;
  b: boolean;
}

function branchy(flags: Flags): number {
  if (flags.a) {
    return 1;
  } else if (flags.b) {
    return 2;
  } else if (flags.a && flags.b) {
    return 3;
  }
  return flags.a || flags.b ? 4 : 5;
}

export { branchy };
