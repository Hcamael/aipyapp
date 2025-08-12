---
name: "deploy"
description: "Deploy application to different environments"
modes: ["task"]
arguments:
  - name: "environment"
    type: "choice"
    choices: ["dev", "staging", "prod"]
    required: true
    help: "Target deployment environment"
  - name: "--version"
    type: "str"
    help: "Version to deploy"
  - name: "--force"
    type: "flag"
    help: "Force deployment even if checks fail"
subcommands:
  rollback:
    description: "Rollback to previous version"
    arguments:
      - name: "--steps"
        type: "int"
        default: 1
        help: "Number of versions to rollback"
template_vars:
  app_name: "MyApp"
---

# Deploy {{app_name}} to {{environment}}

{% if subcommand == 'rollback' %}
## Rollback Operation

Rolling back {{steps|default(1)}} version(s) in {{environment}} environment.

Please execute the rollback procedure for {{app_name}}.

{% else %}
## Deployment Operation

Deploying {{app_name}} to **{{environment}}** environment.

{% if version %}
**Version:** {{version}}
{% endif %}

{% if force %}
⚠️ **Force deployment enabled** - skipping safety checks
{% endif %}

### Deployment Steps:
1. Validate environment configuration
2. Build application artifacts
{% if not force %}
3. Run pre-deployment checks
{% endif %}
4. Deploy to {{environment}}
5. Run post-deployment verification

Please execute the deployment process with these parameters.
{% endif %}