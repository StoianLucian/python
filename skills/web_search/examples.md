# `/web_search` Response Format

This describes the **final response** returned to the user *after* the
`web_search` tool has run. It uses the base `text`, `url`, and `error` object
types.

There are NO sample answers here — only the required shape. Build the answer
entirely from the `web_search` tool results in the current conversation.

## Where the data is in the tool message

The `web_search` tool message has this shape (the useful data is nested under
`result`):

```json
{
  "success": true,
  "result": {
    "query": "the search query",
    "answer": "a ready-made synthesized answer to the query",
    "results": [
      { "title": "...", "url": "https://...", "content": "..." }
    ]
  }
}
```

- The answer to give the user is at `result.answer`.
- The sources to cite are the objects in `result.results` (use their `url` and
  `title`).
- If `success` is `true`, there ARE results — read `result.answer` and
  `result.results`; do not claim the search returned nothing.

## Output Format

- Return a JSON array.
- Emit exactly one `text` object holding the answer:
  - Use `result.answer` verbatim (or lightly trimmed) as the `text`. Do NOT
    rewrite it from the raw `result.results`.
  - Only if `result.answer` is missing or empty, write a one-to-three sentence
    answer yourself from the `result.results` snippets.
- Emit one `url` object for each source in `result.results` that you used.
  - `text`: a short (2–5 word) label for the source, based on its `title`.
  - `url`: the source `url`, copied verbatim from the tool result.
- Do not emit `url` objects for results you did not use, and never invent a URL.
- Every fact you state must come from the tool result. Do not guess.
- Only return a single `error` object if `success` is `false`, or if both
  `result.answer` and `result.results` are empty.

## Response shape (structure only — fill from the tool results)

One `text` object with the answer, followed by one `url` object per source you
used. The `text` object always comes first; add a `url` object for each result
that has a URL. Replace every `...` below with values from the tool results.

```json
[
  { "type": "text", "text": "<answer, from the tool result `answer` field>" },
  { "type": "url", "text": "<label for source 1>", "url": "<url of source 1>" },
  { "type": "url", "text": "<label for source 2>", "url": "<url of source 2>" }
]
```

If the tool results contain no URLs, emit only the `text` object:

```json
[
  { "type": "text", "text": "<answer, from the tool result `answer` field>" }
]
```

## Error shape (when there is no usable answer)

```json
[
  { "type": "error", "text": "..." }
]
```
