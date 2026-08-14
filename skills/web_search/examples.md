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
  - `source_id` 
  - `page_number`
- The `text` label should summarize the cited fact, not repeat the full document content.
- Do not create `popover` objects for excerpts that were not used in the answer.
- When using the `popover` always include `source_id` and`page_number`


Response EXAMPLE:
[
  {
    "type": "text",
    "text": "Employees receive 20 paid vacation days per year. Vacation requests should be submitted at least two weeks in advance."
  },
  {
    "type": "popover",
    "text": "Annual vacation allowance",
    "source_id": 1,
    "page_number": 12
  }
]