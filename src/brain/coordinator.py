
import asyncio
import json
import re
import sys

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

from src.brain.llm import model, chat_history as original_history
from src.brain.memory import initialize_memory, load_history, save_exchange
from src.voice.speech_to_text import listen_and_transcribe
from src.voice.tts import speak

from contextlib import AsyncExitStack
from langchain_mcp_adapters.tools import load_mcp_tools

SYSTEM_PROMPT = original_history[0].content

SYSTEM_PROMPT += """

BROWSER INTENT RULES:
- Always prioritise the user's latest explicit instruction.
- Previous conversation history must not override a new command.
- "Open Chrome" means open the browser, not YouTube.
- "Open YouTube" means navigate to YouTube.
- "Search YouTube for X" means use browser_youtube_search.
- "Play X on YouTube" means use browser_youtube_play.
- If Wednesday has just asked the user for a song or video title after opening YouTube, interpret the next title/query as a PLAY request.
- In that situation, call browser_youtube_play, not browser_youtube_search.
- Pass the complete song title and artist as the query when known.
- Never claim a video is playing unless playback is verified.
- If YouTube requires verification, ask the user to complete it manually.
- Do not repeatedly retry blocked pages.
- Wait for the playback tool result before responding.
"""

SYSTEM_PROMPT += """

MAC FILE AND FINDER RULES:

1. FINDER
- If the user says "open Finder" without specifying a folder,
  call open_finder with {"folder": "."}.
- Never pass null for the folder argument.
- If the user specifies a folder, pass its path as a string.
- If the user specifies a folder, pass that folder to open_finder.
- If the user asks to choose or select a file, call finder_select_file.
- If the user asks to choose or select a folder, call finder_select_folder.

2. FILE DISCOVERY
- If the user asks to find or list files in a folder, call list_user_files.
- Use the folder path supplied by the user.
- Relative paths are relative to the user's home folder.

3. READING FILES
- If the user asks to read a file, call read_user_file.
- Use the exact path returned by Finder or file discovery.
- Never invent a file path.

4. OPENING FILES
- If the user asks to open a file, call open_user_file.
- If the file was selected using Finder, use the returned path.
- Do not claim a file was opened unless the tool succeeds.

5. SECURITY
- Never attempt to bypass protected-file restrictions.
- Never read hidden files, credentials, API keys or protected folders.
- Never modify or delete user files without explicit approval.
- Use workspace creation and editing workflows for workspace files.
- Do not claim access to a file if macOS denies permission.

6. TOOL SELECTION
- Use Finder tools for opening Finder and selecting files or folders.
- Use list_user_files for browsing file names.
- Use read_user_file for reading file contents.
- Use open_user_file for opening files in their default applications.
"""

FILE_DRAFT_PROMPT = """
You prepare files for Wednesday, a personal assistant.

The user wants a file prepared for review before it is saved.

Return ONLY a valid JSON object with these two string fields:
{
"filename": "example.py",
"content": "print('Hello World')"
}

Rules:
- filename must be a relative path inside the workspace.
- Never use an absolute path or .. path traversal.
- Generate the complete requested file content.
- Preserve code indentation and newlines.
- Do not use Markdown fences around the JSON.
- Do not claim the file has been saved.
- If revising a draft, return the entire revised file.
"""


def extract_text(content):
    """Convert supported LangChain content formats into plain text."""
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                if text:
                    parts.append(text)
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts).strip()

    return str(content).strip()


def is_file_request(text):
    """Recognize common explicit requests to create a new file."""
    patterns = [
        r"\bcreate\b.{0,50}\bfile\b",
        r"\bmake\b.{0,50}\bfile\b",
        r"\bwrite\b.{0,50}\bfile\b",
        r"\bgenerate\b.{0,50}\bfile\b",
        r"\bcreate\b.{0,50}\bscript\b",
        r"\bmake\b.{0,50}\bscript\b",
        r"\bwrite\b.{0,50}\bscript\b",
        r"\bsave\b.{0,40}\bas\b.{0,40}\bfile\b",
    ]
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def parse_draft(raw):
    """Parse the JSON draft returned by the LLM."""
    raw = raw.strip()

    # Tolerate accidental JSON Markdown fences.
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    start = raw.find("{")
    end = raw.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("The model did not return a valid JSON draft.")

    draft = json.loads(raw[start:end + 1])

    filename = draft.get("filename")
    content = draft.get("content")

    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("The draft has no valid filename.")

    if not isinstance(content, str):
        raise ValueError("The draft has no valid file content.")

    return {"filename": filename.strip(), "content": content}


def is_approval(text):
    return text.lower().strip().rstrip(".!?") in {
        "yes", "yes save", "save", "save it", "approve",
        "approved", "confirm", "confirmed", "go ahead",
        "do it", "proceed", "save the file",
    }


def is_cancellation(text):
    return text.lower().strip().rstrip(".!?") in {
        "no", "cancel", "cancel it", "discard", "discard it",
        "don't save", "do not save", "never mind", "nevermind",
    }


def is_revision(text):
    return text.lower().strip().rstrip(".!?") in {
        "change it", "revise it", "edit it", "modify it",
        "make changes", "try again",
    }


def safe_filename(filename):
    """Reject paths that are clearly unsafe before calling MCP."""
    from pathlib import PurePosixPath, PureWindowsPath

    path = PurePosixPath(filename)
    windows_path = PureWindowsPath(filename)

    if (
        not filename.strip()
        or path.is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or ".." in path.parts
        or "\\" in filename
        or path.name in {"", ".", ".."}
    ):
        raise ValueError(
            "Use a relative filename inside the workspace, "
            "without parent-directory traversal."
        )

    return filename



async def prepare_draft(request, previous_draft=None, revision=None):
    """Generate a draft without writing anything to disk."""
    previous_draft_text = (
        json.dumps(previous_draft, ensure_ascii=False)
        if previous_draft is not None
        else "None"
    )

    messages = [
        SystemMessage(content=FILE_DRAFT_PROMPT),
        HumanMessage(
            content=(
                f"Original request:\n{request}\n\n"
                f"Previous draft:\n{previous_draft_text}\n\n"
                f"Requested changes:\n{revision or 'None'}\n\n"
                "Prepare the complete file and return the required JSON."
            )
        ),
    ]

    response = await model.ainvoke(messages)
    draft = parse_draft(extract_text(response.content))
    draft["filename"] = safe_filename(draft["filename"])

    return draft



async def main():
    initialize_memory()
    conversation_history = load_history()
    voice_mode = "--text" not in sys.argv

    # A draft remains in memory until approved or cancelled.
    pending_draft = None
    original_request = None



    client = MultiServerMCPClient(
        {
            "local_files": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", "src.tools.local_files_server"],
            },
            "android": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", "src.tools.android_communication_server"],
            },
            "browser": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", "src.tools.browser_automation_server"],
            },
        }
    )


    stack = AsyncExitStack()
    
    try:
        
        await stack.__aenter__()

        browser_session = await stack.enter_async_context(
            client.session("browser")
        )
        browser_tools = await load_mcp_tools(browser_session)

        file_tools = await client.get_tools(server_name="local_files")
        android_tools = await client.get_tools(server_name="android")

        tools = file_tools + android_tools + browser_tools

        print("\n" + "=" * 45)
        print("Wednesday MCP tools")
        print("=" * 45)

        for tool in tools:
            print(f"- {tool.name}: {tool.description}")

        # Prevent the normal agent from bypassing the confirmation
        # workflow through direct file creation or editing calls.
        agent_tools = [
            tool for tool in tools
            if not (
                tool.name.endswith("create_workspace_file")
                or tool.name.endswith("edit_workspace_file")
            )
        ]

        tool_by_suffix = {
            tool.name.split("__")[-1]: tool
            for tool in tools
        }

        create_tool = next(
            (
                tool for tool in tools
                if tool.name.endswith("create_workspace_file")
            ),
            None,
        )

        if create_tool is None:
            raise RuntimeError(
                "The MCP create_workspace_file tool was not found."
            )

        agent = create_agent(
            model=model,
            tools=agent_tools,
            system_prompt=SYSTEM_PROMPT,
        )

        print(
            f"\nLoaded {len(conversation_history) // 2} "
            "previous exchanges."
        )

        if voice_mode:
            print("\nWednesday is ready in voice mode.")
            print("Say 'exit' to stop.")
            await asyncio.to_thread(
                speak, "Wednesday is ready. How can I help you?"
            )
        else:
            print("\nWednesday is ready in text mode.")
            print("Type 'exit' or 'quit' to stop.")

        while True:
            try:
                if voice_mode:
                    print("\nListening...")
                    query = await asyncio.to_thread(listen_and_transcribe)

                    if not query or not str(query).strip():
                        print("No speech detected. Listening again.")
                        continue

                    query = str(query).strip()
                    print(f"\nVarenya: {query}")
                else:
                    query = await asyncio.to_thread(
                        input, "\nVarenya: "
                    )
                    query = query.strip()

                if not query:
                    continue

                if query.lower().rstrip(".!?") in {
                    "exit", "quit", "stop", "shut down"
                }:
                    print("\nWednesday shutting down.")
                    if voice_mode:
                        await asyncio.to_thread(
                            speak, "Goodbye, Varenya."
                        )
                    break

                # -------------------------------------------------
                # 1. Handle an existing pending draft FIRST.
                # -------------------------------------------------
                if pending_draft is not None:

                    if is_approval(query):
                        print(
                            f"\nSaving approved file: "
                            f"{pending_draft['filename']}"
                        )

                        result = await create_tool.ainvoke(
                            {
                                "filename": pending_draft["filename"],
                                "content": pending_draft["content"],
                            }
                        )

                        result_text = extract_text(result)
                        print(f"\nWednesday: {result_text}")

                        if voice_mode:
                            await asyncio.to_thread(
                                speak, result_text
                            )

                        # Clear the draft only after a successful save.
                        if result_text.lower().startswith(
                            "successfully created"
                        ):
                            save_exchange(
                                f"Create file: {original_request}",
                                (
                                    f"User approved and saved "
                                    f"{pending_draft['filename']}."
                                ),
                            )
                            pending_draft = None
                            original_request = None

                        continue

                    if is_cancellation(query):
                        pending_draft = None
                        original_request = None

                        reply = (
                            "Draft discarded. No file was saved."
                        )
                        print(f"\nWednesday: {reply}")

                        if voice_mode:
                            await asyncio.to_thread(speak, reply)

                        continue

                    # Any other response while a draft is pending
                    # is treated as a revision request, not approval.
                    if is_revision(query) or query:
                        print("\nRevising the draft...")

                        revised = await prepare_draft(
                            original_request,
                            previous_draft=pending_draft,
                            revision=query,
                        )

                        pending_draft = revised

                        review = (
                            f"Revised file: {revised['filename']}.\n"
                            "Proposed content follows:\n\n"
                            f"{revised['content']}\n\n"
                            "Do you approve saving this file? "
                            "Say yes to save, or ask for changes. "
                            "Say cancel to discard it."
                        )

                        print(f"\nWednesday: {review}")

                        if voice_mode:
                            await asyncio.to_thread(speak, review)

                        continue

                # -------------------------------------------------
                # 2. Start a new file creation request.
                # -------------------------------------------------
                if is_file_request(query):
                    try:
                        draft = await prepare_draft(query)
                    except (ValueError, json.JSONDecodeError) as error:
                        reply = (
                            "I couldn't prepare a valid file draft. "
                            f"{error} Please describe the file again."
                        )
                        print(f"\nWednesday: {reply}")

                        if voice_mode:
                            await asyncio.to_thread(speak, reply)

                        continue

                    pending_draft = draft
                    original_request = query

                    review = (
                        f"I have prepared {draft['filename']}.\n"
                        "I have not saved it.\n"
                        "Here is the proposed content:\n\n"
                        f"{draft['content']}\n\n"
                        "Do you approve saving this file? "
                        "Say yes to save, or ask for changes. "
                        "Say cancel to discard it."
                    )

                    print(f"\nWednesday: {review}")

                    if voice_mode:
                        await asyncio.to_thread(speak, review)

                    continue

                # -------------------------------------------------
                # 3. Normal assistant conversation and MCP tools.
                # -------------------------------------------------
                result = await agent.ainvoke(
                    {
                        "messages": (
                            conversation_history
                            + [HumanMessage(content=query)]
                        )
                    }
                )

                final_message = next(
                    (
                        message
                        for message in reversed(result["messages"])
                        if isinstance(message, AIMessage)
                        and not getattr(message, "tool_calls", None)
                        and extract_text(message.content)
                    ),
                    None,
                )

                if final_message is None:
                    print("\nWednesday: No response was generated.")
                    continue

                reply = extract_text(final_message.content)
                print(f"\nWednesday: {reply}")

                save_exchange(query, reply)

                conversation_history.extend(
                    [
                        HumanMessage(content=query),
                        AIMessage(content=reply),
                    ]
                )
                conversation_history = conversation_history[-20:]

                if voice_mode:
                    await asyncio.to_thread(speak, reply)

            except KeyboardInterrupt:
                print("\n\nWednesday shutting down.")
                break

            except EOFError:
                print("\nWednesday shutting down.")
                break

            except Exception as error:
                print(
                    f"\nWednesday error: "
                    f"{type(error).__name__}: {error}"
                )

    finally:
        await stack.aclose()

if __name__ == "__main__":
    asyncio.run(main())
