// Fixture: TypeScript file with known issues for adapter integration tests.
// Intentional issues: unused variable (dead-code), duplicate logic (duplication).

const unusedConst = 42;

export function greet(name: string): string {
    return `Hello, ${name}!`;
}

export function greetAgain(name: string): string {
    return `Hello, ${name}!`;
}
