
import httpx

from fastapi import APIRouter, Request
import os

from lmm.factory import get_lmm_provider
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

router = APIRouter(
    prefix="/github",
    tags=["github"],
)

GITHUB_TOKEN = os.getenv("TOKEN")

review_prompt = """
You are a senior software engineer performing an automated code review of a GitHub Pull Request.

Your job is to review ONLY the changes provided in the Pull Request diff.

Focus on issues that are:
- Real and technically valid
- Relevant to the changed code
- Likely to cause bugs or problems
- Actionable by the developer

Look specifically for:
- Bugs and incorrect behavior
- Logic errors
- Security vulnerabilities
- Performance problems
- Incorrect API usage
- Missing or incorrect error handling
- Race conditions or concurrency issues
- Null/None/undefined handling
- Edge cases
- Breaking changes
- Maintainability problems when they have a meaningful impact

Do NOT report:
- Pure formatting or style preferences
- Minor naming preferences
- Issues unrelated to the changed code
- Hypothetical problems without a reasonable technical basis
- Issues that are already correctly handled elsewhere in the shown code

IMPORTANT:
- Do not invent context that is not present in the diff.
- If you are unsure whether something is a problem, do not report it.
- Prefer a small number of high-confidence findings over many speculative ones.
- If the code is correct, explicitly say that no significant issues were found.
- Do not suggest changes just for the sake of suggesting something.

For every issue, explain:
1. What is wrong
2. Why it is a problem
3. How it could be fixed

Keep the review concise and professional.

Use this format:

## AI Code Review

### Summary
Briefly summarize what the PR changes and your overall assessment.

### Issues
For each issue:

**[severity] `filename`**
- **Problem:** Explain the issue.
- **Why:** Explain the impact.
- **Suggestion:** Explain how to fix it.

Use these severity levels:
- 🔴 Critical — security vulnerabilities, data loss, crashes, or severe breaking behavior
- 🟠 High — serious bugs or significant production impact
- 🟡 Medium — bugs or problems that should be addressed
- 🔵 Low — minor but meaningful improvements

If there are no significant issues, write:

### Issues
No significant issues found.

### Suggestions
Only include suggestions that provide meaningful value. Do not include this section if there are no useful suggestions.
"""


@router.post("/")
async def check_response(request: Request):
    provider = get_lmm_provider()
    github_headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    payload = await request.json()
    pull_request = payload.get("pull_request")
    repository = payload.get("repository")

    if not pull_request or not repository:
        return {"ok": True}

    repo_full_name = repository["full_name"]
    pr_number = pull_request["number"]

    files_url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}/files"
    comment_url = (
        f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
    )
    changes = []
    async with httpx.AsyncClient() as client:
        files_response = await client.get(
            files_url,
            headers=github_headers,
        )

    if files_response.is_error:
        detail = files_response.json().get("message", files_response.text)
        print(f"failed to fetch changed files: {files_response.status_code} {detail}")
        return {
            "ok": False,
            "status": files_response.status_code,
            "error": detail,
        }

    files = files_response.json()  # get modified files

    for file in files:
        changes.append(
            f"""
            File: {file["filename"]}
            Satus: {file["status"]}
            Additions: {file["additions"]}
            Deletions: {file["deletions"]}

            ```diff
            {file.get("patch", "Patch unavailable")}
            ```
            """
        )

    diff = "\n".join(changes)

    review_message = f"""
        Review the following GitHub Pull Request.

        Repository: {repo_full_name}
        Pull Request: #{pr_number}
        Title: {pull_request.get("title", "")}

        PR Description:
        {pull_request.get("body") or "No description provided."}

        Changes:
        {diff}
        """

    messages = [
        {
            "role": "system",
            "content": review_prompt,
        },
        {
            "role": "user",
            "content": review_message,
        },
    ]

    print("CHANGED FILES:", files)

    response = provider.chat(model="qwen3:8b", messages=messages)
    content = response.get("message", {}).get("content")

    print(content, "content============")

    if not content:
        return {"ok": False, "error": "empty review from model"}

    async with httpx.AsyncClient() as client:
        comment_response = await client.post(
            comment_url,
            headers=github_headers,
            json={"body": content},
        )

    if comment_response.is_error:
        detail = comment_response.json().get("message", comment_response.text)
        print(f"failed to post comment: {comment_response.status_code} {detail}")
        return {
            "ok": False,
            "status": comment_response.status_code,
            "error": detail,
        }

    return {
        "ok": True,
        "comment_url": comment_response.json()["html_url"],
    }
