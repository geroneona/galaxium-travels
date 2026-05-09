
# Configuration

## Environment Variables

**Required**:
- `ICA_TOKEN`: JWT or API token for ICA platform authentication
- `ICA_TEAM_ID`: Team ID for agent registration
- `ICA_APP_ID`: Application ID in ICA platform
- `ICA_APP_NAME`: Application name

**Optional**:
- `AWS_REGION`: AWS region for Bedrock (default: `eu-central-1`)
- `AWS_PROFILE`: AWS profile to use
- `ALLOWED_ORIGINS`: CORS allowed origins (default: localhost ports)
- `PORT`: Server port (default: `8000`)
- `PUBLIC_AGENT_URL`: Public URL for agent registration
- `A2A_PROTOCOL`: Protocol type - `JSONRPC` or `HTTP+JSON` (default: `JSONRPC`)
- `RPC_PATH`: JSON-RPC endpoint path (default: `/v1/rpc`)
- `A2A_BEARER_TOKEN`: Optional bearer token for authentication
- `KEYCLOAK_ISSUER_URL`: Keycloak realm issuer for JWT validation
- `ICA_OBSERVABILITY`: Enable Phoenix observability (default: `false`)
- `PHOENIX_COLLECTOR_ENDPOINT`: Phoenix collector endpoint for tracing

