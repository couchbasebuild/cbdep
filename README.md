# cbdep - Generalized Tool Installer

`cbdep` is a command-line tool for installing and managing development dependencies and tools. It provides a simple interface to download and install various packages with automatic platform detection and caching.

## Installation

The easiest way to install `cbdep` is using `uv`:

```bash
uv tool install cbdep
```

This will install `cbdep` to `~/.local/bin/` (or the equivalent on Windows). Make sure this directory is on your `PATH`.

### Alternative: Using the Wrapper Script

For CI/CD environments or systems where you don't want to pre-install tools, you can use the wrapper script which automatically installs and updates `cbdep` via `uv`:

**Linux/macOS:**
```bash
curl -qLsSf https://packages.couchbase.com/cbdep/latest/cbdep -O
chmod +x cbdep
./cbdep install <package> <version>
```

**Windows:**
```powershell
# Download cbdep.exe from packages.couchbase.com
.\cbdep.exe install <package> <version>
```

The wrapper script will automatically install `uv` if needed, then install/update `cbdep` itself.

## Usage

### List Available Packages

See all packages that can be installed:

```bash
cbdep list
```

### Install a Package

Install a specific version of a package:

```bash
cbdep install <package> <version>
```

For example:

```bash
cbdep install golang 1.21.0
cbdep install cmake 3.25.0
```

By default, packages are installed to the `./install` directory. You can specify a different location:

```bash
cbdep install golang 1.21.0 --dir /opt/tools
```

### Cache Management

Cache a download without installing:

```bash
cbdep cache <url>
```

Get the cached filename:

```bash
cbdep cache <url> --report
```

Save a cached file locally:

```bash
cbdep cache <url> --output ./myfile.tar.gz
```

### Platform Information

Display detected platform and architecture:

```bash
cbdep platform
```

Override platform or architecture detection:

```bash
cbdep --platform linux --arch arm64 install golang 1.21.0
```

## Options

Global options:
- `--debug` - Enable debug output
- `-p, --platform <platform>` - Override detected platform
- `-a, --arch <arch>` - Override detected architecture
- `-V, --version` - Show version information

Install options:
- `-d, --dir <directory>` - Installation directory (default: `./install`)
- `-c, --config-file <file>` - Use custom YAML configuration file
- `-n, --cache-only` - Only download, don't install
- `-r, --report` - Report cached filename
- `-o, --output <file>` - Save cached file to local path
- `--recache` - Re-download files, replacing cache

## Configuration

`cbdep` includes a built-in configuration file that defines available packages and their download locations. You can also provide a custom configuration file with `--config-file`.

Downloaded files are cached in `~/.cbdepcache` to avoid repeated downloads.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for information about development, testing, and publishing.

## License

See [LICENSE.txt](LICENSE.txt) for license information.
