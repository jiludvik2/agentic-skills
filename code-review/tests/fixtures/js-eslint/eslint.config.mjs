// Flat config (eslint v9) shipped by this fixture "project" so the adapter can
// discover it by searching upward from the target dir (the cwd it anchors).
// Mirrors the analyzer-coverage smoke fixture: no-console + no-unused-vars.
export default [
  {
    rules: {
      "no-console": "error",
      "no-unused-vars": "error",
    },
  },
];
