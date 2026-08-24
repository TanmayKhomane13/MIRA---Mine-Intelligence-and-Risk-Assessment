document.addEventListener("DOMContentLoaded", () => {

    const mapContainer = document.getElementById("map");

    if (!mapContainer) return;

    const map = L.map("map").setView(
        [20.5937, 78.9629],
        5
    );
    // OpenStreetMap
    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            maxZoom: 19,
            attribution:
                '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }
    ).addTo(map);
    fetch("/api/v1/gis/mines")
        .then(response => {
            if (!response.ok) {
                throw new Error(
                    `HTTP error ${response.status}`
                );
            }
            return response.json();
        })
        .then(data => {
            if (!data.features || data.features.length === 0) {
                console.warn("No mine GIS data available");
                return;
            }

            const mineLayer = L.geoJSON(data, {
                pointToLayer: (feature, latlng) => {

                    const risk =
                        feature.properties.risk_level || "LOW";

                    let fillColor = "#059669";

                    if (risk === "HIGH") {
                        fillColor = "#dc2626";
                    }
                    else if (risk === "MEDIUM") {
                        fillColor = "#d97706";
                    }

                    return L.circleMarker(latlng, {
                        radius: 7,
                        fillColor: fillColor,
                        color: "#ffffff",
                        weight: 2,
                        opacity: 1,
                        fillOpacity: 0.9
                    });
                },
                onEachFeature: (feature, layer) => {
                    const p = feature.properties;
                    const popup = `
                        <div style="
                            font-family: Arial, sans-serif;
                            font-size: 13px;
                            line-height: 1.5;
                            min-width: 220px;
                        ">
                            <strong style="font-size:15px;">
                                ${p.name || "Unknown Mine"}
                            </strong>
                            <hr style="margin:6px 0;">
                            <b>Mine ID:</b>
                            ${p.mine_id || "N/A"}<br>
                            <b>State:</b>
                            ${p.state || "N/A"}<br>
                            <b>District:</b>
                            ${p.district || "N/A"}<br>
                            <b>Company:</b>
                            ${p.company || "N/A"}<br>
                            <b>Mine Type:</b>
                            ${p.mine_type || "N/A"}<br>
                            <b>Status:</b>
                            ${p.status || "N/A"}<br>
                            <b>Risk:</b>
                            <span style="font-weight:600;">
                                ${p.risk_level || "LOW"}
                            </span>
                            <br>
                            <b>Risk Score:</b>
                            ${p.risk_score ?? "N/A"}<br>
                            <b>Compliance:</b>
                            ${p.compliance ?? "N/A"}%
                            <br><br>
                            <a
                                href="/mines/${p.mine_id}"
                                style="
                                    color:#059669;
                                    font-weight:600;
                                    text-decoration:none;
                                "
                            >
                                View Mine Profile →
                            </a>
                        </div>
                    `;
                    layer.bindPopup(popup);
                }
            }).addTo(map);
            // Automatically fit map to mine locations
            map.fitBounds(
                mineLayer.getBounds(),
                {
                    padding: [30, 30]
                }
            );
        })
        .catch(error => {
            console.error(
                "Error loading mine GIS data:",
                error
            );
        });
});
const satellite = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    {
        attribution: "Tiles &copy; Esri"
    }
);

const osm = L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        attribution:
            '&copy; OpenStreetMap contributors'
    }
);

osm.addTo(map);

L.control.layers({
    "Street Map": osm,
    "Satellite": satellite
}).addTo(map);