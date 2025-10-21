import React from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'

interface OrderFormProps {
  symbol: string
  name: string
  orderType: 'MARKET' | 'LIMIT'
  price: number
  quantity: number
  onSymbolChange: (symbol: string) => void
  onOrderTypeChange: (orderType: 'MARKET' | 'LIMIT') => void
  onPriceChange: (price: number) => void
  onQuantityChange: (quantity: number) => void
  onAdjustPrice: (delta: number) => void
  onAdjustQuantity: (delta: number) => void
  lastPrices?: Record<string, number | null>
}

export default function OrderForm({
  symbol,
  name,
  orderType,
  price,
  quantity,
  onSymbolChange,
  onOrderTypeChange,
  onPriceChange,
  onQuantityChange,
  onAdjustPrice,
  onAdjustQuantity,
  lastPrices = {}
}: OrderFormProps) {
  const handlePriceChange = (value: string) => {
    if (orderType === 'MARKET') return // 市价单不允许手动改价
    // 只允许数字和一个小数点
    if (!/^\d*\.?\d{0,2}$/.test(value)) return
    
    const numValue = parseFloat(value) || 0
    onPriceChange(numValue)
  }

  return (
    <div className="space-y-4">
      {/* Symbol */}
      <div className="space-y-2">
        <label className="text-xs">Code</label>
        <div className="relative">
          <Input 
            value={symbol}
            onChange={(e) => onSymbolChange(e.target.value)}
          />
        </div>
        <div className="text-xs text-muted-foreground">{name}</div>
      </div>

      {/* 订单类型 */}
      <div className="space-y-2">
        <div className="flex items-center gap-1">
          <label className="text-xs text-muted-foreground">Order Type</label>
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-info w-3 h-3 text-muted-foreground">
            <circle cx="12" cy="12" r="10"></circle>
            <path d="M12 16v-4"></path>
            <path d="M12 8h.01"></path>
          </svg>
        </div>
        <Select value={orderType} onValueChange={(v) => onOrderTypeChange(v as 'MARKET' | 'LIMIT')}>
          <SelectTrigger className="bg-input text-xs h-6">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="LIMIT">Limit Order</SelectItem>
            <SelectItem value="MARKET">Market Order</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* 价格 */}
      <div className="space-y-2">
        <label className="text-xs">Price</label>
        <div className="flex items-center gap-2">
         <Button 
            onClick={() => onAdjustPrice(-0.01)}
            variant="outline"
            disabled={orderType === 'MARKET'}
          >
            -
          </Button>
          <div className="relative flex-1">
           <Input 
              inputMode="decimal"
              value={price.toString()}
              onChange={(e) => handlePriceChange(e.target.value)}
              className="text-center"
              disabled={orderType === 'MARKET'}
            />
          </div>
         <Button 
            onClick={() => onAdjustPrice(0.01)}
            variant="outline"
            disabled={orderType === 'MARKET'}
          >
            +
          </Button>
        </div>
      </div>

      {/* 数量 */}
      <div className="space-y-2">
        <label className="text-xs">Quantity</label>
        <div className="flex items-center gap-2">
          <Button 
            onClick={() => onAdjustQuantity(-1)}
            variant="outline"
          >
            -
          </Button>
          <div className="relative flex-1">
            <Input 
              inputMode="numeric"
              value={quantity}
              onChange={(e) => onQuantityChange(parseInt(e.target.value) || 0)}
              className="text-center"
            />
          </div>
          <Button 
            onClick={() => onAdjustQuantity(1)}
            variant="outline"
          >
            +
          </Button>
        </div>
      </div>
    </div>
  )
}
