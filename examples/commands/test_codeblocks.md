---
name: "testblocks"
description: "Test different code block types"
modes: ["main"]
arguments:
  - name: "type"
    type: "choice"
    choices: ["python", "bash", "all"]
    required: true
    help: "Type of code block to test"
---

# Code Block Testing

This command demonstrates different types of executable code blocks.

{% if type == 'python' or type == 'all' %}
## Python Code Block

````python
print("Hello from Python!")
print(f"Current LLM: {ctx.tm.get_status()['client']}")
print(f"Available tasks: {len(ctx.tm.get_tasks())}")

# Some calculations
import math
result = math.sqrt(16)
print(f"Square root of 16 is: {result}")
````
{% endif %}

{% if type == 'bash' or type == 'all' %}
## Bash Code Block

````bash
echo "Hello from Bash!"
echo "Current directory: $(pwd)"
echo "Current user: $USER"
date
````
{% endif %}


---
*Test completed for: {{type}}*