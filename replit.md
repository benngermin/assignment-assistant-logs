# Assignment Assistant Dashboard

## Overview

This is a Flask-based web dashboard for the Assignment Assistant system that integrates with a Bubble API to manage assignment-related data. The application provides a clean, responsive web interface using Bootstrap with a dark theme, featuring interactive charts and real-time metrics. Users can view comprehensive analytics including activity counts, course distributions, conversation trends over time, and detailed session breakdowns through an intuitive dashboard interface.

## Recent Changes (August 2025)

### Security Update (August 7, 2025)
- **API Key Security**: Moved Bubble API key from hardcoded values to secure Replit Secrets
- **Environment Variable**: API key now stored as BUBBLE_API_KEY_LIVE in Replit Secrets
- **Code Cleanup**: Removed all hardcoded API keys from source files (DASHBOARD_SETUP.md, start_dashboard.sh)
- **Verified Connectivity**: Confirmed API connection working with secure credential storage

### Database Sync Fix (August 7, 2025)
- **Fixed Empty Dashboard Issue**: Resolved problem where dashboard showed 0 conversations and messages despite API having data
- **Incremental Sync Solution**: Created new incremental sync endpoint that fetches data in very small batches (10-25 items)
- **Timeout Prevention**: Each refresh now adds only 100 items at a time to prevent timeouts completely
- **Progressive Loading**: Users can click refresh multiple times to gradually sync all 8000+ conversations and 10000+ messages
- **Current Database State**: Successfully synced 920 conversations and 570 messages
- **User Experience**: Clear progress messages show how many items were added with each sync
- **API Stats**: Bubble API contains 8000+ conversations and 10000+ messages total

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
- **Client-side JavaScript**: Vanilla JavaScript for dashboard interactions with async/await for data sync
- **CSS Organization**: Custom CSS variables and Bootstrap overrides for consistent theming
- **Data Refresh**: Two-stage refresh process - first syncs Bubble API to database, then loads dashboard from database

### Backend Architecture
The backend uses a database-driven architecture with Flask and PostgreSQL:
- **Web Framework**: Flask with SQLAlchemy ORM for database operations
- **Database**: PostgreSQL for local data storage and caching
- **Data Sync**: BubbleSyncManager handles incremental and full syncs from Bubble API
- **Query Layer**: Database query functions for efficient data retrieval
- **Error Handling**: Comprehensive logging and exception handling for API and database operations
- **Session Management**: Flask sessions with configurable secret key from environment variables

### Data Integration Pattern
The system uses a database-centric approach with API sync:
- **Primary Data Store**: Local PostgreSQL database for all dashboard data
- **Sync Strategy**: On-demand sync from Bubble API triggered by "Refresh Data" button
- **Incremental Updates**: After initial full sync, only fetches new/modified records
- **Data Models**: SQLAlchemy models for Users, Courses, Assignments, Conversations, Messages, etc.
- **Sync Tracking**: SyncStatus table tracks last sync time and status for each data type
- **API Fallback**: Falls back to direct API calls if database is empty

### Database Schema
Key database tables:
- **users**: User profiles with email, roles, and settings
- **courses**: Course information with names and metadata
- **assignments**: Assignment details linked to courses
- **conversations**: User conversations with course/assignment associations
- **messages**: Individual messages within conversations
- **conversation_starters**: Activity types (Quiz, Review, etc.)
- **sync_status**: Tracks sync state for each data type

### Configuration Management
Environment-based configuration pattern:
- **Environment Variables**: Used for sensitive data like session secrets and API credentials
- **Database Connection**: DATABASE_URL for PostgreSQL connection
- **API Authentication**: BUBBLE_API_KEY_LIVE for Bubble API access
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