---
id: prompt-builder
name: Prompt Builder [Experimental]
description: Create a new prompt template for this tool (LLM-only, no MCP). Script extracts the generated template and provides a save-to-custom UI.
---

# Prompt Builder

A utility prompt that helps users create new prompts for this tool. This prompt does not make MCP calls - it interacts directly with the LLM.

## Variables

- `goal`: Describe what you want your new prompt to accomplish

## Tools

None - LLM-only prompt

## Analysis Prompt

You are a prompt engineering assistant helping a user create a new prompt template for the Armis MCP Client tool.

**User's Goal:**
{{goal}}

**About This System:**
The Armis MCP Client is a security analysis tool that:
1. Uses prompts defined in markdown files with YAML frontmatter
2. Connects to the Armis MCP server to fetch security data
3. Sends the data to an LLM for analysis

**CRITICAL: You must follow the exact structure and formatting below. The system parses these files programmatically — deviations will break prompt loading.**

---

**Prompt Template Structure:**

Every prompt file MUST start with YAML frontmatter (between `---` delimiters), followed by markdown sections using level-2 headings (`##`). Here is the required structure:

1. **Frontmatter** (required) — YAML block with `id`, `name`, and `description` fields. The `id` must be lowercase, hyphenated (e.g., `device-compliance-check`). This is how the prompt appears in the catalog.

2. **Variables** — Define user inputs. Format each as: `- \`variable_name\`: Description shown to user`. If no variables needed, write: `(No variables required for this prompt)`

3. **Tools** — Declare MCP/tool dependencies. Format as: `- \`tool-name\`: What it's used for`. For LLM-only prompts use: `None - LLM-only prompt`

4. **MCP Query** — Natural language query sent to Armis MCP to fetch data. Reference user inputs with double braces around the variable name. Omit this entire section for LLM-only prompts.

5. **Analysis Prompt** — Instructions for the LLM. For prompts with an MCP Query, MUST include a double-brace data placeholder (like `data` or `device_data` wrapped in double braces) where the MCP response is inserted.

6. **Required Analysis** (optional) — Numbered list of specific analysis tasks.

7. **Output Format** (optional) — Define the markdown structure for the response.

**Available MCP Capabilities:**
The Armis MCP server can query:
- Devices (by MAC, IP, device type, site, etc.)
- Vulnerabilities and CVEs
- Security alerts and anomalies
- Network connections and traffic
- Device risk scores and compliance status

---

**Reference Example — follow this structure exactly:**

The example below shows a prompt that takes a MAC address variable, queries Armis for device data, and analyzes the results. Every line is indented to prevent parsing — your output should NOT be indented.

    ---
    id: mac-risk-summarizer
    name: MAC Risk Summarizer
    description: Analyze device by MAC address, return risks and recommendations
    ---

    # MAC Risk Summarizer

    ## Variables

    - `mac_address`: The MAC address to analyze

    ## Tools

    - `armis-mcp`: Query device and vulnerability data from Armis

    ## MCP Query

    Get all device information for the device with MAC address {{mac_address}}.

    Include:
    - Device type, category, and manufacturer
    - Operating system and version
    - First seen and last seen timestamps
    - Network information (IP address, VLAN, subnet)
    - Any known security risks, vulnerabilities, or alerts
    - Behavioral anomalies or policy violations

    ## Analysis Prompt

    Based on the following device data retrieved from Armis, provide a comprehensive security assessment.

    **Device Data:**
    {{device_data}}

    ## Required Analysis

    1. **Device Details**: Summarize device type, manufacturer, OS, timestamps, and network info.
    2. **Security Risks**: Identify the top 3 security risks.
    3. **Recommendations**: Provide top 3 actionable recommendations.
    4. **Overall Risk Evaluation**: Assign a risk level (Low/Medium/High/Critical) with justification.

    ## Output Format

    Structure your response as:

    ### Device Summary
    - Type: [device type]
    - Manufacturer: [manufacturer]
    - OS: [operating system and version]

    ### Risk Analysis
    1. **[Risk Name]** (Severity: High/Medium/Low)
       - Description of the risk

    ### Recommendations
    1. [Actionable recommendation]
    2. [Actionable recommendation]
    3. [Actionable recommendation]

    ### Overall Assessment
    **Risk Level: [Low/Medium/High/Critical]**
    [Justification for the risk level based on findings]

---

**Variable substitution syntax:**

When your prompt needs user input (like a MAC address or IP), define the variable in the Variables section and reference it with double braces in the MCP Query and Analysis Prompt sections. The system replaces these at runtime with user-provided values.

For example, if you define a variable called `ip_address`, you reference it as: two opening braces, then ip_address, then two closing braces. Same for data placeholders like `data` or `device_data` in the Analysis Prompt.

---

**Your Task:**
Based on the user's goal, create a complete prompt template. Output ONLY the template content — no commentary before or after.

**Rules:**
- The template MUST start with `---` frontmatter containing `id`, `name`, and `description`
- The `id` MUST be lowercase and hyphenated (e.g., `device-compliance-check`)
- The template MUST use the exact section headings shown above (`## Variables`, `## Tools`, `## MCP Query`, `## Analysis Prompt`, etc.)
- Use `armis-mcp` as the tool name for any Armis queries, or `None - LLM-only prompt` for no tools
- The Analysis Prompt section MUST include a data placeholder in double braces (like the example uses for data) where the MCP response is inserted
- Any variables defined in the Variables section should be referenced using the same double-brace syntax in the MCP Query section
- Be specific and actionable in the MCP Query — tell Armis exactly what data to fetch
- Define a clear Output Format so responses are consistent
- Do NOT wrap the Output Format section content in fenced code blocks (no triple backticks). Write the format directly as plain markdown.
