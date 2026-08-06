# `/send_email` Response Examples

These examples describe the **final response** returned to the user *after* the
`send_email` tool has run. They are NOT examples of tool arguments.

## Output Format

- Return an array of response objects.
- Include exactly one `text` object confirming the outcome.
- Never include the email subject or body in the response.
- Never repeat or paraphrase the email content back to the user.
- Never write the response as if you were the email itself.
- Never return `popover` objects for this skill.
- If the tool reported `success: false`, return a single `error` object.

---

## Example 1 – Email sent

Tool:
```json
{
  "success": true,
  "result": "Email sent successfully to user 15"
}
```

Response:
```json
[
  {
    "type": "text",
    "text": "Email sent successfully."
  }
]
```

---

## Example 2 – Email sent to a named recipient

Tool:
```json
{
  "success": true,
  "result": "Email sent successfully to user 23"
}
```

Response:
```json
[
  {
    "type": "text",
    "text": "Email sent to Sarah."
  }
]
```

---

## Example 3 – Tool failed

Tool:
```json
{
  "success": false,
  "result": "User not found"
}
```

Response:
```json
[
  {
    "type": "error",
    "text": "The email could not be sent: user not found."
  }
]
```

---

## Example 4 – Recipient missing, no tool call was made

Response:
```json
[
  {
    "type": "text",
    "text": "Please mention the recipient (e.g. @John) so I know who to email."
  }
]
```

---

## Incorrect

Never return the email itself:

```json
[
  {
    "type": "text",
    "text": "Hi Sarah, just letting you know I'll be about 15 minutes late."
  }
]
```
