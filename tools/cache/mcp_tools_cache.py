class MCPToolsCache:
    _tool_cache = None

    @classmethod
    async def get_tools(cls, mcp):
        if cls._tool_cache is None:
            cls._tool_cache = await mcp.list_tools()
        return cls._tool_cache