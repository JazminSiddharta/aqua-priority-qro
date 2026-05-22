import { useState, useEffect } from "react";
import { MapaCalor } from "./MapaCalor";
import "./App.css";

// PUNTO 2: Conexión real a Backend (Polling cada 10s)
export function useReportes() {
  const [data, setData] = useState([]);
  useEffect(() => {
    const fetch_ = () => fetch("http://localhost:8000/reportes/mapa")
      .then(r => r.json()).then(setData).catch(() => { });
    fetch_();
    const id = setInterval(fetch_, 10000);
    return () => clearInterval(id);
  }, []);
  return data;
}

export default function App() {
  const reportes = useReportes();
  const [rutas, setRutas] = useState([]);
  const [medidores, setMedidores] = useState([]);
  const [tab, setTab] = useState("reportes"); // PUNTO 7: Tabs
  const [verZonas, setVerZonas] = useState(true); // PUNTO 6: Toggle
  const [mapa, setMapa] = useState(null);

  // Cargar datos adicionales desde Mongo/API
  useEffect(() => {
    fetch("http://localhost:8000/rutas").then(r => r.json()).then(setRutas).catch(() => { });
    fetch("http://localhost:8000/medidores").then(r => r.json()).then(setMedidores).catch(() => { });
  }, []);

  // PUNTO 4: Ordenar prioridad alta primero
  const ordenPrioridad = { alta: 3, media: 2, baja: 1 };
  const reportesOrdenados = [...reportes].sort((a, b) =>
    ordenPrioridad[b.prioridad] - ordenPrioridad[a.prioridad]
  );

  return (
    <div className="dashboard-container">

      {/* IZQUIERDA: MAPA (70%) */}
      <div className="map-section">
        <MapaCalor
          reportes={reportes}
          rutas={rutas}
          mostrarZonas={verZonas}
          setMapaInstancia={setMapa}
        />

        {/* Toggle del Punto 6 */}
        <div className="zona-toggle">
          <label style={{ cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={verZonas}
              onChange={() => setVerZonas(!verZonas)}
            /> Ver Zonas Críticas
          </label>
        </div>
      </div>

      {/* DERECHA: PANEL (30%) */}
      <div className="panel-section">
        <div className="panel-header">
          <h2>AQUA PRIORITY</h2>
        </div>

        {/* Tabs del Punto 7 */}
        <div className="tabs-container">
          <button
            className={`tab-btn ${tab === 'reportes' ? 'active' : ''}`}
            onClick={() => setTab("reportes")}
          >
            REPORTES
          </button>
          <button
            className={`tab-btn ${tab === 'medidores' ? 'active' : ''}`}
            onClick={() => setTab("medidores")}
          >
            MEDIDORES
          </button>
        </div>

        <div className="tab-content">
          {tab === "reportes" ? (
            <table className="custom-table">
              <thead>
                <tr><th>Ubicación</th><th>Prioridad</th></tr>
              </thead>
              <tbody>
                {reportesOrdenados.map((r, i) => (
                  <tr
                    key={i}
                    onClick={() => mapa && mapa.setView([r.lat, r.lon], 16)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>
                      <strong>{r.ubicacion_texto || r.zona || 'Zona Central'}</strong><br />
                      <small style={{ color: '#888' }}>{r.zona ? `${r.zona} · ${r.tipo}` : r.tipo}</small>
                    </td>
                    <td>
                      <span className={`badge badge-${r.prioridad}`}>
                        {r.prioridad.toUpperCase()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <table className="custom-table">
              <thead>
                <tr><th>ID Medidor</th><th>Estado</th></tr>
              </thead>
              <tbody>
                {medidores.map((m, i) => (
                  <tr key={i} className={m.requiere_revision ? "row-falla" : ""}>
                    <td>
                      <strong>{m.id}</strong><br />
                      <small>{m.zona}</small>
                    </td>
                    <td>
                      <span className="status-label">{m.estado}</span>
                      {m.requiere_revision && <div style={{ color: 'red', fontSize: '10px', marginTop: '4px' }}>Requiere Atención</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}