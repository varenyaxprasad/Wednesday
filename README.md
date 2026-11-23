# Wednesday — Personal AI Assistant

**Wednesday** is a Python-based AI-powered personal assistant designed to interact with users through natural language and execute real-world tasks using AI, voice processing, and Model Context Protocol (MCP) tools.

Powered by **Groq LLM and LangChain**, Wednesday understands user instructions, determines the appropriate actions, and connects with external tools to perform tasks on the user's behalf.

The project combines conversational AI, voice interaction, persistent memory, and system automation into a single personal assistant.

---

##  Features

###  AI Intelligence
- Groq-powered LLM for natural language understanding and response generation.
- LangChain-based agent architecture.
- Understands user instructions and determines when external tools are required.
- Dynamically selects tools based on user intent.

###  Voice Interaction
- Speech-to-text using OpenAI Whisper.
- Voice Activity Detection (VAD) using Silero VAD.
- Text-to-speech using Kokoro TTS.
- Supports both text-based and voice-based interaction.

###  MCP Tool Integration
Wednesday uses the **Model Context Protocol (MCP)** to connect its AI agent with external tools and services.

Current integrations include:

- **File System:** List, read, and create files within the permitted workspace.
- **Browser Automation:** Open websites and interact with browser tabs.
- **Android Device Control:** Interact with an Android device, including application-level operations.

###  Persistent Memory
- SQLite-based conversation memory.
- Stores conversational context across interactions.
- Allows Wednesday to maintain continuity between conversations.

### System Automation
- Open websites and browser tabs.
- Access files within the permitted workspace.
- Perform supported Android device operations.
- Execute actions through connected tools rather than merely generating textual instructions.

---

##  Tech Stack

| Technology | Purpose |
|---|---|
| Python | Core development |
| Groq | LLM inference |
| LangChain | Agent orchestration |
| MCP | External tool integration |
| Whisper | Speech recognition |
| Silero VAD | Voice activity detection |
| Kokoro TTS | Speech generation |
| SQLite | Persistent memory |
| ADB | Android device interaction |

---

##  Architecture

Wednesday follows an AI agent architecture in which the LLM acts as the decision-making component.

```text
             USER INPUT
                  |
          Text / Voice Input
                  |
          Speech-to-Text
             (Whisper)
                  |
                  v
          LANGCHAIN AGENT
                  |
             GROQ LLM
                  |
          Intent Understanding
                  |
          Tool Selection
                  |
           MCP CLIENT
                  |
       +----------+----------+
       |          |          |
       v          v          v
    File MCP  Browser MCP  Android
       |          |       Integration
       v          v          v
   File Tasks  Web Tasks  Device Tasks
       |          |          |
       +----------+----------+
                  |
            Tool Response
                  |
           LLM Processing
                  |
          Response Generation
                  |
          +-------+-------+
          |               |
       Text Output     Kokoro TTS
                          |
                     Voice Output

          SQLite Memory
          (Conversation Context)
```

### How Wednesday Works

1. **User Input:** The user provides an instruction through text or voice.
2. **Speech Processing:** If the input is voice, Whisper converts speech into text.
3. **Understanding:** The LangChain agent sends the instruction to the Groq-powered LLM.
4. **Decision Making:** The LLM determines whether the request requires a connected tool.
5. **Tool Execution:** The MCP client connects to the appropriate MCP server and executes the requested operation.
6. **Response:** The tool result is returned to the agent, which generates a natural-language response.
7. **Memory:** SQLite maintains conversational context for future interactions.
8. **Voice Output:** Kokoro TTS converts the response into speech when voice output is enabled.

---

##  Project Structure

```text
Wednesday/
│
├── src/
│   ├── brain/
│   │   ├── llm.py
│   │   └── ...
│   │
│   ├── voice/
│   │   ├── speech_to_text.py
│   │   ├── tts.py
│   │   └── ...
│   │
│   ├── tools/
│   │   └── ...
│   │
│   └── ...
│
├── mcp_servers/
│   └── ...
│
├── memory/
│   └── ...
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

*The directory tree is illustrative. Update it to match the actual repository structure.*

---

##  Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/Wednesday.git
cd Wednesday
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it:

**macOS / Linux**
```bash
source venv/bin/activate
```

**Windows**
```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root.

```env
GROQ_API_KEY=your_groq_api_key
```

Add any additional configuration required by your MCP servers and voice components.

Get your Groq API key from:

https://console.groq.com/

### 5. Configure MCP Servers

Configure the MCP server connections according to the project's MCP configuration.

Ensure that:
- Required MCP servers are installed.
- Their dependencies are available.
- Server commands and paths are correctly configured.
- Android device access is configured where required.

### 6. Run Wednesday

Run the project's main entry-point script:

```bash
python <main-entry-file>.py
```

Replace the placeholder with the actual entry-point filename.

---

## Security Considerations

Wednesday interacts with local files, browsers, and external devices. Security is an important part of its design.

- API keys and credentials should be stored in environment variables.
- Never commit `.env` files or API keys to GitHub.
- File operations should remain restricted to authorized workspaces.
- Sensitive operations should require appropriate user confirmation.
- MCP servers should only receive the permissions they need.

---

##  Future Improvements

Potential areas of development include:

- Advanced multi-agent orchestration.
- Gmail integration and email automation.
- Calendar and scheduling integration.
- More advanced browser automation.
- Improved conversational memory and context retrieval.
- Expanded Android automation.
- Better task planning and execution.
- A graphical user interface.

---

##  Project Objective

The primary objective of Wednesday is to build an intelligent personal assistant that goes beyond answering questions.

Instead of simply responding to user instructions, Wednesday aims to understand intent, make decisions, interact with external tools, and execute tasks in the real world.

**The vision: An AI assistant that doesn't just tell you what to do — it helps you get it done.**

---

##  Author

**Varenya Prasad**

GitHub: https://github.com/YOUR_USERNAME

---

*Built with Python, Groq, LangChain, MCP, and open-source voice technologies.*
