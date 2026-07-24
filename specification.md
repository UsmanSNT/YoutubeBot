# VideoGrabberBot: Technical Specification

This specification describes the architecture and functionality of VideoGrabberBot, a Telegram bot for downloading videos and audio from YouTube with format selection options.

## Overview

VideoGrabberBot allows users to download videos and audio from YouTube by sending links to the bot. It offers multiple format options (SD, HD, Full HD, Original for video; MP3 for audio) and delivers the files directly in the Telegram chat. Access to the bot is restricted through an authorization system, and all operations are logged with comprehensive error handling.

## Functional Requirements

### 1. Media Source Support

- **YouTube Integration**:
  - Process standard YouTube URLs (youtube.com, youtu.be, m.youtube.com, youtube-nocookie.com)
  - Extract video metadata and available formats
  - Support for both short and long videos (up to Bot API's file size limit of 50MB)

### 2. Format Selection System

- **Video Quality Options**:
  - Standard Definition (480p resolution)
  - High Definition (720p resolution) 
  - Full High Definition (1080p resolution)
  - Original Quality (maximum available resolution)

- **Audio Extraction**:
  - High-quality audio extraction (320kbps equivalent)
  - Audio-only download option

- **Selection Interface**:
  - Present format options via Telegram's InlineKeyboard
  - Allow user to select desired format with a single tap
  - Provide feedback on selected format during download

### 3. Access Control System

- **User Authorization Mechanisms**:
  - Admin-only access for initial setup (configurable via ADMIN_USER_ID)
  - Invitation link system for granting access to new users
  - Direct user addition by admin (using /adduser command)

- **Persistent User Storage**:
  - Store authorized users in persistent database
  - Track invitation creation and usage

### 4. Download Queue Management

- **Asynchronous Processing**:
  - Queue system for handling multiple download requests
  - Sequential processing to prevent resource contention
  - Status updates for queued downloads

- **Task Tracking**:
  - Track current download status
  - Allow cancellation of queued downloads
  - Provide queue position updates

### 5. Error Handling & Notification

- **Comprehensive Error Management**:
  - Handle network failures, API changes, and invalid URLs
  - Provide clear error messages to users
  - Notify admin of critical failures

- **Logging System**:
  - Detailed logging of all operations
  - Error stack traces for debugging
  - Admin notifications for critical issues

## Technical Architecture

### Core Components

1. **Bot Framework Layer**:
   - Telegram Bot API integration framework
   - Event-driven architecture with message routing
   - Asynchronous message handling

2. **Handler Layer**:
   - Command processing system
   - URL processing and validation
   - User interaction callback handlers

3. **Service Layer**:
   - Video download service: Interface to external video downloading library
   - Format management service: Quality and format option handling
   - Task queue service: Download request processing queue
   - Temporary storage service: Short-term URL and file storage

4. **Data Layer**:
   - Database abstraction and utilities
   - Persistent storage for user authorization and invitations
   - Temporary file system management

5. **Utility Layer**:
   - Logging configuration
   - Error notification
   - Configuration management

### Component Interactions

```
User -> Telegram -> Bot Framework -> Handlers -> Services -> External APIs
                                                 |
                                                 v
                                              Database
```

1. User sends a YouTube URL to the bot via Telegram
2. Bot framework passes message to URL handler
3. Handler verifies user authorization via database
4. Handler displays format options via InlineKeyboard
5. User selects a format, triggering a callback
6. Handler adds download task to queue
7. Queue processor executes download via video extraction service
8. Downloaded file is sent back to user via Telegram

## Data Model

### User Entity

**Purpose**: Store authorized users and track access permissions

**Attributes**:
- User identifier (unique, matches Telegram user ID)
- Username (for display purposes)
- Authorization timestamp
- Reference to authorizing user (who added this user)
- Active status flag

### Invitation Entity

**Purpose**: Manage access control through invitation system

**Attributes**:
- Unique invitation code
- Creator reference (who created the invite)
- Creation timestamp
- Usage information (who used it, when)
- Active status flag

**Relationships**:
- Creator: User who generated the invitation
- Used by: User who redeemed the invitation (if any)

### Configuration Entity

**Purpose**: Store system settings and configuration

**Attributes**:
- Setting key (unique identifier)
- Setting value (flexible data storage)
- Last update timestamp

### Entity Relationships

- Users can create multiple Invitations
- Each Invitation can be used by at most one User
- Users have a hierarchical relationship (added_by references another User)
- Configuration settings are independent key-value pairs

## Implementation Details

### Download Process

1. **URL Validation**:
   - Verify URL is from supported platform (YouTube)
   - Check for valid video ID format

2. **Format Analysis**:
   - Parse available formats using video extraction library
   - Filter and group formats based on resolution/quality
   - Present simplified options to user

3. **Download Execution**:
   - Create temporary directory for download
   - Configure video extraction service with selected format
   - Monitor download progress
   - Verify downloaded file integrity

4. **File Delivery**:
   - Send file as document via Telegram
   - Include metadata (title, source)
   - Clean up temporary files after sending

### Authentication Flow

1. **Initial Setup**:
   - Admin ID is set via environment variable
   - Admin has full access to all commands

2. **User Authorization**:
   - New users can join via invite links
   - Admin can directly add users with /adduser command
   - All user access is verified on each command

3. **Invite Generation**:
   - Admin or authorized user creates invite
   - Unique UUID is generated and stored in database
   - Invite link includes bot username and invite code
   - Invites can be used only once

## Environment Requirements

### Runtime Requirements

- **Programming Language**: Support for asynchronous programming, strong networking capabilities
- **Telegram Bot API Integration**: Framework or library for Telegram Bot API interactions
- **Video Download Capability**: Library supporting YouTube video extraction and download
- **Database Support**: Persistent storage system with async operations support
- **Logging System**: Structured logging with multiple output formats
- **Configuration Management**: Environment variable handling and configuration

### Development Requirements

- **Type System**: Static type checking capability
- **Testing Framework**: Async-compatible testing with mocking and coverage support
- **Code Quality Tools**: Linting, formatting, and style checking tools
- **Development Workflow**: Package management and dependency resolution

### Configuration

Required environment variables:
- `TELEGRAM_TOKEN`: Bot API token from BotFather
- `ADMIN_USER_ID`: Telegram user ID of the administrator

### Storage Structure

**Data Directory**:
- **Database Files**: Persistent storage for user authorization and configuration
- **Temporary Storage**: Short-term storage for download/upload operations
- **Log Files**: System operation logs and audit trails

**Storage Requirements**:
- Persistent data must survive system restarts
- Temporary files can be cleared on startup
- Adequate space for concurrent download operations

## Deployment Requirements

### System Requirements

**Compute Resources**:
- CPU: Sufficient for concurrent video processing and file I/O operations
- Memory: Adequate for handling multiple concurrent download requests
- Storage: Space for temporary file storage during download/upload process

**Network Requirements**:
- Stable internet connection with adequate bandwidth for video downloads
- Access to Telegram Bot API endpoints
- Access to YouTube and other supported video platforms

**Runtime Environment**:
- Support for asynchronous programming execution
- File system access for temporary storage
- Environment variable configuration support
- Process management capabilities

### Deployment Process

**Preparation Steps**:
1. Obtain source code from repository
2. Install required runtime environment and dependencies
3. Configure system environment variables
4. Initialize persistent data storage
5. Set up temporary file storage directories

**Configuration Requirements**:
- Bot API token (from Telegram BotFather)
- Administrator user identification
- Storage location configuration
- Optional: Logging level and output settings

**Startup Process**:
- Initialize database and verify connectivity
- Establish Telegram Bot API connection
- Start message handling and queue processing systems
- Begin health monitoring and logging

## Security Considerations

### Data Protection
- API credentials stored securely outside source control
- Temporary files automatically cleaned after processing
- Minimal user data collection (only authorization information)
- No sensitive personal information stored or transmitted

### Access Control
- Multi-layer authorization system prevents unauthorized usage
- All user interactions require authorization validation
- Administrative functions restricted to designated admin users
- Invitation system provides controlled access expansion

### Network Security
- Rate limiting handled by external API providers
- Secure communication with Telegram Bot API
- No direct user data transmission to third parties
- Error messages sanitized to prevent information disclosure

### Authorization System
- All user interactions require authorization validation
- Authorization checks implemented in both URL processing and callback handling
- Prevents bypass attacks through direct callback manipulation

### Recent Security Improvements
- Fixed callback query authorization bypass vulnerability (January 2025)
- Added comprehensive security test coverage (43 security tests)
- Implemented defense-in-depth for all user-facing endpoints
- All handlers now validate user authorization before processing

## Limitations

- Maximum file size: 50MB (Telegram Bot API limitation)
- Processing time dependent on video length/quality
- Queue system handles requests sequentially
- Single admin user configuration
- YouTube only support (no other platforms)