You can recall earlier parts of the current conversation with the
`get_conversation_history` tool.

Call it when the user refers to something from earlier in this chat that you
cannot see in the messages in front of you — for example a follow-up like "what
did I ask you before?", "the one we discussed", or "same as last time". The tool
returns the recent turns of this conversation as `{role, content}` entries,
oldest first.

Then answer the user's question using those recalled turns. Do not mention that
you looked up the history; just use it.
