# `/send_email` Tool Usage

This document describes how to decide the arguments for the `send_email` tool.
The `content` argument is the email body — it is sent to the recipient and must
never appear in your reply to the user. After the tool returns, only confirm the
outcome.

---

## Example 1 – Valid Request

### Serialized Input

```js
[
  {
    "type": "skill-mention",
    "attrs": {
      "id": 1,
      "label": "/send_email"
    }
  },
  {
    "type": "text",
    "text": " to "
  },
  {
    "type": "user-mention",
    "attrs": {
      "id": "15",
      "label": "John"
    }
  },
  {
    "type": "text",
    "text": " saying tomorrow's meeting has moved to 3 PM"
  }
]
```

### Assistant reasoning

- The `/send_email` skill was invoked.
- A valid `user-mention` identifies the recipient.
- Generate an appropriate subject and email content.
- Call `send_email`.

### Example output

```json
send_email(
  user_id="15",
  subject="Tomorrow's Meeting Moved to 3 PM",
  content="Hi John,\n\nJust letting you know that tomorrow's meeting has been moved to 3:00 PM.\n\nSee you then!"
)
```

---

## Example 2 – Missing User Mention

### Serialized Input

```js
[
  {
    "type": "skill-mention",
    "attrs": {
      "id": 1,
      "label": "/send_email"
    }
  },
  {
    "type": "text",
    "text": " to John saying I'll be about 15 minutes late"
  }
]
```

### Assistant reasoning

- The `/send_email` skill was invoked.
- No `user-mention` node is present.
- The assistant cannot determine which contact "John" refers to.
- Do **not** call `send_email`.
- Ask the user to mention the intended recipient.

### Example output

> Please mention the recipient (e.g. @John) so I know which user to email.

---

## Example 3 – Valid Request

### Serialized Input

```js
[
  {
    "type": "skill-mention",
    "attrs": {
      "id": 1,
      "label": "/send_email"
    }
  },
  {
    "type": "text",
    "text": " to "
  },
  {
    "type": "user-mention",
    "attrs": {
      "id": "31",
      "label": "Alex"
    }
  },
  {
    "type": "text",
    "text": " thanking them for their help last week"
  }
]
```

### Assistant reasoning

- The recipient is identified by a `user-mention`.
- Generate the email subject and content.
- Call `send_email`.

### Example output

```json
send_email(
  user_id="31",
  subject="Thank You",
  content="Hi Alex,\n\nI just wanted to thank you for all your help last week. I really appreciate your support.\n\nThanks again!"
)
```