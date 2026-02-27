# Guidelines for Developping
for internal use

- we use **uv** as a package manager!
- we never work directly on main
- we use pre-commit to boost us towards clean code
- we only use english


## Setup
**install uv**
https://docs.astral.sh/uv/getting-started/installation/
macOS (with homebrew):
```cmd
brew install uv
```

Windows (with pip):
```cmd
pip install uv
```

**install ruff**
```cmd
uv tool install ruff
```

## Working with pre-commit & ruff
Check for errors: 
``` cmd
uv run ruff check .
```

Auto-fix errors:
``` cmd
uv run ruff check --fix .
```

Format your code:
``` cmd
uv run ruff format .
```
FYI: to change checking and formatting --> pyproject.toml
Further information: https://docs.astral.sh/ruff/