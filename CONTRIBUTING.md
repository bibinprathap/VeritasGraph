# Contributing to VeritasGraph

First off, thank you for taking the time to contribute! 🎉 VeritasGraph is a
governed, on-prem GraphRAG and agent framework, and contributions of all kinds
are welcome — code, documentation, bug reports, feature ideas, and more.

This document explains how to get involved and the conventions we follow.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Ways to Contribute](#ways-to-contribute)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Commit Messages](#commit-messages)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Enhancements](#suggesting-enhancements)
- [Security Issues](#security-issues)
- [License](#license)

## Code of Conduct

This project and everyone participating in it is governed by our
[Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to
uphold this code. Please report unacceptable behavior as described in the
[security policy](SECURITY.md).

## Ways to Contribute

- **Report bugs** using the bug report issue template.
- **Request features** using the feature request issue template.
- **Improve documentation** — fix typos, clarify instructions, add examples.
- **Submit code** — bug fixes, new features, performance improvements, tests.
- **Review pull requests** and help triage issues.

## Getting Started

1. **Fork** the repository and clone your fork locally:

   ```bash
   git clone https://github.com/<your-username>/VeritasGraph.git
   cd VeritasGraph
   ```

2. **Set up your environment** (Python 3.10+ is required):

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Create a branch** for your work:

   ```bash
   git checkout -b feature/short-description
   ```

## Development Workflow

- Keep changes focused. One pull request should address one concern.
- Add or update tests for any behavior you change.
- Update documentation (README, docstrings) when behavior or interfaces change.
- Run the test suite locally before pushing:

  ```bash
  pytest
  ```

## Coding Standards

- Target **Python 3.10+**.
- Follow [PEP 8](https://peps.python.org/pep-0008/) style conventions.
- Use clear, descriptive names and add docstrings to public functions/classes.
- Prefer small, readable functions over large, complex ones.
- Keep dependencies minimal; discuss new runtime dependencies in an issue first.

## Commit Messages

Write clear, descriptive commit messages. We encourage the
[Conventional Commits](https://www.conventionalcommits.org/) style:

```
feat: add graph traversal caching
fix: handle empty entity list in retriever
docs: clarify local setup instructions
test: add coverage for agent tool routing
```

## Submitting a Pull Request

1. Ensure your branch is up to date with the base branch.
2. Make sure tests pass and linting is clean.
3. Push your branch and open a pull request against the default branch.
4. Fill out the pull request template completely.
5. Link any related issues (e.g., `Closes #123`).
6. Be responsive to review feedback — maintainers may request changes.

## Reporting Bugs

Before opening a bug report, please search existing issues to avoid duplicates.
When filing a bug, use the **Bug report** template and include:

- A clear, descriptive title.
- Steps to reproduce the behavior.
- Expected vs. actual behavior.
- Environment details (OS, Python version, VeritasGraph version).
- Relevant logs, stack traces, or screenshots.

## Suggesting Enhancements

Use the **Feature request** template. Describe the problem you're trying to
solve, your proposed solution, and any alternatives you've considered.

## Security Issues

**Do not** open public issues for security vulnerabilities. Please follow the
responsible disclosure process in our [security policy](SECURITY.md).

## License

By contributing to VeritasGraph, you agree that your contributions will be
licensed under the [MIT License](LICENSE) that covers the project.
