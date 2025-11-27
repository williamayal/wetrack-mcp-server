# WeTrack MCP Server

MCP (Model Context Protocol) server for MongoDB pipeline generation and execution. This server exposes tools for AI models to interact with financial event data stored in MongoDB.

## Features

- **Pipeline Generation**: Generate MongoDB aggregation pipelines from natural language queries using GPT-5.1
- **Pipeline Execution**: Execute MongoDB aggregation pipelines and return results
- **Remote Access**: HTTP/SSE server for remote MCP access (Claude AI, etc.)
- **Authentication**: OAuth2 and Bearer token authentication support
- **Date Handling**: Automatic conversion of date strings to datetime objects for MongoDB queries

## Tools

1. **generate_mongodb_pipeline**: Generates a MongoDB aggregation pipeline from a natural language query
2. **execute_mongodb_pipeline**: Executes a MongoDB aggregation pipeline and returns results

## Setup

1. Install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Configure environment variables in `.env`:
```env
MONGODB_URI=your_mongodb_uri
MONGODB_DATABASE=your_database
MONGODB_VIEW=your_view_or_collection
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL_PIPELINE=gpt-5.1
SERVER_PORT=8002

# Authentication (optional)
OAUTH_ENABLED=false
OAUTH_CLIENT_ID=your_client_id
OAUTH_CLIENT_SECRET=your_client_secret
BEARER_TOKEN_ENABLED=false
BEARER_TOKEN=your_bearer_token
MCP_TOKEN=your_mcp_token
MCP_CLIENT_ID=your_client_id
```

3. Run the server:
```bash
python -m src.server_http
```

## Remote Access (Claude AI)

1. Expose the server using ngrok:
```bash
ngrok http 8002
```

2. Configure Claude AI with the ngrok URL and authentication credentials.

## Project Structure

```
wetrack-mcp-server/
├── src/
│   ├── config/          # Configuration settings
│   ├── services/         # LLM and MongoDB services
│   ├── tools/           # MCP tools (generate, execute)
│   ├── utils/           # Date and JSON utilities
│   ├── auth.py          # Authentication utilities
│   ├── oauth.py         # OAuth2 implementation
│   └── server_http.py   # HTTP/SSE server
├── test_pipeline.py     # Pipeline testing script
└── requirements.txt     # Python dependencies
```

## License

MIT
