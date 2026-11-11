# Tools and structured output

The library represents tool definitions and calls; your application owns executing
client-side tools. Validate tool arguments and apply your application's permissions
before performing actions. A provider-hosted search tool is a different operation
from a local Python function.

## Define a tool

<!-- test: offline -->
```python
from ocai.chat import ChatRequest, Message, Tool

def get_weather(city: str) -> str:
    """Return a weather description for a city."""
    return "Example weather for " + city

tool = Tool.from_function(get_weather)
request = ChatRequest(messages=[Message.user("Weather in Paris?")], tools=[tool])
assert request.tools[0].name == "get_weather"
```

Pass the request to your configured model. Inspect `PartToolCall` parts in the
reply. `args_json` preserves the original argument string; `args()` parses it for
validation. Keep the call ID when returning a `PartToolResult` through
`Message.tool(...)`, and include the model's tool-call message in the history.
The model does not execute the Python function merely because it was registered.
See the [chat types reference](../reference/ocai-chat.md) for exact fields.

## Structured output

<!-- test: offline -->
```python
from ocai.chat import ChatConfig, ChatRequest, Message
from ocai.chat.types import OutputFormat

request = ChatRequest(
    messages=[Message.user("Return a JSON object describing a color.")],
    config=ChatConfig(output=OutputFormat(mode="json")),
)
assert request.config is not None
```

`OutputFormat` also supports schema-based output. Consult its signature and the
selected provider's qualified coverage before relying on enforcement. A typed
canonical field or successful local schema conversion is not a guarantee that a
provider honors every constraint. Inspect fidelity reports and validate returned
application data. Ordinary tool calls, server tools and tool results remain distinct.
