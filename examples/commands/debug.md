---
name: "debug"
description: "Debug assistant for troubleshooting issues"
modes: ["task"]
arguments:
  - name: "issue"
    type: "choice"
    choices: ["error", "performance", "crash", "logic", "integration"]
    required: true
    help: "Type of issue to debug"
  - name: "--severity"
    type: "choice"
    choices: ["low", "medium", "high", "critical"]
    default: "medium"
    help: "Issue severity level"
  - name: "--context"
    type: "str"
    help: "Additional context about the issue"
---

# Debug Assistant - {{issue|title}} Issue

## Issue Analysis

**Type:** {{issue|title}}  
**Severity:** {{severity|title}}  
{% if context %}**Context:** {{context}}{% endif %}

## Debugging Approach

{% if issue == "error" %}
Let's systematically debug this error:

1. **Error Analysis**
   - Examine the error message and stack trace
   - Identify the root cause
   - Check for common error patterns

2. **Environment Check**
   - Verify system requirements
   - Check dependencies and versions
   - Review configuration settings

3. **Code Investigation**
   - Analyze the problematic code section
   - Look for syntax or logical errors
   - Check variable states and data flow

{% elif issue == "performance" %}
Let's analyze the performance issue:

1. **Performance Profiling**
   - Identify bottlenecks
   - Measure execution times
   - Analyze resource usage

2. **Code Optimization**
   - Review algorithm efficiency
   - Check for unnecessary operations
   - Optimize database queries

3. **System Analysis**
   - Check memory usage patterns
   - Analyze CPU utilization
   - Review I/O operations

{% elif issue == "crash" %}
Let's investigate the crash:

1. **Crash Analysis**
   - Examine crash logs and core dumps
   - Identify the crash location
   - Analyze the sequence of events

2. **Memory Investigation**
   - Check for memory leaks
   - Look for buffer overflows
   - Analyze pointer operations

3. **State Analysis**
   - Review variable states at crash time
   - Check for race conditions
   - Analyze thread safety

{% elif issue == "logic" %}
Let's trace the logic issue:

1. **Logic Flow Analysis**
   - Map the expected vs actual behavior
   - Identify decision points
   - Check conditional statements

2. **Data Flow Tracking**
   - Trace data transformations
   - Verify input/output relationships
   - Check data integrity

3. **Business Logic Review**
   - Verify requirements compliance
   - Check edge case handling
   - Validate business rules

{% elif issue == "integration" %}
Let's debug the integration issue:

1. **Interface Analysis**
   - Check API contracts
   - Verify data formats
   - Test communication protocols

2. **Dependency Review**
   - Validate service availability
   - Check version compatibility
   - Test connection reliability

3. **Configuration Check**
   - Review integration settings
   - Verify authentication
   - Check network configuration

{% endif %}

## Severity Impact

{% if severity == "critical" %}
🔴 **Critical Issue** - Immediate attention required. System may be completely non-functional.
{% elif severity == "high" %}
🟡 **High Priority** - Significant impact on functionality. Should be resolved quickly.
{% elif severity == "medium" %}
🟢 **Medium Priority** - Noticeable impact but system remains functional.
{% elif severity == "low" %}
⚪ **Low Priority** - Minor issue with minimal impact.
{% endif %}

Please provide the relevant code, logs, or error messages so I can help you debug this {{issue}} issue.