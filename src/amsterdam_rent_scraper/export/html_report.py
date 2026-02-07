"""Generate interactive HTML report with filtering, sorting, and map view."""

from pathlib import Path
from typing import Any, Optional

import folium
from jinja2 import Template
from rich.console import Console

from amsterdam_rent_scraper.config.settings import (
    DEFAULT_CITY,
    HTML_FILENAME,
    WORK_LAT,
    WORK_LNG,
    WORK_ADDRESS,
    get_city_config,
)
from amsterdam_rent_scraper.models.listing import RentalListing

console = Console()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ city_name }} Rental Listings</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        :root {
            --color-primary: #3498db;
            --color-primary-dark: #2980b9;
            --color-secondary: #2c3e50;
            --color-secondary-dark: #1a252f;
            --color-success: #27ae60;
            --color-warning: #f39c12;
            --color-danger: #e74c3c;
            --color-gray-100: #f8f9fa;
            --color-gray-200: #ecf0f1;
            --color-gray-300: #ddd;
            --color-gray-500: #95a5a6;
            --color-gray-600: #666;
            --color-gray-700: #34495e;
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.08);
            --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
            --shadow-lg: 0 10px 25px rgba(0,0,0,0.15);
            --radius-sm: 4px;
            --radius-md: 8px;
            --radius-lg: 12px;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); min-height: 100vh; }
        .container { max-width: 1600px; margin: 0 auto; padding: 20px; }
        header { background: linear-gradient(135deg, var(--color-secondary) 0%, var(--color-secondary-dark) 100%); color: white; padding: 24px 28px; margin-bottom: 24px; border-radius: var(--radius-lg); box-shadow: var(--shadow-lg); }
        header h1 { font-size: 1.8rem; margin-bottom: 8px; font-weight: 700; }
        header p { opacity: 0.85; font-size: 0.95rem; }

        .filters { background: white; padding: 20px 24px; border-radius: var(--radius-lg); margin-bottom: 20px; box-shadow: var(--shadow-md); }
        .filter-row { display: flex; flex-wrap: wrap; gap: 16px; align-items: end; }
        .filter-group { display: flex; flex-direction: column; }
        .filter-group label { font-size: 0.75rem; color: var(--color-gray-600); margin-bottom: 6px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
        .filter-group input, .filter-group select { padding: 10px 14px; border: 2px solid var(--color-gray-200); border-radius: var(--radius-sm); font-size: 0.9rem; transition: border-color 0.2s, box-shadow 0.2s; }
        .filter-group input:focus, .filter-group select:focus { outline: none; border-color: var(--color-primary); box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.15); }
        .filter-group input[type="number"] { width: 110px; }

        /* Price range slider styles */
        .price-slider-group { min-width: 280px; }
        .price-slider-container { position: relative; height: 40px; }
        .price-slider-track { position: absolute; top: 50%; left: 0; right: 0; height: 6px; background: var(--color-gray-200); border-radius: 3px; transform: translateY(-50%); }
        .price-slider-range { position: absolute; top: 50%; height: 6px; background: linear-gradient(90deg, var(--color-success) 0%, var(--color-warning) 50%, var(--color-danger) 100%); border-radius: 3px; transform: translateY(-50%); }
        .price-slider-container input[type="range"] { position: absolute; top: 50%; transform: translateY(-50%); width: 100%; height: 6px; -webkit-appearance: none; background: transparent; pointer-events: none; }
        .price-slider-container input[type="range"]::-webkit-slider-thumb { -webkit-appearance: none; width: 20px; height: 20px; background: white; border: 3px solid var(--color-primary); border-radius: 50%; cursor: pointer; pointer-events: auto; box-shadow: var(--shadow-sm); transition: transform 0.15s; }
        .price-slider-container input[type="range"]::-webkit-slider-thumb:hover { transform: scale(1.15); }
        .price-slider-container input[type="range"]::-moz-range-thumb { width: 20px; height: 20px; background: white; border: 3px solid var(--color-primary); border-radius: 50%; cursor: pointer; pointer-events: auto; box-shadow: var(--shadow-sm); }
        .price-slider-values { display: flex; justify-content: space-between; margin-top: 8px; font-size: 0.85rem; font-weight: 600; color: var(--color-secondary); }

        button { padding: 10px 20px; background: var(--color-primary); color: white; border: none; border-radius: var(--radius-sm); cursor: pointer; font-size: 0.9rem; font-weight: 600; transition: background 0.2s, transform 0.15s; }
        button:hover { background: var(--color-primary-dark); transform: translateY(-1px); }
        button:active { transform: translateY(0); }
        .btn-reset { background: var(--color-gray-500); }
        .btn-reset:hover { background: #7f8c8d; }

        .view-toggle { display: flex; gap: 8px; margin-bottom: 20px; }
        .view-toggle button { background: var(--color-gray-200); color: var(--color-secondary); padding: 10px 18px; }
        .view-toggle button.active { background: var(--color-primary); color: white; }

        #map { height: 600px; border-radius: var(--radius-lg); margin-bottom: 20px; display: none; position: relative; box-shadow: var(--shadow-md); }
        #map.visible { display: block; }
        .map-legend { position: absolute; bottom: 20px; left: 10px; background: white; padding: 12px 16px; border-radius: var(--radius-md); box-shadow: var(--shadow-lg); z-index: 1000; font-size: 0.8rem; }
        .map-legend h4 { margin: 0 0 8px 0; font-size: 0.85rem; font-weight: 700; color: var(--color-secondary); }
        .legend-item { display: flex; align-items: center; margin: 4px 0; }
        .legend-dot { width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; border: 2px solid white; box-shadow: 0 1px 2px rgba(0,0,0,0.2); }
        .legend-circle { width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; border: 1px dashed; background: transparent; }

        .stats { background: white; padding: 18px 24px; border-radius: var(--radius-lg); margin-bottom: 20px; display: flex; gap: 40px; box-shadow: var(--shadow-md); }
        .stat { text-align: center; }
        .stat-value { font-size: 1.6rem; font-weight: 700; color: var(--color-secondary); }
        .stat-label { font-size: 0.75rem; color: var(--color-gray-600); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }

        /* Cards View */
        .cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; display: none; }
        .cards-grid.visible { display: grid; }
        .listing-card { background: white; border-radius: var(--radius-lg); overflow: hidden; box-shadow: var(--shadow-md); transition: transform 0.2s, box-shadow 0.2s; display: flex; flex-direction: column; }
        .listing-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-lg); }
        .card-header { padding: 16px 20px; background: linear-gradient(135deg, var(--color-gray-100) 0%, white 100%); border-bottom: 1px solid var(--color-gray-200); }
        .card-price { font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; }
        .card-price.price-low { color: var(--color-success); }
        .card-price.price-mid { color: var(--color-warning); }
        .card-price.price-high { color: var(--color-danger); }
        .card-address { font-size: 0.9rem; color: var(--color-gray-600); line-height: 1.4; }
        .card-body { padding: 16px 20px; flex: 1; display: flex; flex-direction: column; gap: 12px; }
        .card-specs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
        .card-spec { text-align: center; padding: 10px 8px; background: var(--color-gray-100); border-radius: var(--radius-sm); }
        .card-spec-value { font-size: 1.1rem; font-weight: 700; color: var(--color-secondary); }
        .card-spec-label { font-size: 0.7rem; color: var(--color-gray-600); text-transform: uppercase; margin-top: 2px; }
        .card-commute { display: flex; gap: 16px; padding: 12px 14px; background: var(--color-gray-100); border-radius: var(--radius-sm); }
        .card-commute-item { display: flex; align-items: center; gap: 6px; font-size: 0.85rem; color: var(--color-gray-600); }
        .card-commute-item span { font-weight: 600; color: var(--color-secondary); }
        .card-neighborhood { display: flex; align-items: center; gap: 10px; padding: 10px 14px; background: var(--color-gray-100); border-radius: var(--radius-sm); }
        .card-neighborhood-score { font-size: 1.1rem; font-weight: 700; padding: 4px 10px; border-radius: var(--radius-sm); }
        .card-neighborhood-name { font-size: 0.85rem; color: var(--color-gray-600); }
        .card-tags { display: flex; flex-wrap: wrap; gap: 6px; }
        .card-summary { font-size: 0.85rem; color: var(--color-gray-600); line-height: 1.5; flex: 1; }
        .card-footer { padding: 14px 20px; border-top: 1px solid var(--color-gray-200); display: flex; justify-content: space-between; align-items: center; background: var(--color-gray-100); }
        .card-source { font-size: 0.75rem; color: var(--color-gray-500); text-transform: uppercase; letter-spacing: 0.5px; }
        .card-link { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; background: var(--color-primary); color: white; text-decoration: none; border-radius: var(--radius-sm); font-size: 0.85rem; font-weight: 600; transition: background 0.2s; }
        .card-link:hover { background: var(--color-primary-dark); }

        /* Table View */
        table { width: 100%; background: white; border-radius: var(--radius-lg); overflow: hidden; box-shadow: var(--shadow-md); display: none; }
        table.visible { display: table; }
        th { background: var(--color-gray-700); color: white; padding: 14px 10px; text-align: left; font-size: 0.8rem; cursor: pointer; white-space: nowrap; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
        th:hover { background: var(--color-secondary); }
        th.sorted-asc::after { content: ' ▲'; }
        th.sorted-desc::after { content: ' ▼'; }
        td { padding: 12px 10px; border-bottom: 1px solid var(--color-gray-200); font-size: 0.85rem; vertical-align: top; }
        tr:hover { background: var(--color-gray-100); }
        .price { font-weight: 700; }
        .price-low { color: var(--color-success); }
        .price-mid { color: var(--color-warning); }
        .price-high { color: var(--color-danger); }
        .url-link { color: var(--color-primary); text-decoration: none; font-weight: 600; }
        .url-link:hover { text-decoration: underline; }
        .summary { max-width: 300px; }
        .tag { display: inline-block; padding: 3px 8px; border-radius: var(--radius-sm); font-size: 0.7rem; font-weight: 600; text-transform: uppercase; }
        .tag-furnished { background: #d5f5e3; color: var(--color-success); }
        .tag-unfurnished { background: #fdebd0; color: #e67e22; }
        .tag-upholstered { background: #e8daef; color: #8e44ad; }

        .neighborhood-score { display: inline-block; padding: 4px 10px; border-radius: var(--radius-sm); font-size: 0.8rem; font-weight: 700; }
        .score-high { background: #d5f5e3; color: var(--color-success); }
        .score-mid { background: #fef9e7; color: #d68910; }
        .score-low { background: #fadbd8; color: #c0392b; }
        .neighborhood-name { font-size: 0.75rem; color: var(--color-gray-600); display: block; margin-top: 3px; }
        .neighborhood-tooltip { position: relative; cursor: help; }
        .neighborhood-tooltip .tooltip-content { display: none; position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%); background: var(--color-secondary); color: white; padding: 12px 14px; border-radius: var(--radius-md); font-size: 0.75rem; white-space: nowrap; z-index: 100; box-shadow: var(--shadow-lg); }
        .neighborhood-tooltip:hover .tooltip-content { display: block; }
        .tooltip-row { display: flex; justify-content: space-between; gap: 15px; margin: 4px 0; }
        .tooltip-label { opacity: 0.8; }
        .tooltip-value { font-weight: 700; }

        .no-results { text-align: center; padding: 60px 40px; color: var(--color-gray-600); background: white; border-radius: var(--radius-lg); box-shadow: var(--shadow-md); }
        .no-results h3 { font-size: 1.2rem; margin-bottom: 8px; color: var(--color-secondary); }

        @media (max-width: 768px) {
            .filter-row { flex-direction: column; }
            .stats { flex-wrap: wrap; gap: 20px; }
            .cards-grid { grid-template-columns: 1fr; }
            .price-slider-group { min-width: 100%; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{{ city_name }} Rental Listings</h1>
            <p>{{ listings|length }} listings scraped from {{ sources|length }} sources | Target: {{ work_address }}</p>
        </header>

        <div class="filters">
            <div class="filter-row">
                <div class="filter-group price-slider-group">
                    <label>Price Range (EUR)</label>
                    <div class="price-slider-container">
                        <div class="price-slider-track"></div>
                        <div class="price-slider-range" id="priceSliderRange"></div>
                        <input type="range" id="priceSliderMin" min="500" max="3500" value="1000" step="50">
                        <input type="range" id="priceSliderMax" min="500" max="3500" value="2000" step="50">
                    </div>
                    <div class="price-slider-values">
                        <span id="priceMinDisplay">EUR 1000</span>
                        <span id="priceMaxDisplay">EUR 2000</span>
                    </div>
                </div>
                <div class="filter-group">
                    <label>Min Rooms</label>
                    <input type="number" id="minRooms" placeholder="1">
                </div>
                <div class="filter-group">
                    <label>Max Distance (km)</label>
                    <input type="number" id="maxDistance" placeholder="10">
                </div>
                <div class="filter-group">
                    <label>Max Bike Commute (min)</label>
                    <input type="number" id="maxBikeTime" placeholder="30">
                </div>
                <div class="filter-group">
                    <label>Max Transit Commute (min)</label>
                    <input type="number" id="maxTransitTime" placeholder="45">
                </div>
                <div class="filter-group">
                    <label>Furnished</label>
                    <select id="furnished">
                        <option value="">Any</option>
                        <option value="Furnished">Furnished</option>
                        <option value="Unfurnished">Unfurnished</option>
                        <option value="Upholstered">Upholstered</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Source</label>
                    <select id="source">
                        <option value="">All Sources</option>
                        {% for source in sources %}
                        <option value="{{ source }}">{{ source }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="filter-group">
                    <label>Min Neighborhood Score</label>
                    <input type="number" id="minNeighborhoodScore" placeholder="7" step="0.1" min="1" max="10">
                </div>
                <button onclick="applyFilters()">Apply Filters</button>
                <button class="btn-reset" onclick="resetFilters()">Reset</button>
            </div>
        </div>

        <div class="view-toggle">
            <button id="btnCards" class="active" onclick="showView('cards')">Cards</button>
            <button id="btnTable" onclick="showView('table')">Table</button>
            <button id="btnMap" onclick="showView('map')">Map</button>
        </div>

        <div class="stats">
            <div class="stat">
                <div class="stat-value" id="statCount">{{ listings|length }}</div>
                <div class="stat-label">Listings</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="statAvgPrice">-</div>
                <div class="stat-label">Avg Price</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="statAvgSize">-</div>
                <div class="stat-label">Avg Size (m2)</div>
            </div>
        </div>

        <div id="map">
            <div class="map-legend">
                <h4>Price Range</h4>
                <div class="legend-item"><span class="legend-dot" style="background:#27ae60;"></span> &lt; EUR 1300</div>
                <div class="legend-item"><span class="legend-dot" style="background:#f39c12;"></span> EUR 1300-1700</div>
                <div class="legend-item"><span class="legend-dot" style="background:#e74c3c;"></span> &gt; EUR 1700</div>
                <h4 style="margin-top:10px;">Distance</h4>
                <div class="legend-item"><span class="legend-circle" style="border-color:#3498db;"></span> 5 km</div>
                <div class="legend-item"><span class="legend-circle" style="border-color:#9b59b6;"></span> 10 km</div>
                <div class="legend-item"><span class="legend-circle" style="border-color:#95a5a6;"></span> 15 km</div>
            </div>
        </div>

        <div class="cards-grid visible" id="cardsGrid"></div>

        <table id="listingsTable">
            <thead>
                <tr>
                    <th data-sort="source_site">Source</th>
                    <th data-sort="price_eur">Price</th>
                    <th data-sort="address">Address</th>
                    <th data-sort="surface_m2">Size</th>
                    <th data-sort="rooms">Rooms</th>
                    <th data-sort="furnished">Furnished</th>
                    <th data-sort="available_date">Available</th>
                    <th data-sort="distance_km">Distance</th>
                    <th data-sort="commute_time_bike_min">Bike</th>
                    <th data-sort="commute_time_transit_min">Transit</th>
                    <th data-sort="commute_time_driving_min">Car</th>
                    <th data-sort="neighborhood_overall">Area</th>
                    <th>Summary</th>
                    <th>Link</th>
                </tr>
            </thead>
            <tbody id="tableBody">
            </tbody>
        </table>
        <div class="no-results" id="noResults" style="display:none;">
            <h3>No listings found</h3>
            <p>Try adjusting your filters to see more results.</p>
        </div>
    </div>

    <script>
        const listings = {{ listings_json|safe }};
        const workLocation = [{{ work_lat }}, {{ work_lng }}];
        let map = null;
        let markers = [];
        let currentRoute = null;
        let currentSort = { column: 'price_eur', direction: 'asc' };
        let currentView = 'cards';

        // Price slider setup
        const priceSliderMin = document.getElementById('priceSliderMin');
        const priceSliderMax = document.getElementById('priceSliderMax');
        const priceSliderRange = document.getElementById('priceSliderRange');
        const priceMinDisplay = document.getElementById('priceMinDisplay');
        const priceMaxDisplay = document.getElementById('priceMaxDisplay');

        function updatePriceSlider() {
            const min = parseInt(priceSliderMin.value);
            const max = parseInt(priceSliderMax.value);
            const sliderMin = parseInt(priceSliderMin.min);
            const sliderMax = parseInt(priceSliderMin.max);
            const range = sliderMax - sliderMin;

            // Prevent crossing
            if (min > max - 100) {
                if (this === priceSliderMin) {
                    priceSliderMin.value = max - 100;
                } else {
                    priceSliderMax.value = min + 100;
                }
            }

            const minVal = parseInt(priceSliderMin.value);
            const maxVal = parseInt(priceSliderMax.value);
            const leftPercent = ((minVal - sliderMin) / range) * 100;
            const rightPercent = ((maxVal - sliderMin) / range) * 100;

            priceSliderRange.style.left = leftPercent + '%';
            priceSliderRange.style.width = (rightPercent - leftPercent) + '%';

            priceMinDisplay.textContent = 'EUR ' + minVal;
            priceMaxDisplay.textContent = 'EUR ' + maxVal;
        }

        priceSliderMin.addEventListener('input', updatePriceSlider);
        priceSliderMax.addEventListener('input', updatePriceSlider);
        priceSliderMin.addEventListener('change', applyFilters);
        priceSliderMax.addEventListener('change', applyFilters);
        updatePriceSlider();

        function initMap() {
            map = L.map('map').setView(workLocation, 12);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap contributors'
            }).addTo(map);

            L.circle(workLocation, { radius: 5000, color: '#3498db', fillColor: '#3498db', fillOpacity: 0.05, weight: 1, dashArray: '5, 5' }).addTo(map).bindPopup('5 km from work');
            L.circle(workLocation, { radius: 10000, color: '#9b59b6', fillColor: '#9b59b6', fillOpacity: 0.03, weight: 1, dashArray: '5, 5' }).addTo(map).bindPopup('10 km from work');
            L.circle(workLocation, { radius: 15000, color: '#95a5a6', fillColor: '#95a5a6', fillOpacity: 0.02, weight: 1, dashArray: '5, 5' }).addTo(map).bindPopup('15 km from work');

            L.marker(workLocation, {
                icon: L.divIcon({
                    className: 'work-marker',
                    html: '<div style="background:#2c3e50;color:white;padding:5px 10px;border-radius:4px;font-weight:bold;box-shadow:0 2px 4px rgba(0,0,0,0.3);">Office</div>',
                    iconSize: [50, 30]
                })
            }).addTo(map).bindPopup('<b>Work Location</b><br>{{ work_address }}');
        }

        function getPriceColor(price) {
            if (!price) return '#95a5a6';
            if (price < 1300) return '#27ae60';
            if (price < 1700) return '#f39c12';
            return '#e74c3c';
        }

        function getPriceClass(price) {
            if (!price) return '';
            if (price < 1300) return 'price-low';
            if (price < 1700) return 'price-mid';
            return 'price-high';
        }

        function getScoreClass(score) {
            if (!score) return '';
            if (score >= 7.5) return 'score-high';
            if (score >= 6) return 'score-mid';
            return 'score-low';
        }

        function createPriceMarker(price) {
            const color = getPriceColor(price);
            return L.divIcon({
                className: 'price-marker',
                html: `<div style="background:${color};color:white;padding:3px 6px;border-radius:50%;width:12px;height:12px;border:2px solid white;box-shadow:0 2px 4px rgba(0,0,0,0.3);"></div>`,
                iconSize: [16, 16],
                iconAnchor: [8, 8]
            });
        }

        function clearRoute() {
            if (currentRoute) {
                map.removeLayer(currentRoute);
                currentRoute = null;
            }
        }

        function showRoute(listing) {
            clearRoute();
            if (!listing.bike_route_coords || listing.bike_route_coords.length === 0) return;
            const latLngs = listing.bike_route_coords.map(coord => [coord[1], coord[0]]);
            currentRoute = L.polyline(latLngs, { color: '#3498db', weight: 4, opacity: 0.8, dashArray: '10, 5' }).addTo(map);
            map.fitBounds(currentRoute.getBounds().pad(0.1));
        }

        function updateMap(filteredListings) {
            markers.forEach(m => map.removeLayer(m));
            markers = [];
            clearRoute();

            filteredListings.forEach(listing => {
                if (listing.latitude && listing.longitude) {
                    const bikeInfo = listing.commute_time_bike_min ? `🚴 ${listing.commute_time_bike_min} min` : '';
                    const transitTransfers = listing.transit_transfers !== null && listing.transit_transfers !== undefined ? ` (${listing.transit_transfers}x)` : '';
                    const transitInfo = listing.commute_time_transit_min ? `🚇 ${listing.commute_time_transit_min} min${transitTransfers}` : '';
                    const carInfo = listing.commute_time_driving_min ? `🚗 ${listing.commute_time_driving_min} min` : '';
                    const commuteInfo = [bikeInfo, transitInfo, carInfo].filter(x => x).join(' | ');
                    const hasRoute = listing.bike_route_coords && listing.bike_route_coords.length > 0;
                    const neighborhoodInfo = listing.neighborhood_name ? `<span style="color:#666;">📍 ${listing.neighborhood_name} (${listing.neighborhood_overall}/10)</span><br>` : '';

                    const popupContent = `
                        <div style="min-width:200px;">
                            <b>${listing.title || listing.address || 'Listing'}</b><br>
                            <b style="color:${getPriceColor(listing.price_eur)}">EUR ${listing.price_eur || '?'}/month</b><br>
                            ${listing.surface_m2 ? listing.surface_m2 + ' m²' : ''} | ${listing.rooms || '?'} rooms<br>
                            ${neighborhoodInfo}
                            ${commuteInfo ? `<span style="color:#666;">${commuteInfo}</span><br>` : ''}
                            ${hasRoute ? `<button onclick="showRoute(listings.find(l => l.listing_url === '${listing.listing_url.replace(/'/g, "\\'")}'))" style="margin-top:5px;padding:3px 8px;background:#3498db;color:white;border:none;border-radius:3px;cursor:pointer;">Show bike route</button><br>` : ''}
                            <a href="${listing.listing_url}" target="_blank" style="color:#3498db;">View listing</a>
                        </div>
                    `;

                    const marker = L.marker([listing.latitude, listing.longitude], { icon: createPriceMarker(listing.price_eur) }).bindPopup(popupContent);
                    marker.addTo(map);
                    markers.push(marker);
                }
            });
        }

        function renderCards(data) {
            const grid = document.getElementById('cardsGrid');
            grid.innerHTML = '';

            if (data.length === 0) {
                document.getElementById('noResults').style.display = 'block';
                grid.classList.remove('visible');
                return;
            }

            document.getElementById('noResults').style.display = 'none';
            if (currentView === 'cards') grid.classList.add('visible');

            data.forEach(listing => {
                const card = document.createElement('div');
                card.className = 'listing-card';

                const priceClass = getPriceClass(listing.price_eur);
                const scoreClass = getScoreClass(listing.neighborhood_overall);

                // Build tags
                let tagsHtml = '';
                if (listing.furnished) {
                    const tagClass = listing.furnished.toLowerCase() === 'furnished' ? 'tag-furnished' : listing.furnished.toLowerCase() === 'upholstered' ? 'tag-upholstered' : 'tag-unfurnished';
                    tagsHtml += `<span class="tag ${tagClass}">${listing.furnished}</span>`;
                }
                if (listing.available_date) {
                    tagsHtml += `<span class="tag" style="background:#e8f4fd;color:#2980b9;">${listing.available_date}</span>`;
                }

                // Commute section
                let commuteHtml = '';
                if (listing.commute_time_bike_min || listing.commute_time_transit_min || listing.commute_time_driving_min || listing.distance_km) {
                    commuteHtml = '<div class="card-commute">';
                    if (listing.commute_time_bike_min) commuteHtml += `<div class="card-commute-item">🚴 <span>${listing.commute_time_bike_min} min</span></div>`;
                    if (listing.commute_time_transit_min) {
                        const transfers = listing.transit_transfers !== null && listing.transit_transfers !== undefined ? ` (${listing.transit_transfers}x)` : '';
                        commuteHtml += `<div class="card-commute-item">🚇 <span>${listing.commute_time_transit_min} min${transfers}</span></div>`;
                    }
                    if (listing.commute_time_driving_min) commuteHtml += `<div class="card-commute-item">🚗 <span>${listing.commute_time_driving_min} min</span></div>`;
                    if (listing.distance_km) commuteHtml += `<div class="card-commute-item">📍 <span>${listing.distance_km.toFixed(1)} km</span></div>`;
                    commuteHtml += '</div>';
                }

                // Neighborhood section
                let neighborhoodHtml = '';
                if (listing.neighborhood_overall && listing.neighborhood_name) {
                    neighborhoodHtml = `
                        <div class="card-neighborhood">
                            <span class="card-neighborhood-score ${scoreClass}">${listing.neighborhood_overall}/10</span>
                            <span class="card-neighborhood-name">${listing.neighborhood_name}</span>
                        </div>
                    `;
                }

                card.innerHTML = `
                    <div class="card-header">
                        <div class="card-price ${priceClass}">EUR ${listing.price_eur || '?'}/mo</div>
                        <div class="card-address">${listing.address || listing.title || 'Unknown location'}</div>
                    </div>
                    <div class="card-body">
                        <div class="card-specs">
                            <div class="card-spec">
                                <div class="card-spec-value">${listing.surface_m2 || '?'}</div>
                                <div class="card-spec-label">m²</div>
                            </div>
                            <div class="card-spec">
                                <div class="card-spec-value">${listing.rooms || '?'}</div>
                                <div class="card-spec-label">Rooms</div>
                            </div>
                            <div class="card-spec">
                                <div class="card-spec-value">${listing.bedrooms || '?'}</div>
                                <div class="card-spec-label">Beds</div>
                            </div>
                        </div>
                        ${commuteHtml}
                        ${neighborhoodHtml}
                        ${tagsHtml ? `<div class="card-tags">${tagsHtml}</div>` : ''}
                        ${listing.description_summary ? `<div class="card-summary">${listing.description_summary}</div>` : ''}
                    </div>
                    <div class="card-footer">
                        <span class="card-source">${listing.source_site || 'Unknown'}</span>
                        <a href="${listing.listing_url}" target="_blank" class="card-link">View Listing</a>
                    </div>
                `;
                grid.appendChild(card);
            });
        }

        function renderTable(data) {
            const tbody = document.getElementById('tableBody');
            tbody.innerHTML = '';

            if (data.length === 0) {
                document.getElementById('noResults').style.display = 'block';
                document.getElementById('listingsTable').classList.remove('visible');
                return;
            }

            document.getElementById('noResults').style.display = 'none';
            if (currentView === 'table') document.getElementById('listingsTable').classList.add('visible');

            data.forEach(listing => {
                const row = document.createElement('tr');
                const priceClass = getPriceClass(listing.price_eur);

                let neighborhoodHtml = '-';
                if (listing.neighborhood_overall) {
                    const scoreClass = getScoreClass(listing.neighborhood_overall);
                    neighborhoodHtml = `
                        <div class="neighborhood-tooltip">
                            <span class="neighborhood-score ${scoreClass}">${listing.neighborhood_overall}</span>
                            <span class="neighborhood-name">${listing.neighborhood_name || ''}</span>
                            <div class="tooltip-content">
                                <div class="tooltip-row"><span class="tooltip-label">Safety:</span><span class="tooltip-value">${listing.neighborhood_safety || '-'}/10</span></div>
                                <div class="tooltip-row"><span class="tooltip-label">Green space:</span><span class="tooltip-value">${listing.neighborhood_green_space || '-'}/10</span></div>
                                <div class="tooltip-row"><span class="tooltip-label">Amenities:</span><span class="tooltip-value">${listing.neighborhood_amenities || '-'}/10</span></div>
                                <div class="tooltip-row"><span class="tooltip-label">Restaurants:</span><span class="tooltip-value">${listing.neighborhood_restaurants || '-'}/10</span></div>
                                <div class="tooltip-row"><span class="tooltip-label">Family:</span><span class="tooltip-value">${listing.neighborhood_family_friendly || '-'}/10</span></div>
                                <div class="tooltip-row"><span class="tooltip-label">Expat:</span><span class="tooltip-value">${listing.neighborhood_expat_friendly || '-'}/10</span></div>
                            </div>
                        </div>
                    `;
                }

                const tagClass = listing.furnished ? (listing.furnished.toLowerCase() === 'furnished' ? 'tag-furnished' : listing.furnished.toLowerCase() === 'upholstered' ? 'tag-upholstered' : 'tag-unfurnished') : '';

                row.innerHTML = `
                    <td>${listing.source_site || '-'}</td>
                    <td class="price ${priceClass}">EUR ${listing.price_eur || '?'}</td>
                    <td>${listing.address || listing.title || '-'}</td>
                    <td>${listing.surface_m2 ? listing.surface_m2 + ' m²' : '-'}</td>
                    <td>${listing.rooms || '-'}</td>
                    <td>${listing.furnished ? `<span class="tag ${tagClass}">${listing.furnished}</span>` : '-'}</td>
                    <td>${listing.available_date || '-'}</td>
                    <td>${listing.distance_km ? listing.distance_km.toFixed(1) + ' km' : '-'}</td>
                    <td>${listing.commute_time_bike_min ? listing.commute_time_bike_min + ' min' : '-'}</td>
                    <td>${listing.commute_time_transit_min ? listing.commute_time_transit_min + ' min' + (listing.transit_transfers !== null && listing.transit_transfers !== undefined ? ' (' + listing.transit_transfers + 'x)' : '') : '-'}</td>
                    <td>${listing.commute_time_driving_min ? listing.commute_time_driving_min + ' min' : '-'}</td>
                    <td>${neighborhoodHtml}</td>
                    <td class="summary">${listing.description_summary || '-'}</td>
                    <td><a href="${listing.listing_url}" target="_blank" class="url-link">View</a></td>
                `;
                tbody.appendChild(row);
            });
        }

        function updateStats(data) {
            document.getElementById('statCount').textContent = data.length;
            const prices = data.filter(l => l.price_eur).map(l => l.price_eur);
            const avgPrice = prices.length ? Math.round(prices.reduce((a,b) => a+b, 0) / prices.length) : '-';
            document.getElementById('statAvgPrice').textContent = avgPrice !== '-' ? 'EUR ' + avgPrice : '-';
            const sizes = data.filter(l => l.surface_m2).map(l => l.surface_m2);
            const avgSize = sizes.length ? Math.round(sizes.reduce((a,b) => a+b, 0) / sizes.length) : '-';
            document.getElementById('statAvgSize').textContent = avgSize !== '-' ? avgSize + ' m²' : '-';
        }

        function getFilteredListings() {
            const minPrice = parseInt(priceSliderMin.value) || 0;
            const maxPrice = parseInt(priceSliderMax.value) || 99999;
            const minRooms = parseInt(document.getElementById('minRooms').value) || 0;
            const maxDistance = parseFloat(document.getElementById('maxDistance').value) || 99999;
            const maxBikeTime = parseInt(document.getElementById('maxBikeTime').value) || 99999;
            const maxTransitTime = parseInt(document.getElementById('maxTransitTime').value) || 99999;
            const furnished = document.getElementById('furnished').value;
            const source = document.getElementById('source').value;
            const minNeighborhoodScore = parseFloat(document.getElementById('minNeighborhoodScore').value) || 0;

            return listings.filter(l => {
                if (l.price_eur && (l.price_eur < minPrice || l.price_eur > maxPrice)) return false;
                if (l.rooms && l.rooms < minRooms) return false;
                if (l.distance_km && l.distance_km > maxDistance) return false;
                if (l.commute_time_bike_min && l.commute_time_bike_min > maxBikeTime) return false;
                if (l.commute_time_transit_min && l.commute_time_transit_min > maxTransitTime) return false;
                if (furnished && l.furnished !== furnished) return false;
                if (source && l.source_site !== source) return false;
                if (minNeighborhoodScore > 0 && (!l.neighborhood_overall || l.neighborhood_overall < minNeighborhoodScore)) return false;
                return true;
            });
        }

        function sortListings(data) {
            return [...data].sort((a, b) => {
                let aVal = a[currentSort.column];
                let bVal = b[currentSort.column];
                if (aVal === null || aVal === undefined) return 1;
                if (bVal === null || bVal === undefined) return -1;
                if (typeof aVal === 'string') aVal = aVal.toLowerCase();
                if (typeof bVal === 'string') bVal = bVal.toLowerCase();
                if (currentSort.direction === 'asc') {
                    return aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
                } else {
                    return aVal < bVal ? 1 : aVal > bVal ? -1 : 0;
                }
            });
        }

        function applyFilters() {
            const filtered = getFilteredListings();
            const sorted = sortListings(filtered);
            renderCards(sorted);
            renderTable(sorted);
            updateStats(sorted);
            if (map) updateMap(sorted);
        }

        function resetFilters() {
            priceSliderMin.value = '1000';
            priceSliderMax.value = '2000';
            updatePriceSlider();
            document.getElementById('minRooms').value = '';
            document.getElementById('maxDistance').value = '';
            document.getElementById('maxBikeTime').value = '';
            document.getElementById('maxTransitTime').value = '';
            document.getElementById('furnished').value = '';
            document.getElementById('source').value = '';
            document.getElementById('minNeighborhoodScore').value = '';
            applyFilters();
        }

        function showView(view) {
            currentView = view;
            document.getElementById('btnCards').classList.toggle('active', view === 'cards');
            document.getElementById('btnTable').classList.toggle('active', view === 'table');
            document.getElementById('btnMap').classList.toggle('active', view === 'map');
            document.getElementById('map').classList.toggle('visible', view === 'map');
            document.getElementById('cardsGrid').classList.toggle('visible', view === 'cards');
            document.getElementById('listingsTable').classList.toggle('visible', view === 'table');
            document.getElementById('noResults').style.display = 'none';

            if (view === 'map' && !map) {
                initMap();
                const filtered = getFilteredListings();
                updateMap(filtered);
            }
        }

        // Sorting (table only)
        document.querySelectorAll('th[data-sort]').forEach(th => {
            th.addEventListener('click', () => {
                const column = th.dataset.sort;
                if (currentSort.column === column) {
                    currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
                } else {
                    currentSort.column = column;
                    currentSort.direction = 'asc';
                }
                document.querySelectorAll('th').forEach(t => t.classList.remove('sorted-asc', 'sorted-desc'));
                th.classList.add(`sorted-${currentSort.direction}`);
                applyFilters();
            });
        });

        // Initial render
        applyFilters();
    </script>
</body>
</html>
"""


def export_to_html(
    listings: list[dict | RentalListing],
    output_dir: Path,
    filename: str = None,
    city: str = None,
) -> Path:
    """Generate interactive HTML report.

    Args:
        listings: List of listing dicts or RentalListing objects
        output_dir: Output directory path
        filename: Output filename (default: {city}_rentals.html)
        city: City name for city-specific settings (default: amsterdam)
    """
    import json

    # Get city configuration
    city_config = get_city_config(city) if city else get_city_config(DEFAULT_CITY)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = filename or HTML_FILENAME
    filepath = output_dir / filename

    console.print(f"[cyan]Generating HTML report for {len(listings)} listings...[/]")

    # Convert listings to dicts
    listings_data = []
    for listing in listings:
        if isinstance(listing, RentalListing):
            data = listing.model_dump()
        else:
            data = listing
        # Convert datetime to string for JSON
        if "scraped_at" in data and data["scraped_at"]:
            data["scraped_at"] = str(data["scraped_at"])
        listings_data.append(data)

    # Get unique sources
    sources = sorted(set(l.get("source_site", "") for l in listings_data if l.get("source_site")))

    # Render template with city-specific values
    template = Template(HTML_TEMPLATE)
    html_content = template.render(
        listings=listings_data,
        listings_json=json.dumps(listings_data),
        sources=sources,
        work_lat=city_config.work_lat,
        work_lng=city_config.work_lng,
        work_address=city_config.work_address,
        city_name=city_config.name,
    )

    filepath.write_text(html_content, encoding="utf-8")
    console.print(f"[green]HTML report saved: {filepath}[/]")

    return filepath
