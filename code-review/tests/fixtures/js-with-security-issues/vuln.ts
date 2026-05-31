// TypeScript counterpart of vuln.js (s3 / G6). The type annotation forces semgrep
// to parse this as TS, validating the rules' declared `typescript` language entry.
export function processInput(userInput: string): void {
    eval(userInput);                         // js-eval: CWE-95
    document.body.innerHTML = userInput;     // js-innerhtml-xss: CWE-79
}
