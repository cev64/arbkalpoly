const config = window.ARB_APP_CONFIG;
const statusEl = document.querySelector('[data-api-status]');
const tableBody = document.querySelector('[data-opportunities]');

async function refresh() {
  try {
    const health = await fetch(`${config.apiBaseUrl}/health`).then((response) => response.json());
    statusEl.textContent = health.status === 'ok' ? 'Backend online' : 'Backend unavailable';
    const opportunities = await fetch(`${config.apiBaseUrl}/opportunities`).then((response) => response.json());
    tableBody.innerHTML = opportunities.length
      ? opportunities.map(renderOpportunity).join('')
      : '<tr><td colspan="8">No active opportunities yet.</td></tr>';
  } catch (error) {
    statusEl.textContent = 'Backend offline';
    tableBody.innerHTML = '<tr><td colspan="8">Start the FastAPI backend to load opportunities.</td></tr>';
  }
}

function renderOpportunity(opportunity) {
  return `<tr>
    <td>${opportunity.sport}</td>
    <td>${opportunity.event}</td>
    <td>${opportunity.market}</td>
    <td>${opportunity.kalshi_side} @ ${opportunity.kalshi_price}</td>
    <td>${opportunity.polymarket_side} @ ${opportunity.polymarket_price}</td>
    <td>${(opportunity.roi * 100).toFixed(2)}%</td>
    <td>${opportunity.match_confidence}</td>
    <td>${opportunity.status}</td>
  </tr>`;
}

refresh();
setInterval(refresh, 15000);
