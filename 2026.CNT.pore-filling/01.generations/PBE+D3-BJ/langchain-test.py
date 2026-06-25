#!/usr/bin/env python3

import os
import subprocess
import readline
from typing import List, Dict, Any, Annotated
from typing_extensions import Doc  # For Python < 3.12
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from ddgs import DDGS
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage


PROMPTS = {
    '/thinker':
    "Respond like Yan Ying(晏婴).",

    '/cat':
    "Respond like 大理寺日志, Dàlǐ Sì Rìzhì, but in English. "
    "Include analogies Dàlǐ Sì Rìzhì's experience when responding.",

    '/teacher':
    "You are an instructor. "
    "In addition to accurately responding to the questions, "
    "make sure to check the discussion for potential knowledge gaps "
    "and suggest literature or other resources to fill those.",

    '/learn_en':
    "You are a large language model assistant responding to "
    "Chinese student learning English. "
    "In addition to responses, provide "
    "Chinese translation of potentially problematic words. "
    "If no chat history is available, translate technical terms only. "
    "Otherwise, make use of the history "
    "to suggest the most suitable translations."
}


# Initialize LLM
llm = init_chat_model(
    "deepseek-v4-flash",
    model_provider="deepseek",
    temperature=float(os.getenv("DEEPSEEK_TEMPERATURE", "0.7")),
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key=os.getenv("DEEPSEEK_API_KEY"),
)


# Define tools
@tool
def web_search(
    query: Annotated[
        str,
        Doc("The search query string to be executed on DuckDuckGo.")
    ]
) -> Annotated[
    List[Dict[str, Any]],
    Doc("""
    A list of dictionaries, where each dictionary represents a search result.
    Each result may contain keys like 'title', 'link', 'snippet', or 'error'.
    """)
]:
    """
    Perform a web search using DuckDuckGo and return results.
    Example:
        >>> web_search("latest Python releases")
        [{'title': 'Python Releases', 'link': 'https://python.org/downloads', ...}]
    """
    print(f"Tool: Search web: {query}")
    try:
        results = DDGS().text(query, max_results=5)
        return results
    except Exception as e:
        return [{"error": f"Web search failed: {str(e)}"}]

@tool
def shell_execute(
    command: Annotated[
        str,
        Doc("The shell command to execute (e.g., 'ls -l').")
    ]
) -> Annotated[
    str,
    Doc("""
    The command output (stdout) or error message (stderr).
    Truncated to 100KB if too large.
    """)
]:
    """
    Execute a shell command after user confirmation.
    Example:
        >>> shell_execute("ls -l")
        'total 8\\n-rw-r--r-- 1 user ...'
    """
    print(f"Tool: Execute shell command '{command}'")
    confirmation = input("Confirm shell execution (y/n): ").strip().lower()
    if confirmation != "y":
        return "Shell execution canceled by user."
    try:
        result = subprocess.run(
            command, shell=True, check=True,
            text=True, capture_output=True
        )
        output = result.stdout
        if len(output) > 102400:
            output = output[:102400] + "\n...output truncated..."
        return output
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"


# Bind tools to the model
tools = [web_search, shell_execute]
model_with_tools = llm.bind_tools(tools)
agent_executor = create_react_agent(model_with_tools, tools)


def main():
    # Initialize readline for session-only history and completion
    def setup_readline():
        # Tab completion for commands
        def complete(text, state):
            commands = list(PROMPTS.keys()) + ["/system", "/exit"]
            matches = [cmd for cmd in commands if cmd.startswith(text)]
            return matches[state] if state < len(matches) else None

        readline.set_completer(complete)
        readline.parse_and_bind("tab: complete")
        readline.set_completer_delims(" \t\n")  # Disable mid-word completion
        # Key binding: Ctrl+L to clear screen
        readline.parse_and_bind("Control-l: clear-screen")

    setup_readline()

    print("Welcome to simplified DeepSeek Terminal Chat with Tools")
    print("Commands: [query], /exit, /cat, /thinker, /teacher, /learn_en, /system <message>")
    print("Tools: web_search, shell_execute")

    # Initialize message history and default system message
    message_history = []
    system_message = None

    while True:
        user_input = input("\nUser: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "/exit":
            print("Exiting.")
            break

        # Handle system message selection
        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=1)
            command = parts[0].lower()

            if command == "/exit":
                print("Exiting.")
                break
            elif command in PROMPTS:
                system_message = SystemMessage(content=PROMPTS[command])
                print(f"System message set to: {command}")
                continue
            elif command == "/system":
                if len(parts) > 1:
                    system_message = SystemMessage(content=parts[1])
                    print("Custom system message set.")
                else:
                    print("Using default model's system message.")
                    system_message = None
                continue
            else:
                print(f"Unknown command: {command}")
                continue

        # Process query
        query = user_input
        user_message = {"role": "user", "content": query}
        message_history.append(user_message)

        # Prepare input for agent (include system message if set)
        agent_input = {'messages': message_history}
        if system_message:
            agent_input['messages'].insert(0, system_message)

        # Invoke the agent
        response = agent_executor.invoke(agent_input)
        assistant_message = response["messages"][-1]
        assistant_message.pretty_print()
        message_history.append(assistant_message)


if __name__ == "__main__":
    main()
