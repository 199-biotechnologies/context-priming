"""Source gathering — scan memories, codebase, git history, and project config."""

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Source:
    """A single gathered source with metadata."""
    category: str       # memories, codebase, git, config, external
    name: str           # human-readable identifier
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


def gather_memories(project_dir: str, memory_paths: list[str] | None = None) -> list[Source]:
    """Scan memory files — MEMORY.md, topic files, .claude/memory/."""
    sources = []
    project = Path(project_dir)

    search_paths = []
    if memory_paths:
        search_paths = [Path(p) for p in memory_paths]
    else:
        # Default memory locations — scoped to this project
        candidates = [
            project / "MEMORY.md",
            project / ".claude" / "memory",
            Path.home() / ".claude" / "memory",
        ]
        # Look for project-specific memory directory (keyed by path)
        projects_dir = Path.home() / ".claude" / "projects"
        if projects_dir.is_dir():
            # Find the memory dir that matches this project's path
            project_abs = project.resolve()
            for pdir in projects_dir.iterdir():
                if not pdir.is_dir():
                    continue
                # Claude Code encodes paths with dashes: /Users/foo/bar → -Users-foo-bar
                encoded = str(project_abs).replace("/", "-")
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


def gather_codebase(project_dir: str, max_depth: int = 3) -> list[Source]:
    """Scan codebase structure — directory tree, key files."""
    sources = []
    project = Path(project_dir)

    # Directory tree (limited depth)
    try:
        result = subprocess.run(
            ["find", ".", "-maxdepth", str(max_depth), "-type", "f",
             "-not", "-path", "./.git/*",
             "-not", "-path", "./node_modules/*",
             "-not", "-path", "./.venv/*",
             "-not", "-path", "./__pycache__/*"],
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

    # Key files that describe the project
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
            # Deduplicate files (e.g. README.md and readme.md on case-insensitive FS)
            inode = fpath.stat().st_ino
            if inode in seen_inodes:
                continue
            seen_inodes.add(inode)

            content = fpath.read_text(errors="replace")
            # Truncate very large files
            if len(content) > 8000:
                content = content[:8000] + "\n\n... [truncated]"
            if content.strip():
                sources.append(Source(
                    category="codebase",
                    name=fname,
                    content=content,
                ))
    return sources


def gather_git_history(project_dir: str, commit_count: int = 20) -> list[Source]:
    """Scan recent git history — commits, branches, recent changes."""
    sources = []

    def run_git(args: list[str]) -> str | None:
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True, text=True, cwd=project_dir, timeout=10,
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    # Recent commits
    log = run_git(["log", f"--oneline", f"-{commit_count}", "--no-decorate"])
    if log:
        sources.append(Source(
            category="git",
            name="recent_commits",
            content=log,
        ))

    # Current branch and status
    branch = run_git(["branch", "--show-current"])
    status = run_git(["status", "--short"])
    if branch or status:
        sources.append(Source(
            category="git",
            name="current_state",
            content=f"Branch: {branch or 'unknown'}\n\nStatus:\n{status or 'clean'}",
        ))

    # Recent diff (staged + unstaged, limited)
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

    # Look for priority/todo files
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
    memory_paths: list[str] | None = None,
    max_depth: int = 3,
    commit_count: int = 20,
) -> GatheredSources:
    """Gather all sources from a project directory.

    Returns a GatheredSources object containing everything the priming
    engine needs to work with.
    """
    all_sources = []
    all_sources.extend(gather_memories(project_dir, memory_paths))
    all_sources.extend(gather_codebase(project_dir, max_depth))
    all_sources.extend(gather_git_history(project_dir, commit_count))
    all_sources.extend(gather_project_config(project_dir))

    return GatheredSources(
        sources=all_sources,
        project_dir=project_dir,
    )
