from src.mcp_server.mcp_server import my_mcp

if __name__ == '__main__':
    my_mcp.run(
        transport='streamable-http',
        host='127.7.7.1',
        port=7777,
        path='/streamable',
        log_level="debug",

    )