import asyncio
import sys

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

from src.brain.llm import model, chat_history as original_history
from src.brain.memory import initialize_memory, load_history, save_exchange
from src.voice.speech_to_text import listen_and_transcribe
from src.voice.tts import speak

# Reuse the complete original prompt from llm.py without rewriting it.
SYSTEM_PROMPT = original_history[0].content


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

async def main():
    initialize_memory()
    conversation_history = load_history()
    voice_mode = "--text" not in sys.argv

    client = MultiServerMCPClient(
        {
            "local_files": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", "src.tools.local_files_server"],
            }
        }
    )

    try:
        tools = await client.get_tools()
        print("\n" + "=" * 45)
        print("Wednesday MCP tools")
        print("=" * 45)
        for tool in tools:
            print(f"- {tool.name}: {tool.description}")

        agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
        )

        print(f"\nLoaded {len(conversation_history) // 2} previous exchanges.")

        if voice_mode:
            print("\nWednesday is ready in voice mode. Speak into your microphone.")
            print("Say 'exit' to stop.")
            await asyncio.to_thread(speak, "Wednesday is ready. How can I help you?")
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
                    query = await asyncio.to_thread(input, "\nVarenya: ")
                    query = query.strip()

                if not query:
                    continue

                if query.lower().rstrip(".!?") in {"exit", "quit", "stop", "shut down"}:
                    print("\nWednesday shutting down.")
                    if voice_mode:
                        await asyncio.to_thread(speak, "Goodbye, Varenya.")
                    break

                result = await agent.ainvoke(
                    {"messages": conversation_history + [HumanMessage(content=query)]}
                )

                final_message = next(
                    (
                        message for message in reversed(result["messages"])
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
                    [HumanMessage(content=query), AIMessage(content=reply)]
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
                print(f"\nWednesday error: {type(error).__name__}: {error}")
    finally:
        close = getattr(client, "close", None)
        if close is not None:
            result = close()
            if asyncio.iscoroutine(result):
                await result


if __name__ == "__main__":
    asyncio.run(main())
