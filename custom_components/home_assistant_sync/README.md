# Home Assistant Sync

This custom integration allows you to synchronize entities between two Home Assistant instances in real-time.

## Features

- **Dual Mode Operation**: Configure as either a server or client
- **Secure Authentication**: JWT token-based authentication between server and client
- **Selective Entity Sync**: Choose which entities to expose (server) or import (client)
- **Real-time Synchronization**: WebSocket-based event synchronization
- **Support for Multiple Entity Types**: Sensors, binary sensors, switches, and lights

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

## Security Notes

- Keep your JWT secret secure and don't share it publicly
- Use HTTPS/WSS for production deployments
- Consider using a reverse proxy for additional security

## Supported Entity Types

Currently supported:
- Sensors
- Binary Sensors
- Switches
- Lights

## Limitations

- Client-to-server control commands (for switches/lights) require additional server implementation
- Only one-way synchronization (server to client) is fully implemented
- Entity state changes from client side are not yet propagated back to server

## License

MIT License