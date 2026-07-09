import React, { useState } from "react";
import {
  House, ScanLine, Archive, ChefHat, PiggyBank, ChevronRight,
  Snowflake, TriangleAlert, Check, X, Camera, Sparkles, TrendingDown,
  TrendingUp, Clock, Leaf, Receipt, Flame
} from "lucide-react";

/* ─────────────────────────  Design tokens  ───────────────────────── */
const T = {
  font: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif",
  bg: "#F6F6F8",
  card: "#FFFFFF",
  ink: "#1D1D1F",
  sub: "#86868B",
  hair: "#ECECEE",
  green: "#2F8460",
  greenBg: "#EAF5EF",
  amber: "#C07A1B",
  amberBg: "#FBF2E1",
  red: "#C4513F",
  redBg: "#FAECE9",
  blue: "#3670C9",
  blueBg: "#EBF1FB",
};

const eur = (n) =>
  n.toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €";

/* ─────────────────────────  Datos (ticket Makro real 04/07/2026)  ───────────────────────── */
const spendHistory = [
  { m: "Feb", v: 612 }, { m: "Mar", v: 587 }, { m: "Abr", v: 641 },
  { m: "May", v: 598 }, { m: "Jun", v: 634 }, { m: "Jul", v: 212 },
];

const ticketLines = [
  { d: "Huevos M (10 doc.)", q: "120 ud", p: 26.92, vat: 4, ok: true },
  { d: "Barra sandwich", q: "2,870 kg", p: 11.74, vat: 10, ok: true, kg: 4.09 },
  { d: "Ensaladilla 2,5 kg", q: "1 ud", p: 2.75, vat: 4, ok: true },
  { d: "Jamón cocido", q: "2,920 kg", p: 19.42, vat: 10, ok: true, kg: 6.65, exp: "27/01/2027" },
  { d: "Callos vacuno", q: "0,940 kg", p: 6.35, vat: 10, ok: true, kg: 6.75 },
  { d: "Pechuga de pollo", q: "2,370 kg", p: 12.77, vat: 10, ok: true, kg: 5.39 },
  { d: "Pechuga de pollo", q: "2,188 kg", p: 11.79, vat: 10, ok: true, kg: 5.39 },
  { d: "Pechuga de pollo", q: "2,308 kg", p: 12.44, vat: 10, ok: true, kg: 5.39 },
  { d: "Picada mixta", q: "1,592 kg", p: 11.61, vat: 10, ok: true, kg: 7.29, promo: true },
  { d: "Picada mixta", q: "1,615 kg", p: 11.77, vat: 10, ok: true, kg: 7.29, promo: true },
  { d: "Burger mixta 16u", q: "1,790 kg", p: 16.02, vat: 10, ok: true, kg: 8.95 },
  { d: "Burger mixta 16u", q: "1,803 kg", p: 16.14, vat: 10, ok: true, kg: 8.95 },
  { d: "Aceite girasol 5 L", q: "1 ud", p: 9.69, vat: 10, ok: true },
  { d: "Macarrones 5 kg", q: "1 ud", p: 5.39, vat: 10, ok: true },
  { d: "Espaguetis 5 kg", q: "1 ud", p: 5.39, vat: 10, ok: true },
  { d: "Arroz largo 5 kg ×2", q: "10 kg", p: 12.10, vat: 4, ok: true },
  { d: "Ketchup Heinz 875 ml", q: "1 ud", p: 3.89, vat: 10, ok: true },
];

const pantry = [
  { d: "Barra sandwich", q: "2,9 kg", where: "Despensa", days: 1, val: 11.74 },
  { d: "Ensaladilla", q: "2,5 kg", where: "Nevera", days: 2, val: 2.75 },
  { d: "Pechuga de pollo", q: "2,9 kg", where: "Nevera", days: 3, val: 15.5 },
  { d: "Picada mixta", q: "1,6 kg", where: "Nevera", days: 3, val: 11.61 },
  { d: "Jamón cocido", q: "2,9 kg", where: "Nevera", days: 197, val: 19.42 },
  { d: "Huevos", q: "120 ud", where: "Despensa", days: 24, val: 26.92 },
  { d: "Arroz largo", q: "10 kg", where: "Despensa", days: 540, val: 12.1 },
  { d: "Pasta (mac. + esp.)", q: "10 kg", where: "Despensa", days: 540, val: 10.78 },
  { d: "Aceite girasol", q: "5 L", where: "Despensa", days: 365, val: 9.69 },
];

const freezer = [
  { d: "Pechuga de pollo", q: "4,0 kg", frozen: "04/07", until: "04/01/27", val: 21.5 },
  { d: "Burger mixta", q: "3,6 kg", frozen: "04/07", until: "04/10/26", val: 32.16 },
  { d: "Picada mixta", q: "1,6 kg", frozen: "04/07", until: "04/09/26", val: 11.77 },
  { d: "Callos vacuno", q: "0,9 kg", frozen: "04/07", until: "04/12/26", val: 6.35 },
];

const menus = [
  {
    day: "Hoy · cena", title: "Pechuga a la plancha con ensaladilla",
    why: "Usa 1,2 kg de pechuga y la ensaladilla que caduca el domingo",
    urgent: true, feeds: 5, status: "suggested",
  },
  {
    day: "Mañana · comida", title: "Arroz con pollo al horno",
    why: "Termina la pechuga fresca antes del martes · el arroz ya está en despensa",
    urgent: true, feeds: 5, status: "suggested",
  },
  {
    day: "Mañana · cena", title: "Sandwiches calientes de jamón",
    why: "La barra sandwich caduca mañana · jamón cocido abierto",
    urgent: true, feeds: 5, status: "suggested",
  },
  {
    day: "Domingo · comida", title: "Macarrones con picada",
    why: "Picada fresca de la nevera · pasta de despensa, cero compra extra",
    urgent: false, feeds: 5, status: "accepted",
  },
];

/* ─────────────────────────  Piezas UI  ───────────────────────── */
const Card = ({ children, style, onClick }) => (
  <div
    onClick={onClick}
    style={{
      background: T.card, borderRadius: 18, padding: 16,
      boxShadow: "0 1px 2px rgba(0,0,0,0.04)", ...style,
    }}
  >
    {children}
  </div>
);

const Pill = ({ color, bg, children }) => (
  <span style={{
    fontSize: 11, fontWeight: 600, color, background: bg,
    padding: "3px 8px", borderRadius: 99, whiteSpace: "nowrap",
  }}>{children}</span>
);

const SectionTitle = ({ children, action }) => (
  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", margin: "20px 4px 10px" }}>
    <span style={{ fontSize: 20, fontWeight: 700, letterSpacing: -0.4 }}>{children}</span>
    {action && <span style={{ fontSize: 13, color: T.green, fontWeight: 600 }}>{action}</span>}
  </div>
);

/* ─────────────────────────  Pantalla: Inicio  ───────────────────────── */
function Home({ go }) {
  const max = Math.max(...spendHistory.map((s) => s.v));
  return (
    <>
      <div style={{ padding: "8px 4px 0" }}>
        <div style={{ fontSize: 13, color: T.sub, fontWeight: 500 }}>Sábado, 4 de julio</div>
        <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: -0.6 }}>Hola, Guido</div>
      </div>

      {/* Alerta firma: riesgo de desperdicio del ticket de hoy */}
      <Card style={{ marginTop: 14, background: T.amberBg, border: `1px solid #F3E2C2` }}>
        <div style={{ display: "flex", gap: 12 }}>
          <div style={{
            width: 38, height: 38, borderRadius: 12, background: "#FFFFFF",
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}>
            <Snowflake size={20} color={T.amber} />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15 }}>6,9 kg de carne fresca hoy</div>
            <div style={{ fontSize: 13, color: "#8A6A2E", marginTop: 2, lineHeight: 1.4 }}>
              Para 5 personas es más de lo que consumiréis en 3 días.
              Congela <b>4 kg de pollo y las burgers</b> hoy mismo.
            </div>
            <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
              <button onClick={() => go("pantry")} style={{
                border: "none", background: T.ink, color: "#fff", fontWeight: 600,
                fontSize: 13, padding: "8px 14px", borderRadius: 99, fontFamily: T.font,
              }}>Congelar ahora</button>
              <button style={{
                border: "none", background: "transparent", color: "#8A6A2E",
                fontWeight: 600, fontSize: 13, fontFamily: T.font,
              }}>Más tarde</button>
            </div>
          </div>
        </div>
      </Card>

      {/* Gasto del mes */}
      <SectionTitle action="Ver detalle">Julio</SectionTitle>
      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <div>
            <div style={{ fontSize: 13, color: T.sub }}>Gasto en comida</div>
            <div style={{ fontSize: 34, fontWeight: 800, letterSpacing: -1 }}>211,87 €</div>
            <div style={{ fontSize: 12, color: T.sub, marginTop: 2 }}>
              1 compra · 42,37 € por persona
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 6, height: 64 }}>
            {spendHistory.map((s, i) => (
              <div key={s.m} style={{ textAlign: "center" }}>
                <div style={{
                  width: 18, borderRadius: 6,
                  height: Math.max(8, (s.v / max) * 56),
                  background: i === spendHistory.length - 1 ? T.green : "#E3E3E7",
                }} />
                <div style={{ fontSize: 9, color: T.sub, marginTop: 4 }}>{s.m}</div>
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 10 }}>
        <Card>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <Leaf size={14} color={T.green} />
            <span style={{ fontSize: 12, color: T.sub, fontWeight: 600 }}>Ahorro 2026</span>
          </div>
          <div style={{ fontSize: 22, fontWeight: 800, color: T.green, marginTop: 4 }}>342,18 €</div>
        </Card>
        <Card>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <Archive size={14} color={T.blue} />
            <span style={{ fontSize: 12, color: T.sub, fontWeight: 600 }}>Valor en casa</span>
          </div>
          <div style={{ fontSize: 22, fontWeight: 800, marginTop: 4 }}>192,64 €</div>
        </Card>
        <Card>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <Flame size={14} color={T.red} />
            <span style={{ fontSize: 12, color: T.sub, fontWeight: 600 }}>Desperdicio jul.</span>
          </div>
          <div style={{ fontSize: 22, fontWeight: 800, marginTop: 4 }}>0,00 €</div>
        </Card>
        <Card>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <Clock size={14} color={T.amber} />
            <span style={{ fontSize: 12, color: T.sub, fontWeight: 600 }}>Caducan pronto</span>
          </div>
          <div style={{ fontSize: 22, fontWeight: 800, marginTop: 4 }}>4 <span style={{ fontSize: 13, fontWeight: 600, color: T.sub }}>items</span></div>
        </Card>
      </div>

      {/* Menú de hoy */}
      <SectionTitle action="Ver semana">Esta noche</SectionTitle>
      <Card onClick={() => go("menus")} style={{ cursor: "pointer" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ display: "flex", gap: 6, marginBottom: 6 }}>
              <Pill color={T.amber} bg={T.amberBg}>Evita desperdicio</Pill>
            </div>
            <div style={{ fontWeight: 700, fontSize: 16 }}>Pechuga a la plancha con ensaladilla</div>
            <div style={{ fontSize: 12.5, color: T.sub, marginTop: 3 }}>
              Usa la ensaladilla que caduca el domingo · 5 raciones
            </div>
          </div>
          <ChevronRight size={18} color={T.sub} />
        </div>
      </Card>
      <div style={{ height: 12 }} />
    </>
  );
}

/* ─────────────────────────  Pantalla: Escáner (resultado real)  ───────────────────────── */
function Scan() {
  const [confirmed, setConfirmed] = useState(false);
  return (
    <>
      <div style={{ padding: "8px 4px 0" }}>
        <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: -0.6 }}>Ticket leído</div>
        <div style={{ fontSize: 13, color: T.sub, marginTop: 2 }}>
          Makro Barcelona · hoy 4 jul · confianza 96 %
        </div>
      </div>

      <Card style={{ marginTop: 14, background: T.greenBg, border: "1px solid #D5EADF" }}>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <div style={{
            width: 34, height: 34, borderRadius: 99, background: T.green,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}><Check size={18} color="#fff" strokeWidth={3} /></div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14.5, color: "#1E5A40" }}>Todo cuadra al céntimo</div>
            <div style={{ fontSize: 12.5, color: "#4B7A63" }}>
              196,18 € − 1,29 € dto. + 16,98 € IVA = <b>211,87 €</b>
            </div>
          </div>
        </div>
      </Card>

      <Card style={{ marginTop: 10, padding: 0, overflow: "hidden" }}>
        {ticketLines.map((l, i) => (
          <div key={i} style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            padding: "11px 16px", borderBottom: i < ticketLines.length - 1 ? `1px solid ${T.hair}` : "none",
          }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: 14 }}>{l.d}</div>
              <div style={{ fontSize: 12, color: T.sub, display: "flex", gap: 6, alignItems: "center", marginTop: 2, flexWrap: "wrap" }}>
                <span>{l.q}</span>
                {l.kg && <span>· {l.kg.toLocaleString("es-ES")} €/kg</span>}
                {l.exp && <Pill color={T.blue} bg={T.blueBg}>cad. {l.exp}</Pill>}
                {l.promo && <Pill color={T.green} bg={T.greenBg}>promo</Pill>}
              </div>
            </div>
            <div style={{ fontWeight: 700, fontSize: 14, marginLeft: 10 }}>{eur(l.p)}</div>
          </div>
        ))}
      </Card>

      <Card style={{ marginTop: 10 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
          <Sparkles size={15} color={T.green} />
          <span style={{ fontWeight: 700, fontSize: 14 }}>Análisis de la compra</span>
        </div>
        <div style={{ fontSize: 13, lineHeight: 1.55, color: "#3A3A3C" }}>
          <b style={{ color: T.green }}>Buena compra:</b> arroz a 1,21 €/kg y pasta a 1,08 €/kg,
          un 22 % por debajo del precio habitual en súper.{" "}
          <b style={{ color: T.green }}>Promo aplicada:</b> picada a 6,89 €/kg (−0,40 €/kg).{" "}
          <b style={{ color: T.amber }}>Atención:</b> 6,9 kg de carne fresca de una vez —
          congela hoy lo que no uses antes del martes.
        </div>
      </Card>

      <button
        onClick={() => setConfirmed(true)}
        style={{
          width: "100%", marginTop: 12, padding: "15px 0", borderRadius: 16,
          border: "none", background: confirmed ? T.greenBg : T.ink,
          color: confirmed ? T.green : "#fff",
          fontWeight: 700, fontSize: 15.5, fontFamily: T.font, transition: "all .2s",
        }}
      >
        {confirmed ? "✓ Añadido a la despensa (17 productos)" : "Confirmar y actualizar despensa"}
      </button>
      <div style={{ height: 12 }} />
    </>
  );
}

/* ─────────────────────────  Pantalla: Despensa  ───────────────────────── */
function Pantry() {
  const [tab, setTab] = useState("all");
  const expDays = (d) => d <= 1 ? { t: d === 0 ? "hoy" : "mañana", c: T.red, b: T.redBg }
    : d <= 3 ? { t: `${d} días`, c: T.amber, b: T.amberBg }
    : { t: `${d} días`, c: T.sub, b: "#F2F2F4" };
  const totalPantry = pantry.reduce((a, b) => a + b.val, 0);
  const totalFreezer = freezer.reduce((a, b) => a + b.val, 0);

  return (
    <>
      <div style={{ padding: "8px 4px 0" }}>
        <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: -0.6 }}>Despensa</div>
        <div style={{ fontSize: 13, color: T.sub, marginTop: 2 }}>
          {eur(totalPantry + totalFreezer)} en casa · {pantry.length + freezer.length} productos
        </div>
      </div>

      <div style={{ display: "flex", gap: 6, marginTop: 14, background: "#EBEBED", padding: 3, borderRadius: 12 }}>
        {[["all", "Todo"], ["soon", "Caduca pronto"], ["frz", "Congelador"]].map(([k, lbl]) => (
          <button key={k} onClick={() => setTab(k)} style={{
            flex: 1, padding: "8px 0", borderRadius: 10, border: "none", fontFamily: T.font,
            fontWeight: 600, fontSize: 13,
            background: tab === k ? "#fff" : "transparent",
            color: tab === k ? T.ink : T.sub,
            boxShadow: tab === k ? "0 1px 3px rgba(0,0,0,.08)" : "none",
          }}>{lbl}</button>
        ))}
      </div>

      {tab !== "frz" && (
        <Card style={{ marginTop: 12, padding: 0, overflow: "hidden" }}>
          {pantry
            .filter((p) => tab === "all" || p.days <= 3)
            .sort((a, b) => a.days - b.days)
            .map((p, i, arr) => {
              const e = expDays(p.days);
              return (
                <div key={i} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "12px 16px", borderBottom: i < arr.length - 1 ? `1px solid ${T.hair}` : "none",
                }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14.5 }}>{p.d}</div>
                    <div style={{ fontSize: 12, color: T.sub, marginTop: 2 }}>{p.q} · {p.where}</div>
                  </div>
                  <Pill color={e.c} bg={e.b}>{e.t}</Pill>
                </div>
              );
            })}
        </Card>
      )}

      {tab !== "soon" && (
        <>
          <SectionTitle>
            <Snowflake size={16} style={{ verticalAlign: -2, marginRight: 6 }} color={T.blue} />
            Congelador · {eur(totalFreezer)}
          </SectionTitle>
          <Card style={{ padding: 0, overflow: "hidden" }}>
            {freezer.map((f, i) => (
              <div key={i} style={{
                display: "flex", justifyContent: "space-between", alignItems: "center",
                padding: "12px 16px", borderBottom: i < freezer.length - 1 ? `1px solid ${T.hair}` : "none",
              }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14.5 }}>{f.d}</div>
                  <div style={{ fontSize: 12, color: T.sub, marginTop: 2 }}>
                    {f.q} · congelado {f.frozen}
                  </div>
                </div>
                <Pill color={T.blue} bg={T.blueBg}>consumir antes {f.until}</Pill>
              </div>
            ))}
          </Card>
        </>
      )}
      <div style={{ height: 12 }} />
    </>
  );
}

/* ─────────────────────────  Pantalla: Menús  ───────────────────────── */
function Menus() {
  const [state, setState] = useState({});
  return (
    <>
      <div style={{ padding: "8px 4px 0" }}>
        <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: -0.6 }}>Menús</div>
        <div style={{ fontSize: 13, color: T.sub, marginTop: 2 }}>
          Primero, lo que caduca antes · 5 raciones
        </div>
      </div>

      <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 10 }}>
        {menus.map((m, i) => {
          const st = state[i] || m.status;
          return (
            <Card key={i} style={st === "rejected" ? { opacity: 0.45 } : {}}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: T.sub, textTransform: "uppercase", letterSpacing: 0.4 }}>{m.day}</span>
                {m.urgent && <Pill color={T.amber} bg={T.amberBg}>evita desperdicio</Pill>}
              </div>
              <div style={{ fontWeight: 700, fontSize: 16.5, letterSpacing: -0.2 }}>{m.title}</div>
              <div style={{ fontSize: 13, color: T.sub, marginTop: 4, lineHeight: 1.45 }}>
                <Sparkles size={12} style={{ verticalAlign: -1, marginRight: 4 }} color={T.green} />
                {m.why}
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                {st === "suggested" && (
                  <>
                    <button onClick={() => setState({ ...state, [i]: "accepted" })} style={{
                      flex: 1, padding: "10px 0", borderRadius: 12, border: "none",
                      background: T.ink, color: "#fff", fontWeight: 700, fontSize: 13.5, fontFamily: T.font,
                    }}>Aceptar</button>
                    <button onClick={() => setState({ ...state, [i]: "rejected" })} style={{
                      width: 44, borderRadius: 12, border: `1px solid ${T.hair}`,
                      background: "#fff", color: T.sub, fontFamily: T.font,
                      display: "flex", alignItems: "center", justifyContent: "center",
                    }}><X size={16} /></button>
                  </>
                )}
                {st === "accepted" && (
                  <button onClick={() => setState({ ...state, [i]: "cooked" })} style={{
                    flex: 1, padding: "10px 0", borderRadius: 12, border: "none",
                    background: T.greenBg, color: T.green, fontWeight: 700, fontSize: 13.5, fontFamily: T.font,
                  }}>Marcar como cocinado</button>
                )}
                {st === "cooked" && (
                  <div style={{
                    flex: 1, padding: "10px 0", borderRadius: 12, textAlign: "center",
                    background: "#F2F2F4", color: T.sub, fontWeight: 700, fontSize: 13.5,
                  }}>✓ Cocinado · despensa actualizada</div>
                )}
              </div>
            </Card>
          );
        })}
      </div>
      <div style={{ height: 12 }} />
    </>
  );
}

/* ─────────────────────────  Pantalla: Ahorro  ───────────────────────── */
function Savings() {
  const total = 342.18, goal = 600;
  const pct = total / goal;
  const R = 62, C = 2 * Math.PI * R;
  return (
    <>
      <div style={{ padding: "8px 4px 0" }}>
        <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: -0.6 }}>Ahorro</div>
        <div style={{ fontSize: 13, color: T.sub, marginTop: 2 }}>Cada euro tiene un propósito</div>
      </div>

      <Card style={{ marginTop: 14, display: "flex", flexDirection: "column", alignItems: "center", padding: 24 }}>
        <div style={{ position: "relative", width: 150, height: 150 }}>
          <svg width="150" height="150" style={{ transform: "rotate(-90deg)" }}>
            <circle cx="75" cy="75" r={R} fill="none" stroke="#EFEFF1" strokeWidth="11" />
            <circle cx="75" cy="75" r={R} fill="none" stroke={T.green} strokeWidth="11"
              strokeLinecap="round" strokeDasharray={C} strokeDashoffset={C * (1 - pct)} />
          </svg>
          <div style={{
            position: "absolute", inset: 0, display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center",
          }}>
            <div style={{ fontSize: 26, fontWeight: 800, letterSpacing: -0.8, color: T.green }}>342 €</div>
            <div style={{ fontSize: 11, color: T.sub, fontWeight: 600 }}>de 600 € objetivo</div>
          </div>
        </div>
        <div style={{ fontSize: 13, color: T.sub, marginTop: 10, textAlign: "center" }}>
          Ahorro acumulado en 2026 · al ritmo actual: <b style={{ color: T.ink }}>684 €/año</b>
        </div>
      </Card>

      <SectionTitle>De dónde viene</SectionTitle>
      <Card style={{ padding: 0, overflow: "hidden" }}>
        {[
          { icon: <Receipt size={16} color={T.blue} />, t: "Promociones aprovechadas", v: 96.4, note: "hoy: −1,29 € Makro" },
          { icon: <TrendingDown size={16} color={T.green} />, t: "Comprar al mejor precio", v: 148.6, note: "arroz y pasta −22 % hoy" },
          { icon: <Leaf size={16} color={T.green} />, t: "Desperdicio evitado", v: 97.18, note: "34 alertas atendidas" },
        ].map((r, i, arr) => (
          <div key={i} style={{
            display: "flex", alignItems: "center", gap: 12, padding: "13px 16px",
            borderBottom: i < arr.length - 1 ? `1px solid ${T.hair}` : "none",
          }}>
            <div style={{
              width: 32, height: 32, borderRadius: 10, background: "#F4F4F6",
              display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
            }}>{r.icon}</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, fontSize: 14 }}>{r.t}</div>
              <div style={{ fontSize: 11.5, color: T.sub }}>{r.note}</div>
            </div>
            <div style={{ fontWeight: 700, color: T.green }}>{eur(r.v)}</div>
          </div>
        ))}
      </Card>

      <SectionTitle>Inflación familiar</SectionTitle>
      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: 13, color: T.sub }}>Vuestra cesta vs. hace 6 meses</div>
            <div style={{ fontSize: 24, fontWeight: 800, color: T.red, letterSpacing: -0.5 }}>
              <TrendingUp size={18} style={{ verticalAlign: -2, marginRight: 4 }} />+3,8 %
            </div>
          </div>
          <div style={{ fontSize: 12, color: T.sub, textAlign: "right", lineHeight: 1.5 }}>
            Lo que más sube:<br />
            <b style={{ color: T.ink }}>aceite +11 % · huevos +7 %</b>
          </div>
        </div>
      </Card>
      <div style={{ height: 12 }} />
    </>
  );
}

/* ─────────────────────────  Shell del teléfono  ───────────────────────── */
export default function FamilyLedger() {
  const [tab, setTab] = useState("home");
  const screens = { home: <Home go={setTab} />, scan: <Scan />, pantry: <Pantry />, menus: <Menus />, savings: <Savings /> };
  const tabs = [
    { k: "home", icon: House, lbl: "Inicio" },
    { k: "pantry", icon: Archive, lbl: "Despensa" },
    { k: "scan", icon: null, lbl: "" },
    { k: "menus", icon: ChefHat, lbl: "Menús" },
    { k: "savings", icon: PiggyBank, lbl: "Ahorro" },
  ];

  return (
    <div style={{
      minHeight: "100vh", background: "#E9E9EC", display: "flex",
      alignItems: "center", justifyContent: "center", fontFamily: T.font, padding: 24,
    }}>
      <div style={{
        width: 390, height: 800, background: T.bg, borderRadius: 46,
        border: "10px solid #16161A", overflow: "hidden", position: "relative",
        boxShadow: "0 30px 80px rgba(0,0,0,.35)", display: "flex", flexDirection: "column",
        color: T.ink,
      }}>
        {/* status bar */}
        <div style={{
          display: "flex", justifyContent: "space-between", padding: "12px 26px 4px",
          fontSize: 13.5, fontWeight: 700, flexShrink: 0,
        }}>
          <span>9:41</span>
          <div style={{
            position: "absolute", top: 10, left: "50%", transform: "translateX(-50%)",
            width: 110, height: 26, background: "#16161A", borderRadius: 99,
          }} />
          <span>􀙇 􀛨</span>
        </div>

        {/* contenido scrollable */}
        <div style={{ flex: 1, overflowY: "auto", padding: "6px 16px 90px" }}>
          {screens[tab]}
        </div>

        {/* tab bar */}
        <div style={{
          position: "absolute", bottom: 0, left: 0, right: 0,
          background: "rgba(255,255,255,.92)", backdropFilter: "blur(18px)",
          borderTop: `1px solid ${T.hair}`, display: "flex",
          justifyContent: "space-around", alignItems: "center", padding: "8px 8px 20px",
        }}>
          {tabs.map(({ k, icon: Icon, lbl }) =>
            k === "scan" ? (
              <button key={k} onClick={() => setTab("scan")} style={{
                width: 56, height: 56, borderRadius: 99, border: "none",
                background: T.green, marginTop: -26,
                boxShadow: "0 6px 18px rgba(47,132,96,.4)",
                display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer",
              }}>
                <Camera size={24} color="#fff" />
              </button>
            ) : (
              <button key={k} onClick={() => setTab(k)} style={{
                border: "none", background: "transparent", fontFamily: T.font,
                display: "flex", flexDirection: "column", alignItems: "center", gap: 3,
                color: tab === k ? T.ink : "#B4B4B9", cursor: "pointer", width: 62,
              }}>
                <Icon size={22} strokeWidth={tab === k ? 2.4 : 2} />
                <span style={{ fontSize: 10.5, fontWeight: 600 }}>{lbl}</span>
              </button>
            )
          )}
        </div>
      </div>
    </div>
  );
}
