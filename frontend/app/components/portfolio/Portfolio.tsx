import AccountSelector from '@/components/layout/AccountSelector'

interface User {
  id: number
  username: string
  initial_capital: number
  current_cash: number
  frozen_cash: number
  has_password: boolean
}

interface PortfolioProps {
  user: User
  onUserChange?: (username: string) => void
}

export default function Portfolio({
  user,
  onUserChange
}: PortfolioProps) {
  return (
    <div className="space-y-6">
      {/* Account Selector */}
      {onUserChange && (
        <div className="flex justify-end">
          <AccountSelector
            currentUser={user}
            onUserChange={onUserChange}
          />
        </div>
      )}
    </div>
  )
}