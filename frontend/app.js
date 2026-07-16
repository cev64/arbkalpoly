const config = window.ARB_APP_CONFIG;
const statusEl = document.querySelector('[data-api-status]');
const marketsBody = document.querySelector('[data-markets]');
const opportunitiesBody = document.querySelector('[data-opportunities]');
const marketCountEl = document.querySelector('[data-market-count]');
const matchCountEl = document.querySelector('[data-match-count]');
const opportunityCountEl = document.querySelector('[data-opportunity-count]');
const highestRoiEl = document.querySelector('[data-highest-roi]');

function replaceRows(body, rows, emptyMessage, columnCount) {
  body.replaceChildren();
  if (!rows.length) {
    const row = body.insertRow();
    const cell = row.insertCell();
    cell.colSpan = columnCount;
    cell.textContent = emptyMessage;
    return;
  }

  for (const values of rows) {
    const row = body.insertRow();
    for (const value of values) {
      row.insertCell().textContent = value ?? '—';
    }
  }
}

function gameLabel(market) {
  if (market.away_team && market.home_team) {
    return `${market.away_team} at ${market.home_team}`;
  }
  return market.event_id;
}

function formatPrice(price) {
  return Number.isFinite(price) ? `$${price.toFixed(3)}` : '—';
}

function formatTime(value) {
  return value ? new Date(value).toLocaleString() : '—';
}

async function getJson(path) {
  const response = await fetch(`${config.apiBaseUrl}${path}`);
  if (!response.ok) throw new Error(`${path} returned ${response.status}`);
  return response.json();
}

async function refresh() {
  try {
    const [health, markets, matches, opportunities] = await Promise.all([
      getJson('/health'),
      getJson('/markets?league=MLB&limit=500'),
      getJson('/matches'),
      getJson('/opportunities'),
    ]);

    const collectorErrors = Object.keys(health.collectors?.errors || {}).length;
    statusEl.textContent = collectorErrors ? 'Backend online · feed warning' : 'Live feeds online';
    marketCountEl.textContent = health.market_count ?? markets.length;
    matchCountEl.textContent = matches.length;
    opportunityCountEl.textContent = opportunities.filter((item) => item.status === 'confirmed').length;
    highestRoiEl.textContent = opportunities.length
      ? `${(Math.max(...opportunities.map((item) => item.roi)) * 100).toFixed(2)}%`
      : '—';

    replaceRows(
      marketsBody,
      markets.slice(0, 100).map((market) => [
        market.exchange,
        gameLabel(market),
        formatTime(market.event_start),
        market.selection,
        formatPrice(market.yes_best_bid),
        formatPrice(market.yes_best_ask),
        formatTime(market.updated_at),
      ]),
      'No live markets loaded yet.',
      7,
    );

    replaceRows(
      opportunitiesBody,
      opportunities.map((opportunity) => [
        opportunity.sport,
        opportunity.event,
        opportunity.market,
        `${opportunity.kalshi_side} @ ${opportunity.kalshi_price}`,
        `${opportunity.polymarket_side} @ ${opportunity.polymarket_price}`,
        `${(opportunity.roi * 100).toFixed(2)}%`,
        opportunity.match_confidence,
        opportunity.status,
      ]),
      'No active opportunities yet.',
      8,
    );
  } catch (error) {
    statusEl.textContent = 'Backend offline';
    replaceRows(marketsBody, [], 'Start the FastAPI backend to load markets.', 7);
    replaceRows(opportunitiesBody, [], 'Start the FastAPI backend to load opportunities.', 8);
  }
}

refresh();
setInterval(refresh, 15000);
