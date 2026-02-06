"""Generate interactive HTML report with filtering, sorting, and map view."""

from pathlib import Path
from typing import Any

import folium
from jinja2 import Template
from rich.console import Console

from amsterdam_rent_scraper.config.settings import (
    HTML_FILENAME,
    WORK_LAT,
    WORK_LNG,
    WORK_ADDRESS,
)
from amsterdam_rent_scraper.models.listing import RentalListing

console = Console()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Amsterdam Rental Listings</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .container { max-width: 1600px; margin: 0 auto; padding: 20px; }
        header { background: #2c3e50; color: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; }
        header h1 { font-size: 1.8rem; margin-bottom: 5px; }
        header p { opacity: 0.8; }

        .filters { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .filter-row { display: flex; flex-wrap: wrap; gap: 15px; align-items: end; }
        .filter-group { display: flex; flex-direction: column; }
        .filter-group label { font-size: 0.8rem; color: #666; margin-bottom: 4px; }
        .filter-group input, .filter-group select { padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9rem; }
        .filter-group input[type="number"] { width: 100px; }
        button { padding: 8px 16px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.9rem; }
        button:hover { background: #2980b9; }
        .btn-reset { background: #95a5a6; }
        .btn-reset:hover { background: #7f8c8d; }

        .view-toggle { display: flex; gap: 10px; margin-bottom: 20px; }
        .view-toggle button { background: #ecf0f1; color: #2c3e50; }
        .view-toggle button.active { background: #3498db; color: white; }

        #map { height: 600px; border-radius: 8px; margin-bottom: 20px; display: none; position: relative; }
        #map.visible { display: block; }
        .map-legend { position: absolute; bottom: 20px; left: 10px; background: white; padding: 10px 15px; border-radius: 6px; box-shadow: 0 2px 6px rgba(0,0,0,0.2); z-index: 1000; font-size: 0.8rem; }
        .map-legend h4 { margin: 0 0 8px 0; font-size: 0.85rem; }
        .legend-item { display: flex; align-items: center; margin: 4px 0; }
        .legend-dot { width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; border: 2px solid white; box-shadow: 0 1px 2px rgba(0,0,0,0.2); }
        .legend-circle { width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; border: 1px dashed; background: transparent; }

        .stats { background: white; padding: 15px 20px; border-radius: 8px; margin-bottom: 20px; display: flex; gap: 30px; }
        .stat { text-align: center; }
        .stat-value { font-size: 1.5rem; font-weight: bold; color: #2c3e50; }
        .stat-label { font-size: 0.8rem; color: #666; }

        table { width: 100%; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        th { background: #34495e; color: white; padding: 12px 8px; text-align: left; font-size: 0.85rem; cursor: pointer; white-space: nowrap; }
        th:hover { background: #2c3e50; }
        th.sorted-asc::after { content: ' ▲'; }
        th.sorted-desc::after { content: ' ▼'; }
        td { padding: 10px 8px; border-bottom: 1px solid #eee; font-size: 0.85rem; vertical-align: top; }
        tr:hover { background: #f8f9fa; }
        .price { font-weight: bold; }
        .price-low { color: #27ae60; }
        .price-mid { color: #f39c12; }
        .price-high { color: #e74c3c; }
        .url-link { color: #3498db; text-decoration: none; word-break: break-all; }
        .url-link:hover { text-decoration: underline; }
        .summary { max-width: 300px; }
        .pros { color: #27ae60; }
        .cons { color: #e74c3c; }
        .tag { display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 0.75rem; margin-right: 4px; }
        .tag-furnished { background: #d5f5e3; color: #27ae60; }
        .tag-unfurnished { background: #fdebd0; color: #e67e22; }

        .no-results { text-align: center; padding: 40px; color: #666; }

        @media (max-width: 768px) {
            .filter-row { flex-direction: column; }
            .stats { flex-wrap: wrap; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Amsterdam Rental Listings</h1>
            <p>{{ listings|length }} listings scraped from {{ sources|length }} sources | Target: {{ work_address }}</p>
        </header>

        <div class="filters">
            <div class="filter-row">
                <div class="filter-group">
                    <label>Min Price (EUR)</label>
                    <input type="number" id="minPrice" placeholder="1000" value="1000">
                </div>
                <div class="filter-group">
                    <label>Max Price (EUR)</label>
                    <input type="number" id="maxPrice" placeholder="2000" value="2000">
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
                <button onclick="applyFilters()">Apply Filters</button>
                <button class="btn-reset" onclick="resetFilters()">Reset</button>
            </div>
        </div>

        <div class="view-toggle">
            <button id="btnTable" class="active" onclick="showView('table')">Table View</button>
            <button id="btnMap" onclick="showView('map')">Map View</button>
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
                    <th data-sort="commute_time_driving_min">Car</th>
                    <th>Summary</th>
                    <th>Link</th>
                </tr>
            </thead>
            <tbody id="tableBody">
            </tbody>
        </table>
        <div class="no-results" id="noResults" style="display:none;">No listings match your filters.</div>
    </div>

    <script>
        const listings = {{ listings_json|safe }};
        const workLocation = [{{ work_lat }}, {{ work_lng }}];
        let map = null;
        let markers = [];
        let currentRoute = null;  // Store current route polyline
        let currentSort = { column: 'price_eur', direction: 'asc' };

        function initMap() {
            map = L.map('map').setView(workLocation, 12);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap contributors'
            }).addTo(map);

            // Commute distance circles (km to meters)
            L.circle(workLocation, {
                radius: 5000, // 5 km
                color: '#3498db',
                fillColor: '#3498db',
                fillOpacity: 0.05,
                weight: 1,
                dashArray: '5, 5'
            }).addTo(map).bindPopup('5 km from work');

            L.circle(workLocation, {
                radius: 10000, // 10 km
                color: '#9b59b6',
                fillColor: '#9b59b6',
                fillOpacity: 0.03,
                weight: 1,
                dashArray: '5, 5'
            }).addTo(map).bindPopup('10 km from work');

            L.circle(workLocation, {
                radius: 15000, // 15 km
                color: '#95a5a6',
                fillColor: '#95a5a6',
                fillOpacity: 0.02,
                weight: 1,
                dashArray: '5, 5'
            }).addTo(map).bindPopup('15 km from work');

            // Work location marker
            L.marker(workLocation, {
                icon: L.divIcon({
                    className: 'work-marker',
                    html: '<div style="background:#2c3e50;color:white;padding:5px 10px;border-radius:4px;font-weight:bold;box-shadow:0 2px 4px rgba(0,0,0,0.3);">Office</div>',
                    iconSize: [50, 30]
                })
            }).addTo(map).bindPopup('<b>Work Location</b><br>{{ work_address }}');
        }

        function getPriceColor(price) {
            if (!price) return '#95a5a6'; // gray for unknown
            if (price < 1300) return '#27ae60'; // green: affordable
            if (price < 1700) return '#f39c12'; // orange: mid-range
            return '#e74c3c'; // red: expensive
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
            if (!listing.bike_route_coords || listing.bike_route_coords.length === 0) {
                return;
            }
            // OSRM returns [lon, lat], Leaflet needs [lat, lon]
            const latLngs = listing.bike_route_coords.map(coord => [coord[1], coord[0]]);
            currentRoute = L.polyline(latLngs, {
                color: '#3498db',
                weight: 4,
                opacity: 0.8,
                dashArray: '10, 5'
            }).addTo(map);
            // Fit map to show route
            map.fitBounds(currentRoute.getBounds().pad(0.1));
        }

        function updateMap(filteredListings) {
            markers.forEach(m => map.removeLayer(m));
            markers = [];
            clearRoute();

            filteredListings.forEach(listing => {
                if (listing.latitude && listing.longitude) {
                    const bikeInfo = listing.commute_time_bike_min ? `🚴 ${listing.commute_time_bike_min} min` : '';
                    const carInfo = listing.commute_time_driving_min ? `🚗 ${listing.commute_time_driving_min} min` : '';
                    const commuteInfo = [bikeInfo, carInfo].filter(x => x).join(' | ');
                    const hasRoute = listing.bike_route_coords && listing.bike_route_coords.length > 0;

                    const popupContent = `
                        <div style="min-width:200px;">
                            <b>${listing.title || listing.address || 'Listing'}</b><br>
                            <b style="color:${getPriceColor(listing.price_eur)}">EUR ${listing.price_eur || '?'}/month</b><br>
                            ${listing.surface_m2 ? listing.surface_m2 + ' m²' : ''} | ${listing.rooms || '?'} rooms<br>
                            ${commuteInfo ? `<span style="color:#666;">${commuteInfo}</span><br>` : ''}
                            ${hasRoute ? `<button onclick="showRoute(listings.find(l => l.listing_url === '${listing.listing_url}'))" style="margin-top:5px;padding:3px 8px;background:#3498db;color:white;border:none;border-radius:3px;cursor:pointer;">Show bike route</button><br>` : ''}
                            <a href="${listing.listing_url}" target="_blank" style="color:#3498db;">View listing →</a>
                        </div>
                    `;

                    const marker = L.marker([listing.latitude, listing.longitude], {
                        icon: createPriceMarker(listing.price_eur)
                    }).bindPopup(popupContent);
                    marker.addTo(map);
                    markers.push(marker);
                }
            });
        }

        function renderTable(data) {
            const tbody = document.getElementById('tableBody');
            tbody.innerHTML = '';

            if (data.length === 0) {
                document.getElementById('noResults').style.display = 'block';
                document.getElementById('listingsTable').style.display = 'none';
                return;
            }

            document.getElementById('noResults').style.display = 'none';
            document.getElementById('listingsTable').style.display = 'table';

            data.forEach(listing => {
                const row = document.createElement('tr');
                const priceClass = listing.price_eur ? (listing.price_eur < 1300 ? 'price-low' : listing.price_eur < 1700 ? 'price-mid' : 'price-high') : '';
                row.innerHTML = `
                    <td>${listing.source_site || '-'}</td>
                    <td class="price ${priceClass}">EUR ${listing.price_eur || '?'}</td>
                    <td>${listing.address || listing.title || '-'}</td>
                    <td>${listing.surface_m2 ? listing.surface_m2 + ' m2' : '-'}</td>
                    <td>${listing.rooms || '-'}</td>
                    <td>${listing.furnished ? `<span class="tag tag-${listing.furnished.toLowerCase()}">${listing.furnished}</span>` : '-'}</td>
                    <td>${listing.available_date || '-'}</td>
                    <td>${listing.distance_km ? listing.distance_km.toFixed(1) + ' km' : '-'}</td>
                    <td>${listing.commute_time_bike_min ? listing.commute_time_bike_min + ' min' : '-'}</td>
                    <td>${listing.commute_time_driving_min ? listing.commute_time_driving_min + ' min' : '-'}</td>
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
            document.getElementById('statAvgSize').textContent = avgSize !== '-' ? avgSize + ' m2' : '-';
        }

        function getFilteredListings() {
            const minPrice = parseInt(document.getElementById('minPrice').value) || 0;
            const maxPrice = parseInt(document.getElementById('maxPrice').value) || 99999;
            const minRooms = parseInt(document.getElementById('minRooms').value) || 0;
            const maxDistance = parseFloat(document.getElementById('maxDistance').value) || 99999;
            const maxBikeTime = parseInt(document.getElementById('maxBikeTime').value) || 99999;
            const furnished = document.getElementById('furnished').value;
            const source = document.getElementById('source').value;

            return listings.filter(l => {
                if (l.price_eur && (l.price_eur < minPrice || l.price_eur > maxPrice)) return false;
                if (l.rooms && l.rooms < minRooms) return false;
                if (l.distance_km && l.distance_km > maxDistance) return false;
                if (l.commute_time_bike_min && l.commute_time_bike_min > maxBikeTime) return false;
                if (furnished && l.furnished !== furnished) return false;
                if (source && l.source_site !== source) return false;
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
            renderTable(sorted);
            updateStats(sorted);
            if (map) updateMap(sorted);
        }

        function resetFilters() {
            document.getElementById('minPrice').value = '1000';
            document.getElementById('maxPrice').value = '2000';
            document.getElementById('minRooms').value = '';
            document.getElementById('maxDistance').value = '';
            document.getElementById('maxBikeTime').value = '';
            document.getElementById('furnished').value = '';
            document.getElementById('source').value = '';
            applyFilters();
        }

        function showView(view) {
            document.getElementById('btnTable').classList.toggle('active', view === 'table');
            document.getElementById('btnMap').classList.toggle('active', view === 'map');
            document.getElementById('map').classList.toggle('visible', view === 'map');
            document.getElementById('listingsTable').style.display = view === 'table' ? 'table' : 'none';

            if (view === 'map' && !map) {
                initMap();
                const filtered = getFilteredListings();
                updateMap(filtered);
            }
        }

        // Sorting
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
    listings: list[dict | RentalListing], output_dir: Path, filename: str = None
) -> Path:
    """Generate interactive HTML report."""
    import json

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

    # Render template
    template = Template(HTML_TEMPLATE)
    html_content = template.render(
        listings=listings_data,
        listings_json=json.dumps(listings_data),
        sources=sources,
        work_lat=WORK_LAT,
        work_lng=WORK_LNG,
        work_address=WORK_ADDRESS,
    )

    filepath.write_text(html_content, encoding="utf-8")
    console.print(f"[green]HTML report saved: {filepath}[/]")

    return filepath
