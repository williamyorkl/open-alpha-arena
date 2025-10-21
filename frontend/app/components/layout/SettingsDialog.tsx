import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Trash2, Plus, Pencil } from 'lucide-react'
import { 
  getDemoAccounts,
  initDemoUser,
  resetDemoAccount,
  type TradingAccount,
  type TradingAccountCreate 
} from '@/lib/api'

interface SettingsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const [accounts, setAccounts] = useState<AIAccount[]>([])
  const [loading, setLoading] = useState(false)
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [newAccount, setNewAccount] = useState<AIAccountCreate>({
    username: '',
    model: '',
    base_url: '',
    api_key: '',
  })
  const [editAccount, setEditAccount] = useState<AIAccountCreate>({
    username: '',
    model: '',
    base_url: '',
    api_key: '',
  })

  const loadAccounts = async () => {
    try {
      setLoading(true)
      const data = await getDemoAccounts("demo")
      setAccounts(data)
    } catch (error) {
      console.error('Failed to load accounts:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open) {
      loadAccounts()
    }
  }, [open])

  const handleAddAccount = async () => {
    if (!newAccount.username || !newAccount.model || !newAccount.base_url || !newAccount.api_key) {
      alert('Please fill in all fields')
      return
    }

    try {
      await createAIAccount(newAccount)
      setNewAccount({ username: '', model: '', base_url: '', api_key: '' })
      setShowAddForm(false)
      await loadAccounts()
    } catch (error) {
      console.error('Failed to create account:', error)
      alert('Failed to create account. Please check if the username already exists.')
    }
  }

  const handleEditAccount = (account: AIAccount) => {
    setEditingId(account.id)
    setEditAccount({
      username: account.username,
      model: account.model,
      base_url: account.base_url,
      api_key: account.api_key,
    })
    setShowAddForm(false)
  }

  const handleUpdateAccount = async () => {
    if (!editAccount.username || !editAccount.model || !editAccount.base_url || !editAccount.api_key) {
      alert('Please fill in all fields')
      return
    }

    if (editingId === null) return

    try {
      await updateAIAccount(editingId, editAccount)
      setEditingId(null)
      setEditAccount({ username: '', model: '', base_url: '', api_key: '' })
      await loadAccounts()
    } catch (error) {
      console.error('Failed to update account:', error)
      alert('Failed to update account. Please check if the username already exists.')
    }
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setEditAccount({ username: '', model: '', base_url: '', api_key: '' })
  }

  const handleDeleteAccount = async (id: number) => {
    if (!confirm('Are you sure you want to delete this account?')) {
      return
    }

    try {
      await deleteAIAccount(id)
      await loadAccounts()
    } catch (error: any) {
      console.error('Failed to delete account:', error)
      const errorMessage = error.message || 'Failed to delete account'
      alert(errorMessage)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>AI Trader Accounts</DialogTitle>
          <DialogDescription>
            Manage your AI trader accounts. Each account has its own portfolio and AI model configuration.
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          {/* Account List */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium">Accounts</h3>
              <Button
                size="sm"
                onClick={() => setShowAddForm(!showAddForm)}
                variant="outline"
              >
                <Plus className="w-4 h-4 mr-1" />
                Add Account
              </Button>
            </div>

            {loading ? (
              <p className="text-sm text-muted-foreground">Loading...</p>
            ) : accounts.length === 0 ? (
              <p className="text-sm text-muted-foreground">No accounts configured</p>
            ) : (
              <div className="space-y-2">
                {accounts.map((account) => (
                  editingId === account.id ? (
                    <div key={account.id} className="space-y-3 p-4 border rounded-lg bg-muted/50">
                      <h4 className="text-sm font-medium">Edit Account</h4>
                      <Input
                        placeholder="Account Name (e.g., GPT, Claude)"
                        value={editAccount.username}
                        onChange={(e) =>
                          setEditAccount({ ...editAccount, username: e.target.value })
                        }
                      />
                      <Input
                        placeholder="Model (e.g., gpt-4, claude-3)"
                        value={editAccount.model}
                        onChange={(e) =>
                          setEditAccount({ ...editAccount, model: e.target.value })
                        }
                      />
                      <Input
                        placeholder="Base URL (e.g., https://api.openai.com/v1)"
                        value={editAccount.base_url}
                        onChange={(e) =>
                          setEditAccount({ ...editAccount, base_url: e.target.value })
                        }
                      />
                      <Input
                        placeholder="API Key"
                        type="password"
                        value={editAccount.api_key}
                        onChange={(e) =>
                          setEditAccount({ ...editAccount, api_key: e.target.value })
                        }
                      />
                      <div className="flex gap-2">
                        <Button onClick={handleUpdateAccount} className="flex-1">
                          Update Account
                        </Button>
                        <Button
                          variant="outline"
                          onClick={handleCancelEdit}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div
                      key={account.id}
                      className="flex items-start justify-between p-3 border rounded-lg"
                    >
                      <div className="flex-1 space-y-1">
                        <div className="font-medium text-sm">{account.username}</div>
                        <div className="text-xs text-muted-foreground">
                          Model: {account.model}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Balance: ${account.current_cash.toFixed(2)} / ${account.initial_capital.toFixed(2)}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          API Key: {account.api_key.slice(0, 10)}...
                        </div>
                      </div>
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleEditAccount(account)}
                        >
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleDeleteAccount(account.id)}
                        >
                          <Trash2 className="w-4 h-4 text-destructive" />
                        </Button>
                      </div>
                    </div>
                  )
                ))}
              </div>
            )}
          </div>

          {/* Add Account Form */}
          {showAddForm && (
            <div className="space-y-3 p-4 border rounded-lg bg-muted/50">
              <h4 className="text-sm font-medium">Add New Account</h4>
              <Input
                placeholder="Account Name (e.g., GPT, Claude)"
                value={newAccount.username}
                onChange={(e) =>
                  setNewAccount({ ...newAccount, username: e.target.value })
                }
              />
              <Input
                placeholder="Model (e.g., gpt-4, claude-3)"
                value={newAccount.model}
                onChange={(e) =>
                  setNewAccount({ ...newAccount, model: e.target.value })
                }
              />
              <Input
                placeholder="Base URL (e.g., https://api.openai.com/v1)"
                value={newAccount.base_url}
                onChange={(e) =>
                  setNewAccount({ ...newAccount, base_url: e.target.value })
                }
              />
              <Input
                placeholder="API Key"
                type="password"
                value={newAccount.api_key}
                onChange={(e) =>
                  setNewAccount({ ...newAccount, api_key: e.target.value })
                }
              />
              <div className="flex gap-2">
                <Button onClick={handleAddAccount} className="flex-1">
                  Add Account
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowAddForm(false)
                    setNewAccount({ username: '', model: '', base_url: '', api_key: '' })
                  }}
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}