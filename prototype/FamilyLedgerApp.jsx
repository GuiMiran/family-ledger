import { useState } from "react";
import demo from "./demo-data.json";

// Deliberately isolated visual demo: no API, account, token, real prices or writes.
export default function FamilyLedgerApp() {
  const [screen, setScreen] = useState("receipt");
  const money = (value) => new Intl.NumberFormat("es-ES", {
    style: "currency", currency: demo.currency,
  }).format(value);
  const total = demo.lines.reduce((sum, line) => sum + line.amount, 0);
  return (
    <main style={{ maxWidth: 480, margin: "32px auto", padding: 24,
      fontFamily: "system-ui, sans-serif", color: "#183b32", background: "#f3f7f4",
      borderRadius: 20 }}>
      <p role="note" style={{ background: "#ffe7b2", padding: 12, fontWeight: 700 }}>
        {demo.kind}
      </p>
      <h1>Family Ledger</h1>
      <p>{demo.family_label}</p>
      <p>Datos inventados. Este prototipo no carga perfiles ni guarda compras.</p>
      <nav aria-label="Pantallas de demostración" style={{ display: "flex", gap: 12 }}>
        <button onClick={() => setScreen("receipt")} aria-pressed={screen === "receipt"}>Ticket ficticio</button>
        <button onClick={() => setScreen("pantry")} aria-pressed={screen === "pantry"}>Despensa ficticia</button>
      </nav>
      {screen === "receipt" ? (
        <section>
          <h2>{demo.receipt_label}</h2>
          <p>{demo.store_label} · sin fecha ni identificador real</p>
          <ul>{demo.lines.map((line) => <li key={line.id} style={{ margin: "16px 0" }}>
            {line.description} · {line.quantity} · <strong>{money(line.amount)}</strong>
          </li>)}</ul>
          <p>Total ficticio: <strong>{money(total)}</strong></p>
          <p>No confirma persistencia, impuestos ni existencias reales.</p>
        </section>
      ) : (
        <section>
          <h2>Despensa de ejemplo</h2>
          <ul>{demo.pantry.map((item) => <li key={item.id} style={{ margin: "16px 0" }}>
            {item.description} · {item.quantity} · {item.location}
          </li>)}</ul>
          <p>La disponibilidad mostrada es inventada y no procede de una compra.</p>
        </section>
      )}
      <footer style={{ borderTop: "1px solid #c8d8ce", marginTop: 24, paddingTop: 12 }}>
        Para usar la aplicación privada, cada familia debe configurar su propio perfil.
      </footer>
    </main>
  );
}
