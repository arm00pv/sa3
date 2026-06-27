import { useState, useEffect } from 'react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts'
import {
  DollarSign, TrendingUp, AlertTriangle, Shield, RefreshCw,
  ArrowUpRight, ArrowDownRight, Copy, Ghost, ChevronRight,
  Zap, BarChart3, Users, Link as LinkIcon, Database
} from 'lucide-react'
import './App.css'

const API_BASE = 'http://localhost:8200/api'

const CATEGORY_COLORS = {
  cloud: '#6366f1',
  development: '#8b5cf6',
  communication: '#3b82f6',
  productivity: '#10b981',
  design: '#f59e0b',
  marketing: '#ef4444',
  security: '#06b6d4',
  analytics: '#ec4899',
  finance: '#14b8a6',
  hr: '#f97316',
  other: '#64748b',
}

function formatCurrency(amount) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD',
    minimumFractionDigits: 0, maximumFractionDigits: 0,
  }).format(amount)
}

function formatCurrencyFull(amount) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount)
}

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="custom-tooltip">
        <p className="label">{label}</p>
        <p className="value">{formatCurrencyFull(payload[0].value)}</p>
      </div>
    )
  }
  return null
}

export default function App() {
  const [dashboard, setDashboard] = useState(null)
  const [subscriptions, setSubscriptions] = useState([])
  const [loading, setLoading] = useState(true)
  const [ingesting, setIngesting] = useState(false)
  const [reconciling, setReconciling] = useState(false);
  const [bankConnected, setBankConnected] = useState(false);
  const [activeEmployees, setActiveEmployees] = useState(null);

  const fetchData = async () => {
    try {
      const [dashRes, subRes] = await Promise.all([
        fetch(`${API_BASE}/dashboard/`),
        fetch(`${API_BASE}/subscriptions/`),
      ])
      const dashData = await dashRes.json()
      const subData = await subRes.json()
      setDashboard(dashData)
      setSubscriptions(subData.results || subData)
      setLoading(false)
    } catch (err) {
      console.error('Fetch error:', err)
      setLoading(false)
    }
  }

  const handleIngest = async () => {
    setIngesting(true)
    try {
      const res = await fetch(`${API_BASE}/ingest/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ organization_name: 'Acme Corp', use_mock: true }),
      })
      await res.json()
      await fetchData()
    } catch (err) {
      console.error('Ingest error:', err)
    }
    setIngesting(false)
  }

  useEffect(() => { fetchData() }, [])

  const handleReconcile = async () => {
    setReconciling(true);
    try {
      const res = await fetch(`${API_BASE}/reconcile/`, { method: 'POST' });
      const data = await res.json();
      if (data.active_employees) {
        setActiveEmployees(data.active_employees);
        fetchData();
      }
    } catch (e) {
      console.error(e);
    }
    setReconciling(false);
  };

  const handleConnectBank = () => {
    setTimeout(() => {
      setBankConnected(true);
      fetchData();
    }, 1000);
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner" />
        <p className="loading-text">Loading dashboard...</p>
      </div>
    )
  }

  const d = dashboard || {}
  const monthlyTrend = (d.monthly_trend || []).map(t => ({
    ...t,
    month: t.month?.slice(5) || t.month,
  }))

  const categoryData = (d.category_breakdown || []).map(c => ({
    name: c.category,
    value: c.total,
    color: CATEGORY_COLORS[c.category] || CATEGORY_COLORS.other,
  }))

  const pieData = categoryData.slice(0, 6)

  return (
    <div className="app-container">
      {/* ─── Header ──────────────────────── */}
      <header className="app-header">
        <div className="app-logo">
          <div className="app-logo-icon">
            <Zap size={22} color="white" />
          </div>
          <div>
            <h1 className="app-title">SpendShield</h1>
            <p className="app-subtitle">Shadow IT & SaaS Spend Optimizer</p>
          </div>
        </div>
        <div className="header-actions">
          <div className="flex items-center space-x-4">
          {!bankConnected ? (
            <button 
              onClick={handleConnectBank}
              className="flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg transition-colors"
            >
              <LinkIcon className="h-5 w-5" />
              <span>Connect Bank (Plaid)</span>
            </button>
          ) : (
            <div className="flex items-center space-x-2 text-emerald-400 bg-emerald-900/30 px-4 py-2 rounded-lg border border-emerald-800">
              <Database className="h-5 w-5" />
              <span>Bank Connected</span>
            </div>
          )}
          
          <button 
            onClick={handleReconcile}
            disabled={reconciling}
            className="flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
          >
            <Users className="h-5 w-5" />
            <span>{reconciling ? 'Syncing...' : 'Sync Workspace'}</span>
          </button>
          
          <button className="btn btn-secondary" onClick={fetchData}>
            <RefreshCw size={16} /> Refresh
          </button>
          </div>
          <button
            className="btn btn-primary"
            onClick={handleIngest}
            disabled={ingesting}
          >
            {ingesting ? <RefreshCw size={16} className="spin" /> : <BarChart3 size={16} />}
            {ingesting ? 'Syncing...' : 'Sync Transactions'}
          </button>
        </div>
      </header>

      {/* ─── Stats Cards ──────────────────── */}
      <div className="stats-grid">
        <div className="stat-card accent fade-in">
          <div className="stat-header">
            <span className="stat-label">Monthly SaaS Spend</span>
            <div className="stat-icon accent">
              <DollarSign size={18} />
            </div>
          </div>
          <div className="stat-value">{formatCurrency(d.total_monthly_spend || 0)}</div>
          <div className="stat-change negative">
            <ArrowUpRight size={14} />
            {formatCurrency(d.total_annual_spend || 0)}/year
          </div>
        </div>

        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm font-medium mb-1">Active Employees</p>
              <h3 className="text-3xl font-bold text-white">
                {activeEmployees !== null ? activeEmployees : '--'}
              </h3>
            </div>
            <div className="bg-purple-900/50 p-3 rounded-lg border border-purple-800/50">
              <Users className="h-6 w-6 text-purple-400" />
            </div>
          </div>
        </div>

        <div className="stat-card danger fade-in">
          <div className="stat-header">
            <span className="stat-label">Estimated Waste</span>
            <div className="stat-icon danger">
              <AlertTriangle size={18} />
            </div>
          </div>
          <div className="stat-value">{formatCurrency(d.estimated_waste || 0)}</div>
          <div className="stat-change negative">
            <ArrowDownRight size={14} />
            {(d.duplicate_subscriptions || 0) + (d.orphaned_subscriptions || 0)} flagged items
          </div>
        </div>

        <div className="stat-card warning fade-in">
          <div className="stat-header">
            <span className="stat-label">Issues Found</span>
            <div className="stat-icon warning">
              <Shield size={18} />
            </div>
          </div>
          <div className="stat-value">
            {(d.duplicate_subscriptions || 0) + (d.flagged_subscriptions || 0) + (d.orphaned_subscriptions || 0)}
          </div>
          <div className="stat-change">
            <Copy size={14} style={{ color: 'var(--warning)' }} />
            <span style={{ color: 'var(--warning)' }}>{d.duplicate_subscriptions || 0} dupes</span>
            <Ghost size={14} style={{ color: 'var(--info)', marginLeft: 8 }} />
            <span style={{ color: 'var(--info)' }}>{d.orphaned_subscriptions || 0} orphaned</span>
          </div>
        </div>
      </div>

      {/* ─── Charts Row ──────────────────── */}
      <div className="dashboard-grid">
        <div className="panel fade-in">
          <div className="panel-header">
            <h3 className="panel-title">Monthly SaaS Spend Trend</h3>
            <span className="panel-badge live">● Live</span>
          </div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={monthlyTrend}>
                <defs>
                  <linearGradient id="spendGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.08)" />
                <XAxis
                  dataKey="month" tick={{ fill: '#64748b', fontSize: 12 }}
                  axisLine={{ stroke: 'rgba(99,102,241,0.1)' }}
                />
                <YAxis
                  tick={{ fill: '#64748b', fontSize: 12 }}
                  axisLine={{ stroke: 'rgba(99,102,241,0.1)' }}
                  tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone" dataKey="spend"
                  stroke="#6366f1" strokeWidth={2.5}
                  fill="url(#spendGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="panel fade-in">
          <div className="panel-header">
            <h3 className="panel-title">Spend by Category</h3>
          </div>
          {pieData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={pieData} cx="50%" cy="50%"
                    innerRadius={50} outerRadius={75}
                    paddingAngle={3} dataKey="value"
                  >
                    {pieData.map((entry, idx) => (
                      <Cell key={idx} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => formatCurrencyFull(v)} />
                </PieChart>
              </ResponsiveContainer>
              <ul className="category-list">
                {categoryData.map((cat, idx) => (
                  <li key={idx} className="category-item">
                    <div className="category-info">
                      <div className="category-dot" style={{ background: cat.color }} />
                      <span className="category-name">{cat.name}</span>
                    </div>
                    <span className="category-amount">{formatCurrencyFull(cat.value)}</span>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px 0' }}>
              No data. Click "Sync Transactions" to begin.
            </p>
          )}
        </div>
      </div>

      {/* ─── Subscriptions Table ──────────── */}
      <div className="panel fade-in">
        <div className="panel-header">
          <h3 className="panel-title">
            All Subscriptions
            <span style={{ color: 'var(--text-muted)', fontWeight: 400, marginLeft: 8 }}>
              ({subscriptions.length})
            </span>
          </h3>
        </div>
        {subscriptions.length > 0 ? (
          <table className="sub-table">
            <thead>
              <tr>
                <th>Vendor</th>
                <th>Monthly Cost</th>
                <th>Category</th>
                <th>Status</th>
                <th>Charges</th>
                <th>First Seen</th>
              </tr>
            </thead>
            <tbody>
              {subscriptions.map((sub) => (
                <tr key={sub.id}>
                  <td>
                    <div className="vendor-cell">
                      <div className="vendor-icon">
                        {(sub.vendor_name || sub.matched_description || '?')[0]}
                      </div>
                      <div>
                        <div className="vendor-name">
                          {sub.vendor_name || sub.matched_description}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td style={{ fontWeight: 700 }}>
                    {formatCurrencyFull(sub.monthly_cost)}
                  </td>
                  <td>
                    <span style={{
                      color: CATEGORY_COLORS[sub.vendor_category] || 'var(--text-secondary)',
                      textTransform: 'capitalize'
                    }}>
                      {sub.vendor_category || 'other'}
                    </span>
                  </td>
                  <td>
                    <span className={`status-badge ${sub.status}`}>
                      {sub.status === 'duplicate' && <Copy size={12} />}
                      {sub.status === 'flagged' && <AlertTriangle size={12} />}
                      {sub.status === 'orphaned' && <Ghost size={12} />}
                      {sub.status}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-secondary)' }}>
                    {sub.transaction_count}×
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                    {sub.first_seen}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px 0' }}>
            No subscriptions found. Click "Sync Transactions" to ingest mock data.
          </p>
        )}
      </div>
    </div>
  )
}
