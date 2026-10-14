"""Optional stdio MCP bridge for a compatible locally installed AI client."""
from connectors.owner_client import OwnerClient
try:
    from mcp.server import MCPServer
    server=MCPServer('JARVIS execution')
except ImportError:
    from mcp.server.fastmcp import FastMCP
    server=FastMCP('JARVIS execution')

@server.tool()
def jarvis_devices() -> list:
    """List paired owner devices and explicitly enabled execution capabilities."""
    return OwnerClient().devices()

@server.tool()
def jarvis_submit(device_id:str,capability:str,args:dict,idempotency_key:str) -> dict:
    """Queue an authorized task. Reuse the same key after uncertain HTTP results."""
    return OwnerClient().submit(device_id,capability,args,idempotency_key)

@server.tool()
def jarvis_result(task_id:str) -> dict:
    """Read task result. Claimed/uncertain is not success; never blindly repeat."""
    return OwnerClient().status(task_id)

if __name__=='__main__':server.run(transport='stdio')
