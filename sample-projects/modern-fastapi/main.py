"""FastAPI application with some issues for testing."""
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel
import asyncio

app = FastAPI(title="Sample API", version="1.0.0")

# Database simulation
USERS_DB = {}
ITEMS_DB = {}


class User(BaseModel):
    id: int
    name: str
    email: str
    is_active: bool = True


class UserCreate(BaseModel):
    name: str
    email: str


class Item(BaseModel):
    id: int
    name: str
    price: float
    owner_id: int


# Missing async - should be async for consistency
def get_user_sync(user_id: int) -> Optional[User]:
    """Get user by ID (sync version)."""
    return USERS_DB.get(user_id)


async def get_user(user_id: int) -> Optional[User]:
    """Get user by ID."""
    # Simulating async database call
    await asyncio.sleep(0.01)
    return USERS_DB.get(user_id)


# SQL injection pattern (simulated)
def search_users_unsafe(query: str):
    # Simulating unsafe query building
    sql = f"SELECT * FROM users WHERE name LIKE '%{query}%'"
    return sql


async def get_items_for_user(user_id: int) -> List[Item]:
    """Get all items for a user."""
    await asyncio.sleep(0.01)
    return [item for item in ITEMS_DB.values() if item.owner_id == user_id]


# Dependency
async def get_current_user(user_id: int = Query(...)) -> User:
    user = await get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/users/{user_id}")
async def read_user(user_id: int):
    """Get a user by ID."""
    user = await get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/users")
async def list_users(skip: int = 0, limit: int = 100):
    """List all users."""
    users = list(USERS_DB.values())
    return users[skip:skip + limit]


@app.post("/users")
async def create_user(user: UserCreate):
    """Create a new user."""
    user_id = len(USERS_DB) + 1
    new_user = User(id=user_id, name=user.name, email=user.email)
    USERS_DB[user_id] = new_user
    return new_user


@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    """Delete a user."""
    if user_id not in USERS_DB:
        raise HTTPException(status_code=404, detail="User not found")
    del USERS_DB[user_id]
    return {"status": "deleted"}


@app.get("/users/{user_id}/items")
async def read_user_items(user_id: int):
    """Get items for a user."""
    items = await get_items_for_user(user_id)
    return items


@app.post("/items")
async def create_item(name: str, price: float, owner_id: int):
    """Create a new item."""
    item_id = len(ITEMS_DB) + 1
    new_item = Item(id=item_id, name=name, price=price, owner_id=owner_id)
    ITEMS_DB[item_id] = new_item
    return new_item


# Duplicate logic - same as create_item
@app.post("/items/bulk")
async def create_items_bulk(items: List[dict]):
    """Create multiple items."""
    created = []
    for item_data in items:
        item_id = len(ITEMS_DB) + 1
        new_item = Item(
            id=item_id,
            name=item_data["name"],
            price=item_data["price"],
            owner_id=item_data["owner_id"]
        )
        ITEMS_DB[item_id] = new_item
        created.append(new_item)
    return created


# Missing error handling
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return ITEMS_DB[item_id]  # KeyError if not found


@app.get("/search")
async def search(q: str):
    """Search for users."""
    # Uses unsafe SQL building
    sql = search_users_unsafe(q)
    # In reality, this would execute the unsafe query
    return {"query": sql}


# Hardcoded values
@app.get("/config")
async def get_config():
    return {
        "api_version": "1.0.0",
        "max_items_per_page": 100,
        "cache_ttl": 3600,
        "debug": True,  # Debug in production!
    }


# Complex function that needs refactoring
def process_order(order_data):
    """Process an order - too complex."""
    if not order_data:
        return None

    items = order_data.get("items", [])
    if not items:
        return None

    total = 0
    for item in items:
        if item.get("quantity", 0) > 0:
            price = item.get("price", 0)
            quantity = item.get("quantity", 0)
            discount = item.get("discount", 0)
            if discount > 0:
                if discount > 100:
                    discount = 100
                price = price * (1 - discount / 100)
            subtotal = price * quantity
            if subtotal > 1000:
                subtotal = subtotal * 0.95  # Bulk discount
            total += subtotal

    shipping = 0
    if total < 50:
        shipping = 10
    elif total < 100:
        shipping = 5
    else:
        shipping = 0

    tax = total * 0.1
    final_total = total + shipping + tax

    return {
        "subtotal": total,
        "shipping": shipping,
        "tax": tax,
        "total": final_total,
    }


# Unused function
def old_process_payment(amount: float) -> bool:
    """Old payment processing - deprecated."""
    return True


# TODO: Add authentication
# FIXME: This endpoint is too slow
@app.get("/slow")
async def slow_endpoint():
    await asyncio.sleep(5)
    return {"status": "done"}
