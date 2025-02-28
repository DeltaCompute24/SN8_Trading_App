from pydantic import BaseModel
from typing import Dict, Optional

        
        
class UserDetails(BaseModel):
    """
    Represents user details associated with a hotkey.
    Used for mapping hotkeys to user information.
    """
    name: Optional[str] = None
    email: Optional[str] = None
    user_id: Optional[int] = None
    trader_id: Optional[int] = None
    top_trader_pairs: Optional[Dict] = None
    all_time_returns: Optional[float] =None
    id: Optional[int] = None  # Added id field with default None

class HotKeyMap(BaseModel):
    data: Dict[str, UserDetails]
    class Config:
        orm_mode = True