# 🛡️ Risk Management System

## Overview

The risk management system provides comprehensive protection against financial loss through position sizing, loss limits, emergency controls, and real-time monitoring. This is the most critical component for real trading safety.

## Risk Management Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Order Input   │───▶│   Risk Manager  │───▶│   Decision      │
│                 │    │                 │    │   (Allow/Block) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │
                    ┌─────────────────┐
                    │   Risk Metrics  │
                    │   - Position    │
                    │   - Daily P&L    │
                    │   - Exposure    │
                    └─────────────────┘
```

## Core Risk Management Implementation

### 1. Advanced Risk Manager

```python
# backend/services/risk_manager.py
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from database.models import Account, Trade, Position, Order, RiskLog

logger = logging.getLogger(__name__)

class RiskManager:
    """
    Comprehensive risk management system with multiple layers of protection
    """

    def __init__(self, account: Account, db: Session):
        self.account = account
        self.db = db
        self.risk_limits = self._load_risk_limits()
        self.current_metrics = self._calculate_current_metrics()

    def _load_risk_limits(self) -> Dict[str, Decimal]:
        """Load risk limits from account configuration"""
        return {
            'max_position_size': Decimal(str(self.account.max_position_size or 1000.0)),
            'max_daily_loss': Decimal(str(self.account.max_daily_loss or 100.0)),
            'max_positions': int(self.account.max_positions or 5),
            'max_leverage': Decimal(str(self.account.max_leverage or 1.0)),
            'max_portfolio_risk': Decimal('0.02'),  # 2% max portfolio risk
            'max_correlation': Decimal('0.7'),        # 70% max correlation
        }

    def _calculate_current_metrics(self) -> Dict[str, Decimal]:
        """Calculate current risk metrics"""
        try:
            # Get current positions
            positions = self.db.query(Position).filter(
                Position.account_id == self.account.id,
                Position.quantity > 0
            ).all()

            # Calculate total exposure
            total_exposure = Decimal('0')
            position_count = len(positions)
            daily_pnl = self._calculate_daily_pnl()

            for position in positions:
                # Get current price
                from .market_data import get_last_price
                current_price = Decimal(str(get_last_price(position.symbol)))
                position_value = Decimal(str(position.quantity)) * current_price
                total_exposure += position_value

            # Calculate available balance
            available_balance = Decimal(str(self.account.current_cash))

            return {
                'total_exposure': total_exposure,
                'available_balance': available_balance,
                'position_count': position_count,
                'daily_pnl': daily_pnl,
                'total_balance': total_exposure + available_balance,
            }

        except Exception as e:
            logger.error(f"Failed to calculate current metrics: {e}")
            return {
                'total_exposure': Decimal('0'),
                'available_balance': Decimal('0'),
                'position_count': 0,
                'daily_pnl': Decimal('0'),
                'total_balance': Decimal('0'),
            }

    def can_place_order(self, symbol: str, side: str, quantity: float,
                        price: Optional[float] = None) -> Tuple[bool, str]:
        """
        Comprehensive order validation with multiple risk checks

        Returns:
            Tuple of (can_place_order, reason_if_blocked)
        """
        try:
            # 1. Emergency stop check
            if self.account.emergency_stop == "true":
                return False, "Emergency stop is activated"

            # 2. Trading enabled check
            if self.account.trading_enabled != "true":
                return False, "Trading is not enabled for this account"

            # 3. Testnet mode enforcement
            if self.account.testnet_mode != "true":
                self._log_risk_event("LIVE_TRADING_ATTEMPT", "CRITICAL",
                                   "Attempted live trading - blocked for safety")
                return False, "Live trading is disabled - testnet mode required"

            # 4. Basic order validation
            if quantity <= 0:
                return False, "Order quantity must be greater than 0"

            if price is not None and price <= 0:
                return False, "Order price must be greater than 0"

            # 5. Position size check
            if price:
                position_value = Decimal(str(quantity * price))
                if position_value > self.risk_limits['max_position_size']:
                    return False, f"Position size ${position_value} exceeds limit ${self.risk_limits['max_position_size']}"

            # 6. Daily loss limit check
            daily_loss = abs(self.current_metrics['daily_pnl'])
            if daily_loss > self.risk_limits['max_daily_loss']:
                return False, f"Daily loss ${daily_loss} exceeds limit ${self.risk_limits['max_daily_loss']}"

            # 7. Maximum positions check
            if side.upper() == "BUY":
                # Check if this would exceed max positions
                current_positions = self.current_metrics['position_count']

                # Check if we already have this position
                existing_position = self.db.query(Position).filter(
                    Position.account_id == self.account.id,
                    Position.symbol == symbol,
                    Position.quantity > 0
                ).first()

                if not existing_position and current_positions >= self.risk_limits['max_positions']:
                    return False, f"Maximum positions ({self.risk_limits['max_positions']}) would be exceeded"

            # 8. Portfolio risk check
            if price and not self._check_portfolio_risk(symbol, quantity, price):
                return False, "Portfolio risk limits would be exceeded"

            # 9. Correlation check (for new positions)
            if side.upper() == "BUY" and price:
                if not self._check_correlation_risk(symbol):
                    return False, "Correlation risk limits would be exceeded"

            # 10. Available balance check
            if side.upper() == "BUY" and price:
                required_amount = Decimal(str(quantity * price))
                if required_amount > self.current_metrics['available_balance']:
                    return False, f"Insufficient balance: need ${required_amount}, available ${self.current_metrics['available_balance']}"

            # All checks passed
            return True, "All risk checks passed"

        except Exception as e:
            logger.error(f"Risk check failed: {e}")
            return False, f"Risk check error: {str(e)}"

    def _check_portfolio_risk(self, symbol: str, quantity: float, price: float) -> bool:
        """Check if new position would exceed portfolio risk limits"""
        try:
            position_value = Decimal(str(quantity * price))
            total_portfolio_value = self.current_metrics['total_balance']

            if total_portfolio_value <= 0:
                return False  # No portfolio value to measure against

            # Calculate position as percentage of portfolio
            position_percentage = position_value / total_portfolio_value

            # Check against max position risk (default 2% per position)
            if position_percentage > self.risk_limits['max_portfolio_risk']:
                self._log_risk_event("POSITION_SIZE_LIMIT", "HIGH",
                                   f"Position {position_percentage:.2%} exceeds limit {self.risk_limits['max_portfolio_risk']:.2%}")
                return False

            return True

        except Exception as e:
            logger.error(f"Portfolio risk check failed: {e}")
            return False

    def _check_correlation_risk(self, symbol: str) -> bool:
        """Check correlation risk with existing positions"""
        try:
            # Get existing positions
            existing_positions = self.db.query(Position).filter(
                Position.account_id == self.account.id,
                Position.quantity > 0
            ).all()

            if not existing_positions:
                return True  # No existing positions, no correlation risk

            # Simplified correlation check based on asset classes
            # In production, you'd use actual correlation coefficients
            asset_classes = {
                'BTC': 'large_cap_crypto',
                'ETH': 'large_cap_crypto',
                'SOL': 'defi_token',
                'DOGE': 'meme_coin',
                'XRP': 'payment_token',
                'BNB': 'exchange_token',
            }

            new_asset_class = asset_classes.get(symbol, 'other')

            # Count positions in same asset class
            same_class_positions = 0
            for position in existing_positions:
                position_class = asset_classes.get(position.symbol, 'other')
                if position_class == new_asset_class:
                    same_class_positions += 1

            # If more than 70% of positions are in the same class, block
            if len(existing_positions) > 0:
                same_class_percentage = same_class_positions / len(existing_positions)
                if same_class_percentage > Decimal('0.7'):
                    self._log_risk_event("CORRELATION_LIMIT", "MEDIUM",
                                       f"High correlation risk: {same_class_percentage:.2%} in same asset class")
                    return False

            return True

        except Exception as e:
            logger.error(f"Correlation risk check failed: {e}")
            return True  # Default to allow on error

    def _calculate_daily_pnl(self) -> Decimal:
        """Calculate daily profit/loss"""
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            # Get today's trades
            today_trades = self.db.query(Trade).filter(
                Trade.account_id == self.account.id,
                Trade.trade_time >= today_start
            ).all()

            daily_pnl = Decimal('0')
            for trade in today_trades:
                if trade.side == "SELL":
                    # Realized PnL for sells (simplified)
                    # In production, this would account for cost basis
                    daily_pnl += Decimal(str(trade.price * trade.quantity)) - Decimal(str(trade.commission))
                else:
                    # Buy trades reduce available cash (cost)
                    daily_pnl -= Decimal(str(trade.price * trade.quantity)) + Decimal(str(trade.commission))

            return daily_pnl

        except Exception as e:
            logger.error(f"Failed to calculate daily PnL: {e}")
            return Decimal('0')

    def get_risk_metrics(self) -> Dict:
        """Get comprehensive risk metrics"""
        return {
            'account_id': self.account.id,
            'risk_limits': {
                'max_position_size': float(self.risk_limits['max_position_size']),
                'max_daily_loss': float(self.risk_limits['max_daily_loss']),
                'max_positions': self.risk_limits['max_positions'],
                'max_leverage': float(self.risk_limits['max_leverage']),
            },
            'current_metrics': {
                'total_exposure': float(self.current_metrics['total_exposure']),
                'available_balance': float(self.current_metrics['available_balance']),
                'position_count': self.current_metrics['position_count'],
                'daily_pnl': float(self.current_metrics['daily_pnl']),
                'total_balance': float(self.current_metrics['total_balance']),
            },
            'risk_status': {
                'emergency_stop': self.account.emergency_stop == "true",
                'trading_enabled': self.account.trading_enabled == "true",
                'testnet_mode': self.account.testnet_mode == "true",
                'daily_loss_used_percent': min(
                    100.0,
                    (abs(self.current_metrics['daily_pnl']) / self.risk_limits['max_daily_loss']) * 100
                ) if self.risk_limits['max_daily_loss'] > 0 else 0.0,
            }
        }

    def activate_emergency_stop(self, reason: str, source: str = "MANUAL") -> bool:
        """Activate emergency stop - IMMEDIATELY HALT ALL TRADING"""
        try:
            self.account.emergency_stop = "true"
            self.db.commit()

            # Log the emergency event
            self._log_risk_event("EMERGENCY_STOP", "CRITICAL",
                               f"Emergency stop activated: {reason} (Source: {source})")

            logger.critical(f"EMERGENCY STOP ACTIVATED for account {self.account.id}: {reason}")

            # Cancel all open orders
            self._cancel_all_orders()

            return True

        except Exception as e:
            logger.error(f"Failed to activate emergency stop: {e}")
            return False

    def _cancel_all_orders(self):
        """Cancel all open orders"""
        try:
            open_orders = self.db.query(Order).filter(
                Order.account_id == self.account.id,
                Order.status.in_(["SUBMITTED", "PARTIALLY_FILLED"])
            ).all()

            for order in open_orders:
                order.status = "CANCELLED"
                order.updated_at = datetime.utcnow()

            self.db.commit()
            logger.info(f"Cancelled {len(open_orders)} orders due to emergency stop")

        except Exception as e:
            logger.error(f"Failed to cancel orders during emergency stop: {e}")

    def _log_risk_event(self, event_type: str, severity: str, message: str):
        """Log risk management events"""
        try:
            risk_log = RiskLog(
                account_id=self.account.id,
                event_type=event_type,
                event_severity=severity,
                event_message=message,
                current_position_size=float(self.current_metrics['total_exposure']),
                current_daily_loss=float(abs(self.current_metrics['daily_pnl'])),
                available_balance=float(self.current_metrics['available_balance']),
                total_exposure=float(self.current_metrics['total_exposure']),
                action_taken="ORDER_BLOCKED" if "LIMIT" in event_type else "ALERT_SENT"
            )

            self.db.add(risk_log)
            self.db.commit()

        except Exception as e:
            logger.error(f"Failed to log risk event: {e}")

class RiskMonitor:
    """Monitor risk metrics in real-time"""

    def __init__(self, db: Session):
        self.db = db

    def check_all_accounts_risk(self) -> Dict:
        """Check risk metrics for all active trading accounts"""
        results = {
            'accounts_checked': 0,
            'warnings': [],
            'critical_alerts': [],
            'emergency_stops': []
        }

        accounts = self.db.query(Account).filter(
            Account.trading_mode == "LIVE",
            Account.trading_enabled == "true"
        ).all()

        for account in accounts:
            try:
                risk_manager = RiskManager(account, self.db)
                metrics = risk_manager.get_risk_metrics()

                results['accounts_checked'] += 1

                # Check for critical conditions
                if metrics['risk_status']['daily_loss_used_percent'] >= 100:
                    results['critical_alerts'].append({
                        'account_id': account.id,
                        'account_name': account.name,
                        'issue': 'Daily loss limit exceeded',
                        'severity': 'CRITICAL'
                    })

                # Check for warnings
                if metrics['risk_status']['daily_loss_used_percent'] >= 80:
                    results['warnings'].append({
                        'account_id': account.id,
                        'account_name': account.name,
                        'issue': f"Daily loss usage at {metrics['risk_status']['daily_loss_used_percent']:.1f}%",
                        'severity': 'WARNING'
                    })

                if metrics['risk_status']['emergency_stop']:
                    results['emergency_stops'].append({
                        'account_id': account.id,
                        'account_name': account.name,
                        'issue': 'Emergency stop is active',
                        'severity': 'CRITICAL'
                    })

            except Exception as e:
                logger.error(f"Failed to check risk for account {account.id}: {e}")

        return results

    def get_risk_summary(self, account_id: int) -> Dict:
        """Get comprehensive risk summary for an account"""
        try:
            account = self.db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return {'error': 'Account not found'}

            risk_manager = RiskManager(account, self.db)
            metrics = risk_manager.get_risk_metrics()

            # Get recent risk events
            recent_events = self.db.query(RiskLog).filter(
                RiskLog.account_id == account_id,
                RiskLog.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).order_by(RiskLog.created_at.desc()).limit(10).all()

            return {
                'metrics': metrics,
                'recent_events': [
                    {
                        'event_type': event.event_type,
                        'severity': event.event_severity,
                        'message': event.event_message,
                        'created_at': event.created_at
                    }
                    for event in recent_events
                ],
                'recommendations': self._generate_risk_recommendations(metrics, recent_events)
            }

        except Exception as e:
            logger.error(f"Failed to get risk summary: {e}")
            return {'error': str(e)}

    def _generate_risk_recommendations(self, metrics: Dict, events: List) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []

        # Check daily loss usage
        daily_loss_usage = metrics['risk_status']['daily_loss_used_percent']
        if daily_loss_usage > 50:
            recommendations.append("Consider reducing position sizes - daily loss limit usage is high")

        # Check position count
        position_count = metrics['current_metrics']['position_count']
        max_positions = metrics['risk_limits']['max_positions']
        if position_count >= max_positions * 0.8:
            recommendations.append("Approaching maximum position limit - consider consolidating positions")

        # Check recent critical events
        critical_events = [e for e in events if e.event_severity == 'CRITICAL']
        if critical_events:
            recommendations.append("Recent critical risk events detected - review trading strategy")

        # Check emergency stop
        if metrics['risk_status']['emergency_stop']:
            recommendations.append("Emergency stop is active - investigate and resolve before trading")

        return recommendations
```

### 2. Position Sizing Calculator

```python
# backend/services/position_sizing.py
import logging
from decimal import Decimal
from typing import Dict, Optional
from database.models import Account

logger = logging.getLogger(__name__)

class PositionSizer:
    """Calculate optimal position sizes based on risk management rules"""

    def __init__(self, account: Account):
        self.account = account
        self.max_risk_per_trade = Decimal('0.01')  # 1% risk per trade
        self.max_portfolio_risk = Decimal('0.02')  # 2% max portfolio risk per position

    def calculate_position_size(self, symbol: str, entry_price: float,
                              stop_loss_price: Optional[float] = None,
                              risk_amount: Optional[float] = None) -> Dict:
        """
        Calculate optimal position size based on risk parameters

        Args:
            symbol: Trading symbol
            entry_price: Expected entry price
            stop_loss_price: Stop loss price (optional)
            risk_amount: Maximum risk amount in USD (optional)

        Returns:
            Dictionary with position size recommendations
        """
        try:
            entry_price = Decimal(str(entry_price))
            account_balance = Decimal(str(self.account.current_cash))

            # Default risk amounts if not provided
            if risk_amount is None:
                risk_amount = account_balance * self.max_risk_per_trade
            else:
                risk_amount = Decimal(str(risk_amount))

            # Calculate position size based on stop loss
            if stop_loss_price:
                stop_loss_price = Decimal(str(stop_loss_price))
                risk_per_share = abs(entry_price - stop_loss_price)

                if risk_per_share > 0:
                    # Position size = Risk Amount / Risk per Share
                    position_shares = risk_amount / risk_per_share
                    position_value = position_shares * entry_price
                else:
                    # No stop loss provided or invalid
                    position_shares = Decimal('0')
                    position_value = Decimal('0')
            else:
                # No stop loss - use fixed percentage of portfolio
                position_value = account_balance * self.max_portfolio_risk
                position_shares = position_value / entry_price if entry_price > 0 else Decimal('0')

            # Apply maximum position size limit
            max_position_value = Decimal(str(self.account.max_position_size or 1000.0))
            if position_value > max_position_value:
                position_value = max_position_value
                position_shares = position_value / entry_price if entry_price > 0 else Decimal('0')

            # Calculate risk metrics
            actual_risk_amount = position_shares * abs(entry_price - (stop_loss_price or entry_price))
            portfolio_percentage = (position_value / account_balance) * 100 if account_balance > 0 else 0

            return {
                'symbol': symbol,
                'recommended_shares': float(position_shares),
                'recommended_value': float(position_value),
                'risk_per_share': float(risk_per_share) if stop_loss_price else 0.0,
                'total_risk_amount': float(actual_risk_amount),
                'portfolio_percentage': float(portfolio_percentage),
                'risk_percentage': float((actual_risk_amount / account_balance) * 100) if account_balance > 0 else 0.0,
                'within_limits': position_value <= max_position_value and actual_risk_amount <= risk_amount,
                'warnings': self._generate_sizing_warnings(position_value, actual_risk_amount, account_balance)
            }

        except Exception as e:
            logger.error(f"Failed to calculate position size: {e}")
            return {
                'error': str(e),
                'recommended_shares': 0.0,
                'recommended_value': 0.0,
                'within_limits': False
            }

    def _generate_sizing_warnings(self, position_value: Decimal, risk_amount: Decimal,
                                 account_balance: Decimal) -> List[str]:
        """Generate warnings for position sizing"""
        warnings = []

        # Check position size limit
        max_position = Decimal(str(self.account.max_position_size or 1000.0))
        if position_value >= max_position * 0.9:
            warnings.append(f"Position size is near maximum limit (${max_position})")

        # Check portfolio concentration
        portfolio_percentage = (position_value / account_balance) * 100 if account_balance > 0 else 0
        if portfolio_percentage > 10:
            warnings.append(f"Position represents {portfolio_percentage:.1f}% of portfolio - consider reducing size")

        # Check risk amount
        max_risk = account_balance * self.max_risk_per_trade
        if risk_amount > max_risk:
            warnings.append(f"Risk amount exceeds recommended {self.max_risk_per_trade:.1%} of portfolio")

        # Check available balance
        if position_value > account_balance:
            warnings.append("Position size exceeds available balance")

        return warnings

    def calculate_portfolio_heat(self, positions: Dict[str, float]) -> Dict:
        """
        Calculate portfolio heat (total exposure across all positions)

        Args:
            positions: Dictionary of symbol -> position_value

        Returns:
            Portfolio heat metrics
        """
        try:
            account_balance = Decimal(str(self.account.current_cash))
            total_exposure = sum(Decimal(str(value)) for value in positions.values())
            portfolio_heat = (total_exposure / account_balance) if account_balance > 0 else 0

            # Risk assessment based on portfolio heat
            if portfolio_heat <= 0.5:
                risk_level = "LOW"
            elif portfolio_heat <= 0.8:
                risk_level = "MEDIUM"
            elif portfolio_heat <= 1.0:
                risk_level = "HIGH"
            else:
                risk_level = "CRITICAL"

            return {
                'total_exposure': float(total_exposure),
                'account_balance': float(account_balance),
                'portfolio_heat_percentage': float(portfolio_heat * 100),
                'risk_level': risk_level,
                'recommended_max_exposure': float(account_balance * 0.8),  # 80% max recommended
                'warnings': self._generate_portfolio_warnings(portfolio_heat, positions)
            }

        except Exception as e:
            logger.error(f"Failed to calculate portfolio heat: {e}")
            return {'error': str(e)}

    def _generate_portfolio_warnings(self, portfolio_heat: Decimal, positions: Dict) -> List[str]:
        """Generate portfolio-level warnings"""
        warnings = []

        if portfolio_heat > 1.0:
            warnings.append("Portfolio heat exceeds 100% - immediate risk of margin call")
        elif portfolio_heat > 0.9:
            warnings.append("Portfolio heat is very high (>90%) - consider reducing positions")
        elif portfolio_heat > 0.8:
            warnings.append("Portfolio heat is high (>80%) - monitor closely")

        # Check position concentration
        if positions:
            max_position_value = max(Decimal(str(value)) for value in positions.values())
            account_balance = Decimal(str(self.account.current_cash))
            max_position_percentage = (max_position_value / account_balance) * 100 if account_balance > 0 else 0

            if max_position_percentage > 25:
                warnings.append(f"Largest position represents {max_position_percentage:.1f}% of portfolio")

        return warnings
```

### 3. Stop Loss and Take Profit Manager

```python
# backend/services/sltp_manager.py
import logging
from decimal import Decimal
from datetime import datetime
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from database.models import Account, Order, Position

logger = logging.getLogger(__name__)

class SLTPManager:
    """Manage Stop Loss and Take Profit orders"""

    def __init__(self, account: Account, db: Session):
        self.account = account
        self.db = db
        self.default_stop_loss_pct = Decimal('0.05')  # 5% default stop loss
        self.default_take_profit_pct = Decimal('0.10')  # 10% default take profit

    def create_sl_tp_orders(self, parent_order: Order, stop_loss_price: Optional[float] = None,
                           take_profit_price: Optional[float] = None) -> Dict:
        """
        Create stop loss and take profit orders for a position

        Args:
            parent_order: The original order that opened the position
            stop_loss_price: Stop loss price (optional)
            take_profit_price: Take profit price (optional)

        Returns:
            Dictionary with created order information
        """
        try:
            created_orders = []

            # Calculate default prices if not provided
            if not stop_loss_price and not take_profit_price:
                entry_price = Decimal(str(parent_order.price or 0))
                if entry_price > 0:
                    if parent_order.side.upper() == "BUY":
                        default_stop = entry_price * (1 - self.default_stop_loss_pct)
                        default_tp = entry_price * (1 + self.default_take_profit_pct)
                    else:  # SELL
                        default_stop = entry_price * (1 + self.default_stop_loss_pct)
                        default_tp = entry_price * (1 - self.default_take_profit_pct)

                    stop_loss_price = float(default_stop) if not stop_loss_price else stop_loss_price
                    take_profit_price = float(default_tp) if not take_profit_price else take_profit_price

            # Create stop loss order
            if stop_loss_price:
                sl_order = self._create_stop_order(parent_order, stop_loss_price, "STOP_LOSS")
                if sl_order:
                    created_orders.append({'type': 'STOP_LOSS', 'order': sl_order})

            # Create take profit order
            if take_profit_price:
                tp_order = self._create_stop_order(parent_order, take_profit_price, "TAKE_PROFIT")
                if tp_order:
                    created_orders.append({'type': 'TAKE_PROFIT', 'order': tp_order})

            return {
                'success': True,
                'created_orders': created_orders,
                'parent_order_id': parent_order.id
            }

        except Exception as e:
            logger.error(f"Failed to create SL/TP orders: {e}")
            return {'success': False, 'error': str(e)}

    def _create_stop_order(self, parent_order: Order, trigger_price: float,
                           order_type: str) -> Optional[Order]:
        """Create a stop loss or take profit order"""
        try:
            # Determine order side
            if parent_order.side.upper() == "BUY":
                # For long positions, SL is a SELL order
                sl_side = "SELL" if order_type == "STOP_LOSS" else "SELL"
            else:
                # For short positions, SL is a BUY order
                sl_side = "BUY" if order_type == "STOP_LOSS" else "BUY"

            stop_order = Order(
                account_id=self.account.id,
                order_no=f"{order_type}_{parent_order.order_no}_{datetime.utcnow().timestamp()}",
                symbol=parent_order.symbol,
                name=parent_order.name,
                market=parent_order.market,
                side=sl_side,
                order_type="STOP",
                price=trigger_price,
                quantity=parent_order.quantity,
                filled_quantity=0,
                status="PENDING",
                parent_order_id=parent_order.id,
                created_by="sltp_manager"
            )

            self.db.add(stop_order)
            self.db.commit()
            self.db.refresh(stop_order)

            logger.info(f"Created {order_type} order: {stop_order.order_no} at ${trigger_price}")
            return stop_order

        except Exception as e:
            logger.error(f"Failed to create stop order: {e}")
            self.db.rollback()
            return None

    def check_stop_orders(self) -> List[Dict]:
        """Check if any stop orders should be triggered"""
        try:
            from .market_data import get_last_price

            triggered_orders = []

            # Get all pending stop orders
            stop_orders = self.db.query(Order).filter(
                Order.account_id == self.account.id,
                Order.order_type == "STOP",
                Order.status == "PENDING"
            ).all()

            for order in stop_orders:
                try:
                    current_price = get_last_price(order.symbol)

                    should_trigger = False
                    if order.side.upper() == "SELL":
                        # Stop loss for long position - trigger if price <= stop price
                        if current_price <= float(order.price):
                            should_trigger = True
                    else:
                        # Stop loss for short position - trigger if price >= stop price
                        if current_price >= float(order.price):
                            should_trigger = True

                    if should_trigger:
                        # Convert to market order and execute
                        result = self._execute_stop_order(order, current_price)
                        triggered_orders.append(result)

                except Exception as e:
                    logger.error(f"Failed to check stop order {order.id}: {e}")

            return triggered_orders

        except Exception as e:
            logger.error(f"Failed to check stop orders: {e}")
            return []

    def _execute_stop_order(self, stop_order: Order, market_price: float) -> Dict:
        """Execute a triggered stop order at market price"""
        try:
            from .exchange_trader import ExchangeTrader

            trader = ExchangeTrader(self.account, self.db)

            # Determine original order side
            if stop_order.side.upper() == "SELL":
                # Close long position
                trade_side = "SELL"
            else:
                # Close short position
                trade_side = "BUY"

            # Execute market order
            result = trader.create_market_order(
                stop_order.symbol,
                trade_side,
                float(stop_order.quantity)
            )

            # Update stop order status
            if result.get('success'):
                stop_order.status = "TRIGGERED"
                stop_order.filled_price = market_price
                stop_order.fill_timestamp = datetime.utcnow()
                self.db.commit()

                logger.info(f"Stop order triggered: {stop_order.order_no} at ${market_price}")
                return {
                    'success': True,
                    'stop_order_id': stop_order.id,
                    'execution_price': market_price,
                    'execution_order_id': result.get('order_id')
                }
            else:
                return {
                    'success': False,
                    'stop_order_id': stop_order.id,
                    'error': result.get('error')
                }

        except Exception as e:
            logger.error(f"Failed to execute stop order: {e}")
            return {
                'success': False,
                'stop_order_id': stop_order.id,
                'error': str(e)
            }

    def cancel_related_orders(self, parent_order_id: int) -> bool:
        """Cancel SL/TP orders when parent order is cancelled"""
        try:
            # Find related stop orders
            stop_orders = self.db.query(Order).filter(
                Order.parent_order_id == parent_order_id,
                Order.status.in_(["PENDING", "SUBMITTED"])
            ).all()

            cancelled_count = 0
            for order in stop_orders:
                order.status = "CANCELLED"
                cancelled_count += 1

            self.db.commit()
            logger.info(f"Cancelled {cancelled_count} related stop orders")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel related orders: {e}")
            return False
```

## Risk Management API Endpoints

```python
# backend/api/risk_routes.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, List
from database.connection import get_db
from database.models import Account, RiskLog
from services.risk_manager import RiskManager, RiskMonitor

router = APIRouter(prefix="/api/risk", tags=["risk-management"])

@router.get("/metrics/{account_id}")
def get_risk_metrics(account_id: int, db: Session = Depends(get_db)):
    """Get comprehensive risk metrics for an account"""
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        risk_manager = RiskManager(account, db)
        return risk_manager.get_risk_metrics()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/emergency-stop/{account_id}")
def activate_emergency_stop(account_id: int, reason: str, db: Session = Depends(get_db)):
    """Activate emergency stop for an account"""
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        risk_manager = RiskManager(account, db)
        success = risk_manager.activate_emergency_stop(reason)

        if success:
            return {"message": "Emergency stop activated", "account_id": account_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to activate emergency stop")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary/{account_id}")
def get_risk_summary(account_id: int, db: Session = Depends(get_db)):
    """Get risk summary with recommendations"""
    try:
        risk_monitor = RiskMonitor(db)
        return risk_monitor.get_risk_summary(account_id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard")
def get_risk_dashboard(db: Session = Depends(get_db)):
    """Get risk dashboard for all accounts"""
    try:
        risk_monitor = RiskMonitor(db)
        return risk_monitor.check_all_accounts_risk()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/events/{account_id}")
def get_risk_events(account_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """Get recent risk events for an account"""
    try:
        events = db.query(RiskLog).filter(
            RiskLog.account_id == account_id
        ).order_by(RiskLog.created_at.desc()).limit(limit).all()

        return [
            {
                'id': event.id,
                'event_type': event.event_type,
                'severity': event.event_severity,
                'message': event.event_message,
                'action_taken': event.action_taken,
                'created_at': event.created_at
            }
            for event in events
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Testing Risk Management

```python
# backend/tests/test_risk_management.py
import pytest
from decimal import Decimal
from services.risk_manager import RiskManager, PositionSizer
from database.models import Account

class TestRiskManager:
    """Test risk management functionality"""

    @pytest.fixture
    def test_account(self, db):
        """Create test account with risk limits"""
        account = Account(
            name="Test Risk Account",
            current_cash=10000.0,
            max_position_size=1000.0,
            max_daily_loss=100.0,
            max_positions=5,
            testnet_mode="true",
            trading_enabled="true",
            emergency_stop="false"
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        return account

    def test_position_size_limit(self, test_account, db):
        """Test that large orders are blocked"""
        risk_manager = RiskManager(test_account, db)

        # Try to place order larger than max position size
        can_place, reason = risk_manager.can_place_order("BTC", "buy", 1.0, 60000.0)  # $60,000 position

        assert not can_place
        assert "exceeds limit" in reason

    def test_daily_loss_limit(self, test_account, db):
        """Test daily loss limit enforcement"""
        # Simulate account with high daily loss
        risk_manager = RiskManager(test_account, db)
        risk_manager.current_metrics['daily_pnl'] = -150.0  # $150 loss (exceeds $100 limit)

        can_place, reason = risk_manager.can_place_order("BTC", "buy", 0.1, 50000.0)

        assert not can_place
        assert "Daily loss" in reason

    def test_emergency_stop_blocks_all(self, test_account, db):
        """Test that emergency stop blocks all trading"""
        test_account.emergency_stop = "true"
        db.commit()

        risk_manager = RiskManager(test_account, db)

        can_place, reason = risk_manager.can_place_order("BTC", "buy", 0.1, 50000.0)

        assert not can_place
        assert "Emergency stop" in reason

    def test_live_trading_blocked(self, test_account, db):
        """Test that live trading attempts are blocked"""
        test_account.testnet_mode = "false"
        db.commit()

        risk_manager = RiskManager(test_account, db)

        can_place, reason = risk_manager.can_place_order("BTC", "buy", 0.1, 50000.0)

        assert not can_place
        assert "testnet mode required" in reason

class TestPositionSizer:
    """Test position sizing calculations"""

    @pytest.fixture
    def test_account(self, db):
        """Create test account for position sizing"""
        account = Account(
            name="Test Position Sizing",
            current_cash=10000.0,
            max_position_size=1000.0,
            max_daily_loss=100.0
        )
        db.add(account)
        db.commit()
        return account

    def test_position_size_with_stop_loss(self, test_account):
        """Test position size calculation with stop loss"""
        sizer = PositionSizer(test_account)

        result = sizer.calculate_position_size(
            symbol="BTC",
            entry_price=50000.0,
            stop_loss_price=47500.0  # 5% stop loss
        )

        # Should recommend position size based on 1% risk ($100)
        expected_shares = 100.0 / (50000.0 - 47500.0)  # Risk / Risk per share
        expected_shares = 4.0  # 100 / 2500

        assert result['recommended_shares'] == pytest.approx(expected_shares, rel=0.1)
        assert result['within_limits'] is True

    def test_position_size_limit_enforced(self, test_account):
        """Test that maximum position size is enforced"""
        sizer = PositionSizer(test_account)

        result = sizer.calculate_position_size(
            symbol="BTC",
            entry_price=50000.0,
            stop_loss_price=45000.0  # Very wide stop loss
        )

        # Should be limited to max_position_size ($1000)
        assert result['recommended_value'] <= 1000.0
        assert result['within_limits'] is True
```

This comprehensive risk management system provides multiple layers of protection to ensure safe trading operations while maintaining flexibility for legitimate trading strategies.