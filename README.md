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

## Available Prompts

| ID | Name | Description |
|----|------|-------------|
| mac-risk-summarizer | MAC Risk Summarizer | Analyze device by MAC address, return risks and recommendations |
| cve-volume-top5 | Top 5 CVEs by Volume | Get the top 5 CVEs affecting the most devices |

## Project Structure

```
armis-mcp-test/
├── main.py           # CLI entry point
├── mcp_client.py     # MCP server connection
├── llm.py            # Ollama integration with tool calling
├── prompts.py        # Context and prompt loading
├── config.py         # Environment configuration
└── context/
    ├── Role.md       # Agent persona
    ├── Rules.md      # Behavioral constraints
    ├── Prompts.md    # Prompt index
    └── prompts/      # Individual prompt templates
        ├── mac-risk-summarizer.md
        ├── cve-volume-top5.md
        └── _example.md   # Template for creating new prompts
```

## Adding New Prompts

Adding new prompts requires **no Python code changes**. Simply:

1. Create a new file in `context/prompts/` (e.g., `my-prompt.md`)
2. Add an entry to the table in `context/Prompts.md`

The system automatically parses variables from your prompt file and prompts users for input in interactive mode.

### Prompt Template Format

See `context/prompts/_example.md` for a complete template. The basic structure is:

```markdown
# Prompt Name

## Variables
- `variable_name`: Description shown to user when prompted

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

### Key Sections

| Section | Required | Purpose |
|---------|----------|---------|
| Variables | No | Defines inputs collected from the user. Omit for prompts with no inputs. |
| MCP Query | Yes | The query sent to Armis to fetch data |
| Analysis Prompt | Yes | Instructions for the LLM (must include `{{data}}` placeholder) |
| Required Analysis | No | Detailed analysis requirements |
| Output Format | No | Structure for the LLM's response |

### Variable Format

Variables are defined as a markdown list with backtick-quoted names:

```markdown
## Variables
- `mac_address`: The MAC address to analyze
- `severity`: Minimum severity level (low/medium/high/critical)
```

The description after the colon is shown to users when they're prompted for input.
