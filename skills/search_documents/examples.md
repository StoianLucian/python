# Example 1 - Summarize Relevant Results

User:
> What is our vacation policy?

Assistant:
search_documents({
  "user_query": "What is our vacation policy?"
})

Tool:
{
  "success": true,
  "result": [
    {
      "page_number": 12,
      "source_id": 1,
      "content": "Employees receive 20 paid vacation days per year."
    },
    {
      "page_number": 13,
      "source_id": 1,
      "content": "Vacation requests should be submitted at least two weeks in advance."
    },
    {
      "page_number": 12,
      "source_id": 1,
      "content": "Unused vacation days may be carried over for up to one year."
    },
    {
      "page_number": 12,
      "source_id": 8,
      "content": "Managers are responsible for approving vacation requests."
    },
    {
      "page_number": 13,
      "source_id": 1,
      "content": "Public holidays are not counted as vacation days."
    }
  ]
}

## Output Format

When answering using `search_documents` results:

- Return an array of response objects.
- Include exactly one `text` object containing the synthesized answer.
- Include one `popover` object for each document excerpt referenced.
- Each `popover` must contain:
  - `text`: a short (2–5 word) label describing the cited information.
  - `content`: the short, specific span from the tool result that supports the answer.
  - `source_id`
  - `page_number`
- The `text` label should summarize the cited fact, not repeat the full document content.
- The `content` field is used to locate and highlight the exact text inside the
  source PDF, so it MUST be:
  - SHORT and FOCUSED — only the specific phrase, line, or value that directly
    supports the cited fact (roughly 3–12 words). Do NOT paste the whole excerpt
    or a large passage; a long blob will not match and highlights nothing.
  - Copied VERBATIM from the tool result's `content` — the same characters,
    spacing, and punctuation. Do NOT paraphrase, translate, summarize, reformat,
    fix typos, reorder, or add/remove words. Any change breaks the highlight.
  Example: if the excerpt is a long invoice, `content` should be just
  "Total General: 505,61", not the entire invoice text.
- Do not create `popover` objects for excerpts that were not used in the answer.
- When using the `popover` always include `content`, `source_id` and `page_number`.


Response EXAMPLE:
[
  {
    "type": "text",
    "text": "Employees receive 20 paid vacation days per year. Vacation requests should be submitted at least two weeks in advance."
  },
  {
    "type": "popover",
    "text": "Annual vacation allowance",
    "content": "Employees receive 20 paid vacation days per year.",
    "source_id": 1,
    "page_number": 12
  },
  {
    "type": "popover",
    "text": "Vacation request notice",
    "content": "Vacation requests should be submitted at least two weeks in advance.",
    "source_id": 1,
    "page_number": 13
  }
]
