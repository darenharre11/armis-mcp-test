import re
import shutil
from dataclasses import dataclass
from pathlib import Path

CONTEXT_DIR = Path(__file__).parent / "context"
PROMPTS_DIR = CONTEXT_DIR / "prompts"
CUSTOM_DIR = PROMPTS_DIR / "custom"


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown text.

    Returns (metadata dict, body without frontmatter).
    If no frontmatter, returns ({}, original text).
    """
    if not text.startswith("---"):
        return {}, text
    end = text.find("---", 3)
    if end == -1:
        return {}, text
    raw = text[3:end].strip()
    body = text[end + 3:].lstrip("\n")
    meta = {}
    for line in raw.split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip()
    return meta, body


@dataclass
class ParsedPrompt:
    """Parsed prompt with MCP query and analysis prompt separated."""
    tools: list[str]       # List of tools/MCPs this prompt requires (empty = LLM-only)
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
    """Scan prompt directories for markdown files with frontmatter.

    Returns list of dicts with keys: id, name, description
    Skips _example and custom directories.
    """
    if not PROMPTS_DIR.exists():
        return []

    skip = {"custom", "_example"}
    prompts = []
    for d in sorted(PROMPTS_DIR.iterdir()):
        if not d.is_dir() or d.name in skip:
            continue
        md = d / "prompt.md"
        if not md.exists():
            md = d / f"{d.name}.md"  # legacy fallback
        if not md.exists():
            continue
        meta, _ = _parse_frontmatter(md.read_text())
        if not meta:
            continue
        prompts.append({
            "id": d.name,
            "name": meta.get("name", d.name),
            "description": meta.get("description", ""),
            "has_script": (d / "script.py").exists() or (d / f"{d.name}.py").exists(),
        })

    return prompts


def load_prompt(prompt_id: str) -> str | None:
    """Read prompt from context/prompts/{id}/prompt.md or custom/{id}/prompt.md.

    Strips frontmatter before returning content.
    """
    for base in [PROMPTS_DIR, CUSTOM_DIR]:
        path = base / prompt_id / "prompt.md"
        if not path.exists():
            path = base / prompt_id / f"{prompt_id}.md"  # legacy fallback
        if path.exists():
            _, body = _parse_frontmatter(path.read_text())
            return body
    return None


def _extract_section(content: str, section_name: str) -> str | None:
    """Extract content between ## Section Name and the next ## header.

    Only matches ## at the start of a line (not indented).
    """
    pattern = rf"^## {re.escape(section_name)}\s*\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def extract_variables(prompt_id: str) -> list[dict]:
    """
    Extract variable definitions from a prompt's ## Variables section.

    Returns list of dicts with keys: name, description
    Example: [{"name": "mac_address", "description": "The MAC address to analyze"}]
    """
    template = load_prompt(prompt_id)
    if template is None:
        return []

    variables_section = _extract_section(template, "Variables")
    if not variables_section:
        return []

    variables = []
    # Parse lines like: - `variable_name`: Description
    for line in variables_section.split("\n"):
        line = line.strip()
        match = re.match(r"-\s*`(\w+)`:\s*(.+)", line)
        if match:
            variables.append({
                "name": match.group(1),
                "description": match.group(2).strip(),
            })

    return variables


def extract_tools(prompt_id: str) -> list[str]:
    """
    Extract tool/MCP requirements from a prompt's ## Tools section.

    Returns list of tool identifiers (e.g., ["armis-mcp"]).
    Returns empty list if no tools section or if "none" is specified.
    """
    template = load_prompt(prompt_id)
    if template is None:
        return []

    tools_section = _extract_section(template, "Tools")
    if not tools_section:
        return []

    tools = []
    for line in tools_section.split("\n"):
        line = line.strip().lower()
        # Skip "none" indicators
        if line in ("none", "none.", "n/a", "-") or "no tools" in line or "llm-only" in line:
            return []
        # Parse lines like: - armis-mcp or - `armis-mcp`
        match = re.match(r"-\s*`?(\w[\w-]*)`?", line)
        if match:
            tools.append(match.group(1))

    return tools


def parse_prompt(prompt_id: str, **variables) -> ParsedPrompt | None:
    """
    Parse a prompt template into its components.

    Extracts:
    - Tools: List of MCP/tool dependencies
    - MCP Query: The query to send directly to the MCP server
    - Analysis Prompt: Everything after "## Analysis Prompt" to send to the LLM

    Substitutes {{variable}} placeholders in both sections.
    """
    template = load_prompt(prompt_id)
    if template is None:
        return None

    # Extract tools before variable substitution
    tools = extract_tools(prompt_id)

    # Substitute variables in the template
    for key, value in variables.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))

    # Extract MCP Query section
    mcp_query = _extract_section(template, "MCP Query")

    # Extract everything from Analysis Prompt onwards for the LLM
    analysis_match = re.search(r"^## Analysis Prompt\s*\n(.*)", template, re.DOTALL | re.MULTILINE)
    if analysis_match:
        analysis_prompt = analysis_match.group(1).strip()
    else:
        # Fallback: use the whole template if no Analysis Prompt section
        analysis_prompt = template

    return ParsedPrompt(
        tools=tools,
        mcp_query=mcp_query,
        analysis_prompt=analysis_prompt,
        full_content=template,
    )


def load_script(prompt_id: str):
    """Load optional companion script for a prompt.

    Looks for context/prompts/{prompt_id}/script.py with a run(result: str) function.
    Returns the function, or None if no companion file exists.
    """
    path = PROMPTS_DIR / prompt_id / "script.py"
    if not path.exists():
        path = PROMPTS_DIR / prompt_id / f"{prompt_id}.py"  # legacy fallback
    if not path.exists():
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location(f"script_{prompt_id}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "run", None)


def parse_content(content: str) -> ParsedPrompt:
    """Parse raw prompt content into components (no file loading)."""
    tools_section = _extract_section(content, "Tools")
    tools = []
    if tools_section:
        for line in tools_section.split("\n"):
            line = line.strip().lower()
            if line in ("none", "none.", "n/a", "-") or "no tools" in line or "llm-only" in line:
                tools = []
                break
            match = re.match(r"-\s*`?(\w[\w-]*)`?", line)
            if match:
                tools.append(match.group(1))

    mcp_query = _extract_section(content, "MCP Query")

    analysis_match = re.search(r"^## Analysis Prompt\s*\n(.*)", content, re.DOTALL | re.MULTILINE)
    if analysis_match:
        analysis_prompt = analysis_match.group(1).strip()
    else:
        analysis_prompt = content

    return ParsedPrompt(
        tools=tools,
        mcp_query=mcp_query,
        analysis_prompt=analysis_prompt,
        full_content=content,
    )


def save_custom_prompt(
    name: str, content: str, prompt_id: str | None = None, description: str = ""
) -> str:
    """Save content as a custom prompt with frontmatter metadata. Returns the prompt ID."""
    if not prompt_id:
        prompt_id = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    # Enforce valid id pattern
    prompt_id = re.sub(r"[^a-z0-9-]", "", prompt_id.lower().replace(" ", "-")).strip("-")
    prompt_dir = CUSTOM_DIR / prompt_id
    prompt_dir.mkdir(parents=True, exist_ok=True)
    # Strip any existing frontmatter from content before prepending new one
    _, body = _parse_frontmatter(content)
    desc = description or "Custom prompt"
    frontmatter = f"---\nid: {prompt_id}\nname: {name}\ndescription: {desc}\n---\n\n"
    (prompt_dir / "prompt.md").write_text(frontmatter + body)
    return prompt_id


def custom_prompt_exists(prompt_id: str) -> bool:
    """Check if a custom prompt with the given ID already exists."""
    d = CUSTOM_DIR / prompt_id
    return (d / "prompt.md").exists() or (d / f"{prompt_id}.md").exists()


def delete_custom_prompt(prompt_id: str) -> bool:
    """Delete a custom prompt by ID. Returns True if deleted."""
    prompt_dir = CUSTOM_DIR / prompt_id
    if prompt_dir.exists() and prompt_dir.is_dir():
        shutil.rmtree(prompt_dir)
        return True
    return False


def list_custom_prompts() -> list[dict]:
    """List custom prompts from context/prompts/custom/."""
    if not CUSTOM_DIR.exists():
        return []
    customs = []
    for d in sorted(CUSTOM_DIR.iterdir()):
        if not d.is_dir():
            continue
        md = d / "prompt.md"
        if not md.exists():
            md = d / f"{d.name}.md"  # legacy fallback
        if not md.exists():
            continue
        meta, body = _parse_frontmatter(md.read_text())
        if meta:
            name = meta.get("name", d.name)
            description = meta.get("description", "Custom prompt")
        else:
            # Fallback: read H1 title from markdown
            title_match = re.match(r"#\s+(.+)", body)
            name = title_match.group(1).strip() if title_match else d.name
            description = "Custom prompt"
        customs.append({
            "id": d.name,
            "name": name,
            "description": description,
            "custom": True,
            "has_script": (d / "script.py").exists() or (d / f"{d.name}.py").exists(),
        })
    return customs


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
