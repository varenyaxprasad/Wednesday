
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Wednesday Local Files")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = (PROJECT_ROOT / "workspace").resolve()


def is_inside_workspace(path: Path) -> bool:
    return path == WORKSPACE or WORKSPACE in path.parents


@mcp.tool()
def list_workspace_files() -> str:
    """List files in Wednesday's approved workspace folder."""
    WORKSPACE.mkdir(parents=True, exist_ok=True)

    results = []

    for path in WORKSPACE.rglob("*"):
        if path.is_symlink():
            continue

        resolved = path.resolve()

        if not is_inside_workspace(resolved):
            continue

        if resolved.is_file():
            results.append(str(resolved.relative_to(WORKSPACE)))

    if not results:
        return "The workspace is empty. No files were found."

    return "\n".join(sorted(results))


@mcp.tool()
def create_workspace_file(filename: str, content: str) -> str:
    """Create a text file inside the approved workspace folder."""
    WORKSPACE.mkdir(parents=True, exist_ok=True)

    relative_path = Path(filename)

    if relative_path.is_absolute():
        return "Error: Absolute paths are not allowed."

    if not filename.strip() or relative_path.name in {"", ".", ".."}:
        return "Error: Provide a valid filename."

    target = (WORKSPACE / relative_path).resolve()

    if not is_inside_workspace(target):
        return "Error: Files can only be created inside the workspace."

    if target.exists():
        return "Error: That file already exists. It was not overwritten."

    if not target.parent.is_dir():
        return "Error: The destination folder does not exist."

    if target.is_symlink():
        return "Error: Symbolic links are not allowed."

    try:
        with target.open("x", encoding="utf-8") as file:
            file.write(content)

        return f"Successfully created {target.relative_to(WORKSPACE)}."

    except FileExistsError:
        return "Error: That file already exists. It was not overwritten."

    except OSError as error:
        return f"Error creating file: {error}"


@mcp.tool()
def read_workspace_file(filename: str) -> str:
    """Read a UTF-8 text file inside the approved workspace folder."""
    WORKSPACE.mkdir(parents=True, exist_ok=True)

    relative_path = Path(filename)

    if relative_path.is_absolute():
        return "Error: Absolute paths are not allowed."

    if not filename.strip() or relative_path.name in {"", ".", ".."}:
        return "Error: Provide a valid filename."

    target = (WORKSPACE / relative_path).resolve()

    if not is_inside_workspace(target):
        return "Error: Files can only be read inside the workspace."

    if not target.is_file() or target.is_symlink():
        return "Error: File not found or not a regular file."

    try:
        return target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "Error: This tool only reads UTF-8 text files."
    except OSError as error:
        return f"Error reading file: {error}"
    
    
@mcp.tool()
def edit_workspace_file(filename: str, content: str) -> str:
    """Replace the contents of an existing UTF-8 text file in the workspace."""
    WORKSPACE.mkdir(parents=True, exist_ok=True)

    relative_path = Path(filename)

    if relative_path.is_absolute():
        return "Error: Absolute paths are not allowed."

    if not filename.strip() or relative_path.name in {"", ".", ".."}:
        return "Error: Provide a valid filename."

    target = (WORKSPACE / relative_path).resolve()

    if not is_inside_workspace(target):
        return "Error: Files can only be edited inside the workspace."

    if target.is_symlink() or not target.is_file():
        return "Error: Existing regular file not found."

    try:
        with target.open("r+", encoding="utf-8") as file:
            file.seek(0)
            file.write(content)
            file.truncate()

        return f"Successfully updated {target.relative_to(WORKSPACE)}."

    except (OSError, UnicodeError) as error:
        return f"Error editing file: {error}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
