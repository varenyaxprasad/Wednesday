
from pathlib import Path
from mcp.server.fastmcp import FastMCP
import subprocess

mcp = FastMCP("Wednesday Local Files")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = (PROJECT_ROOT / "workspace").resolve()
USER_HOME = Path.home().resolve()

MAX_READ_SIZE = 1_000_000

BLOCKED_NAMES = {
    "library",
    ".ssh",
    ".gnupg",
    ".aws",
    ".azure",
    "keychains",
    "browser-profile",
    "node_modules",
    ".venv",
    ".git",
}

BLOCKED_SUFFIXES = {
    ".pem", ".key", ".p12", ".pfx",
}

BLOCKED_FILES = {
    ".env",
    ".env.local",
    ".env.production",
    "credentials",
    "id_rsa",
    "id_ed25519",
}


# --------------------------------------------------
# SECURITY: USER FILE ACCESS
# --------------------------------------------------

def safe_user_path(path: str) -> Path:
    """Allow access inside the user's home, excluding protected paths."""

    candidate = Path(path).expanduser()

    if not candidate.is_absolute():
        candidate = USER_HOME / candidate

    # Reject symbolic links before resolving them.
    current = candidate

    while current != current.parent:
        if current.is_symlink():
            raise ValueError("Access denied: symbolic links are not allowed.")
        current = current.parent

    candidate = candidate.resolve()

    if candidate != USER_HOME and USER_HOME not in candidate.parents:
        raise ValueError("Access denied: outside your user folder.")

    parts = {part.casefold() for part in candidate.parts}
    filename = candidate.name.casefold()

    if parts & BLOCKED_NAMES:
        raise ValueError("Access denied: protected folder.")

    if filename.startswith("."):
        raise ValueError("Access denied: hidden files are protected.")

    if filename in BLOCKED_FILES:
        raise ValueError("Access denied: protected file.")

    if candidate.suffix.lower() in BLOCKED_SUFFIXES:
        raise ValueError("Access denied: sensitive file type.")

    return candidate


# --------------------------------------------------
# USER FILE TOOLS
# --------------------------------------------------

@mcp.tool()
def list_user_files(folder: str = ".") -> str:
    """List accessible files and folders in the user's Mac account."""

    target = safe_user_path(folder)

    if not target.is_dir():
        raise NotADirectoryError(f"Directory not found: {folder}")

    entries = []

    for item in sorted(target.iterdir()):
        try:
            safe_user_path(str(item))

            kind = "DIR" if item.is_dir() else "FILE"
            entries.append(f"{kind}: {item.name}")

        except (ValueError, OSError):
            continue

    return "\n".join(entries) if entries else "No accessible files found."


@mcp.tool()
def read_user_file(path: str) -> str:
    """Read a UTF-8 text file from an accessible user folder."""

    target = safe_user_path(path)

    if not target.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    if target.stat().st_size > MAX_READ_SIZE:
        raise ValueError("File is too large to read. Maximum size is 1 MB.")

    try:
        return target.read_text(encoding="utf-8")

    except UnicodeDecodeError:
        return "This is not a UTF-8 text file. Open it using its default application."

    except OSError as error:
        return f"Error reading file: {error}"


@mcp.tool()
def open_user_file(path: str) -> str:
    """Open an accessible file using its default macOS application."""

    target = safe_user_path(path)

    if not target.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    subprocess.Popen(["open", str(target)])

    return f"Opened: {target.name}"


# --------------------------------------------------
# FINDER TOOLS
# --------------------------------------------------

@mcp.tool()
def open_finder(folder: str = ".") -> str:
    """Open Finder at an accessible folder."""

    target = safe_user_path(folder)

    if not target.is_dir():
        raise NotADirectoryError(f"Folder not found: {folder}")

    subprocess.Popen(["open", str(target)])

    return f"Opened Finder at: {target}"


@mcp.tool()
def finder_select_file() -> str:
    """Show a macOS file picker and return the selected accessible file."""

    script = '''
    set selectedFile to choose file with prompt "Choose a file for Wednesday"
    return POSIX path of selectedFile
    '''

    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return "File selection cancelled or unavailable."

    try:
        target = safe_user_path(result.stdout.strip())

        if not target.is_file():
            return "Please select a file."

        return f"Selected file: {target}"

    except (ValueError, OSError) as error:
        return f"Access denied: {error}"


@mcp.tool()
def finder_select_folder() -> str:
    """Show a macOS folder picker and return the selected accessible folder."""

    script = '''
    set selectedFolder to choose folder with prompt "Choose a folder for Wednesday"
    return POSIX path of selectedFolder
    '''

    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return "Folder selection cancelled or unavailable."

    try:
        target = safe_user_path(result.stdout.strip())

        if not target.is_dir():
            return "Please select a folder."

        return f"Selected folder: {target}"

    except (ValueError, OSError) as error:
        return f"Access denied: {error}"


# --------------------------------------------------
# WORKSPACE SECURITY
# --------------------------------------------------

def is_inside_workspace(path: Path) -> bool:
    return path == WORKSPACE or WORKSPACE in path.parents


def safe_workspace_path(filename: str) -> Path:
    """Resolve a workspace path and reject traversal and symbolic links."""

    relative_path = Path(filename)

    if not filename.strip() or relative_path.is_absolute():
        raise ValueError("Provide a valid relative workspace path.")

    target = WORKSPACE / relative_path

    current = target

    while current != WORKSPACE and WORKSPACE in current.parents:
        if current.is_symlink():
            raise ValueError("Symbolic links are not allowed.")
        current = current.parent

    target = target.resolve()

    if not is_inside_workspace(target):
        raise ValueError("Access denied: outside workspace.")

    return target


# --------------------------------------------------
# WORKSPACE TOOLS
# --------------------------------------------------

@mcp.tool()
def list_workspace_files() -> str:
    """List files inside Wednesday's workspace."""

    WORKSPACE.mkdir(parents=True, exist_ok=True)

    results = []

    for path in WORKSPACE.rglob("*"):
        if path.is_symlink():
            continue

        resolved = path.resolve()

        if is_inside_workspace(resolved) and resolved.is_file():
            results.append(str(resolved.relative_to(WORKSPACE)))

    return "\n".join(sorted(results)) if results else "The workspace is empty."


@mcp.tool()
def create_workspace_file(filename: str, content: str) -> str:
    """Create a new file inside workspace without overwriting existing files."""

    WORKSPACE.mkdir(parents=True, exist_ok=True)

    try:
        target = safe_workspace_path(filename)

        if target.exists():
            return "Error: File already exists. It was not overwritten."

        if not target.parent.is_dir():
            return "Error: Destination folder does not exist."

        with target.open("x", encoding="utf-8") as file:
            file.write(content)

        return f"Successfully created: {target.relative_to(WORKSPACE)}"

    except (ValueError, OSError) as error:
        return f"Error creating file: {error}"


@mcp.tool()
def read_workspace_file(filename: str) -> str:
    """Read a UTF-8 text file inside workspace."""

    try:
        target = safe_workspace_path(filename)

        if not target.is_file():
            return "Error: File not found."

        if target.stat().st_size > MAX_READ_SIZE:
            return "Error: File exceeds the 1 MB read limit."

        return target.read_text(encoding="utf-8")

    except (ValueError, OSError, UnicodeError) as error:
        return f"Error reading file: {error}"


@mcp.tool()
def edit_workspace_file(filename: str, content: str) -> str:
    """Edit an existing UTF-8 text file inside workspace."""

    try:
        target = safe_workspace_path(filename)

        if not target.is_file():
            return "Error: Existing file not found."

        with target.open("r+", encoding="utf-8") as file:
            file.seek(0)
            file.write(content)
            file.truncate()

        return f"Successfully updated: {target.relative_to(WORKSPACE)}"

    except (ValueError, OSError, UnicodeError) as error:
        return f"Error editing file: {error}"


# --------------------------------------------------
# START MCP SERVER
# --------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
