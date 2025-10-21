import { useEffect, useState } from 'react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
} from 'chart.js'

// 注册Chart.js组件
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

interface AssetCurveData {
  date: string
  total_assets: number
  cash: number
  positions_value: number
  is_initial: boolean
  user_id: number
  username: string
}

const API_BASE = 'http://127.0.0.1:5611'

export default function AssetCurve() {
  const [data, setData] = useState<AssetCurveData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchAssetCurve()
  }, [])

  const fetchAssetCurve = async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch data for all accounts
      const response = await fetch(`${API_BASE}/api/account/asset-curve/all`)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const assetData = await response.json()
      setData(assetData)
    } catch (err) {
      console.error('Failed to fetch asset curve:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch asset curve')
    } finally {
      setLoading(false)
    }
  }

  // Group data by date and create datasets for each user
  const groupedData = data.reduce((acc, item) => {
    if (!acc[item.date]) {
      acc[item.date] = {}
    }
    acc[item.date][item.username] = item.total_assets
    return acc
  }, {} as Record<string, Record<string, number>>)

  const dates = Object.keys(groupedData).sort()
  const users = Array.from(new Set(data.map(item => item.username))).sort()

  // Generate colors for each user
  const colors = [
    'rgb(59, 130, 246)',   // blue
    'rgb(34, 197, 94)',     // green
    'rgb(168, 85, 247)',    // purple
    'rgb(239, 68, 68)',     // red
    'rgb(245, 158, 11)',    // orange
    'rgb(16, 185, 129)',    // emerald
    'rgb(139, 92, 246)',    // violet
    'rgb(236, 72, 153)',    // pink
  ]

  const chartData = {
    labels: dates.map(date => {
      const d = new Date(date)
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
      })
    }),
    datasets: users.map((username, index) => ({
      label: username.replace('demo_', '').toUpperCase(),
      data: dates.map(date => groupedData[date][username] || 0),
      borderColor: colors[index % colors.length],
      backgroundColor: colors[index % colors.length].replace('rgb', 'rgba').replace(')', ', 0.1)'),
      borderWidth: 2,
      fill: false,
      tension: 0.1,
    })),
  }

  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: 'All Accounts Asset Curve',
        font: {
          size: 16,
          weight: 'bold',
        },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          label: (context) => {
            const label = context.dataset.label || ''
            const value = context.parsed.y
            return `${label}: $${value?.toLocaleString('en-US', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2
            })}`
          },
        },
      },
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Date',
        },
      },
      y: {
        display: true,
        title: {
          display: true,
          text: 'Amount (USD)',
        },
        ticks: {
          callback: function(value) {
            return '$' + Number(value).toLocaleString('en-US')
          },
        },
      },
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false,
    },
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-muted-foreground">Loading asset curve...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-96 space-y-4">
        <div className="text-destructive">Failed to load asset curve: {error}</div>
        <button
          onClick={fetchAssetCurve}
          className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-muted-foreground">No asset data available</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="h-96">
        <Line data={chartData} options={options} />
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-secondary p-4 rounded-lg">
          <div className="text-sm text-secondary-foreground font-medium">Total Accounts</div>
          <div className="text-2xl font-bold text-secondary-foreground">
            {users.length}
          </div>
        </div>

        <div className="bg-secondary p-4 rounded-lg">
          <div className="text-sm text-secondary-foreground font-medium">Total Combined Assets</div>
          <div className="text-2xl font-bold text-secondary-foreground">
            ${users.reduce((total, username) => {
              const latestData = data.filter(item => item.username === username).sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())[0]
              return total + (latestData?.total_assets || 0)
            }, 0).toLocaleString('en-US', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </div>
        </div>

        <div className="bg-secondary p-4 rounded-lg">
          <div className="text-sm text-secondary-foreground font-medium">Data Points</div>
          <div className="text-2xl font-bold text-secondary-foreground">
            {dates.length}
          </div>
        </div>
      </div>
    </div>
  )
}