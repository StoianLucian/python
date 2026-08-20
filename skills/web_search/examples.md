# Web Search Output Format

The examples below illustrate the **structure** of a valid response ONLY.
They are NOT sample answers to copy. Always build your answer from the actual
`web_search` tool results in this conversation — never reuse the placeholder
text or URLs shown here.

## Response shape

- Return a JSON array.
- Include exactly one `text` object: your synthesized answer, written from the
  real tool results.
- Include one `url` object for each web result you actually used.
- Each `url` object must contain:
  - `text`: a short (2–5 word) label describing the cited source.
  - `url`: the source URL (copied from the tool result, not invented).
- Do not create `url` objects for results you did not use.

## Structural example (placeholders — do NOT copy this content)

[
  {
    "type": "text",
    "text": "<one-paragraph answer synthesized from the tool results>"
  },
  {
    "type": "url",
    "text": "<short label for source 1>",
    "url": "<url of source 1 from the tool results>"
  },
  {
    "type": "url",
    "text": "<short label for source 2>",
    "url": "<url of source 2 from the tool results>"
  }
]
