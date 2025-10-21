import React, { useEffect, useState } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

interface User {
  id: number
  username: string
  initial_capital: number
  current_cash: number
  frozen_cash: number
  has_password: boolean
}

interface UserWithAssets extends User {
  total_assets: number
  positions_value: number
}

interface AccountSelectorProps {
  currentUser: User | null
  onUserChange: (username: string) => void
}

// Use relative path to work with proxy
const API_BASE = '/api'

export default function AccountSelector({ currentUser, onUserChange }: AccountSelectorProps) {
  const [users, setUsers] = useState<UserWithAssets[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async () => {
    try {
      const response = await fetch(`${API_BASE}/account/users`)
      if (response.ok) {
        const userData: User[] = await response.json()
        console.log('Fetched users:', userData)
        
        // Fetch overview data for each user to get total_assets
        const usersWithAssets = await Promise.all(
          userData.map(async (user) => {
            try {
              const overviewResponse = await fetch(`${API_BASE}/account/overview?user_id=${user.id}`)
              if (overviewResponse.ok) {
                const overview = await overviewResponse.json()
                return {
                  ...user,
                  total_assets: overview.total_assets,
                  positions_value: overview.positions_value
                }
              }
              // Fallback if overview fails
              return {
                ...user,
                total_assets: user.current_cash + user.frozen_cash,
                positions_value: 0
              }
            } catch (error) {
              console.error(`Failed to fetch overview for user ${user.id}:`, error)
              return {
                ...user,
                total_assets: user.current_cash + user.frozen_cash,
                positions_value: 0
              }
            }
          })
        )
        
        setUsers(usersWithAssets)
      } else {
        console.error('Failed to fetch users, status:', response.status)
        const errorText = await response.text()
        console.error('Error response:', errorText)
      }
    } catch (error) {
      console.error('Error fetching users:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="w-48">
        <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
      </div>
    )
  }

  if (users.length === 0) {
    return (
      <div className="w-64">
        <div className="text-sm text-muted-foreground p-2 border rounded">
          No accounts found
        </div>
      </div>
    )
  }

  const displayName = (user: UserWithAssets) => {
    const baseName = user.username.replace('demo_', '').toUpperCase()
    return `${baseName} ($${user.total_assets.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })})`
  }

  // Find the current user in our loaded users list (which has total_assets)
  const currentUserWithAssets = currentUser 
    ? users.find(u => u.username === currentUser.username) 
    : null

  return (
    <div className="w-64">
      <Select
        value={currentUser?.username || ''}
        onValueChange={onUserChange}
      >
        <SelectTrigger className="w-full">
          <SelectValue placeholder="Select Account">
            {currentUserWithAssets ? displayName(currentUserWithAssets) : currentUser?.username || 'Select Account'}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {users.map((user) => (
            <SelectItem key={user.id} value={user.username}>
              <div className="flex flex-col">
                <span className="font-medium">{displayName(user)}</span>
                <span className="text-xs text-muted-foreground">
                  Cash: ${user.current_cash.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} | 
                  Positions: ${user.positions_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}