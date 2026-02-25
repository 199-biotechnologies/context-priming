"""Source gathering — scan memories, codebase, git history, and project config.

The gatherer's job is to find ALL potentially relevant sources. It should
over-gather rather than under-gather — the scoring step handles filtering.

Critical: This includes ACTUAL SOURCE CODE FILES, not just metadata.
A surgeon needs the patient's cardiac scans, not just the hospital directory.
"""

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Source:
    """A single gathered source with metadata."""
    category: str       # memories, codebase, code, git, config
    name: str           # human-readable identifier (usually relative path)
    content: str        # the actual content
    token_estimate: int = 0  # rough token count (chars / 4)

    def __post_init__(self):
        if not self.token_estimate:
            self.token_estimate = len(self.content) // 4


@dataclass
class GatheredSources:
    """All sources collected from a project."""
    sources: list[Source] = field(default_factory=list)
    project_dir: str = ""

    @property
    def total_tokens(self) -> int:
        return sum(s.token_estimate for s in self.sources)

    def by_category(self, category: str) -> list[Source]:
        return [s for s in self.sources if s.category == category]


# File extensions to consider as source code
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".rb", ".java",
    ".kt", ".swift", ".c", ".cpp", ".h", ".hpp", ".cs", ".php", ".lua",
    ".sh", ".bash", ".zsh", ".sql", ".graphql", ".proto",
    ".yaml", ".yml", ".toml", ".json", ".env.example",
    ".css", ".scss", ".less", ".html", ".svelte", ".vue",
    ".tf", ".hcl",  # terraform
    ".md",  # documentation that may be code-adjacent
}

# Directories to always skip
SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", ".next",
    ".nuxt", "dist", "build", ".cache", ".tox", ".mypy_cache",
    ".pytest_cache", "target", "vendor", ".terraform",
    "coverage", ".nyc_output", "egg-info",
}

# Files to always skip (even if extension matches)
SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "Pipfile.lock", "Gemfile.lock",
    "composer.lock", "Cargo.lock", "go.sum",
}

# Max file size to read (skip binaries and huge generated files)
MAX_FILE_SIZE = 100_000  # ~25k tokens


def gather_memories(project_dir: str, memory_paths: list[str] | None = None) -> list[Source]:
    """Scan memory files — MEMORY.md, topic files, .claude/memory/."""
    sources = []
    project = Path(project_dir)

    search_paths = []
    if memory_paths:
        search_paths = [Path(p) for p in memory_paths]
    else:
        # Default memory locations — scoped to this project only
        candidates = [
            project / "MEMORY.md",
            project / ".claude" / "memory",
        ]
        # Global memory (shared across projects)
        global_memory = Path.home() / ".claude" / "memory"
        if global_memory.is_dir():
            candidates.append(global_memory)

        # Project-specific memory directory (keyed by path)
        projects_dir = Path.home() / ".claude" / "projects"
        if projects_dir.is_dir():
            project_abs = project.resolve()
            encoded = str(project_abs).replace("/", "-")
            for pdir in projects_dir.iterdir():
                if not pdir.is_dir():
                    continue
                if encoded in pdir.name or pdir.name in encoded:
                    memory_dir = pdir / "memory"
                    if memory_dir.is_dir():
                        candidates.append(memory_dir)
                    break

        for c in candidates:
            if c.exists():
                search_paths.append(c)

    for path in search_paths:
        if path.is_file() and path.suffix == ".md":
            content = path.read_text(errors="replace")
            if content.strip():
                sources.append(Source(
                    category="memories",
                    name=path.name,
                    content=content,
                ))
        elif path.is_dir():
            for md in sorted(path.glob("**/*.md")):
                content = md.read_text(errors="replace")
                if content.strip():
                    sources.append(Source(
                        category="memories",
                        name=str(md.relative_to(path)),
                        content=content,
                    ))
    return sources


def gather_codebase(project_dir: str, max_depth: int = 4) -> list[Source]:
    """Scan codebase structure and key project files."""
    sources = []
    project = Path(project_dir)

    # Directory tree (for orientation)
    try:
        result = subprocess.run(
            ["find", ".", "-maxdepth", str(max_depth), "-type", "f",
             "-not", "-path", "./.git/*",
             "-not", "-path", "./node_modules/*",
             "-not", "-path", "./.venv/*",
             "-not", "-path", "./__pycache__/*",
             "-not", "-path", "./dist/*",
             "-not", "-path", "./build/*"],
            capture_output=True, text=True, cwd=project_dir, timeout=10,
        )
        if result.stdout.strip():
            sources.append(Source(
                category="codebase",
                name="directory_structure",
                content=result.stdout.strip(),
            ))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Key project files
    key_files = [
        "README.md", "readme.md",
        "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
        "CLAUDE.md", ".claude/CLAUDE.md", "AGENTS.md",
        "Makefile", "docker-compose.yml",
    ]
    seen_inodes = set()
    for fname in key_files:
        fpath = project / fname
        if fpath.is_file():
            inode = fpath.stat().st_ino
            if inode in seen_inodes:
                continue
            seen_inodes.add(inode)

            content = fpath.read_text(errors="replace")
            if len(content) > 8000:
                content = content[:8000] + "\n\n... [truncated]"
            if content.strip():
                sources.append(Source(
                    category="codebase",
                    name=fname,
                    content=content,
                ))
    return sources


def gather_code_files(
    project_dir: str,
    task: str = "",
    max_files: int = 50,
    max_depth: int = 8,
) -> list[Source]:
    """Gather actual source code files relevant to the task.

    This is the critical gatherer that both reviewers flagged as missing.
    Strategy:
    1. Extract keywords from the task description
    2. grep the codebase for files containing those keywords
    3. Also include files whose NAMES match task keywords
    4. Read the actual file content — the agent needs the real code

    This is a heuristic pre-filter, not an LLM call. Fast (~100ms).
    The scoring step will do the nuanced relevance ranking.
    """
    sources = []
    project = Path(project_dir)

    if not task:
        return sources

    # Extract keywords from task (simple heuristic, no LLM needed)
    keywords = _extract_keywords(task)
    if not keywords:
        return sources

    matched_files: dict[str, float] = {}  # path -> relevance hint

    # Strategy 1: grep for files containing task keywords
    for keyword in keywords:
        try:
            result = subprocess.run(
                ["grep", "-rl", "--include=*.py", "--include=*.ts",
                 "--include=*.js", "--include=*.tsx", "--include=*.jsx",
                 "--include=*.go", "--include=*.rs", "--include=*.rb",
                 "--include=*.java", "--include=*.swift", "--include=*.c",
                 "--include=*.cpp", "--include=*.h", "--include=*.cs",
                 "--include=*.php", "--include=*.yaml", "--include=*.yml",
                 "--include=*.toml", "--include=*.json", "--include=*.md",
                 "--include=*.sql", "--include=*.graphql",
                 "--include=*.html", "--include=*.css", "--include=*.scss",
                 "--include=*.vue", "--include=*.svelte",
                 "--include=*.sh", "--include=*.bash",
                 "--exclude-dir=.git", "--exclude-dir=node_modules",
                 "--exclude-dir=.venv", "--exclude-dir=__pycache__",
                 "--exclude-dir=dist", "--exclude-dir=build",
                 "--exclude-dir=.next", "--exclude-dir=target",
                 "--exclude-dir=coverage",
                 "-i",  # case insensitive
                 keyword, "."],
                capture_output=True, text=True, cwd=project_dir, timeout=10,
            )
            if result.stdout.strip():
                for fpath in result.stdout.strip().split("\n"):
                    fpath = fpath.strip().lstrip("./")
                    if fpath:
                        matched_files[fpath] = matched_files.get(fpath, 0) + 1
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # Strategy 2: find files whose names match task keywords
    for keyword in keywords:
        kw_lower = keyword.lower()
        try:
            result = subprocess.run(
                ["find", ".", "-maxdepth", str(max_depth), "-type", "f",
                 "-iname", f"*{kw_lower}*",
                 "-not", "-path", "./.git/*",
                 "-not", "-path", "./node_modules/*",
                 "-not", "-path", "./.venv/*",
                 "-not", "-path", "./__pycache__/*"],
                capture_output=True, text=True, cwd=project_dir, timeout=10,
            )
            if result.stdout.strip():
                for fpath in result.stdout.strip().split("\n"):
                    fpath = fpath.strip().lstrip("./")
                    if fpath:
                        # Filename matches are strong signals — boost score
                        matched_files[fpath] = matched_files.get(fpath, 0) + 3
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # Strategy 3: recently modified files (git) — with fallback chain
    for git_cmd in [
        ["git", "diff", "--name-only", "HEAD~10..HEAD"],  # recent commits
        ["git", "diff", "--name-only", "HEAD"],            # unstaged changes
        ["git", "diff", "--name-only", "--cached"],        # staged changes
    ]:
        try:
            result = subprocess.run(
                git_cmd,
                capture_output=True, text=True, cwd=project_dir, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                for fpath in result.stdout.strip().split("\n"):
                    fpath = fpath.strip()
                    if fpath:
                        matched_files[fpath] = matched_files.get(fpath, 0) + 0.5
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # Sort by match count (more keyword hits = more likely relevant)
    ranked = sorted(matched_files.items(), key=lambda x: x[1], reverse=True)

    # Read the top files
    for fpath, score in ranked[:max_files]:
        full_path = project / fpath
        if not full_path.is_file():
            continue

        # Skip files that are too large (probably generated)
        try:
            size = full_path.stat().st_size
            if size > MAX_FILE_SIZE:
                continue
            if size == 0:
                continue
        except OSError:
            continue

        # Skip lock files and other known garbage
        if full_path.name in SKIP_FILES:
            continue

        # Skip non-code files
        suffix = full_path.suffix.lower()
        if suffix not in CODE_EXTENSIONS:
            continue

        try:
            content = full_path.read_text(errors="replace")
            if content.strip():
                sources.append(Source(
                    category="code",
                    name=fpath,
                    content=content,
                ))
        except (OSError, UnicodeDecodeError):
            continue

    return sources


def _extract_keywords(task: str) -> list[str]:
    """Extract search keywords from a task description.

    Simple heuristic: split on spaces/punctuation, keep meaningful words,
    drop common English stop words. No LLM needed.
    """
    stop_words = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "must",
        "i", "me", "my", "we", "our", "you", "your", "he", "she", "it",
        "they", "them", "this", "that", "these", "those",
        "and", "but", "or", "nor", "not", "so", "yet", "both",
        "in", "on", "at", "to", "for", "of", "with", "by", "from",
        "up", "out", "if", "then", "than", "too", "very",
        "just", "about", "also", "all", "any", "each", "every",
        "how", "what", "when", "where", "which", "who", "why",
        "add", "fix", "update", "change", "modify", "create", "make",
        "implement", "write", "build", "improve", "refactor", "remove",
        "delete", "get", "set", "use", "new", "old",
    }

    # Split on non-alphanumeric, keep words 2+ chars
    words = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', task)
    keywords = []
    for w in words:
        lower = w.lower()
        if lower not in stop_words and len(lower) >= 2:
            keywords.append(lower)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for k in keywords:
        if k not in seen:
            seen.add(k)
            unique.append(k)

    return unique[:10]  # Cap at 10 keywords to keep grep fast


def gather_git_history(project_dir: str, commit_count: int = 20) -> list[Source]:
    """Scan recent git history — commits, branches, recent changes."""
    sources = []

    def run_git(args: list[str]):
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True, text=True, cwd=project_dir, timeout=10,
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    log = run_git(["log", "--oneline", f"-{commit_count}", "--no-decorate"])
    if log:
        sources.append(Source(
            category="git",
            name="recent_commits",
            content=log,
        ))

    branch = run_git(["branch", "--show-current"])
    status = run_git(["status", "--short"])
    if branch or status:
        sources.append(Source(
            category="git",
            name="current_state",
            content=f"Branch: {branch or 'unknown'}\n\nStatus:\n{status or 'clean'}",
        ))

    diff = run_git(["diff", "--stat", "HEAD~5..HEAD"])
    if diff:
        sources.append(Source(
            category="git",
            name="recent_changes",
            content=diff,
        ))

    return sources


def gather_project_config(project_dir: str) -> list[Source]:
    """Gather project-specific configuration and priorities."""
    sources = []
    project = Path(project_dir)

    priority_files = [
        "TODO.md", "PRIORITIES.md", "ROADMAP.md",
        ".github/ISSUE_TEMPLATE.md",
        "CONTRIBUTING.md",
    ]
    for fname in priority_files:
        fpath = project / fname
        if fpath.is_file():
            content = fpath.read_text(errors="replace")
            if len(content) > 4000:
                content = content[:4000] + "\n\n... [truncated]"
            if content.strip():
                sources.append(Source(
                    category="config",
                    name=fname,
                    content=content,
                ))
    return sources


def gather_all(
    project_dir: str,
    task: str = "",
    memory_paths: list[str] | None = None,
    max_depth: int = 4,
    commit_count: int = 20,
    max_code_files: int = 50,
) -> GatheredSources:
    """Gather all sources from a project directory.

    If a task is provided, also gathers actual source code files
    that match task keywords (heuristic pre-filter via grep).

    Returns a GatheredSources object containing everything the priming
    engine needs to work with.
    """
    all_sources = []
    all_sources.extend(gather_memories(project_dir, memory_paths))
    all_sources.extend(gather_codebase(project_dir, max_depth))
    all_sources.extend(gather_code_files(project_dir, task, max_code_files, max_depth * 2))
    all_sources.extend(gather_git_history(project_dir, commit_count))
    all_sources.extend(gather_project_config(project_dir))

    return GatheredSources(
        sources=all_sources,
        project_dir=project_dir,
    )
