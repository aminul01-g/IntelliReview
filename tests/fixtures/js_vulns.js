// tests/fixtures/js_vulns.js
// This file contains deliberate intentional vulnerabilities to test the AST/Security scanners.

function executeUserCommand(userInput) {
    // Intentional CWE-94 Code Injection / Eval Usage
    console.log("Executing...");
    const result = eval(userInput);
    return result;
}

function processUserData(userObj) {
    // Intentional CWE-798 Hardcoded Secrets
    const apiToken = "sk-live-0j2R5sA7cD4fE9gH1vX8yZ3qW6eT";
    const dbPass = "production_database_password_99";
    
    // Intentional CWE-79 XSS via innerHTML
    const container = document.getElementById('user-profile');
    if (container) {
        container.innerHTML = "<h1>Welcome, " + userObj.name + "</h1><p>" + userObj.bio + "</p>";
    }
    
    return { token: apiToken, pass: dbPass };
}

function calculateDiscount(user, cart) {
    // Intentional High Cyclomatic Complexity
    let discount = 0;
    if (user.type === 'premium') {
        if (cart.total > 1000) {
            discount += 15;
            if (user.years > 5) discount += 5;
        } else if (cart.total > 500) {
            discount += 10;
        } else {
            discount += 5;
        }
    } else {
        if (cart.total > 1000) {
            discount += 10;
        } else {
            discount += 0;
        }
    }
    return discount;
}
