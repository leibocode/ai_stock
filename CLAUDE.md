# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Stock is a Chinese A-share stock review and analysis system based on sentiment cycle theory. It integrates data from Tushare, Eastmoney (东方财富), and 10jqka (同花顺) to provide multi-dimensional stock screening and market analysis.

## Common Commands

### Frontend (Vue 3 + Vite)
```bash
cd frontend
npm install          # Install dependencies
npm run dev          # Start dev server on port 3000
npm run build        # Production build
```

### Backend PHP (ThinkPHP 6)
```bash
cd backend
composer install     # Install dependencies
php think run        # Start dev server
php -S localhost:8000 -t public  # Alternative server
```

### Database
```bash
mysql -u root -p < database/schema.sql    # Initialize database
mysql -u root -p < database/migrate_chan.sql  # Chan theory migration
```

## Architecture

### Data Flow
Frontend (port 3000) -> Vite proxy -> Backend API (port 8000) -> MySQL + External APIs (Tushare/Eastmoney)

### Backend Structure (PHP - `backend/`)
- `app/controller/Index.php` - Main API controller, handles all `/api/*` routes
- `app/service/` - Business logic (currently empty, logic in controller)
- `services/TushareService.php` - Tushare API integration for stock data
- `services/IndicatorService.php` - Technical indicator calculations (RSI, MACD, KDJ, Bollinger)
- `services/Database.php` - Database connection wrapper
- `route/app.php` - Route definitions mapping URLs to controller methods

### Backend Structure (Python - `backend-python/`)
- `app/core/chan/` - Chan theory (缠论) implementation:
  - `fractal.py` - Top/bottom fractal detection
  - `bi.py` - Bi (笔) stroke calculation
  - `segment.py` - Segment (线段) calculation
  - `hub.py` - Hub/pivot (中枢) calculation
  - `chan_service.py` - Chan theory orchestration service
- `app/core/indicators/rsi.py` - RSI indicator
- `app/services/tushare_service.py` - Tushare API client
- `app/services/cache_service.py` - Data caching

### Frontend Structure (`frontend/`)
- `src/App.vue` - Single large component containing all UI (74KB monolith)
- `src/api/stock.js` - API client with all endpoint definitions
- `src/api/mock.js` - Mock data for development

### Database Tables (MySQL)
Core: `stocks`, `daily_quotes`, `technical_indicators`, `industry_flow`, `review_records`
Chan theory: `chan_fractal`, `chan_bi`, `chan_segment`, `chan_hub`

## API Patterns

All APIs are GET requests with optional `date` query parameter (format: YYYY-MM-DD). Key endpoints:

- Market data: `/api/volume-top`, `/api/limit-up`, `/api/limit-down`
- Technical: `/api/oversold`, `/api/kdj-bottom`, `/api/macd-golden`, `/api/breakout`
- Capital flow: `/api/north-buy`, `/api/margin-buy`, `/api/dragon-tiger`
- Chan theory: `/api/chan-data`, `/api/chan-first-buy`, `/api/chan-second-buy`
- Sync: `/api/sync-daily`, `/api/calc-indicators`, `/api/crawl-eastmoney`

## Domain Concepts

### Sentiment Cycle (情绪周期)
Five phases: 高潮期 (climax) -> 退潮期 (ebb) -> 冰点期 (freezing) -> 回暖期 (recovery) -> 修复期 (repair)

Determined by: limit-up count (涨停数), consecutive board height (连板高度), advance/decline ratio (涨跌比), board-break rate (炸板率)

### Chan Theory (缠论)
Technical analysis framework using: fractals (分型), strokes/bi (笔), segments (线段), and hubs/pivots (中枢) to identify buy/sell points.

## Configuration

- Backend: Copy `.env.example` to `.env`, configure MySQL and Tushare token
- Frontend: Proxy configured in `vite.config.js` to forward `/api` to backend
