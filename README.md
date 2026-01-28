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

### Interactive mode

```bash
python main.py --interactive
```

Select from available prompts and provide required inputs.

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
        └── mac-risk-summarizer.md
```

## Adding New Prompts

1. Create a new file in `context/prompts/` (e.g., `my-prompt.md`)
2. Add an entry to the table in `context/Prompts.md`
3. Update `main.py` interactive mode to collect any required variables

### Prompt Template Format

```markdown
# Prompt Name

## Variables
- `variable_name`: Description

## Prompt
Your prompt text with {{variable_name}} placeholders.
```
