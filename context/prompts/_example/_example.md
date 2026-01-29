---
id: my-prompt-id
name: My Prompt Name
description: Brief description of what it does
---

# Example Prompt Template

This is a template for creating new prompts. Copy this directory and rename it to your prompt ID (e.g., `my-new-prompt/my-new-prompt.md`).

**To add a new prompt:**
1. Copy this directory: `cp -r _example my-prompt-id`
2. Rename the `.md` file to match: `mv my-prompt-id/_example.md my-prompt-id/my-prompt-id.md`
3. Edit the frontmatter `name` and `description` fields above
4. Fill in the sections below

## Variables

Define any inputs the user needs to provide. Each variable should be on its own line with the format:
- `variable_name`: Description shown to user

Example:
- `device_id`: The Armis device ID to analyze
- `time_range`: Time range for the query (e.g., "7 days", "30 days")

If your prompt requires no user input, you can omit this section or leave it empty.

## Tools

Declare which MCP servers or tools this prompt requires. This makes dependencies explicit and supports future multi-MCP configurations.

Format:
- `tool-name`: Brief description of what it's used for

Example (using Armis MCP):
- `armis-mcp`: Query device and vulnerability data

For LLM-only prompts (no external tools), use:
```
None - LLM-only prompt
```

## MCP Query

This is the query sent to the Armis MCP server to fetch data. Use `{{variable_name}}` syntax to substitute user-provided values.

Example:
```
Get all security alerts for device {{device_id}} from the last {{time_range}}.
Include alert severity, description, and recommended actions.
```

## Analysis Prompt

This section tells the LLM how to analyze the data returned from Armis. You MUST include a `{{data}}` placeholder where the MCP response will be inserted.

Example:
```
Analyze the following security alert data and provide a summary.

**Alert Data:**
{{data}}
```

## Required Analysis

Break down what specific analysis the LLM should perform. This helps ensure consistent, comprehensive output.

Example:
1. **Alert Summary**: Count and categorize alerts by severity
2. **Trend Analysis**: Identify patterns or recurring issues
3. **Risk Assessment**: Evaluate overall risk level
4. **Recommendations**: Suggest remediation steps

## Output Format

Define the structure for the LLM's response. Using markdown formatting helps ensure readable output.

Example:
```
### Alert Summary
- Critical: X alerts
- High: X alerts
- Medium: X alerts
- Low: X alerts

### Key Findings
1. [Finding 1]
2. [Finding 2]

### Recommendations
1. [Action item 1]
2. [Action item 2]

### Risk Level: [Low/Medium/High/Critical]
[Justification]
```
