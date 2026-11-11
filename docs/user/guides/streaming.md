# Streaming and async

Streams are owned resources. Use a context manager so breaking a loop, exceptions
and cancellation release upstream resources. A successful stream has `end`;
closed, failed or incomplete streams have an `outcome` and must not be presented
as completed responses. Ending the local stream does not undo provider billing.

## Consume and fold

<!-- test: recorded -->
```python
import ocai.chat
from ocai.chat import ChatRequest, Message
from ocai.core import ApiKey
from ocai.wire import HttpxTransport

with HttpxTransport() as transport:
    model = ocai.chat.model(
        "openai/gpt-4o", credentials=ApiKey("synthetic-key"), transport=transport
    )
    request = ChatRequest(messages=[Message.user("Hello!")])
    with model.stream(request) as stream:
        response = stream.fold()
        print(response.message.text)
        print(stream.end)
    print(stream.outcome)
```

Replace the synthetic credential before a live call. `fold()` consumes the remaining
stream; calling it after manually exhausting the iterator does not reconstruct
already-consumed chunks. Use `StreamAccumulator` when you need incremental rendering
and a final accumulated response. The fold parity guarantee is established by
paired fixtures, not by making two nondeterministic live calls and comparing them.

## Async calls

<!-- test: recorded -->
```python
import asyncio
import ocai.chat
from ocai.chat import ChatRequest, Message
from ocai.core import ApiKey
from ocai.wire import HttpxTransport

async def main():
    async with HttpxTransport() as transport:
        model = ocai.chat.model(
            "openai/gpt-4o", credentials=ApiKey("synthetic-key"), transport=transport
        )
        request = ChatRequest(messages=[Message.user("Hello!")])
        result = await model.achat(request)
        print(result.value.message.text)
        async with await model.astream(request) as stream:
            response = await stream.fold()
            print(response.message.text)

asyncio.run(main())
```

`astream` is awaited to obtain the owned async stream. Use `async for` for event
rendering or `await stream.fold()` for accumulation. Do not call `asyncio.run` inside
an already-running event loop; await `main()` there instead.
See [`ocai.chat` types](../reference/ocai-chat.md) for `ChatChunk`, deltas,
`ChatStream`, `AsyncChatStream` and termination methods.
