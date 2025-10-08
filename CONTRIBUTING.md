# Contributing to cbdep

## Development Setup

This project uses [uv](https://github.com/astral-sh/uv) for dependency management and [flit](https://flit.pypa.io/) as its build system.

To set up your development environment:

1. Install `uv` if you don't have it:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Clone the repository and navigate to the project directory

3. Install development dependencies:
   ```bash
   uv sync
   ```

## Running Tests

To run the test suite:

```bash
uv run pytest
```

**Note:** The integration tests in `tests/test_cbdep_install.py` are designed to run on **Linux** and download real packages from external sources. These tests will fail on macOS or Windows because the package configurations are platform-specific:

```bash
# Run full test suite
uv run pytest

# Or run specific test files
uv run pytest tests/test_cache.py tests/test_platform_introspection.py
```

For full integration testing, use a Linux environment (Docker, VM, or CI).

## Publishing

This project uses [flit](https://flit.pypa.io/) as its build system for ease of publishing.

### Prerequisites

Publishing requires credentials configured in `~/.pypirc`. See the [flit documentation](https://flit.pypa.io/en/stable/upload.html) for details on configuration.

Example `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-...

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-...
```

### Publishing to TestPyPI

It's recommended to first publish to TestPyPI to verify everything works:

```bash
uv run flit publish --repository testpypi
```

Then test the installation:

```bash
uv tool install --extra-index-url https://test.pypi.org/simple/ --index-strategy unsafe-best-match cbdep
```

**Notes:**
- Use `--extra-index-url` (not `--index-url`) so that dependencies can still be resolved from the main PyPI while the `cbdep` package itself comes from TestPyPI.
- The `--index-strategy unsafe-best-match` flag allows `uv` to find the best matching versions across all indexes, since TestPyPI doesn't have all dependency versions.

### Publishing to PyPI

Once verified, publish to the main PyPI repository:

```bash
uv run flit publish
```

## Project Structure

```
cbdep/
├── src/cbdep/          # Main package source
│   ├── cli.py          # Command-line interface
│   ├── install.py      # Installation logic
│   ├── cache.py        # Download caching
│   ├── cbdep.config    # Package configuration
│   └── ...
├── wrapper/            # Wrapper scripts for direct download
├── tests/              # Test suite
├── pyproject.toml      # Project metadata and dependencies
└── README.md           # User-facing documentation
```

## Wrapper Scripts

The `wrapper/` directory contains scripts that can be downloaded and run directly without pre-installing `cbdep`. These are primarily for CI/CD environments.

See [wrapper/README.md](wrapper/README.md) for more information about the wrapper scripts.
