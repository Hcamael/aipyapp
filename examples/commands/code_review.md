---
name: "review"
description: "Code review assistant for different types of reviews"
modes: ["task"]
arguments:
  - name: "type"
    type: "choice"
    choices: ["security", "performance", "style", "logic", "full"]
    required: true
    help: "Type of code review to perform"
  - name: "--language"
    type: "choice"
    choices: ["python", "javascript", "java", "go", "rust", "cpp"]
    help: "Programming language (auto-detected if not specified)"
  - name: "--strict"
    type: "flag"
    help: "Apply strict review criteria"
---

# Code Review - {{type|title}} Focus

Please perform a **{{type}}** code review{% if language %} for **{{language}}** code{% endif %}.

## Review Criteria

{% if type == "security" %}
Focus on:
- Input validation and sanitization
- Authentication and authorization
- SQL injection and XSS vulnerabilities
- Secure data handling
- Cryptographic implementations
{% elif type == "performance" %}
Focus on:
- Algorithm complexity
- Memory usage patterns
- Database query optimization
- Caching strategies
- Resource management
{% elif type == "style" %}
Focus on:
- Code formatting and consistency
- Naming conventions
- Documentation and comments
- Project structure
- Best practices adherence
{% elif type == "logic" %}
Focus on:
- Business logic correctness
- Edge case handling
- Error handling
- Control flow
- Data flow analysis
{% elif type == "full" %}
Perform a comprehensive review covering:
- Security vulnerabilities
- Performance implications
- Code style and conventions
- Logic correctness
- Maintainability
{% endif %}

{% if strict %}
## Strict Mode Enabled
Apply strict review criteria and highlight even minor issues.
{% endif %}

{% if language %}
## Language-Specific Guidelines
Apply {{language}}-specific best practices and conventions.
{% endif %}

Please analyze the provided code and provide detailed feedback with specific recommendations for improvement.