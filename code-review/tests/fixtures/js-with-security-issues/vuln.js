// Fixture for s3 / G6: planted JS security defects the vendored
// security-js.yaml ruleset must fire on. One instance per rule.
function processInput(userInput) {
    eval(userInput);                         // js-eval: CWE-95
    document.body.innerHTML = userInput;     // js-innerhtml-xss: CWE-79
}

module.exports = { processInput };
