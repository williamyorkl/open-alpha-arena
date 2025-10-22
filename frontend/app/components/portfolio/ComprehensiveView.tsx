import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { toast } from 'react-hot-toast'
import AssetCurveWithData from './AssetCurveWithData'
import AccountSelector from '@/components/layout/AccountSelector'
import { AIDecision } from '@/lib/api'

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
}

interface Position {
  id: number
  user_id: number
  symbol: string
  name: string
  market: string
  quantity: number
  available_quantity: number
  avg_cost: number
  last_price?: number | null
  market_value?: number | null
}

interface Order {
  id: number
  order_no: string
  symbol: string
  name: string
  market: string
  side: string
  order_type: string
  price?: number
  quantity: number
  filled_quantity: number
  status: string
}

interface Trade {
  id: number
  order_id: number
  user_id: number
  symbol: string
  name: string
  market: string
  side: string
  price: number
  quantity: number
  commission: number
  trade_time: string
}

const API_BASE = typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1:5611'

interface ComprehensiveViewProps {
  overview: Overview | null
  positions: Position[]
  orders: Order[]
  trades: Trade[]
  aiDecisions: AIDecision[]
  allAssetCurves: any[]
  wsRef?: React.MutableRefObject<WebSocket | null>
  onSwitchUser: (username: string) => void
  onSwitchAccount: (accountId: number) => void
  onRefreshData: () => void
}

export default function ComprehensiveView({
  overview,
  positions,
  orders,
  trades,
  aiDecisions,
  allAssetCurves,
  wsRef,
  onSwitchUser,
  onSwitchAccount,
  onRefreshData
}: ComprehensiveViewProps) {

  const switchUser = (username: string) => {
    onSwitchUser(username)
  }

  const switchAccount = (accountId: number) => {
    onSwitchAccount(accountId)
  }

  const cancelOrder = async (orderId: number) => {
    try {
      const response = await fetch(`${API_BASE}/api/orders/cancel/${orderId}`, {
        method: 'POST'
      })

      if (response.ok) {
        toast.success('Order cancelled')
        // Refresh data via parent component
        onRefreshData()
      } else {
        throw new Error(await response.text())
      }
    } catch (error) {
      console.error('Failed to cancel order:', error)
      toast.error('Failed to cancel order')
    }
  }

  if (!overview) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-muted-foreground">Loading comprehensive view...</div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col space-y-6">

      {/* Main Content */}
      <div className="grid grid-cols-5 gap-6 overflow-hidden">
        {/* Left Side - Asset Curve */}
        <div className="col-span-3">
          <AssetCurveWithData data={allAssetCurves} wsRef={wsRef} />
        </div>

        {/* Right Side - Portfolio Tabs */}
        <div className="col-span-2 overflow-hidden">
          <div className="flex justify-end mb-2">
          <AccountSelector
            currentAccount={overview.account}
            onAccountChange={switchAccount}
          />
          </div>
          <Tabs defaultValue="ai-decisions" className="h-full flex flex-col">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="positions">Positions</TabsTrigger>
              <TabsTrigger value="ai-decisions">AI Decisions</TabsTrigger>
              <TabsTrigger value="orders">Orders</TabsTrigger>
              <TabsTrigger value="trades">Trades</TabsTrigger>
            </TabsList>

            <div className="flex-1 overflow-hidden">
              <TabsContent value="positions" className="h-full overflow-y-auto">
                <PositionList positions={positions} />
              </TabsContent>

              <TabsContent value="ai-decisions" className="h-full overflow-y-auto">
                <AIDecisionLog aiDecisions={aiDecisions} />
              </TabsContent>

              <TabsContent value="orders" className="h-full overflow-y-auto">
                <OrderBook orders={orders} onCancelOrder={cancelOrder} />
              </TabsContent>

              <TabsContent value="trades" className="h-full overflow-y-auto">
                <TradeHistory trades={trades} />
              </TabsContent>
            </div>
          </Tabs>
        </div>
      </div>
    </div>
  )
}

// Order Book Component
function OrderBook({ orders, onCancelOrder }: { orders: Order[], onCancelOrder: (id: number) => void }) {
  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Time</TableHead>
            <TableHead>Order No</TableHead>
            <TableHead>Symbol</TableHead>
            <TableHead>Side</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Price</TableHead>
            <TableHead>Qty</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Actions</TableHead>
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
                    onClick={() => onCancelOrder(o.id)}
                  >
                    Cancel
                  </Button>
                ) : null}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

// Position List Component
function PositionList({ positions }: { positions: Position[] }) {
  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Symbol</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Qty</TableHead>
            <TableHead>Available</TableHead>
            <TableHead>Avg Cost</TableHead>
            <TableHead>Last Price</TableHead>
            <TableHead>Market Value</TableHead>
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

// Trade History Component
function TradeHistory({ trades }: { trades: Trade[] }) {
  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Time</TableHead>
            <TableHead>Order ID</TableHead>
            <TableHead>Symbol</TableHead>
            <TableHead>Side</TableHead>
            <TableHead>Price</TableHead>
            <TableHead>Qty</TableHead>
            <TableHead>Commission</TableHead>
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

// AI Decision Log Component
function AIDecisionLog({ aiDecisions }: { aiDecisions: AIDecision[] }) {
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