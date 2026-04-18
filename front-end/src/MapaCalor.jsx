import { useEffect, useRef } from "react";
import L from "leaflet";

const INTENSIDAD = { alta: 1.0, media: 0.6, baja: 0.3 };

export function MapaCalor({ reportes, rutas, mostrarZonas, setMapaInstancia }) {
    const mapRef = useRef(null);
    const heatLayer = useRef(null);
    const geojsonLayer = useRef(null);
    const routesLayer = useRef(L.layerGroup());

    useEffect(() => {
        if (!mapRef.current) {
            mapRef.current = L.map("mapa").setView([20.5888, -100.3899], 13);
            L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(mapRef.current);
            routesLayer.current.addTo(mapRef.current);
            setMapaInstancia(mapRef.current);
        }

        // 1. Calor (Fase 2)
        const pts = reportes.map(r => [r.lat, r.lon, INTENSIDAD[r.prioridad] || 0.5]);
        if (heatLayer.current) mapRef.current.removeLayer(heatLayer.current);
        if (window.L.heatLayer) heatLayer.current = L.heatLayer(pts, { radius: 25, blur: 20 }).addTo(mapRef.current);

        // 2. GeoJSON de Zonas (Punto 6)
        if (geojsonLayer.current) mapRef.current.removeLayer(geojsonLayer.current);
        if (mostrarZonas) {
            fetch("/zonas_qro.geojson")
                .then(r => r.json())
                .then(data => {
                    geojsonLayer.current = L.geoJSON(data, {
                        style: (f) => ({
                            fillColor: f.properties.zona_tipo === 'hospital' ? '#d90429' : f.properties.zona_tipo === 'escuela' ? '#ff9200' : '#ffd60a',
                            fillOpacity: 0.2, weight: 1, color: 'white'
                        })
                    }).addTo(mapRef.current);
                }).catch(() => {
                    // Backup en caso de que no esté el archivo aún
                    L.rectangle([[20.58, -100.40], [20.59, -100.39]], { color: "#d90429", weight: 1, fillOpacity: 0.1 }).addTo(mapRef.current);
                });
        }

        // 3. Rutas (Punto 5)
        routesLayer.current.clearLayers();
        rutas.forEach(ruta => {
            L.polyline(ruta.puntos, { color: '#007bff', weight: 4, dashArray: '5, 10' })
                .addTo(routesLayer.current);
        });

    }, [reportes, rutas, mostrarZonas]);

    return <div id="mapa" style={{ height: "100%", width: "100%" }} />;
}