from pydantic import BaseModel
from typing import Optional, List, Dict


class HsCodeFieldResponse(BaseModel):
    field_name: str
    field_type: str = "text"
    sort_order: int = 0
    is_required: bool = False


class DeclarationProductResponse(BaseModel):
    id: int
    hs_code: str
    product_name: str
    website_name: Optional[str] = None
    product_description: Optional[str] = None
    values: Dict[str, str] = {}


class HsCodeDetailResponse(BaseModel):
    hs_code: str
    website_name: Optional[str] = None
    description: Optional[str] = None
    fields: List[HsCodeFieldResponse] = []
    products: List[DeclarationProductResponse] = []


class HsCodeListItem(BaseModel):
    hs_code: str
    website_name: Optional[str] = None
    product_count: int = 0


class ProductCreate(BaseModel):
    product_name: str
    website_name: Optional[str] = None
    product_description: Optional[str] = None


class ProductUpdate(BaseModel):
    product_name: Optional[str] = None
    website_name: Optional[str] = None
    product_description: Optional[str] = None


class ValuesUpdate(BaseModel):
    values: Dict[str, str] = {}


class FieldCreate(BaseModel):
    field_name: str
    field_type: str = "text"
    sort_order: int = 0
    is_required: bool = False


class FieldUpdate(BaseModel):
    field_name: Optional[str] = None
    field_type: Optional[str] = None
    sort_order: Optional[int] = None
    is_required: Optional[bool] = None
