const config = window.ARB_APP_CONFIG;
const statusEl = document.querySelector('[data-api-status]');
const marketsBody = document.querySelector('[data-markets]');
const opportunitiesBody = document.querySelector('[data-opportunities]');
const marketCountEl = document.querySelector('[data-market-count]');
const matchCountEl = document.querySelector('[data-match-count]');
const opportunityCountEl = document.querySelector('[data-opportunity-count]');
const highestRoiEl = document.querySelector('[data-highest-roi]');
const detailOverlay = document.querySelector('[data-detail-overlay]');
const detailBody = document.querySelector('[data-detail-body]');
const detailCloseButton = document.querySelector('[data-detail-close]');

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

function formatMoney(value) {
  return Number.isFinite(value) ? `$${value.toFixed(2)}` : '—';
}

function formatPercent(value) {
  return Number.isFinite(value) ? `${(value * 100).toFixed(2)}%` : '—';
}

function formatTime(value) {
  return value ? new Date(value).toLocaleString() : '—';
}

async function getJson(path) {
  const response = await fetch(`${config.apiBaseUrl}${path}`);
  if (!response.ok) throw new Error(`${path} returned ${response.status}`);
  return response.json();
}

function wsUrl(path) {
  const url = new URL(path, config.apiBaseUrl);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  return url.toString();
}

// All exchange-sourced text (rules wording, event names, prices) is untrusted
// input, so every DOM node below is built with textContent, never innerHTML.
function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === 'className') node.className = value;
    else if (key === 'textContent') node.textContent = value;
    else if (key === 'href') node.href = value;
    else node.setAttribute(key, value);
  }
  for (const child of children) node.appendChild(child);
  return node;
}

function renderOrderBookTable(title, book) {
  const container = el('div');
  container.appendChild(el('h4', { textContent: title }));
  const table = el('table');
  table.appendChild(el('thead', {}, [
    el('tr', {}, [
      el('th', { textContent: 'Side' }),
      el('th', { textContent: 'Price' }),
      el('th', { textContent: 'Size' }),
    ]),
  ]));

  const levels = [
    ...book.yes_asks.map((level) => ({ side: 'YES ask', ...level })),
    ...book.no_asks.map((level) => ({ side: 'NO ask', ...level })),
  ];
  const tbody = el('tbody');
  if (!levels.length) {
    tbody.appendChild(el('tr', {}, [el('td', { colspan: '3', textContent: 'No depth available' })]));
  }
  for (const level of levels) {
    tbody.appendChild(el('tr', {}, [
      el('td', { textContent: level.side }),
      el('td', { textContent: formatPrice(level.price) }),
      el('td', { textContent: String(level.quantity) }),
    ]));
  }
  table.appendChild(tbody);
  container.appendChild(table);
  return container;
}

function closeDetail() {
  detailOverlay.hidden = true;
  detailBody.replaceChildren();
}

detailCloseButton.addEventListener('click', closeDetail);
detailOverlay.addEventListener('click', (event) => {
  if (event.target === detailOverlay) closeDetail();
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !detailOverlay.hidden) closeDetail();
});

async function openOpportunityDetail(id) {
  detailOverlay.hidden = false;
  detailBody.replaceChildren(el('p', { textContent: 'Loading…' }));

  try {
    const detail = await getJson(`/opportunities/${encodeURIComponent(id)}`);

    const summary = el('p', {
      textContent:
        `${detail.kalshi_side} @ ${formatPrice(detail.kalshi_price)} on Kalshi + ${detail.polymarket_side} @ ` +
        `${formatPrice(detail.polymarket_price)} on Polymarket · Gross cost ${formatMoney(detail.gross_cost)} · ` +
        `Fees ${formatMoney(detail.estimated_fees)} · Net edge ${formatMoney(detail.net_edge)} · ` +
        `ROI ${formatPercent(detail.roi)} · Max size ${formatMoney(detail.maximum_executable_cost)} · ` +
        `Max profit ${formatMoney(detail.maximum_expected_profit)}`,
    });

    const orderBooks = el('div', { className: 'detail-grid' }, [
      renderOrderBookTable('Kalshi order book', detail.kalshi_order_book),
      renderOrderBookTable('Polymarket order book', detail.polymarket_order_book),
    ]);

    const rules = el('div', { className: 'detail-grid' }, [
      el('div', {}, [
        el('h4', { textContent: 'Kalshi settlement wording' }),
        el('pre', { className: 'rules-text', textContent: detail.kalshi_rules_text || '—' }),
      ]),
      el('div', {}, [
        el('h4', { textContent: 'Polymarket settlement wording' }),
        el('pre', { className: 'rules-text', textContent: detail.polymarket_rules_text || '—' }),
      ]),
    ]);

    const links = el('p', { className: 'detail-links' }, [
      el('a', { href: detail.kalshi_url, target: '_blank', rel: 'noopener', textContent: 'View on Kalshi' }),
      el('a', { href: detail.polymarket_url, target: '_blank', rel: 'noopener', textContent: 'View on Polymarket' }),
    ]);

    detailBody.replaceChildren(
      el('h3', { textContent: `${detail.event} — ${detail.market}` }),
      el('p', {
        textContent: `Status: ${detail.status} · Confidence: ${detail.match_confidence} · Last updated: ${formatTime(detail.last_updated)}`,
      }),
      el('p', { textContent: detail.match_explanation }),
      summary,
      orderBooks,
      rules,
      links,
    );
  } catch (error) {
    detailBody.replaceChildren(el('p', { textContent: 'Could not load opportunity detail.' }));
  }
}

function renderLeg(exchangeName, side, price, stake, fee, url) {
  return el('div', { className: 'leg' }, [
    el('h4', { textContent: exchangeName }),
    el('p', { className: 'leg__side', textContent: `Buy ${side} @ ${formatPrice(price)}` }),
    el('p', { className: 'leg__prob', textContent: `Implied probability ${formatPercent(price)}` }),
    el('p', { className: 'leg__stake' }, [
      document.createTextNode('Stake '),
      el('strong', { textContent: formatMoney(stake) }),
    ]),
    el('p', { className: 'leg__fee', textContent: `Est. exchange fee ${formatMoney(fee)}` }),
    el('a', {
      className: 'leg__link',
      href: url,
      target: '_blank',
      rel: 'noopener',
      textContent: `Place bet on ${exchangeName} →`,
    }),
  ]);
}

function renderOpportunityCard(opportunity) {
  const header = el('div', { className: 'opp-card__header' }, [
    el('div', {}, [
      el('span', { className: 'opp-card__sport', textContent: opportunity.sport }),
      el('h3', { textContent: opportunity.event }),
      el('p', { className: 'opp-card__market', textContent: opportunity.market }),
    ]),
    el('span', { className: `status-badge status-${opportunity.status}`, textContent: opportunity.status }),
  ]);

  const legs = el('div', { className: 'opp-card__legs' }, [
    renderLeg(
      'Kalshi', opportunity.kalshi_side, opportunity.kalshi_price,
      opportunity.kalshi_stake, opportunity.kalshi_fee, opportunity.kalshi_url,
    ),
    renderLeg(
      'Polymarket', opportunity.polymarket_side, opportunity.polymarket_price,
      opportunity.polymarket_stake, opportunity.polymarket_fee, opportunity.polymarket_url,
    ),
  ]);

  const detailButton = el('button', {
    type: 'button',
    className: 'opp-card__detail-trigger',
    textContent: 'Full order book & settlement details',
  });
  detailButton.addEventListener('click', () => openOpportunityDetail(opportunity.id));

  const footer = el('div', { className: 'opp-card__footer' }, [
    el('span', { className: 'opp-card__profit' }, [
      document.createTextNode('Guaranteed profit '),
      el('strong', { textContent: formatMoney(opportunity.net_edge) }),
      document.createTextNode(` (${formatPercent(opportunity.roi)} ROI)`),
    ]),
    el('span', {
      className: 'opp-card__meta',
      textContent:
        `${opportunity.contracts} contracts · Confidence ${opportunity.match_confidence} · ` +
        `Updated ${formatTime(opportunity.last_updated)}`,
    }),
    detailButton,
  ]);

  return el('article', { className: 'opp-card' }, [header, legs, footer]);
}

function renderOpportunitiesMessage(message) {
  opportunitiesBody.replaceChildren(el('p', { className: 'section-note', textContent: message }));
}

function renderOpportunities(opportunities) {
  opportunityCountEl.textContent = opportunities.filter((item) => item.status === 'confirmed').length;
  highestRoiEl.textContent = opportunities.length
    ? formatPercent(Math.max(...opportunities.map((item) => item.roi)))
    : '—';

  if (!opportunities.length) {
    renderOpportunitiesMessage('No active opportunities yet.');
    return;
  }

  opportunitiesBody.replaceChildren(...opportunities.map(renderOpportunityCard));
}

// Opportunities stream over the WebSocket for near-real-time updates; everything
// else (health, markets, matches) is cheap enough to keep on REST polling.
const MIN_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 30000;
let reconnectDelayMs = MIN_RECONNECT_DELAY_MS;

function connectOpportunitiesSocket() {
  const socket = new WebSocket(wsUrl('/ws/opportunities'));

  socket.addEventListener('open', () => {
    reconnectDelayMs = MIN_RECONNECT_DELAY_MS;
  });

  socket.addEventListener('message', (event) => {
    renderOpportunities(JSON.parse(event.data));
  });

  socket.addEventListener('close', () => {
    setTimeout(connectOpportunitiesSocket, reconnectDelayMs);
    reconnectDelayMs = Math.min(reconnectDelayMs * 2, MAX_RECONNECT_DELAY_MS);
  });

  socket.addEventListener('error', () => socket.close());
}

async function refresh() {
  try {
    const [health, markets, matches] = await Promise.all([
      getJson('/health'),
      getJson('/markets?league=MLB&limit=500'),
      getJson('/matches'),
    ]);

    const collectorErrors = Object.keys(health.collectors?.errors || {}).length;
    statusEl.textContent = collectorErrors ? 'Backend online · feed warning' : 'Live feeds online';
    marketCountEl.textContent = health.market_count ?? markets.length;
    matchCountEl.textContent = matches.length;

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
  } catch (error) {
    statusEl.textContent = 'Backend offline';
    replaceRows(marketsBody, [], 'Start the FastAPI backend to load markets.', 7);
    renderOpportunitiesMessage('Start the FastAPI backend to load opportunities.');
  }
}

refresh();
setInterval(refresh, 15000);
connectOpportunitiesSocket();
