# Assignment Assistant Dashboard

## Overview

This is a Flask-based web dashboard for the Assignment Assistant system that integrates with a Bubble API to manage assignment-related data. The application provides a clean, responsive web interface using Bootstrap with a dark theme, featuring interactive charts and real-time metrics. Users can view comprehensive analytics including activity counts, course distributions, conversation trends over time, and detailed session breakdowns through an intuitive dashboard interface.

## Recent Changes (August 2025)

### Production-Ready Configuration (August 6, 2025)
- **Restored Bubble API Connections**: Fixed hardcoded API blocking - now properly connects to live Bubble API using BUBBLE_API_KEY_LIVE
- **Removed All Development References**: Completely removed "Dev version" UI toggles and development-specific code
- **Production-Only Mode**: Simplified to single production environment without dev/live switching
- **Enhanced Refresh Button**: Added loading spinner, progress tracking, and better user feedback during data refresh
- **Security Hardening**: Removed development fallback secrets and debug mode
- **UI Cleanup**: Removed environment toggle buttons, now shows "Live Data" status only
- **Logging Optimization**: Changed from DEBUG to INFO level logging for production
- **Cache Simplification**: Removed environment tracking from cache structure

### Bug Fixes (January 6, 2025)
- **Fixed Duplicate Initialization**: Resolved JavaScript error caused by duplicate DOMContentLoaded event listeners that was causing console errors
- **Security Fix**: Moved hardcoded API key to environment variable BUBBLE_API_KEY for better security
- **Prevented Double Initialization**: Added flag to prevent dashboard from initializing twice
- **Fixed Chart Loading**: Charts now properly load on initial page load and refresh

### Previous Changes
- **Fixed Statistics Loading**: Resolved "Failed to load statistics" error by creating missing `/api/stats` endpoint
- **Added Activity Counts**: Implemented feature-specific counting for Quiz Me, Review Terms, Key Takeaways, etc.
- **Interactive Charts**: Added live Chart.js visualizations including:
  - Sessions by Date (line chart with date range selection and grouping by days/weeks/months)
  - Sessions by Course (bar chart) 
  - Sessions by Activity Type (bar chart)
- **Chart API Endpoints**: Created dedicated endpoints for chart data with proper date filtering and aggregation
- **Advanced Date Grouping**: Sessions by Date chart now supports three grouping modes:
  - Days: Individual daily data points
  - Weeks: Weekly aggregation (Monday-Sunday format)
  - Months: Monthly aggregation with full month names
- **Course Title Display**: All course references now show full course titles instead of IDs:
  - Charts display courses as "Claims in an Evolving World" vs "Course 17297132"
  - Conversation lists show proper course names
  - Metrics API returns readable course names
- **Assignment Name Display**: Comprehensive assignment labeling system implemented:
  - Assignment chart endpoint created for future use
  - Conversation lists prepared to show assignment names vs IDs
  - Metrics API updated to use assignment names
  - Priority naming: assignment_name_text > name_text > assignment_name > name > title

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
- **Production Security**: Secure environment-only configuration without fallback values
- **Logging Configuration**: INFO-level logging optimized for production

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

### Runtime Environment
- **Python Runtime**: Flask application requiring Python 3.x
- **Static Asset Serving**: Flask's built-in static file serving for CSS/JS  
- **Template Rendering**: Jinja2 template engine integration