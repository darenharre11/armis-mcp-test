# Armis MCP Client

A Python client that connects to the Armis MCP server and uses Ollama locally for LLM-powered security analysis.

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai/) running locally with the Mistral model
- Armis API credentials

## Setup

1. Install Ollama and pull the Mistral model:
   ```bash
   ollama pull mistral
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your credentials:
   ```
   ARMIS_API_KEY=your-api-key
   ARMIS_MCP_URL=https://your-tenant.armis.com/mcp
   OLLAMA_MODEL=mistral  # optional, defaults to mistral
   ```

## Usage

### Analyze a device by MAC address

```bash
python main.py --mac AA:BB:CC:DD:EE:FF
```

### Ask a free-form question

```bash
python main.py --query "How many critical vulnerabilities are in my environment?"
python main.py -q "Show me all Windows devices"
```

### Interactive mode

```bash
python main.py --interactive
```

Select from available prompts and provide required inputs. Use `l` to list available prompts at any time.

## Web Interface

```bash
streamlit run app.py
```

The Streamlit UI has three tabs:

- **Prompts** -- browse prebuilt and custom prompts
- **Configure** -- fill in variables, edit/preview the prompt, and run
- **Results** -- view output with history of the last 5 runs

## Project Structure

```
armis-mcp-test/
├── main.py           # CLI entry point
├── app.py            # Streamlit web interface
├── mcp_client.py     # MCP server connection
├── llm.py            # Ollama integration with tool calling
├── prompts.py        # Context and prompt loading
├── config.py         # Environment configuration
└── context/
    ├── Role.md       # Agent persona
    ├── Rules.md      # Behavioral constraints
    └── prompts/      # Individual prompt templates
        ├── _example/             # Template for creating new prompts
        ├── mac-risk-summarizer/
        ├── cve-volume-top5/
        ├── prompt-builder/
        └── custom/               # User-created prompts (gitignored)
```

## Prompt System

Each prompt lives in its own directory under `context/prompts/{id}/{id}.md`. Metadata is stored as YAML frontmatter:

```markdown
---
name: My Prompt Name
description: Brief description of what it does
---

# My Prompt Name

## Variables
- `variable_name`: Description shown to user when prompted

## Tools
- `armis-mcp`: Query device data from Armis

## MCP Query
The query sent to Armis MCP server.
Use {{variable_name}} for substitution.

## Analysis Prompt
Instructions for the LLM to analyze the data.

**Data:**
{{data}}

## Required Analysis
What the LLM should analyze...

## Output Format
How the LLM should structure its response...
```

### Adding New Prompts

No Python code changes required:

1. Copy the `_example/` directory: `cp -r context/prompts/_example context/prompts/my-prompt`
2. Rename the `.md` file: `mv context/prompts/my-prompt/_example.md context/prompts/my-prompt/my-prompt.md`
3. Edit the frontmatter (`name`, `description`) and fill in sections

Or use the **Prompt Builder** in the web UI to generate a template and save it as a custom prompt.

### Key Sections

| Section | Required | Purpose |
|---------|----------|---------|
| Frontmatter | Yes | `name` and `description` for catalog display |
| Variables | No | Defines inputs collected from the user. Omit for prompts with no inputs. |
| Tools | No | MCP/tool dependencies. Use `None` for LLM-only prompts. |
| MCP Query | No | The query sent to Armis to fetch data. Omit for LLM-only prompts. |
| Analysis Prompt | Yes | Instructions for the LLM (must include `{{data}}` placeholder if using MCP) |
| Required Analysis | No | Detailed analysis requirements |
| Output Format | No | Structure for the LLM's response |

### Custom Prompts

Custom prompts are saved to `context/prompts/custom/` (gitignored) via the web UI's "Save as Custom" feature. They use the same frontmatter format and appear under the **Custom** section on the Prompts tab.
