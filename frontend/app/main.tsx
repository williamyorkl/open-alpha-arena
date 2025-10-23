import React, { useEffect, useRef, useState } from 'react'
import ReactDOM from 'react-dom/client'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import './index.css'
import { Toaster, toast } from 'react-hot-toast'
import { Button } from '@/components/ui/button'

// Create a module-level WebSocket singleton to avoid duplicate connections in React StrictMode
let __WS_SINGLETON__: WebSocket | null = null;

const resolveWsUrl = () => {
  if (typeof window === 'undefined') return 'ws://localhost:5611/ws'
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws`
}

const resolveApiBase = () => {
  if (typeof window !== 'undefined') return window.location.origin
  return import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:5611'
}

import Header from '@/components/layout/Header'
import Sidebar from '@/components/layout/Sidebar'
import TradingPanel from '@/components/trading/TradingPanel'
import Portfolio from '@/components/portfolio/Portfolio'
import AssetCurve from '@/components/portfolio/AssetCurve'
import ComprehensiveView from '@/components/portfolio/ComprehensiveView'
import { AIDecision } from '@/lib/api'

interface User {
  id: number
  username: string
}

interface Account {
  id: number
  user_id: number
  name: string
  account_type: string
  initial_capital: number
  current_cash: number
  frozen_cash: number
}

interface Overview {
  account: Account
  total_assets: number
  positions_value: number
  portfolio?: {
    total_assets: number
    positions_value: number
  }
}
interface Position { id: number; account_id: number; symbol: string; name: string; market: string; quantity: number; available_quantity: number; avg_cost: number; last_price?: number | null; market_value?: number | null }
interface Order { id: number; order_no: string; symbol: string; name: string; market: string; side: string; order_type: string; price?: number; quantity: number; filled_quantity: number; status: string }
interface Trade { id: number; order_id: number; account_id: number; symbol: string; name: string; market: string; side: string; price: number; quantity: number; commission: number; trade_time: string }

const PAGE_TITLES: Record<string, string> = {
  portfolio: 'Simulated Crypto Trading',
  comprehensive: 'Open Alpha Arena',
}

function App() {
  const [user, setUser] = useState<User | null>(null)
  const [account, setAccount] = useState<Account | null>(null)
  const [overview, setOverview] = useState<Overview | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [orders, setOrders] = useState<Order[]>([])
  const [trades, setTrades] = useState<Trade[]>([])
  const [aiDecisions, setAiDecisions] = useState<AIDecision[]>([])
  const [allAssetCurves, setAllAssetCurves] = useState<any[]>([])
  const [currentPage, setCurrentPage] = useState<string>('comprehensive')
  const [accountRefreshTrigger, setAccountRefreshTrigger] = useState<number>(0)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    let reconnectTimer: NodeJS.Timeout | null = null
    let ws = __WS_SINGLETON__
    const created = !ws || ws.readyState === WebSocket.CLOSING || ws.readyState === WebSocket.CLOSED
    
    const connectWebSocket = () => {
      try {
        ws = new WebSocket(resolveWsUrl())
        __WS_SINGLETON__ = ws
        wsRef.current = ws
        
        const handleOpen = () => {
          console.log('WebSocket connected')
          // Start with hardcoded default user for paper trading
          ws!.send(JSON.stringify({ type: 'bootstrap', username: 'default', initial_capital: 10000 }))
        }
        
        const handleMessage = (e: MessageEvent) => {
          try {
            const msg = JSON.parse(e.data)
            if (msg.type === 'bootstrap_ok') {
              if (msg.user) {
                setUser(msg.user)
              }
              if (msg.account) {
                setAccount(msg.account)
              }
              // request initial snapshot
              ws!.send(JSON.stringify({ type: 'get_snapshot' }))
            } else if (msg.type === 'snapshot') {
              setOverview(msg.overview)
              setPositions(msg.positions)
              setOrders(msg.orders)
              setTrades(msg.trades || [])
              setAiDecisions(msg.ai_decisions || [])
              setAllAssetCurves(msg.all_asset_curves || [])
            } else if (msg.type === 'trades') {
              setTrades(msg.trades || [])
            } else if (msg.type === 'order_filled') {
              toast.success('Order filled')
              ws!.send(JSON.stringify({ type: 'get_snapshot' }))
            } else if (msg.type === 'order_pending') {
              toast('Order placed, waiting for fill', { icon: '⏳' })
              ws!.send(JSON.stringify({ type: 'get_snapshot' }))
            } else if (msg.type === 'user_switched') {
              toast.success(`Switched to ${msg.user.username}`)
              setUser(msg.user)
            } else if (msg.type === 'account_switched') {
              toast.success(`Switched to ${msg.account.name}`)
              setAccount(msg.account)
            } else if (msg.type === 'error') {
              console.error(msg.message)
              toast.error(msg.message || 'Order error')
            }
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err)
          }
        }
        
        const handleClose = (event: CloseEvent) => {
          console.log('WebSocket closed:', event.code, event.reason)
          __WS_SINGLETON__ = null
          if (wsRef.current === ws) wsRef.current = null
          
          // Attempt to reconnect after 3 seconds if the close wasn't intentional
          if (event.code !== 1000 && event.code !== 1001) {
            reconnectTimer = setTimeout(() => {
              console.log('Attempting to reconnect WebSocket...')
              connectWebSocket()
            }, 3000)
          }
        }
        
        const handleError = (event: Event) => {
          console.error('WebSocket error:', event)
          // Don't show toast for every error to avoid spam
          // toast.error('Connection error')
        }

        ws.addEventListener('open', handleOpen)
        ws.addEventListener('message', handleMessage)
        ws.addEventListener('close', handleClose)
        ws.addEventListener('error', handleError)
        
        return () => {
          ws?.removeEventListener('open', handleOpen)
          ws?.removeEventListener('message', handleMessage)
          ws?.removeEventListener('close', handleClose)
          ws?.removeEventListener('error', handleError)
        }
      } catch (err) {
        console.error('Failed to create WebSocket:', err)
        // Retry connection after 5 seconds
        reconnectTimer = setTimeout(connectWebSocket, 5000)
      }
    }
    
    if (created) {
      connectWebSocket()
    } else {
      wsRef.current = ws
    }

    return () => {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer)
      }
      // Don't close the socket in cleanup to avoid issues with React StrictMode
    }
  }, [])

  const placeOrder = (payload: any) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('WS not connected, cannot place order')
      toast.error('Not connected to server')
      return
    }
    try {
      wsRef.current.send(JSON.stringify({ type: 'place_order', ...payload }))
      toast('Placing order...', { icon: '📝' })
    } catch (e) {
      console.error(e)
      toast.error('Failed to send order')
    }
  }

  const switchUser = (username: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('WS not connected, cannot switch user')
      toast.error('Not connected to server')
      return
    }
    try {
      wsRef.current.send(JSON.stringify({ type: 'switch_user', username }))
      toast('Switching account...', { icon: '🔄' })
    } catch (e) {
      console.error(e)
      toast.error('Failed to switch user')
    }
  }

  const switchAccount = (accountId: number) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('WS not connected, cannot switch account')
      toast.error('Not connected to server')
      return
    }
    try {
      wsRef.current.send(JSON.stringify({ type: 'switch_account', account_id: accountId }))
      toast('Switching account...', { icon: '🔄' })
    } catch (e) {
      console.error(e)
      toast.error('Failed to switch account')
    }
  }

  const handleAccountUpdated = () => {
    // Increment refresh trigger to force AccountSelector to refresh
    setAccountRefreshTrigger(prev => prev + 1)
    
    // Also refresh the current data snapshot
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'get_snapshot' }))
    }
  }

  if (!user || !account || !overview) return <div className="p-8">Connecting to trading server...</div>

  const renderMainContent = () => {
    switch (currentPage) {
      case 'asset-curve':
        return (
          <main className="flex-1 p-6 overflow-auto">
            <AssetCurve />
          </main>
        )
      case 'comprehensive':
        return (
          <main className="flex-1 p-6 overflow-auto">
            <ComprehensiveView
              overview={overview}
              positions={positions}
              orders={orders}
              trades={trades}
              aiDecisions={aiDecisions}
              allAssetCurves={allAssetCurves}
              wsRef={wsRef}
              onSwitchUser={switchUser}
              onSwitchAccount={switchAccount}
              accountRefreshTrigger={accountRefreshTrigger}
              onRefreshData={() => {
                if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                  wsRef.current.send(JSON.stringify({ type: 'get_snapshot' }))
                }
              }}
            />
          </main>
        )
      default:
        return (
          <main className="flex-1 p-6 overflow-hidden">
            <Portfolio
              user={overview.account}
              onUserChange={switchUser}
            />
            <div className="flex gap-6 h-[calc(100vh-400px)] mt-4">
              <div className="flex-shrink-0">
                <TradingPanel
                  onPlace={placeOrder}
                  user={user}
                  account={account}
                  positions={positions.map(p => ({ symbol: p.symbol, market: p.market, available_quantity: p.available_quantity }))}
                  lastPrices={Object.fromEntries(positions.map(p => [`${p.symbol}.${p.market}`, p.last_price ?? null]))}
                />
              </div>

              <div className="flex-1 overflow-hidden">
                <Tabs defaultValue="asset" className="h-full flex flex-col">
                  <TabsList className="grid w-full grid-cols-5">
                    <TabsTrigger value="asset">Asset</TabsTrigger>
                    <TabsTrigger value="ai-decisions">AI Decisions</TabsTrigger>
                    <TabsTrigger value="positions">Positions</TabsTrigger>
                    <TabsTrigger value="orders">Orders</TabsTrigger>
                    <TabsTrigger value="trades">Trades</TabsTrigger>
                  </TabsList>

                  <div className="flex-1 overflow-hidden">
                    <TabsContent value="asset" className="h-full overflow-y-auto">
                      <div className="p-4 text-muted-foreground text-sm">
                        Asset details shown in the comprehensive view below
                      </div>
                    </TabsContent>

                    <TabsContent value="ai-decisions" className="h-full overflow-y-auto">
                      <AIDecisionLogWS aiDecisions={aiDecisions} />
                    </TabsContent>

                    <TabsContent value="positions" className="h-full overflow-y-auto">
                      <PositionListWS positions={positions} />
                    </TabsContent>

                    <TabsContent value="orders" className="h-full overflow-y-auto">
                      <OrderBookWS orders={orders} />
                    </TabsContent>

                    <TabsContent value="trades" className="h-full overflow-y-auto">
                      <TradeHistoryWS trades={trades} />
                    </TabsContent>
                  </div>
                </Tabs>
              </div>
            </div>
          </main>
        )
    }
  }

  const pageTitle = PAGE_TITLES[currentPage] ?? PAGE_TITLES.portfolio

  return (
    <div className="h-screen flex overflow-hidden">
      <Sidebar
        currentPage={currentPage}
        onPageChange={setCurrentPage}
        onAccountUpdated={handleAccountUpdated}
      />
      <div className="flex-1 flex flex-col">
        <Header
          title={pageTitle}
          currentUser={user}
          currentAccount={account}
          showAccountSelector={currentPage === 'portfolio' || currentPage === 'comprehensive'}
          onUserChange={switchUser}
        />
        {renderMainContent()}
      </div>
    </div>
  )
}


const API_BASE = resolveApiBase()

function OrderBookWS({ orders }: { orders: Order[] }) {
  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Time</TableHead><TableHead>Order No</TableHead><TableHead>Symbol</TableHead><TableHead>Side</TableHead><TableHead>Type</TableHead><TableHead>Price</TableHead><TableHead>Qty</TableHead><TableHead>Status</TableHead><TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {orders.map(o => (
            <TableRow key={o.id}>
              <TableCell>{o.id}</TableCell>
              <TableCell>{o.order_no}</TableCell>
              <TableCell>{o.symbol}.{o.market}</TableCell>
              <TableCell>{o.side}</TableCell>
              <TableCell>{o.order_type}</TableCell>
              <TableCell>{o.price ?? '-'}</TableCell>
              <TableCell>{o.quantity}</TableCell>
              <TableCell>{o.status}</TableCell>
              <TableCell>
                {o.status === 'PENDING' ? (
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={async () => {
                      try {
                        const resp = await fetch(`${API_BASE}/api/orders/cancel/${o.id}`, { method: 'POST' })
                        if (!resp.ok) throw new Error(await resp.text())
                        toast.success('Order cancelled')
                        // refresh snapshot via WS
                        const ws = (window as any).__WS_SINGLETON__ as WebSocket | undefined
                        ;(ws || (undefined as any))?.send?.(JSON.stringify({ type: 'get_snapshot' }))
                      } catch (e: any) {
                        console.error(e)
                        toast.error(e?.message || 'Cancel failed')
                      }
                    }}
                  >Cancel</Button>
                ) : null}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

function PositionListWS({ positions }: { positions: Position[] }) {
  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Symbol</TableHead><TableHead>Name</TableHead><TableHead>Qty</TableHead><TableHead>Available</TableHead><TableHead>Avg Cost</TableHead><TableHead>Last Price</TableHead><TableHead>Market Value</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {positions.map(p => (
            <TableRow key={p.id}>
              <TableCell>{p.symbol}.{p.market}</TableCell>
              <TableCell>{p.name}</TableCell>
              <TableCell>{p.quantity}</TableCell>
              <TableCell>{p.available_quantity}</TableCell>
              <TableCell>{p.avg_cost.toFixed(4)}</TableCell>
              <TableCell>{p.last_price != null ? p.last_price.toFixed(4) : '-'}</TableCell>
              <TableCell>{p.market_value != null ? `$${p.market_value.toFixed(2)}` : '-'}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

function TradeHistoryWS({ trades }: { trades: Trade[] }) {
  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Time</TableHead><TableHead>Order ID</TableHead><TableHead>Symbol</TableHead><TableHead>Side</TableHead><TableHead>Price</TableHead><TableHead>Qty</TableHead><TableHead>Commission</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {trades.map(t => (
            <TableRow key={t.id}>
              <TableCell>{new Date(t.trade_time).toLocaleString()}</TableCell>
              <TableCell>{t.order_id}</TableCell>
              <TableCell>{t.symbol}.{t.market}</TableCell>
              <TableCell>{t.side}</TableCell>
              <TableCell>{t.price.toFixed(2)}</TableCell>
              <TableCell>{t.quantity}</TableCell>
              <TableCell>{t.commission.toFixed(2)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

function AIDecisionLogWS({ aiDecisions }: { aiDecisions: AIDecision[] }) {
  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Time</TableHead>
            <TableHead>Operation</TableHead>
            <TableHead>Symbol</TableHead>
            <TableHead>Prev %</TableHead>
            <TableHead>Target %</TableHead>
            <TableHead>Balance</TableHead>
            <TableHead>Executed</TableHead>
            <TableHead>Reason</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {aiDecisions.map(d => (
            <TableRow key={d.id}>
              <TableCell>{new Date(d.decision_time).toLocaleString()}</TableCell>
              <TableCell>
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  d.operation === 'buy' ? 'bg-green-100 text-green-800' :
                  d.operation === 'sell' ? 'bg-red-100 text-red-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {d.operation.toUpperCase()}
                </span>
              </TableCell>
              <TableCell>{d.symbol || '-'}</TableCell>
              <TableCell>{(d.prev_portion * 100).toFixed(2)}%</TableCell>
              <TableCell>{(d.target_portion * 100).toFixed(2)}%</TableCell>
              <TableCell>${d.total_balance.toFixed(2)}</TableCell>
              <TableCell>
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  d.executed === 'true' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                }`}>
                  {d.executed === 'true' ? 'Yes' : 'No'}
                </span>
              </TableCell>
              <TableCell className="max-w-xs truncate" title={d.reason}>
                {d.reason}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Toaster position="top-right" />
    <App />
  </React.StrictMode>,
)
