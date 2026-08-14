# Example 1 - Return the full user list

User:
> /users_list

Assistant:
get_all_users()

Tool:
{
  "success": true,
  "result": [
    {
      "id": 12,
      "username": "john",
      "email": "john@test.com"
    },
    {
      "id": 13,
      "username": "gabriel",
      "email": "gabriel@test.com"
    },
    {
      "id": 14,
      "username": "matei",
      "email": "matei@test.com"
    }
  ]
}

## Output Format

When answering using `get_all_users` results:

- Return a JSON array of response objects.
- Include exactly one `text` object introducing the list.
- Include one `user-mention` object for EACH user in the tool result.
- Never list the users inside the `text` string. No numbered lists, no bullets,
  no emails, no ids in the text.
- Each `user-mention` must contain an `attrs` object with:
  - `label`: the user's email address, exactly as returned by the tool.
  - `id`: the user's id as a number, exactly as returned by the tool.
- Do not add fields to `attrs` other than `label` and `id`.
- Do not invent, omit, reorder, or deduplicate users.

Allowed object type for this skill:

{
  "type": "user-mention",
  "attrs": { "label": "<email>", "id": <number> }
}

Response EXAMPLE:
[
  {
    "type": "text",
    "text": "Here is a list of the users"
  },
  {
    "type": "user-mention",
    "attrs": { "label": "john@test.com", "id": 12 }
  },
  {
    "type": "user-mention",
    "attrs": { "label": "gabriel@test.com", "id": 13 }
  },
  {
    "type": "user-mention",
    "attrs": { "label": "matei@test.com", "id": 14 }
  }
]

INCORRECT - never collapse the users into prose:
[
  {
    "type": "text",
    "text": "Here are your users:\n\n1. john - Email: john@test.com, ID: 12\n2. gabriel - Email: gabriel@test.com, ID: 13"
  }
]
