Wednesday --- Personal AI Assistant
Wednesday is a voice-enabled personal AI assistant built in Python. The project combines a Groq-powered language model, a LangChain agent/coordinator, speech input and output, persistent conversation memory, and MCP tools for working with local files.
Project status: This README documents the functionality confirmed working so far. Phone control, WhatsApp actions, YouTube playback/search integrations, and specialized agents are not presented as completed features.
Features implemented
LLM-powered assistant: Uses Groq with the openai/gpt-oss-120b model.
Agent orchestration: Uses LangChain to coordinate the model, conversation history, and MCP tools.
Voice input: Uses Whisper for speech-to-text, with Silero VAD for voice activity detection.
Voice output: Uses Kokoro text-to-speech and afplay for audio playback on macOS.
Persistent memory: Stores and retrieves conversation history using SQLite.
Bounded conversation context: Loads a limited recent history (20 messages) for the assistant.
Text mode: Supports running without voice using the --text option.
Local file tools through MCP: The assistant can discover and use tools to list, read, and create files in its configured workspace.
Confirmation before saving: For the implemented new-file workflow, Wednesday prepares a draft, presents/reads it to the user, and saves only after explicit approval. The user can request a revision or cancel.
Architecture
                 User
                  |
          Voice input / Text mode
                  |
       Whisper + Silero VAD (voice)
                  |
          Coordinator (LangChain)
                  |
        SQLite conversation memory
                  |
          Groq language model
        openai/gpt-oss-120b
                  |
          MCP tool discovery
                  |
        Local Files MCP Server
          |       |        |
        List     Read    Create
                           |
                Approval confirmation
                           |
                  Save to workspace
                  |
          Kokoro text-to-speech
                  |
              afplay (macOS)
Project structure
The following is the structure confirmed during development. Add other files or folders as they exist in your current repository.
Wednesday/
└── src/
    ├── brain/
    │   ├── coordinator.py
    │   ├── memory.py
    │   └── llm.py
    ├── tools/
    │   └── local_files_server.py
    └── voice/
        ├── speech_to_text.py
        ├── tts.py
        ├── microphone.py
        └── voice_test.py
Technology stack
Area                       Technology
Programming language       Python LLM provider/model         Groq --- openai/gpt-oss-120b Agent orchestration        LangChain Tool integration           Model Context Protocol (MCP) Speech recognition         Whisper Voice activity detection   Silero VAD Text-to-speech             Kokoro Audio playback             afplay (macOS) Persistent storage         SQLite
How the main components work
1. Coordinator
src/brain/coordinator.py acts as the central controller. It brings together the language model, conversation memory, voice interaction, and MCP tools. It also supports a text-only mode through the --text option.
2. Language model
src/brain/llm.py contains the LLM configuration used by the assistant. Wednesday uses the Groq-hosted openai/gpt-oss-120b model.
3. Persistent memory
src/brain/memory.py handles SQLite-based conversation memory. The coordinator loads recent history and saves exchanges so that context can be carried across interactions. The active context is bounded to 20 messages.
4. Voice interface
The voice components are separated under src/voice/:
speech_to_text.py --- speech recognition using Whisper.
microphone.py --- microphone/voice input handling, including the voice activity detection flow.
tts.py --- speech generation using Kokoro.
voice_test.py --- voice component testing.
On macOS, generated speech is played using afplay.
5. Local-files MCP server
src/tools/local_files_server.py exposes local workspace file operations through an MCP server using standard input/output (stdio) transport. The confirmed tool capabilities include:
Listing files in the configured workspace.
Reading files.
Creating new files.
The MCP client discovers the available tools and makes them available to the LangChain-based assistant. File operations are intended to remain within the configured workspace.
6. Safe new-file creation
The implemented new-file workflow is confirmation-first:
Wednesday prepares a proposed file draft.
The draft is presented to the user (and spoken in voice mode).
The user can approve, ask for a revision, or cancel.
The file-save tool is called only after approval.
The confirmed save behavior refuses to overwrite an existing file.
Running the project
The exact entry-point command and dependency versions should match the current repository. The coordinator was developed with both voice and text operation; text mode uses the --text option.
Typical development setup:
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install the dependencies listed by the project
pip install -r requirements.txt
Run the coordinator using the entry-point command configured in your repository. To use text mode, pass --text to the coordinator command.
The exact launch command, environment-variable names, and complete dependency list have not been confirmed in the project notes, so they are intentionally not guessed here.
Configuration and security
Keep API credentials in environment variables or a local .env file.
Do not commit API keys, tokens, database files containing private conversations, or other secrets.
Restrict the local-files MCP server to the intended workspace.
Review file drafts before approving a save.
Do not assume that a planned phone or messaging integration is active unless it has been separately configured and tested.
Current development status
Component                           Status
Groq LLM integration                Implemented
LangChain coordinator               Implemented
Whisper speech input                Implemented
Silero VAD                          Integrated in voice input
Kokoro speech output                Implemented
SQLite persistent memory            Implemented
Recent-history limit                Implemented (20 messages)
Text-only mode                      Implemented (--text)
Local-files MCP connection          Implemented
List/read/create file tools         Implemented
Confirmation-first new-file saving  Implemented and tested in the described workflow
Editing existing files with         Not confirmed complete approval
Persistent pending drafts across    Not confirmed complete restarts
Broader macOS control MCP           Planned / not confirmed complete
Android control over same-Wi-Fi ADB Planned / not confirmed complete
WhatsApp automation                 Not confirmed complete
YouTube search/playback integration Example/proposed, not confirmed complete
Specialized research, personal,     Planned / not confirmed complete communication, and knowledge agents
Roadmap
Potential next steps discussed during development:
Complete and test approval-based editing of existing files.
Decide whether pending drafts should survive application restarts.
Expand and test macOS control tools.
Build and test Android control through same-network ADB.
Investigate WhatsApp workflows while retaining user confirmation for sending.
Implement and verify YouTube search separately from playback/device control.
Develop specialized agents for research, personal assistance, communication, and knowledge management.
Improve speech output handling for long responses.
These are roadmap items, not claims about currently working functionality.
Notes
Wednesday is under active development. This README intentionally separates confirmed working components from proposed integrations so that the project documentation reflects the actual implementation rather than the full long-term vision.
