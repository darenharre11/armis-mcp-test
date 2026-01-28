import re
from dataclasses import dataclass
from pathlib import Path

CONTEXT_DIR = Path(__file__).parent / "context"
PROMPTS_DIR = CONTEXT_DIR / "prompts"


@dataclass
class ParsedPrompt:
    """Parsed prompt with MCP query and analysis prompt separated."""
    mcp_query: str | None  # Query to send directly to MCP
    analysis_prompt: str   # Prompt to send to LLM (with {{device_data}} placeholder)
    full_content: str      # Original full content for fallback


def load_context() -> dict[str, str]:
    """Load Role.md and Rules.md into a dict."""
    context = {}
    for name in ("Role", "Rules"):
        path = CONTEXT_DIR / f"{name}.md"
        if path.exists():
            context[name.lower()] = path.read_text()
    return context


def list_prompts() -> list[dict]:
    """
    Parse Prompts.md index to get available prompt names.

    Returns list of dicts with keys: id, name, description
    """
    prompts_index = CONTEXT_DIR / "Prompts.md"
    if not prompts_index.exists():
        return []

    content = prompts_index.read_text()
    prompts = []

    # Parse markdown table rows: | id | name | description |
    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("|") or line.startswith("| ID") or line.startswith("|--"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 4:
            prompts.append({
                "id": parts[1],
                "name": parts[2],
                "description": parts[3],
            })

    return prompts


def load_prompt(prompt_id: str) -> str | None:
    """Read individual prompt from context/prompts/{id}.md"""
    path = PROMPTS_DIR / f"{prompt_id}.md"
    if path.exists():
        return path.read_text()
    return None


def _extract_section(content: str, section_name: str) -> str | None:
    """Extract content between ## Section Name and the next ## header."""
    pattern = rf"## {re.escape(section_name)}\s*\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def parse_prompt(prompt_id: str, **variables) -> ParsedPrompt | None:
    """
    Parse a prompt template into its components.

    Extracts:
    - MCP Query: The query to send directly to the MCP server
    - Analysis Prompt: Everything after "## Analysis Prompt" to send to the LLM

    Substitutes {{variable}} placeholders in both sections.
    """
    template = load_prompt(prompt_id)
    if template is None:
        return None

    # Substitute variables in the template
    for key, value in variables.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))

    # Extract MCP Query section
    mcp_query = _extract_section(template, "MCP Query")

    # Extract everything from Analysis Prompt onwards for the LLM
    analysis_match = re.search(r"## Analysis Prompt\s*\n(.*)", template, re.DOTALL)
    if analysis_match:
        analysis_prompt = analysis_match.group(1).strip()
    else:
        # Fallback: use the whole template if no Analysis Prompt section
        analysis_prompt = template

    return ParsedPrompt(
        mcp_query=mcp_query,
        analysis_prompt=analysis_prompt,
        full_content=template,
    )


def build_prompt(prompt_id: str, **variables) -> str | None:
    """Load prompt template and substitute variables. Returns full content."""
    template = load_prompt(prompt_id)
    if template is None:
        return None

    # Replace {{variable}} placeholders
    for key, value in variables.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))

    return template


def build_system_prompt() -> str:
    """Build system prompt from Role and Rules context."""
    context = load_context()
    parts = []
    if "role" in context:
        parts.append(context["role"])
    if "rules" in context:
        parts.append(context["rules"])
    return "\n\n".join(parts)
