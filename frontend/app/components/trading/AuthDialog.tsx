import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { toast } from 'react-hot-toast'

interface User {
  current_cash: number
  frozen_cash: number
  has_password: boolean
  id?: string
}

interface AuthDialogProps {
  isOpen: boolean
  pendingTrade: { side: 'BUY' | 'SELL' } | null
  user?: User
  onClose: () => void
  onAuthenticate: (sessionToken: string, orderData: any) => void
  orderData: {
    symbol: string
    name: string
    market: string
    side: 'BUY' | 'SELL'
    order_type: 'MARKET' | 'LIMIT'
    price?: number
    quantity: number
  }
}

export default function AuthDialog({
  isOpen,
  pendingTrade,
  user,
  onClose,
  onAuthenticate,
  orderData
}: AuthDialogProps) {
  const [dialogPassword, setDialogPassword] = useState<string>('')
  const [dialogUsername, setDialogUsername] = useState<string>('')

  const handlePasswordSubmit = async () => {
    if (!dialogPassword.trim()) {
      toast.error('Please enter trading password')
      return
    }

    if (!dialogUsername.trim()) {
      toast.error('Please enter username')
      return
    }

    if (!pendingTrade) return

    try {
      // 写死功能：认证成功后自动创建180天免密会话
      const response = await fetch(`/api/account/auth/login?user_id=${user?.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          username: dialogUsername, 
          password: dialogPassword 
        })
      })
      const data = await response.json()
      
      if (response.ok) {
        // 保存180天认证会话
        const sessionToken = data.session_token
        
        // 保存到本地存储
        if (user?.id) {
          localStorage.setItem(`auth_session_${user.id}`, data.session_token)
          localStorage.setItem(`auth_expiry_${user.id}`, data.expires_at)
        }
        
        toast.success('认证成功，180天内免密交易')
        
        // 使用session token执行交易
        const finalOrderData = {
          ...orderData,
          session_token: sessionToken
        }

        onAuthenticate(sessionToken, finalOrderData)
      } else {
        toast.error(data.detail || '用户名或密码错误')
      }
    } catch (error) {
      console.error('Failed to authenticate:', error)
      toast.error('认证失败，请重试')
    } finally {
      // Close dialog and reset state
      handleClose()
    }
  }

  const handleClose = () => {
    onClose()
    setDialogPassword('')
    setDialogUsername('')
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-background rounded-lg p-6 w-80 max-w-sm mx-4">
        <h3 className="text-lg font-semibold mb-4">
          确认交易 - {pendingTrade?.side === 'BUY' ? '买入' : '卖出'}
        </h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              用户名
            </label>
            <Input
              type="text"
              value={dialogUsername}
              onChange={(e) => setDialogUsername(e.target.value)}
              placeholder="输入用户名"
              className="w-full"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              交易密码
            </label>
            <Input
              type="password"
              value={dialogPassword}
              onChange={(e) => setDialogPassword(e.target.value)}
              placeholder={user?.has_password ? "输入交易密码" : "设置新的交易密码"}
              className="w-full"
            />
            <div className="text-xs text-gray-500 mt-1">
              {user?.has_password 
                ? "输入已设置的交易密码" 
                : "首次交易将设置此密码为交易密码"
              }
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <Button
              variant="outline"
              onClick={handleClose}
              className="flex-1"
            >
              取消
            </Button>
            <Button
              onClick={handlePasswordSubmit}
              disabled={!dialogPassword.trim() || !dialogUsername.trim()}
              className="flex-1"
            >
              确认交易
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
