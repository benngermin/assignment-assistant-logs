# Assignment Assistant Dashboard

## Overview

This is a Flask-based web dashboard for the Assignment Assistant system that integrates with a Bubble API to manage assignment-related data. The application provides a clean, responsive web interface using Bootstrap with a dark theme, allowing users to interact with assignment data through a dashboard interface. The system is designed to fetch and display data from an external Bubble.io API service.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
The frontend uses a traditional server-side rendered architecture with Flask templates:
- **Template Engine**: Jinja2 templates with Bootstrap 5 dark theme for responsive UI
- **Styling Framework**: Bootstrap 5 with Replit dark theme integration and Font Awesome icons
- **Client-side JavaScript**: Vanilla JavaScript for dashboard interactions and API error handling
- **CSS Organization**: Custom CSS variables and Bootstrap overrides for consistent theming

### Backend Architecture
The backend follows a simple Flask application pattern:
- **Web Framework**: Flask with basic routing and template rendering
- **API Integration**: RESTful API client for Bubble.io service integration
- **Error Handling**: Comprehensive logging and exception handling for API failures
- **Session Management**: Flask sessions with configurable secret key from environment variables

### Data Integration Pattern
The system uses an external API-first approach:
- **Data Source**: Bubble.io API as the primary data backend
- **API Client**: Custom `fetch_bubble_data()` function with timeout and error handling
- **Data Flow**: API responses are passed directly to templates for rendering
- **Authentication**: Bearer token authentication for API access

### Configuration Management
Environment-based configuration pattern:
- **Environment Variables**: Used for sensitive data like session secrets and API credentials
- **Development Defaults**: Fallback values for development environment
- **Logging Configuration**: Debug-level logging for development and troubleshooting

## External Dependencies

### Core Framework Dependencies
- **Flask**: Python web framework for routing, templating, and request handling
- **Requests**: HTTP library for API communication with timeout and error handling

### Frontend Dependencies
- **Bootstrap 5**: CSS framework with dark theme via Replit CDN
- **Font Awesome 6.4.0**: Icon library for UI elements
- **Replit Bootstrap Theme**: Custom dark theme styling

### External API Services
- **Bubble.io API**: Primary data service at `assignmentassistants.theinstituteslab.org`
  - Bearer token authentication required
  - RESTful endpoints for data retrieval
  - JSON response format
  - 30-second timeout configuration

### Development Environment
- **Python Runtime**: Flask application requiring Python 3.x
- **Static Asset Serving**: Flask's built-in static file serving for CSS/JS
- **Template Rendering**: Jinja2 template engine integration