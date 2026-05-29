// Planted ESLint violations: unused var + debugger statement.
const unusedVar = 42;

function foo() {
  debugger;
  return 1;
}

foo();
