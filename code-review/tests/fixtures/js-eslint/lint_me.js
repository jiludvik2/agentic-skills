// Planted violations for the eslint adapter integration test:
//   - no-unused-vars: `unused` is never read
//   - no-console: console.log call
const unused = 42;
console.log("hello from the eslint fixture");
export const used = 1;
