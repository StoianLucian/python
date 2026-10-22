import re
from typing import Optional

from fastmcp import FastMCP
from sqlalchemy import text

from db.connection import engine
from import_folder.response import ToolResponse

# Keep results bounded for both the model's context and the response payload.
MAX_ROWS = 100
# Per-query timeout (ms) so a heavy or accidental query can't hang the request.
STATEMENT_TIMEOUT_MS = 5000

# Statement-type guard (defense in depth ON TOP OF the READ ONLY transaction):
# reject anything that isn't a plain SELECT / CTE read.
_WRITE_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|"
    r"replace|merge|call|copy|vacuum|comment|do|set|begin|commit|rollback)\b",
    re.IGNORECASE,
)


def _jsonable(value):
    """Coerce a DB value to something JSON-serializable (dates, Decimals, vectors
    → str); leave primitives as-is."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _validate_select(query: str) -> tuple[bool, Optional[str]]:
    """Allow only a single read-only SELECT/CTE statement. Any write/DDL or
    multi-statement input is rejected with a clear 'Not allowed' message."""
    stripped = query.strip().rstrip(";").strip()
    if not stripped:
        return False, "Not allowed: empty query."
    if ";" in stripped:
        return False, "Not allowed: only a single read-only SELECT statement is permitted (no ';')."
    lowered = stripped.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return False, "Not allowed: only read-only SELECT queries are permitted."
    match = _WRITE_KEYWORDS.search(stripped)
    if match:
        return False, (
            f"Not allowed: '{match.group(0).upper()}' is a destructive/write "
            "operation. Only read-only SELECT queries are permitted."
        )
    return True, None


def register_execute_sql_tools(mcp: FastMCP):

    @mcp.tool
    async def execute_sql(query: str) -> ToolResponse:
        """
        Run a READ-ONLY SQL SELECT against the application's PostgreSQL database
        and return the rows. Use this to answer data questions no other tool
        covers.

        Only a SINGLE `SELECT` (or `WITH ... SELECT`) statement is allowed —
        writes (INSERT/UPDATE/DELETE/DDL) are rejected and the query runs inside a
        read-only transaction with a timeout. At most 100 rows are returned.

        If you don't know the schema, first query it, e.g.
        `SELECT table_name FROM information_schema.tables WHERE table_schema='public'`
        or `SELECT column_name, data_type FROM information_schema.columns WHERE table_name='...'`.

        Args:
            query: One SQL SELECT statement (no trailing semicolon).
        """
        print(f"[execute_sql] ▶ query: {query}")

        ok, error = _validate_select(query)
        if not ok:
            print(f"[execute_sql] ✖ rejected: {error}")
            return ToolResponse(success=False, result=error)

        try:
            with engine.connect() as conn:
                with conn.begin():
                    # Hard read-only enforcement at the DB level + a timeout, so
                    # even if the keyword guard is bypassed nothing can be written.
                    conn.exec_driver_sql("SET TRANSACTION READ ONLY")
                    conn.exec_driver_sql(
                        f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}")
                    result = conn.execute(text(query))
                    columns = list(result.keys())
                    rows = result.fetchmany(MAX_ROWS)

            data = [
                {col: _jsonable(val) for col, val in zip(columns, row)}
                for row in rows
            ]
            print(f"[execute_sql] ✔ {len(data)} row(s)")
            return ToolResponse(
                success=True,
                result={"columns": columns, "rows": data, "row_count": len(data)},
            )
        except Exception as e:
            print(f"[execute_sql] ✖ error: {e}")
            return ToolResponse(success=False, result=f"Error: {e}")
