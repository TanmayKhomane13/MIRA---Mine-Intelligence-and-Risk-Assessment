document.addEventListener('DOMContentLoaded', () => {
    const mapContainer = document.getElementById('map');
    if (!mapContainer) return;

    // 1. Initialize Leaflet Map centered (e.g., coordinates or default overview)
    const map = L.map('map').setView([20.5937, 78.9629], 5); // Default center / zoom

    // 2. Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // 3. Fetch GeoJSON from Flask endpoint and render markers
    fetch('/api/v1/gis/mines')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            L.geoJSON(data, {
                pointToLayer: (feature, latlng) => {
                    // Customize marker colors based on risk level
                    let fillColor = '#059669'; // Low (Green)
                    if (feature.properties.risk_level === 'HIGH') {
                        fillColor = '#dc2626'; // High (Red)
                    } else if (feature.properties.risk_level === 'MEDIUM') {
                        fillColor = '#d97706'; // Medium (Amber)
                    }

                    return L.circleMarker(latlng, {
                        radius: 8,
                        fillColor: fillColor,
                        color: '#ffffff',
                        weight: 2,
                        opacity: 1,
                        fillOpacity: 0.9
                    });
                },
                onEachFeature: (feature, layer) => {
                    const props = feature.properties;
                    const popupContent = `
                        <div style="font-family: inherit; font-size: 13px; line-height: 1.4;">
                            <strong>${props.mine_id} - ${props.name}</strong><br>
                            Risk Level: <span style="font-weight: 600;">${props.risk_level}</span> (${props.risk_score})<br>
                            Compliance: ${props.compliance}%<br>
                            <a href="/mines/${props.mine_id}" style="color: black; text-decoration: underline; font-weight: 500; margin-top: 4px; display: inline-block;">View Mine Profile</a>
                        </div>
                    `;
                    layer.bindPopup(popupContent);
                }
            }).addTo(map);
        })
        .catch(error => {
            console.error('Error fetching GIS mine data:', error);
        });
});