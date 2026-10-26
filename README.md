# Bot Client

Chat Client library to connect to the AiChatBot API.

## How to use it?


```python
from chatbot_client import BearerTokenAuth, ChatbotClient, ChatbotConfig

config = ChatbotConfig(
    base_url="https://chatbot-dev.example.com",
    auth=BearerTokenAuth("your-token"),  # MOCK

with ChatbotClient(config) as client:
    chat = client.create_chat("your-bot-id")
    print(chat.send("What can you help me with?"))
    print(chat.send("Summarize that in one sentence."))
```

or

```bash
    export CHATBOT_BASE_URL=https://chatbot-dev.example.com \\
    export CHATBOT_API_TOKEN=your-token \\
    export CHATBOT_BOT_ID=your-bot-id \\
```
```python
    try:
        with ChatbotClient(config) as client:
            chat = client.create_chat(bot_id)
            for question in ("What can you help me with?", "Summarize that in one sentence."):
                print(f"> {question}\n{chat.send(question)}")
    except ChatbotError as error:
        print(f"Chatbot request failed: {error}", file=sys.stderr)
        return 1
    return 0

```


## Install

Requires Python 3.10 or newer. The only dependency is [httpx](https://www.python-httpx.org/).

```bash
pip install .
```

## Usage

### Configure

| `ChatbotConfig` field | Default | Meaning |
| --- | --- | --- |
| `base_url` | required | API root|
| `auth` | `None` | Any `httpx.Auth`, e.g. `BearerTokenAuth`. |
| `timeout` | `60.0` | Seconds to wait for a response. Completions wait for a language model. |
| `connect_timeout` | `10.0` | Seconds to wait while opening a connection. |
| `max_retries` | `2` | See [Retries](#retries). `0` turns retries off. |
| `backoff_factor` | `0.5` | Base delay in seconds between retries. |
| `headers` | `{}` | Extra headers on every request, e.g. a correlation id. |



### Continue a chat later

The server keeps the conversation history, so a chat id is all you need to continue. Store `chat.chat_id` (in a web session or a database) and resume without creating a new chat:

```python
chat = client.resume_chat(saved_chat_id)
answer = chat.send("And what about next year?")
```

`client.send_message(chat_id, message)` does the same in one call.

## Errors

Every error the library raises on purpose is a `ChatbotError`, so a single `except` at your integration boundary is enough. Catch a subclass to react to a specific case:

```python
from chatbot_client import ChatbotError, ChatbotTimeoutError, NotFoundError

try:
    answer = chat.send(question)
except NotFoundError:  # the chat expired or was deleted
    chat = client.create_chat(bot_id)
    answer = chat.send(question)
except ChatbotTimeoutError:
    answer = "The assistant is taking too long. Please try again."
except ChatbotError as error:
    logger.error("Chatbot unavailable: %s", error)
    answer = "The assistant is unavailable right now."
```

## Retries

Both endpoints are POSTs that store the message. Retrying a completion the server already processed would post the user's message twice, so the client retries only when the server cannot have processed it:

- the connection could not be opened, or
- the server answered `429 Too Many Requests` or `503 Service Unavailable`.

The delay is the server's `Retry-After` (in seconds) if it sent one, otherwise exponential backoff with jitter, capped at 10 seconds. Read timeouts and other errors are raised straight away. Each retry is logged as a warning on the `chatbot_client` logger, without message content or credentials.