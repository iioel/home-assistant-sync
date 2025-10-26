# Home Assistant Sync

This custom integration allows you to synchronize entities between two Home Assistant instances in real-time with full bidirectional control.

## Features

- **Dual Mode Operation**: Configure as either a server or client
- **Secure Authentication**: JWT token-based authentication between server and client
- **Selective Entity Sync**: Choose which entities to expose (server) or import (client)
- **Real-time Synchronization**: WebSocket-based event synchronization
- **Bidirectional Control**: Full control of entities from client to server
- **Support for Multiple Entity Types**: Sensors, binary sensors, switches, and lights
- **Optimistic Updates**: Immediate UI feedback with state synchronization

## Installation

1. Copy the `custom_components/home_assistant_sync` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Configuration -> Integrations
4. Click the "+" button and search for "Home Assistant Sync"

## Configuration

### Server Setup

1. Add the integration and select "Server" mode
2. Enter a JWT secret (this will be shared with clients)
3. After setup, go to the integration options
4. Select which entities you want to expose to clients

### Client Setup

1. Add the integration and select "Client" mode
2. Enter the server URL (e.g., `http://192.168.1.100:8123`)
3. Enter the JWT secret from the server
4. After setup, go to the integration options
5. Select which entities you want to import from the server

## How It Works

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
- `GET /api/home_assistant_sync/entities` - Get list of exposed entities
- `POST /api/home_assistant_sync/call_service` - Call a service on an entity
- `GET /api/home_assistant_sync/ws` - WebSocket connection for real-time sync

## Security Notes

- Keep your JWT secret secure and don't share it publicly
- Use HTTPS/WSS for production deployments over the internet
- Consider using a reverse proxy for additional security
- Only exposed entities can be controlled by clients
- All requests are authenticated with JWT tokens

## Supported Entity Types

Currently supported:
- **Sensors** (read-only)
- **Binary Sensors** (read-only)
- **Switches** (full control)
- **Lights** (full control with brightness, color, etc.)

## Troubleshooting

### Connection Issues
- Verify the server URL is correct and accessible from the client
- Check that the JWT secret matches on both server and client
- Ensure the server's Home Assistant instance is running
- Check firewall rules allow connections on port 8123

### Entity Control Issues
- Verify the entity is in the "exposed entities" list on the server
- Check the Home Assistant logs for error messages
- Ensure the entity exists and is controllable on the server

### WebSocket Disconnections
- The client will automatically reconnect after 30 seconds
- Check network stability between client and server
- Review Home Assistant logs for WebSocket errors

## Future Enhancements

Potential features for future versions:
- Support for more entity types (climate, cover, etc.)
- Multiple server support from a single client
- State history synchronization
- Automatic entity discovery
- Custom sync intervals per entity
- Compression for large state updates

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Credits

Created by @iioel