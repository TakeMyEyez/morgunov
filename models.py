from pydantic import BaseModel

class Movietop(BaseModel):
    name: str
    id: int
    cost: float
    director: str
    description: str = ""
    is_published: bool = True
    image_path: str = ""
