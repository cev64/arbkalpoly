# Kalshi ↔ Polymarket Sports Arbitrage Scanner

## Overview

This project is a real-time sports arbitrage scanner that compares equivalent prediction markets between **Kalshi** and **Polymarket**.

The application should continuously monitor both exchanges, automatically match equivalent sports markets, evaluate whether a true arbitrage exists after accounting for fees and liquidity, and display opportunities in a clean web dashboard.

The initial goal is **opportunity detection and monitoring**, not automated trade execution.

## Core Objectives

- Connect to the Kalshi and Polymarket APIs
- Continuously receive live sports-market data
- Filter out all non-sports markets
- Normalize teams, players, leagues, market types, and betting lines
- Automatically identify equivalent markets
- Verify that matched markets resolve identically
- Detect executable arbitrage opportunities
- Account for fees, spreads, order-book depth, and liquidity
- Display opportunities in real time
- Preserve an architecture that can later support alerts or automated execution

## Important Architecture Rule

> Keep the arbitrage engine completely independent from the user interface.

The frontend should only consume normalized opportunity data exposed by the backend.

The arbitrage logic must not depend on HTML elements, browser state, or UI components. This allows the same backend engine to support future clients such as:

- A GitHub Pages dashboard
- A mobile application
- A Discord bot
- A desktop application
- An automated trading service

Each major component should be independently testable.

## Recommended Tech Stack

### Frontend

- HTML5
- CSS
- Vanilla JavaScript
- GitHub Pages

The frontend should remain static so it can be hosted for free through GitHub Pages.

### Backend

Preferred:

- Python
- FastAPI
- WebSockets where useful

Possible hosting providers:

- Render
- Railway
- Fly.io
- Vercel
- Cloudflare Workers

GitHub Pages cannot securely store private API credentials or run a persistent backend. The frontend should call a separately hosted backend service.

### Data Sources

- Kalshi REST API
- Kalshi WebSocket API
- Polymarket REST API
- Polymarket WebSocket API

Prefer WebSocket feeds for live order-book updates. Use REST for market discovery, metadata, recovery, and periodic reconciliation.

## High-Level Architecture

```text
Kalshi API                 Polymarket API
    │                            │
    └──────────┬─────────────────┘
               ▼
        Market Collectors
               ▼
        Sports-Only Filter
               ▼
        Market Normalizer
               ▼
       Market Matching Engine
               ▼
      Resolution-Rule Validator
               ▼
         Arbitrage Engine
               ▼
      Liquidity and Fee Engine
               ▼
        Opportunity Service
               ▼
       REST / WebSocket API
               ▼
    Static GitHub Pages Dashboard
```

## Suggested Repository Structure

```text
/
├── README.md
├── frontend/
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   └── config.js
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── collectors/
│   │   ├── kalshi.py
│   │   └── polymarket.py
│   ├── normalizer/
│   │   ├── sports_normalizer.py
│   │   ├── team_aliases.py
│   │   └── player_aliases.py
│   ├── matcher/
│   │   ├── market_matcher.py
│   │   └── rule_validator.py
│   ├── arbitrage/
│   │   ├── calculator.py
│   │   ├── fees.py
│   │   ├── liquidity.py
│   │   └── sizing.py
│   ├── models/
│   │   ├── market.py
│   │   ├── order_book.py
│   │   └── opportunity.py
│   ├── services/
│   │   ├── opportunity_service.py
│   │   └── market_cache.py
│   └── api/
│       ├── routes.py
│       └── websocket.py
├── tests/
│   ├── test_normalizer.py
│   ├── test_matcher.py
│   ├── test_arbitrage.py
│   └── fixtures/
├── requirements.txt
├── .env.example
└── .gitignore
```

## Sports Scope

Ignore all non-sports markets.

Initial supported sports and leagues:

- MLB
- NFL
- NBA
- NHL
- NCAA Football
- NCAA Basketball
- Soccer
- Tennis
- Golf
- UFC

Start with the sports and market types that are easiest to normalize reliably.

Recommended first implementation:

1. MLB game winners
2. NFL game winners
3. NBA game winners
4. NHL game winners
5. Championship and season-future markets
6. Player props after the matcher is proven reliable

## Canonical Market Model

Normalize exchange-specific data into one internal format.

Example:

```json
{
  "exchange": "kalshi",
  "market_id": "example-id",
  "sport": "MLB",
  "league": "MLB",
  "event_id": "2026-07-16-NYM-ATL",
  "event_start": "2026-07-16T19:10:00-04:00",
  "home_team": "Atlanta Braves",
  "away_team": "New York Mets",
  "player": null,
  "market_type": "moneyline",
  "selection": "New York Mets",
  "line": null,
  "period": "full_game",
  "yes_best_ask": 0.48,
  "yes_best_bid": 0.46,
  "no_best_ask": 0.55,
  "no_best_bid": 0.53,
  "rules_text": "Exchange settlement wording",
  "market_url": "https://example.com",
  "updated_at": "2026-07-16T17:00:00-04:00"
}
```

Prices should use decimal-dollar values between `0` and `1` internally, even if an exchange returns cents.

## Market Normalization

Normalize the following fields before attempting a match:

- Sport
- League
- Team names
- Player names
- Event start time
- Market type
- Selection
- Betting line
- Period or game segment
- Home and away designation
- Resolution wording

Examples of alias normalization:

```text
NY Yankees       → New York Yankees
Yankees          → New York Yankees
NYY              → New York Yankees
LA Dodgers       → Los Angeles Dodgers
Shohei Ohtani Jr → Shohei Ohtani
```

Store aliases in explicit dictionaries or structured data files so they can be reviewed and tested.

Do not rely only on fuzzy text matching.

## Market Matching

The matcher is the most important part of the project.

Never compare two markets simply because their titles look similar.

Markets should only be paired when the following align:

- Sport and league
- Event participants
- Event date and start time
- Player, when applicable
- Market type
- Selection
- Betting line
- Period or time window
- Settlement conditions

### Matching Process

Use a staged process:

1. Generate candidate matches using league, date, teams, and player.
2. Compare normalized market type and line.
3. Compare period and settlement conditions.
4. Assign a confidence score.
5. Reject candidates below the configured threshold.

### Confidence Scoring

Example:

- `100`: Identical normalized event, market type, line, period, and rules
- `95`: Same contract with minor wording differences
- `85`: Strong structural match but rules need additional confirmation
- `<85`: Do not show as confirmed arbitrage

The threshold should be configurable.

Any opportunity involving ambiguous settlement language should be labeled **manual review required** rather than confirmed.

## Resolution-Rule Validation

A price difference is not an arbitrage unless both contracts settle based on the same outcome.

Check for differences involving:

- Postponed or canceled games
- Starting-player requirements
- Regulation-only versus full-game settlement
- Overtime or extra innings
- Stat corrections
- Dead heats
- Participant withdrawal
- Event rescheduling
- Minimum innings, minutes, attempts, or appearances
- Different data providers
- Different settlement deadlines

Preserve the original rules text from both exchanges and show it in the dashboard.

## Arbitrage Logic

For a binary event with mutually exclusive outcomes, a basic cross-exchange arbitrage exists when the executable cost of buying opposite outcomes is less than the guaranteed settlement value.

Example:

```text
Buy YES on Kalshi for 0.47
Buy NO on Polymarket for 0.49

Total gross cost = 0.96
Guaranteed gross payout = 1.00
Gross edge = 0.04
```

The tool must calculate the result using executable order-book prices, not displayed midpoint or last-trade prices.

### Core Calculation

```text
gross_cost = yes_execution_cost + no_execution_cost
gross_profit = guaranteed_payout - gross_cost
net_profit = gross_profit - estimated_fees
roi = net_profit / gross_cost
```

Only flag the opportunity when:

```text
net_profit > 0
```

The engine should evaluate both directions:

```text
Kalshi YES + Polymarket NO
Polymarket YES + Kalshi NO
```

Do not assume the cheapest displayed quote is available for the full desired quantity.

## Position Sizing and Order-Book Depth

For each opportunity:

1. Read both order books.
2. Walk each book level by level.
3. Find the largest equal payout exposure available on both sides.
4. Calculate the blended execution cost.
5. Subtract estimated exchange fees.
6. Report the maximum executable size and expected net profit.

Example output:

```json
{
  "maximum_cost": 740.00,
  "guaranteed_payout": 764.20,
  "estimated_fees": 4.10,
  "net_profit": 20.10,
  "roi": 0.0272
}
```

Do not report theoretical size beyond available depth.

## Fees

Implement exchange fees in separate modules.

Do not hard-code fee assumptions throughout the codebase.

```text
backend/arbitrage/fees.py
```

The fee interface should accept:

- Exchange
- Market
- Side
- Price
- Quantity
- Order type
- Maker or taker status, when relevant

Because fee schedules can change, keep fee logic configurable and document the source and effective date.

## Opportunity Model

Each displayed opportunity should include:

```json
{
  "id": "stable-opportunity-id",
  "sport": "MLB",
  "event": "Mets at Braves",
  "market": "Mets to win",
  "event_start": "2026-07-16T19:10:00-04:00",
  "kalshi_side": "YES",
  "kalshi_price": 0.47,
  "polymarket_side": "NO",
  "polymarket_price": 0.49,
  "gross_cost": 0.96,
  "estimated_fees": 0.005,
  "net_edge": 0.035,
  "roi": 0.0365,
  "maximum_executable_cost": 500.00,
  "maximum_expected_profit": 18.25,
  "match_confidence": 100,
  "status": "confirmed",
  "last_updated": "2026-07-16T17:00:00-04:00",
  "kalshi_url": "https://example.com",
  "polymarket_url": "https://example.com"
}
```

## Backend API

Suggested endpoints:

```text
GET  /health
GET  /markets
GET  /matches
GET  /opportunities
GET  /opportunities/{id}
GET  /config/public
WS   /ws/opportunities
```

Example query parameters:

```text
GET /opportunities?sport=MLB&minimum_roi=0.02&minimum_liquidity=100
```

Never expose API secrets through the public configuration endpoint.

## Frontend Dashboard

Build a modern, responsive dashboard designed for fast scanning.

### Summary Cards

- Active sports markets
- Matched markets
- Confirmed arbitrage opportunities
- Highest current ROI
- Largest executable position
- Last successful data refresh

### Main Table

Columns:

- Sport
- Event
- Market
- Start time
- Kalshi side and price
- Polymarket side and price
- Net ROI
- Maximum position
- Expected profit
- Match confidence
- Status
- Last update

Features:

- Search
- Sort
- League filters
- Market-type filters
- Minimum ROI filter
- Minimum liquidity filter
- Confidence filter
- Hide stale opportunities
- Mobile-friendly layout

### Opportunity Detail View

Selecting an opportunity should show:

- Full Kalshi order book
- Full Polymarket order book
- Blended execution calculation
- Fee estimate
- Maximum executable quantity
- Settlement language from both exchanges
- Match-confidence explanation
- Direct links to both markets
- Last update timestamp

## Opportunity Statuses

Use explicit statuses:

- `confirmed`
- `manual_review`
- `stale`
- `insufficient_liquidity`
- `no_longer_profitable`
- `rules_mismatch`

Do not leave stale arbitrages displayed as active.

## Refresh Strategy

Preferred:

- WebSocket subscriptions for order-book changes
- REST polling for discovery and reconciliation
- Periodic full refresh to recover from missed messages

Suggested behavior:

- Update active prices immediately from WebSockets
- Recalculate affected opportunities on each relevant book update
- Reconcile market metadata every few minutes
- Mark data stale when no update is received within the configured limit
- Reconnect automatically using exponential backoff

## Caching and State

For the first version, an in-memory cache is acceptable.

The backend should maintain:

- Normalized markets
- Current order books
- Confirmed market pairs
- Active opportunities
- Last-update timestamps

A later version may add PostgreSQL or another database for:

- Historical opportunities
- Performance analysis
- Market-pair overrides
- Audit logs
- Alert history

## Security

- Never place private keys or authenticated API credentials in frontend code.
- Never commit `.env` files.
- Include a `.env.example` with placeholder names only.
- Use environment variables for secrets.
- Restrict backend CORS to the deployed GitHub Pages domain.
- Add rate limiting to public backend endpoints.
- Validate all query parameters.
- Treat exchange API data as untrusted input.
- Escape market text before rendering it in HTML.

Example `.env.example`:

```env
KALSHI_API_KEY_ID=
KALSHI_PRIVATE_KEY_PATH=
POLYMARKET_API_KEY=
ALLOWED_ORIGIN=https://yourusername.github.io
MINIMUM_ROI=0.01
MINIMUM_MATCH_CONFIDENCE=90
STALE_AFTER_SECONDS=15
```

Read-only public market data should be used wherever possible for the initial scanner.

## Testing Requirements

Create unit tests before relying on live opportunities.

### Normalizer Tests

- Team aliases
- Player aliases
- Date and timezone handling
- Market-type parsing
- Betting-line parsing
- Period parsing

### Matcher Tests

- True identical markets
- Similar titles with different rules
- Same teams on different dates
- Player props with different lines
- Regulation-only versus full-game markets
- Postponement-rule differences

### Arbitrage Tests

- Profitable binary arbitrage
- Zero-profit case
- Negative edge
- Multiple order-book levels
- Unequal liquidity
- Fee elimination of apparent profit
- Stale quote rejection
- Rounding behavior

Use saved fixtures so tests do not depend on live APIs.

## Logging and Observability

Log:

- API connection status
- Reconnection attempts
- Markets discovered
- Matches created and rejected
- Rule mismatches
- Opportunities created and removed
- Stale-data events
- API errors
- Fee-calculation errors

Never log private keys or authentication signatures.

## Initial Development Roadmap

### Phase 1: API Connectivity

- Connect to both public APIs
- Retrieve sports markets
- Normalize API responses
- Display raw normalized markets locally

### Phase 2: Matching

- Implement league and team normalization
- Match basic game-winner markets
- Add confidence scores
- Store and display both rules texts

### Phase 3: Arbitrage Detection

- Read executable order books
- Evaluate both cross-exchange directions
- Add fee calculations
- Add depth-aware sizing
- Build unit tests

### Phase 4: Web Dashboard

- Build static HTML/CSS/JavaScript frontend
- Create backend REST and WebSocket endpoints
- Add filters and sorting
- Add opportunity detail view
- Deploy frontend to GitHub Pages

### Phase 5: Reliability

- Add reconnection logic
- Add stale-data protection
- Add logging
- Add historical storage
- Add manual match overrides

### Phase 6: Alerts

- Browser notifications
- Discord webhook
- Email
- Optional SMS

Do not begin automated execution until matching, fee, liquidity, and stale-data logic have been thoroughly validated.

## Definition of Done for Version 1

Version 1 is complete when it can:

1. Fetch live sports markets from both exchanges.
2. Normalize teams, events, market types, and prices.
3. Reliably match a limited set of identical markets.
4. Display both contracts' settlement wording.
5. Calculate arbitrage using executable order-book depth.
6. Include estimated fees.
7. Reject stale or ambiguous opportunities.
8. Show maximum executable size and net profit.
9. Update the GitHub Pages dashboard automatically.
10. Pass unit tests for normalization, matching, fees, and arbitrage calculations.

## Guiding Principles

1. Correctness is more important than speed.
2. False arbitrage alerts are worse than missed opportunities.
3. Never compare markets with materially different settlement rules.
4. Always use executable bid and ask prices.
5. Always account for fees and order-book depth.
6. Keep business logic separate from the frontend.
7. Make each module independently testable.
8. Preserve raw exchange data for debugging.
9. Mark stale or uncertain data clearly.
10. Keep the backend API generic enough for future clients.
11. Start with simple market types before player props.
12. Do not automate execution until the scanner has been validated with live data.

## Future Features

- Discord, email, SMS, and browser alerts
- Historical opportunity database
- Opportunity replay
- Profit and ROI analytics
- Manual pair approval interface
- Automated market-pair learning
- Additional exchanges
- Portfolio tracking
- Automated execution
- Hedging failure protection
- Partial-fill management
- Mobile application
