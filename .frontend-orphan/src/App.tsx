import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  MapPin,
  Pill,
  Search,
  ShieldAlert,
  Store,
  RefreshCw,
  Phone,
  Stethoscope,
  TriangleAlert,
} from 'lucide-react';

const API = (import.meta.env.VITE_API as string | undefined) || 'http://localhost:8000';

type Medicine = {
  id: number;
  name: string;
  category: string;
  description: string;
};

type Pharmacy = {
  id: number;
  name: string;
  area: string;
  lat: number | null;
  lng: number | null;
};

type StockEntry = {
  pharmacy_id: number;
  pharmacy_name: string;
  area: string;
  medicine_name: string;
  status: string;
  price: number | null;
  quantity: number | null;
  updated_at: string | null;
  open_now: boolean | null;
};

type Shortage = {
  medicine_name: string;
  pharmacy_name: string;
  area: string;
  created_at: string;
};

type Stats = {
  medicines: number;
  pharmacies: number;
  shortages: number;
  in_stock: number;
};

function fmtCurrency(n: number | null) {
  if (n == null) return '—';
  const u = new Intl.NumberFormat('en-KE', {
    style: 'currency',
    currency: 'KES',
    maximumFractionDigits: 0,
  });
  return u.format(n);
}

export default function App() {
  const [medicines, setMedicines] = useState<Medicine[]>([]);
  const [pharmacies, setPharmacies] = useState<Pharmacy[]>([]);
  const [stock, setStock] = useState<StockEntry[]>([]);
  const [shortages, setShortages] = useState<Shortage[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);

  const [search, setSearch] = useState('');
  const [medicineId, setMedicineId] = useState<string>('');
  const [lat, setLat] = useState<string>('');
  const [lng, setLng] = useState<string>('');
  const [radiusKm, setRadiusKm] = useState<string>('50');
  const [locLoading, setLocLoading] = useState(false);
  const [toast, setToast] = useState('');

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3000);
  }, []);

  const fetchJSON = useCallback(async <T,>(path: string): Promise<T> => {
    const res = await fetch(`${API}${path}`);
    if (!res.ok) throw new Error(`Failed: ${path}`);
    return res.json();
  }, []);

  // Initial load
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [m, p, s, st] = await Promise.all([
          fetchJSON<Medicine[]>('/medicines'),
          fetchJSON<Pharmacy[]>('/pharmacies'),
          fetchJSON<StockEntry[]>('/stock'),
          fetchJSON<Stats>('/stats'),
        ]);
        if (!cancelled) {
          setMedicines(m);
          setPharmacies(p);
          setStock(s);
          setStats(st);
        }
      } catch {
        if (!cancelled) showToast('Could not reach backend. Start it on :8000.');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [fetchJSON, showToast]);

  // Reload shortages on demand
  const refreshShortages = useCallback(async () => {
    try {
      const data = await fetchJSON<Shortage[]>('/shortages?limit=20');
      setShortages(data);
    } catch {
      showToast('Could not load shortage reports.');
    }
  }, [fetchJSON, showToast]);

  // Filter medicines by search
  const filteredMedicines = useMemo(() => {
    const q = search.trim().toLowerCase();
    return q ? medicines.filter((m) => (m.name + ' ' + m.category).toLowerCase().includes(q)) : medicines;
  }, [medicines, search]);

  const med = useMemo(() => medicines.find((m) => String(m.id) === medicineId) || null, [medicineId, medicines]);

  const pinnedStock = useMemo(() => {
    if (!medicineId) return [];
    const q = `${API}/find?medicine_id=${encodeURIComponent(medicineId)}`;
    const params = new URLSearchParams();
    if (lat) params.set('lat', lat);
    if (lng) params.set('lng', lng);
    if (radiusKm) params.set('radius_km', radiusKm);
    const url = `${q}${params.toString() ? '&' + params.toString() : ''}`;
    return fetchJSON<StockEntry[]>(url);
  }, [medicineId, lat, lng, radiusKm, fetchJSON]);

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-2">
            <Pill className="h-6 w-6 text-indigo-600" />
            <div>
              <h1 className="text-lg font-bold leading-tight">MedStock</h1>
              <p className="text-xs text-slate-500">Essential medicine tracker & pharmacy finder</p>
            </div>
          </div>
          <button
            onClick={refreshShortages}
            className="inline-flex items-center gap-2 rounded-full bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh shortages
          </button>
        </div>
      </header>

      {toast && (
        <div className="mx-auto mt-4 max-w-5xl px-4">
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            {toast}
          </div>
        </div>
      )}

      <main className="mx-auto max-w-5xl px-4 py-4 space-y-4">
        {/* Search */}
        <section className="rounded-xl border bg-white p-3 shadow-sm">
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search medicines..."
                className="w-full rounded-lg border bg-white pl-9 pr-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <label className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm">
              Select medicine
              <select
                value={medicineId}
                onChange={(e) => setMedicineId(e.target.value)}
                className="rounded-md border bg-white px-2 py-1 text-sm"
              >
                <option value="">—</option>
                {filteredMedicines.map((m) => (
                  <option key={m.id} value={String(m.id)}>
                    {m.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Tip: use this to find nearest pharmacy with stock.
          </p>
        </section>

        {/* Stats */}
        {stats && (
          <section className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <Stat label="Medicines" value={String(stats.medicines)} icon={<Activity className="h-4 w-4" />} />
            <Stat label="Pharmacies" value={String(stats.pharmacies)} icon={<Store className="h-4 w-4" />} />
            <Stat label="In stock" value={String(stats.in_stock)} icon={<ShieldAlert className="h-4 w-4" />} />
            <Stat label="Shortages" value={String(stats.shortages)} icon={<TriangleAlert className="h-4 w-4" />} />
          </section>
        )}

        {/* Geofilter */}
        {medicineId && (
          <section className="rounded-xl border bg-white p-3 shadow-sm">
            <div className="grid gap-2 sm:grid-cols-4">
              <label className="text-xs text-slate-600 sm:col-span-4">Use your location to rank results</label>
              <input value={lat} onChange={(e) => setLat(e.target.value)} placeholder="Latitude" className="rounded-lg border px-3 py-2 text-sm" />
              <input value={lng} onChange={(e) => setLng(e.target.value)} placeholder="Longitude" className="rounded-lg border px-3 py-2 text-sm" />
              <input value={radiusKm} onChange={(e) => setRadiusKm(e.target.value)} placeholder="Radius km" className="rounded-lg border px-3 py-2 text-sm" />
              <button
                onClick={async () => {
                  setLocLoading(true);
                  try {
                    const pos = await new Promise<GeolocationPosition>((resolve, reject) =>
                      navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 10000 })
                    );
                    setLat(String(pos.coords.latitude));
                    setLng(String(pos.coords.longitude));
                    showToast('Location updated.');
                  } catch {
                    showToast('Location permission denied.');
                  } finally {
                    setLocLoading(false);
                  }
                }}
                className="inline-flex items-center justify-center gap-2 rounded-lg border px-3 py-2 text-sm hover:bg-slate-50"
              >
                <MapPin className="h-4 w-4" /> {locLoading ? 'Locating...' : 'Use my location'}
              </button>
            </div>
          </section>
        )}

        {/* Find / Center list */}
        {medicineId && (
          <section className="space-y-2">
            <h2 className="text-sm font-semibold text-slate-800">
              {med ? `${med.name} availability` : 'Availability'}
            </h2>
            <PromiseSuspense
              promise={pinnedStock}
              fallback={<p className="text-sm text-slate-500">Finding stock…</p>}
            >
              {(rows) => (
                <div className="grid gap-2">
                  {rows.map((r, i) => (
                    <div key={i} className="flex flex-col gap-1 rounded-xl border bg-white px-3 py-2 shadow-sm">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{r.pharmacy_name}</p>
                          <p className="text-xs text-slate-500">{r.area}</p>
                        </div>
                        <span className={`text-xs font-semibold ${statusClass(r.status)}`}>{formatStatus(r.status)}</span>
                      </div>
                      <div className="flex flex-wrap gap-3 text-xs text-slate-700">
                        <span>Qty: {r.quantity ?? '—'}</span>
                        <span>Price: {fmtCurrency(r.price)}</span>
                        {r.distance_km != null && <span>Distance: {Math.round(r.distance_km)} km</span>}
                        {r.open_now == true && <span className="inline-flex items-center gap-1 text-emerald-700">Open now</span>}
                        {r.open_now == false && <span className="inline-flex items-center gap-1 text-slate-500">Closed</span>}
                      </div>
                    </div>
                  ))}
                  {rows.length === 0 && <p className="rounded-lg border bg-white px-3 py-2 text-sm text-slate-500">No stock results.</p>}
                </div>
              )}
            </PromiseSuspense>
          </section>
        )}

        {/* All stock */}
        <section className="rounded-xl border bg-white p-3 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-800">All stock</h2>
          <div className="mt-2 grid gap-2">
            {stock.slice(0, 20).map((r, i) => (
              <div key={i} className="flex flex-col gap-1 rounded-lg border bg-white px-3 py-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{r.medicine_name}</span>
                  <span className={`text-xs font-semibold ${statusClass(r.status)}`}>{formatStatus(r.status)}</span>
                </div>
                <p className="text-xs text-slate-500">{r.pharmacy_name} · {r.area}</p>
              </div>
            ))}
            {stock.length === 0 && <p className="text-sm text-slate-500">No stock records.</p>}
          </div>
        </section>

        {/* Shortages */}
        <section className="rounded-xl border bg-white p-3 shadow-sm">
          <div className="flex items-center gap-2">
            <TriangleAlert className="h-5 w-5 text-red-600" />
            <h2 className="text-sm font-semibold text-slate-800">Recent shortages</h2>
          </div>
          <button onClick={refreshShortages} className="mt-2 inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs hover:bg-slate-50">
            <RefreshCw className="h-3 w-3" /> Load reports
          </button>
          <div className="mt-2 grid gap-2">
            {shortages.map((r, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg border bg-red-50 px-3 py-2 text-sm">
                <div>
                  <p className="font-medium">{r.medicine_name}</p>
                  <p className="text-xs text-slate-600">{r.pharmacy_name} · {r.area}</p>
                </div>
                <time className="text-xs text-slate-500">{r.created_at ? new Date(r.created_at).toLocaleString() : ''}</time>
              </div>
            ))}
            {shortages.length === 0 && <p className="text-sm text-slate-500">No recent shortages loaded yet.</p>}
          </div>
        </section>

        {/* Health note */}
        <section className="rounded-xl border bg-white p-3 shadow-sm">
          <div className="flex items-center gap-2 text-sm text-slate-700">
            <Phone className="h-4 w-4 text-indigo-600" />
            If this is an emergency, call your local emergency number or visit the nearest clinic.
          </div>
        </section>
      </main>
    </div>
  );
}

function Stat({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="rounded-xl border bg-white px-3 py-2 shadow-sm">
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <span className="text-slate-700">{icon}</span>
        {label}
      </div>
      <p className="mt-1 text-lg font-bold">{value}</p>
    </div>
  );
}

function PromiseSuspense<T>({ promise, fallback, children }: { promise: Promise<T>; fallback: React.ReactNode; children: (data: T) => React.ReactNode }) {
  const [data, setData] = useState<T | null>(null);
  useEffect(() => {
    let cancelled = false;
    promise.then((result) => { if (!cancelled) setData(result); });
    return () => { cancelled = true; };
  }, [promise]);
  if (!data) return <div>{fallback}</div>;
  return <>{data && typeof children === 'function' ? children(data) : null}</>;
}

function statusClass(status: string) {
  const base = status.toLowerCase();
  if (base === 'in_stock') return 'rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700';
  if (base === 'low_stock') return 'rounded-full bg-amber-50 px-2 py-0.5 text-amber-700';
  if (base === 'out_of_stock') return 'rounded-full bg-red-50 px-2 py-0.5 text-red-700';
  return 'rounded-full bg-slate-50 px-2 py-0.5 text-slate-700';
}

function formatStatus(status: string) {
  const s = status.toLowerCase();
  if (s === 'in_stock') return 'In stock';
  if (s === 'low_stock') return 'Low';
  if (s === 'out_of_stock') return 'Out of stock';
  return status;
}
