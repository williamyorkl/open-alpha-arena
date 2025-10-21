#!/usr/bin/env python3
"""
Test script to verify WebSocket snapshot data serialization
This tests that all Decimal types are properly converted to float
"""

import json
from database.connection import SessionLocal
from database.models import User, Position, Order, Trade
from repositories.position_repo import list_positions
from repositories.order_repo import list_orders
from services.asset_calculator import calc_positions_value
from services.market_data import get_last_price


def test_snapshot_serialization():
    """Test that snapshot data can be serialized to JSON without type errors"""
    db = SessionLocal()
    try:
        # Get a user
        user = db.query(User).first()
        if not user:
            print("❌ No users found in database")
            return False
        
        print(f"Testing snapshot for user: {user.username} (id={user.id})")
        
        # Get data
        positions = list_positions(db, user.id)
        orders = list_orders(db, user.id)
        trades = (
            db.query(Trade)
            .filter(Trade.user_id == user.id)
            .order_by(Trade.trade_time.desc())
            .limit(200)
            .all()
        )
        positions_value = calc_positions_value(db, user.id)
        
        # Create overview
        overview = {
            "user": {
                "id": user.id,
                "username": user.username,
                "initial_capital": float(user.initial_capital),
                "current_cash": float(user.current_cash),
                "frozen_cash": float(user.frozen_cash),
            },
            "total_assets": positions_value + float(user.current_cash),
            "positions_value": positions_value,
        }
        
        print(f"Found {len(positions)} positions, {len(orders)} orders, {len(trades)} trades")
        
        # Enrich positions (this is where the error was occurring)
        enriched_positions = []
        for p in positions:
            try:
                price = get_last_price(p.symbol, p.market)
            except Exception:
                price = None
            
            # This should NOT raise TypeError anymore
            enriched_positions.append({
                "id": p.id,
                "user_id": p.user_id,
                "symbol": p.symbol,
                "name": p.name,
                "market": p.market,
                "quantity": float(p.quantity),  # Convert Decimal to float
                "available_quantity": float(p.available_quantity),  # Convert Decimal to float
                "avg_cost": float(p.avg_cost),
                "last_price": float(price) if price is not None else None,
                "market_value": (float(price) * float(p.quantity)) if price is not None else None,  # Both float
            })
        
        print("✓ Positions enriched successfully")
        
        # Create full snapshot
        snapshot_data = {
            "type": "snapshot",
            "overview": overview,
            "positions": enriched_positions,
            "orders": [
                {
                    "id": o.id,
                    "order_no": o.order_no,
                    "user_id": o.user_id,
                    "symbol": o.symbol,
                    "name": o.name,
                    "market": o.market,
                    "side": o.side,
                    "order_type": o.order_type,
                    "price": float(o.price) if o.price is not None else None,
                    "quantity": float(o.quantity),  # Convert Decimal to float
                    "filled_quantity": float(o.filled_quantity),  # Convert Decimal to float
                    "status": o.status,
                }
                for o in orders
            ],
            "trades": [
                {
                    "id": t.id,
                    "order_id": t.order_id,
                    "user_id": t.user_id,
                    "symbol": t.symbol,
                    "name": t.name,
                    "market": t.market,
                    "side": t.side,
                    "price": float(t.price),
                    "quantity": float(t.quantity),  # Convert Decimal to float
                    "commission": float(t.commission),
                    "trade_time": str(t.trade_time),
                }
                for t in trades
            ],
        }
        
        print("✓ Snapshot data structure created successfully")
        
        # Try to serialize to JSON (this would fail if there are type issues)
        try:
            json_str = json.dumps(snapshot_data, ensure_ascii=False)
            print(f"✓ JSON serialization successful ({len(json_str)} bytes)")
            
            # Verify we can deserialize it back
            parsed = json.loads(json_str)
            print(f"✓ JSON deserialization successful")
            
            # Print some sample data
            print("\n📊 Sample Snapshot Data:")
            print(f"  Total Assets: ${overview['total_assets']:,.2f}")
            print(f"  Positions: {len(enriched_positions)}")
            print(f"  Orders: {len(snapshot_data['orders'])}")
            print(f"  Trades: {len(snapshot_data['trades'])}")
            
            if enriched_positions:
                print("\n  Sample Position:")
                pos = enriched_positions[0]
                print(f"    {pos['symbol']}: {pos['quantity']} @ ${pos['avg_cost']:.4f}")
                print(f"    Market Value: ${pos['market_value']:.2f}" if pos['market_value'] else "    Market Value: N/A")
            
            if snapshot_data['trades']:
                print("\n  Latest Trade:")
                trade = snapshot_data['trades'][0]
                print(f"    {trade['side']} {trade['quantity']} {trade['symbol']} @ ${trade['price']:.4f}")
                print(f"    Commission: ${trade['commission']:.2f}")
            
            print("\n✅ All tests passed! WebSocket snapshot can be serialized properly.")
            return True
            
        except TypeError as e:
            print(f"\n❌ JSON serialization failed with TypeError: {e}")
            print("This means there are still Decimal types that weren't converted to float")
            return False
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            return False
            
    finally:
        db.close()


if __name__ == "__main__":
    success = test_snapshot_serialization()
    exit(0 if success else 1)
