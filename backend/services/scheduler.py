"""
Scheduled task scheduler service
Used to manage WebSocket snapshot updates and other scheduled tasks
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Set, Callable, Optional
import asyncio
import logging
from datetime import date

from database.connection import SessionLocal
from database.models import Position, CryptoPrice

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Unified task scheduler"""
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self._started = False
        self._account_connections: Dict[int, Set] = {}  # track account connections
        
    def start(self):
        """Start the scheduler"""
        if not self._started:
            self.scheduler = AsyncIOScheduler()
            self.scheduler.start()
            self._started = True
            logger.info("Scheduler started")
    
    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            self._started = False
            logger.info("Scheduler shutdown")
    
    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self._started and self.scheduler and self.scheduler.running
    
    def add_account_snapshot_task(self, account_id: int, interval_seconds: int = 10):
        """
        Add snapshot update task for account

        Args:
            account_id: Account ID
            interval_seconds: Update interval (seconds), default 10 seconds
        """
        if not self.is_running():
            self.start()
            
        job_id = f"snapshot_account_{account_id}"
        
        # Check if task already exists
        if self.scheduler.get_job(job_id):
            logger.debug(f"Snapshot task for account {account_id} already exists")
            return
        
        self.scheduler.add_job(
            func=self._execute_account_snapshot,
            trigger=IntervalTrigger(seconds=interval_seconds),
            args=[account_id],
            id=job_id,
            replace_existing=True,
            max_instances=1  # Avoid duplicate execution
        )
        
        logger.info(f"Added snapshot task for account {account_id}, interval {interval_seconds} seconds")
    
    def remove_account_snapshot_task(self, account_id: int):
        """
        Remove snapshot update task for account

        Args:
            account_id: Account ID
        """
        if not self.scheduler:
            return
            
        job_id = f"snapshot_account_{account_id}"
        
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed snapshot task for account {account_id}")
        except Exception as e:
            logger.debug(f"Failed to remove snapshot task for account {account_id}: {e}")
    
    def add_market_hours_task(self, task_func: Callable, cron_expression: str, task_id: str):
        """
        Add market hours based scheduled task

        Args:
            task_func: Function to execute
            cron_expression: Cron expression, e.g. "0 9 * * 1-5" (9 AM on weekdays)
            task_id: Task unique identifier
        """
        if not self.is_running():
            self.start()
            
        self.scheduler.add_job(
            func=task_func,
            trigger=CronTrigger.from_crontab(cron_expression),
            id=task_id,
            replace_existing=True
        )
        
        logger.info(f"Added market time task {task_id}: {cron_expression}")
    
    def add_interval_task(self, task_func: Callable, interval_seconds: int, task_id: str, *args, **kwargs):
        """
        Add interval execution task

        Args:
            task_func: Function to execute
            interval_seconds: Execution interval (seconds)
            task_id: Task unique identifier
            *args, **kwargs: Parameters passed to task_func
        """
        if not self.is_running():
            self.start()
            
        self.scheduler.add_job(
            func=task_func,
            trigger=IntervalTrigger(seconds=interval_seconds),
            args=args,
            kwargs=kwargs,
            id=task_id,
            replace_existing=True
        )
        
        logger.info(f"Added interval task {task_id}: Execute every {interval_seconds} seconds")
    
    def remove_task(self, task_id: str):
        """
        Remove specified task

        Args:
            task_id: Task ID
        """
        if not self.scheduler:
            return
            
        try:
            self.scheduler.remove_job(task_id)
            logger.info(f"Removed task: {task_id}")
        except Exception as e:
            logger.debug(f"Failed to remove task {task_id}: {e}")

    def get_job_info(self) -> list:
        """Get all task information"""
        if not self.scheduler:
            return []

        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'next_run_time': job.next_run_time,
                'func_name': job.func.__name__ if hasattr(job.func, '__name__') else str(job.func)
            })
        return jobs

    async def _execute_account_snapshot(self, account_id: int):
        """
        Internal method to execute account snapshot update

        Args:
            account_id: Account ID
        """
        try:
            # Dynamic import to avoid circular dependency
            from api.ws import manager, _send_snapshot

            # Check if account still has active connections
            if account_id not in manager.active_connections:
                # Account disconnected, remove task
                self.remove_account_snapshot_task(account_id)
                return

            # Execute snapshot update
            db: Session = SessionLocal()
            try:
                # Send snapshot update
                await _send_snapshot(db, account_id)

                # Save latest prices for account's positions
                await self._save_position_prices(db, account_id)

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Account {account_id} snapshot update failed: {e}")
    
    async def _save_position_prices(self, db: Session, account_id: int):
        """
        Save latest prices for account's positions on the current date

        Args:
            db: Database session
            account_id: Account ID
        """
        try:
            # Get all account's positions
            positions = db.query(Position).filter(
                Position.account_id == account_id,
                Position.quantity > 0
            ).all()

            if not positions:
                logger.debug(f"Account {account_id} has no positions, skip price saving")
                return

            today = date.today()

            for position in positions:
                try:
                    # Check if crypto price already saved today
                    existing_price = db.query(CryptoPrice).filter(
                        CryptoPrice.symbol == position.symbol,
                        CryptoPrice.market == position.market,
                        CryptoPrice.price_date == today
                    ).first()

                    if existing_price:
                        logger.debug(f"crypto {position.symbol} price already exists for today, skip")
                        continue

                    # Get latest price
                    from services.market_data import get_last_price
                    current_price = get_last_price(position.symbol, position.market)

                    # Save price record
                    crypto_price = CryptoPrice(
                        symbol=position.symbol,
                        market=position.market,
                        price=current_price,
                        price_date=today
                    )

                    db.add(crypto_price)
                    db.commit()

                    logger.info(f"Saved crypto price: {position.symbol} {today} {current_price}")

                except Exception as e:
                    logger.error(f"Failed to save crypto {position.symbol} price: {e}")
                    db.rollback()
                    continue

        except Exception as e:
            logger.error(f"Failed to save account {account_id} position prices: {e}")
            db.rollback()


# Global scheduler instance
task_scheduler = TaskScheduler()


# Convenience functions
def start_scheduler():
    """Start global scheduler"""
    task_scheduler.start()


def stop_scheduler():
    """Stop global scheduler"""
    task_scheduler.shutdown()


def add_account_snapshot_job(account_id: int, interval_seconds: int = 10):
    """Convenience function to add snapshot task for account"""
    task_scheduler.add_account_snapshot_task(account_id, interval_seconds)


def remove_account_snapshot_job(account_id: int):
    """Convenience function to remove account snapshot task"""
    task_scheduler.remove_account_snapshot_task(account_id)


# Legacy compatibility functions
def add_user_snapshot_job(user_id: int, interval_seconds: int = 10):
    """Legacy function - now redirects to account-based function"""
    # For backward compatibility, assume this is account_id
    add_account_snapshot_job(user_id, interval_seconds)


def remove_user_snapshot_job(user_id: int):
    """Legacy function - now redirects to account-based function"""
    # For backward compatibility, assume this is account_id
    remove_account_snapshot_job(user_id)


# Market hours related predefined tasks
async def market_open_tasks():
    """Tasks executed at market open"""
    logger.info("Executing market open tasks")
    # Add logic needed at market open here
    # For example: refresh market data, check pending orders, etc.


async def market_close_tasks():
    """Tasks executed at market close"""
    logger.info("Executing market close tasks")
    # Add logic needed at market close here
    # For example: settle daily profits, generate reports, etc.


def setup_market_tasks():
    """Set up market-related scheduled tasks"""
    # US crypto market open time: 9:30 AM ET Monday-Friday (considering time zone conversion)
    # Using UTC time, should adjust based on server time zone in actual deployment
    task_scheduler.add_market_hours_task(
        market_open_tasks,
        "30 14 * * 1-5",  # UTC time, corresponds to 9:30 AM ET
        "market_open"
    )

    # US crypto market close time: 4:00 PM ET Monday-Friday
    task_scheduler.add_market_hours_task(
        market_close_tasks,
        "0 21 * * 1-5",   # UTC time, corresponds to 4:00 PM ET
        "market_close"
    )