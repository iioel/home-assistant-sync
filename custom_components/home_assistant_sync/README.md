# Home Assistant Sync

This custom integration allows you to synchronize entities between two Home Assistant instances in real-time with full bidirectional control and secure token-based authentication.

## Features

- **Dual Mode Operation**: Configure as either a server or client
- **Secure Authentication**: Server-generated JWT tokens for each client
- **Client Management**: Register, revoke, and list clients from the server
- **Selective Entity Sync**: Choose which entities to expose (server) or import (client)
- **Real-time Synchronization**: WebSocket-based event synchronization
- **Bidirectional Control**: Full control of entities from client to server
- **Support for Multiple Entity Types**: Sensors, binary sensors, switches, and lights
- **Optimistic Updates**: Immediate UI feedback with state synchronization
- **Token Storage**: Client tokens are securely stored and persist across restarts

## Installation

1. Copy the `custom_components/home_assistant_sync` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Configuration -> Integrations
4. Click the "+" button and search for "Home Assistant Sync"

## Configuration

### Server Setup

1. Add the integration and select "Server" mode
2. Enter a JWT secret (this will be used to sign client tokens - keep it secure!)
3. After setup, go to the integration options
4. Select which entities you want to expose to clients

**Important**: The JWT secret is used to sign tokens. Keep it secure and share it only with clients you trust.

### Client Setup

1. Add the integration and select "Client" mode
2. Enter the following information:
   - **Server URL**: The URL of your server instance (e.g., `http://192.168.1.100:8123`)
   - **JWT Secret**: The same JWT secret configured on the server
   - **Client Name**: A friendly name for this client (e.g., "Living Room Display")
3. The client will automatically register with the server and receive a unique token
4. After setup, go to the integration options
5. Select which entities you want to import from the server

**Note**: Each client gets a unique token that can be revoked independently from the server.

## Client Management

### Registering Clients

Clients are automatically registered during the initial setup. The server will:
- Generate a unique client ID
- Create a JWT token specific to that client
- Store the client information (name, ID, creation time)
- Token is valid for 365 days by default

### Viewing Clients

You can view all registered clients by making a GET request to:
```
GET /api/home_assistant_sync/clients
```

With a valid client token in the Authorization header.

### Revoking Clients

To revoke a client's access, make a POST request to:
```
POST /api/home_assistant_sync/revoke_client
```

With the client ID in the request body:
```json
{
  "client_id": "client_id_here"
}
```

Revoked clients will no longer be able to connect or control entities.

## How It Works

### Authentication Flow

1. **Server Setup**: Administrator configures JWT secret on server
2. **Client Registration**: 
   - Client provides JWT secret during setup
   - Client sends registration request to server
   - Server validates JWT secret and generates unique client token
   - Client stores token for future authentication
3. **Connection**: Client uses unique token to authenticate WebSocket and API requests
4. **Validation**: Server verifies token is valid and not revoked

### Server to Client Synchronization
- Server monitors state changes of exposed entities
- Changes are broadcast in real-time to all connected clients via WebSocket
- Clients update their synced entities immediately

### Client to Server Control
- Client can control synced entities (switches, lights, etc.)
- Commands are sent to server via WebSocket or HTTP POST
- Server validates the entity is exposed before executing the command
- State changes are broadcast back to all clients
- Optimistic updates provide immediate UI feedback

### Supported Operations

#### Lights
- Turn on/off
- Set brightness
- Set RGB color
- Set color temperature
- All standard light operations

#### Switches
- Turn on/off
- Toggle

#### Sensors & Binary Sensors
- Read-only state synchronization

## API Endpoints

The server exposes the following endpoints:

- `GET /api/home_assistant_sync/auth` - Validate authentication token
- `POST /api/home_assistant_sync/register_client` - Register a new client
- `POST /api/home_assistant_sync/revoke_client` - Revoke a client's access
- `GET /api/home_assistant_sync/clients` - List all registered clients
- `GET /api/home_assistant_sync/entities` - Get list of exposed entities
- `POST /api/home_assistant_sync/call_service` - Call a service on an entity
- `GET /api/home_assistant_sync/ws` - WebSocket connection for real-time sync

## Security Notes

- **JWT Secret**: Keep your JWT secret secure and don't share it publicly
- **Token Management**: Each client gets a unique token that can be revoked independently
- **Token Storage**: Client tokens are stored in `.storage/home_assistant_sync.clients`
- **Network Security**: Use HTTPS/WSS for production deployments over the internet
- **Reverse Proxy**: Consider using a reverse proxy for additional security
- **Entity Access**: Only exposed entities can be controlled by clients
- **Authentication**: All requests are authenticated with JWT tokens
- **Token Expiration**: Tokens expire after 365 days (configurable)

## Storage

### Server Storage
The server stores client information in:
```
<config_dir>/.storage/home_assistant_sync.clients
```

This includes:
- Client IDs
- Client names
- Generated tokens
- Creation timestamps

**Backup**: Make sure to backup this file as part of your Home Assistant backup strategy.

## Troubleshooting

### Connection Issues
- Verify the server URL is correct and accessible from the client
- Check that the JWT secret matches on both server and client
- Ensure the server's Home Assistant instance is running
- Check firewall rules allow connections on port 8123

### Registration Issues
- Verify the JWT secret is correct
- Check server logs for registration errors
- Ensure the server integration is properly configured
- Try restarting the server integration

### Entity Control Issues
- Verify the entity is in the "exposed entities" list on the server
- Check that the client token hasn't been revoked
- Check the Home Assistant logs for error messages
- Ensure the entity exists and is controllable on the server

### WebSocket Disconnections
- The client will automatically reconnect after 30 seconds
- Check network stability between client and server
- Review Home Assistant logs for WebSocket errors
- Verify the client token is still valid

### Token Issues
- Check if token has expired (default: 365 days)
- Verify token hasn't been revoked
- Re-register client if needed
- Check `.storage/home_assistant_sync.clients` file exists on server

## Future Enhancements

Potential features for future versions:
- Token rotation and refresh
- Support for more entity types (climate, cover, etc.)
- Multiple server support from a single client
- State history synchronization
- Automatic entity discovery
- Custom token expiration per client
- Compression for large state updates
- Client groups and permissions

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Credits

Created by @iioel