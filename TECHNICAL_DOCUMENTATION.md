# VyRaTrader - AI-Powered Trading Platform

VyRaTrader is a comprehensive trading platform that combines artificial intelligence with institutional-level trading strategies to provide users with intelligent trading signals and automated portfolio management. The platform features Prince, an AI trading assistant that helps users make informed trading decisions across multiple asset classes including cryptocurrencies, forex, and stocks.

## Overview

VyRaTrader is a full-stack application designed to democratize access to professional-grade trading tools. The platform uses an ensemble of 20+ trading strategies, including institutional-level techniques like VWAP, Order Blocks, Fair Value Gaps, and Market Structure analysis, to generate high-probability trading signals. These signals are filtered through an AI engine that evaluates market conditions and risk parameters before presenting recommendations to users.

## Architecture

### Backend

The backend is built with FastAPI, a modern Python web framework that provides high performance and automatic API documentation. The architecture follows a modular design with clear separation of concerns.

Technology Stack:
- FastAPI for REST API endpoints
- SQLModel/SQLAlchemy for database ORM
- Alembic for database migrations
- AsyncIO for asynchronous operations
- Redis for caching and session management
- PostgreSQL (production) / SQLite (development) for data persistence

Key Components:

1. API Layer (`backend/app/api/v1/`)
   - Authentication and authorization endpoints
   - User management
   - Trading operations
   - Portfolio management
   - Payment processing (Stripe, PayPal, Mobile Money)
   - AI interaction endpoints
   - Market data endpoints
   - Signal generation and delivery

2. Trading Strategies (`backend/app/strategies/`)
   The platform implements 20+ trading strategies organized in tiers:
   
   Institutional-Level Strategies (Highest Priority):
   - VWAP Strategy: Volume-weighted average price analysis used by institutional traders
   - Liquidity Zones: Identifies stop-loss clusters targeted by institutions
   - Order Blocks: Detects areas where large orders were placed
   - Fair Value Gaps: Price imbalances that typically get filled
   - Market Structure: Break of Structure and Change of Character analysis
   - Support/Resistance: Pivot-based levels with order flow confirmation
   - Volume Profile: Price Volume Nodes for natural support/resistance
   
   Technical Indicator Strategies:
   - RSI/MACD Momentum
   - Volume Breakout
   - Trend Following
   - Momentum
   - Breakout
   - Mean Reversion
   - Volatility Breakout
   
   Sentiment and Social Strategies:
   - Sentiment Analysis
   - Sentiment Filter
   - Social Copy Trading

3. AI Engine (`backend/app/ai/`)
   - Ensemble Core: Combines multiple strategy signals with weighted consensus
   - AI Filter: Final quality check using machine learning models
   - Risk Manager: Evaluates trades against risk parameters
   - Trading Engine: Executes approved trades

4. Services (`backend/app/services/`)
   - Data Collector: Aggregates market data from multiple sources
   - Payment Gateway: Handles Stripe, PayPal, Mobile Money, and cryptocurrency payments
   - Broker Adapters: Integration with Binance and OANDA for trade execution
   - Risk Manager: Position sizing, stop-loss management, and portfolio risk limits
   - Scheduler: Background tasks for data collection and signal generation
   - WebSocket Services: Real-time market data streaming

5. Database Models (`backend/app/db/models.py`)
   - User management with premium subscription tracking
   - Account and transaction management
   - Trade history and portfolio tracking
   - AI interaction logs
   - Market data storage (price ticks, orderbooks)
   - Notification system

6. Signal Generator (`signal_generator.py`)
   A standalone service that runs continuously to:
   - Collect market data from free sources
   - Execute all trading strategies
   - Filter signals through AI
   - Send notifications via Telegram
   - Log signals for analysis

### Frontend

The frontend is built with Flutter, enabling cross-platform deployment for iOS, Android, and Web.

Technology Stack:
- Flutter/Dart for cross-platform development
- Provider for state management
- Google Mobile Ads for monetization
- Secure storage for sensitive data
- WebSocket support for real-time updates

Key Features:

1. Authentication System
   - Secure login and registration
   - Password recovery
   - Biometric authentication support
   - Transaction PIN for additional security

2. Dashboard
   - Portfolio overview with P&L tracking
   - Real-time balance and equity display
   - Performance metrics and statistics
   - Win rate and profitability analysis

3. Trading Interface
   - Signal display with AI confidence scores
   - Trade execution with risk parameters
   - Position management
   - Stop-loss and take-profit configuration

4. Payment System
   - Multi-currency support (GHS, USD, EUR, GBP, JPY, CAD, AUD, CHF, CNY, SEK, NGN, ZAR, INR)
   - Multiple payment methods:
     - Mobile Money (MTN, Vodafone, AirtelTigo) for African markets
     - Bank cards via Stripe
     - PayPal integration
     - Cryptocurrency (USDT, USDC, BTC, ETH)
   - Deposit and withdrawal functionality
   - Transaction history

5. Premium Features
   - Subscription management
   - Enhanced signal access
   - Priority support
   - Advanced analytics

6. Prince AI Assistant
   - Floating assistant widget
   - Context-aware trading advice
   - Strategy explanations
   - Risk assessment

7. Ad-Based Monetization
   - Interstitial ads for free users
   - Rewarded ads for additional signals
   - Seamless ad integration

## Key Features

1. Multi-Asset Trading
   - Cryptocurrencies (BTC, ETH, major altcoins)
   - Forex pairs (major and minor pairs)
   - Stock indices and individual stocks

2. Intelligent Signal Generation
   - 20+ trading strategies running simultaneously
   - Weighted ensemble consensus
   - AI-powered filtering for quality assurance
   - Real-time signal delivery

3. Risk Management
   - Position sizing based on account balance
   - Stop-loss and take-profit automation
   - Portfolio risk limits
   - Maximum drawdown protection

4. Payment Processing
   - Secure payment gateway integration
   - Multiple payment methods for global accessibility
   - Automated fee calculation
   - Transaction verification and webhooks

5. User Experience
   - Modern, intuitive interface
   - Real-time data updates
   - Comprehensive trading history
   - Performance analytics

6. Security
   - JWT-based authentication
   - Encrypted sensitive data storage
   - Transaction PIN protection
   - Secure API communication

## Technical Highlights

1. Asynchronous Architecture
   - Full async/await implementation for optimal performance
   - Non-blocking database operations
   - Concurrent strategy execution

2. Scalable Design
   - Modular architecture for easy extension
   - Database migrations for schema evolution
   - Environment-based configuration

3. Production Ready
   - Comprehensive error handling
   - Logging and monitoring
   - Health check endpoints
   - CORS configuration for cross-origin requests

4. Testing
   - Unit tests for core functionality
   - Integration tests for API endpoints
   - Strategy backtesting capabilities

## Deployment

The application supports multiple deployment scenarios:
- Docker containerization for backend services
- Flutter builds for iOS, Android, and Web
- Environment-based configuration for development, staging, and production
- Database migrations via Alembic

## Development Setup

Backend:
1. Install Python dependencies from requirements.txt
2. Configure environment variables (see env.example)
3. Run database migrations: alembic upgrade head
4. Start the FastAPI server: uvicorn backend.app.main:app --reload

Frontend:
1. Install Flutter SDK
2. Install dependencies: flutter pub get
3. Configure .env file with API endpoints
4. Run: flutter run

Signal Generator:
1. Configure AI provider (Ollama, Groq, or HuggingFace)
2. Set Telegram bot token for notifications
3. Run: python signal_generator.py

## Project Structure

```
vyra_trader/
├── backend/              # FastAPI backend application
│   ├── app/
│   │   ├── api/         # API route handlers
│   │   ├── ai/          # AI engine and ensemble
│   │   ├── core/        # Configuration and security
│   │   ├── db/          # Database models and session
│   │   ├── services/    # Business logic services
│   │   ├── strategies/  # Trading strategy implementations
│   │   └── main.py      # Application entry point
│   ├── alembic/         # Database migrations
│   └── requirements.txt # Python dependencies
├── frontend/            # Flutter frontend application
│   ├── lib/
│   │   ├── core/       # Core utilities and configuration
│   │   ├── models/     # Data models
│   │   ├── providers/  # State management
│   │   ├── screens/    # UI screens
│   │   ├── services/   # API clients and services
│   │   └── widgets/    # Reusable UI components
│   └── pubspec.yaml    # Flutter dependencies
├── signal_generator.py  # Standalone signal generation service
├── config/              # Configuration files
└── services/            # Shared services (Telegram, AI filter)
```

## Future Enhancements

- Advanced backtesting framework
- Paper trading mode for strategy testing
- Social trading features
- Mobile app optimization
- Additional broker integrations
- Machine learning model training on historical data
- Real-time collaboration features

This platform represents a complete trading solution that combines institutional-level trading techniques with modern software engineering practices, making professional trading tools accessible to a broader audience.

