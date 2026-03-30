# Contributing to Context Priming

Contributions are welcome. This document covers how to get involved.

## Getting Started

1. Fork the repo and clone your fork.
2. Install in development mode:

```bash
pip install -e ".[all]"
```

3. Create a branch for your change:

```bash
git checkout -b your-feature
```

## What to Work On

- Bug fixes and test coverage
- New source gatherers (e.g., issue trackers, documentation sites)
- New adapters for other coding agents (Cursor, Copilot, Aider)
- Performance improvements to the scoring pipeline
- Documentation improvements

## Code Style

- Python 3.11+ with type hints
- Keep functions small and focused
- Every LLM call should accept a `callable(prompt) -> str` -- keep the core engine model-agnostic
- No unnecessary dependencies

## Submitting Changes

1. Write clear commit messages that explain _why_, not just _what_.
2. Add tests for new functionality.
3. Open a pull request against `main`.
4. Describe what your PR does and link any related issues.

## Reporting Issues

Open a GitHub issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Python version and OS

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
