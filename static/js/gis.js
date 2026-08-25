document.addEventListener("DOMContentLoaded", () => {

    const mapContainer = document.getElementById("map");

    if (!mapContainer) return;


    // =========================================================
    // MAP INITIALIZATION
    // =========================================================

    const map = L.map("map").setView(
        [20.5937, 78.9629],
        5
    );


    // =========================================================
    // BASE MAPS
    // =========================================================

    const osm = L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            maxZoom: 19,

            attribution:
                '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }
    );


    const satellite = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        {
            maxZoom: 19,

            attribution:
                "Tiles &copy; Esri"
        }
    );


    // Default map

    osm.addTo(map);


    // Layer switcher

    L.control.layers(
        {
            "Street Map": osm,
            "Satellite": satellite
        }
    ).addTo(map);


    // =========================================================
    // LOAD MINE GIS DATA
    // =========================================================

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

            if (
                !data.features ||
                data.features.length === 0
            ) {

                console.warn(
                    "No mine GIS data available"
                );

                return;

            }


            // =================================================
            // GEOJSON MINE LAYER
            // =================================================

            const mineLayer = L.geoJSON(
                data,
                {

                    // -----------------------------------------
                    // MINE MARKER
                    // -----------------------------------------

                    pointToLayer: (
                        feature,
                        latlng
                    ) => {

                        const risk =
                            (
                                feature.properties.risk_level ||
                                "LOW"
                            ).toUpperCase();


                        let fillColor = "#059669";


                        if (risk === "CRITICAL") {

                            fillColor = "#991b1b";

                        }

                        else if (risk === "HIGH") {

                            fillColor = "#dc2626";

                        }

                        else if (risk === "MEDIUM") {

                            fillColor = "#d97706";

                        }

                        else if (risk === "LOW") {

                            fillColor = "#059669";

                        }


                        return L.circleMarker(
                            latlng,
                            {

                                radius: 8,

                                fillColor:
                                    fillColor,

                                color: "#ffffff",

                                weight: 2,

                                opacity: 1,

                                fillOpacity: 0.9

                            }
                        );

                    },


                    // -----------------------------------------
                    // POPUP
                    // -----------------------------------------

                    onEachFeature: (
                        feature,
                        layer
                    ) => {

                        const p =
                            feature.properties;


                        const mineId =
                            p.id || "N/A";


                        const mineName =
                            p.name ||
                            "Unknown Mine";


                        const code =
                            p.code ||
                            "N/A";


                        const operator =
                            p.operator ||
                            "N/A";


                        const state =
                            p.state ||
                            "N/A";


                        const district =
                            p.district ||
                            "N/A";


                        const status =
                            p.status ||
                            "N/A";


                        const method =
                            p.method ||
                            "N/A";


                        const riskLevel =
                            p.risk_level ||
                            "Not Analysed";


                        const riskScore =
                            p.risk_score !== null &&
                            p.risk_score !== undefined
                                ? p.risk_score
                                : "N/A";


                        const region =
                            p.region || {};


                        const regionName =
                            region.name ||
                            "Not assigned";


                        const latitude =
                            feature.geometry &&
                            feature.geometry.coordinates
                                ? feature.geometry.coordinates[1]
                                : null;


                        const longitude =
                            feature.geometry &&
                            feature.geometry.coordinates
                                ? feature.geometry.coordinates[0]
                                : null;


                        // -------------------------------------
                        // RISK COLOR
                        // -------------------------------------

                        let riskColor =
                            "#059669";


                        if (
                            riskLevel ===
                            "CRITICAL"
                        ) {

                            riskColor =
                                "#991b1b";

                        }

                        else if (
                            riskLevel ===
                            "HIGH"
                        ) {

                            riskColor =
                                "#dc2626";

                        }

                        else if (
                            riskLevel ===
                            "MEDIUM"
                        ) {

                            riskColor =
                                "#d97706";

                        }


                        // -------------------------------------
                        // POPUP HTML
                        // -------------------------------------

                        const popup = `

                            <div style="
                                font-family: Arial, sans-serif;
                                font-size: 13px;
                                line-height: 1.5;
                                min-width: 240px;
                            ">

                                <strong style="
                                    font-size: 15px;
                                    color: #111827;
                                ">
                                    ${mineName}
                                </strong>


                                <div style="
                                    color: #6b7280;
                                    font-size: 11px;
                                    margin-top: 2px;
                                ">
                                    ${code}
                                </div>


                                <hr style="
                                    margin: 8px 0;
                                    border: none;
                                    border-top: 1px solid #e5e7eb;
                                ">


                                <b>Operator:</b>
                                ${operator}
                                <br>


                                <b>State:</b>
                                ${state}
                                <br>


                                <b>District:</b>
                                ${district}
                                <br>


                                <b>Status:</b>
                                ${status}
                                <br>


                                <b>Mining Method:</b>
                                ${method}
                                <br>


                                <b>GIS Region:</b>
                                ${regionName}
                                <br>


                                <b>Risk:</b>

                                <span style="
                                    color: ${riskColor};
                                    font-weight: 700;
                                ">
                                    ${riskLevel}
                                </span>

                                <br>


                                <b>Risk Score:</b>
                                ${riskScore}
                                ${
                                    riskScore !== "N/A"
                                        ? " / 100"
                                        : ""
                                }

                                <br>


                                <b>Latitude:</b>
                                ${
                                    latitude !== null
                                        ? latitude
                                        : "N/A"
                                }

                                <br>


                                <b>Longitude:</b>
                                ${
                                    longitude !== null
                                        ? longitude
                                        : "N/A"
                                }


                                <br><br>


                                <a
                                    href="/mines/${mineId}"
                                    style="
                                        display: inline-block;
                                        color: #059669;
                                        font-weight: 600;
                                        text-decoration: none;
                                    "
                                >
                                    View Mine Profile →
                                </a>

                            </div>

                        `;
                        layer.bindPopup(popup);
                    }
                }
            ).addTo(map);

            const bounds =
                mineLayer.getBounds();

            if (bounds.isValid()) {
                map.fitBounds(
                    bounds,
                    {
                        padding: [30, 30]
                    }
                );
            }
        })
        .catch(error => {
            console.error(
                "Error loading mine GIS data:",
                error
            );
        });
});