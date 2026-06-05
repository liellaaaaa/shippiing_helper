"""PI contract service — transactional save with pi_data Upsert."""

from app.database import SessionLocal
from app.models.pi_contract import PiContract, PiContractItem, PiData
from app.schemas.pi_contract import PiContractSaveRequest


class PiService:
    """Service for PI contract operations."""

    def __init__(self, db_session):
        self.db = db_session

    def save_contract(self, request: PiContractSaveRequest) -> tuple[int, int, int]:
        """
        Save or update a PI contract.
        Returns: tuple of (contract_id, items_count, pi_data_updated_count)

        Transaction behavior:
        - pi_no exists: delete old pi_contract_items, replace with new ones
        - pi_no new: create new pi_contract
        - pi_data: Upsert (insert if not exists, update if exists)
        """
        try:
            # Check if contract already exists (by pi_no)
            existing = self.db.query(PiContract).filter_by(pi_no=request.pi_no).first()

            if existing:
                # Delete old items
                self.db.query(PiContractItem).filter_by(pi_contract_id=existing.id).delete()
                contract = existing
                # Update header fields
                contract.customer_code = request.customer_code
                contract.sales_person = request.sales_person
                contract.pi_date = request.pi_date
                contract.is_ordered = request.is_ordered
                contract.order_id = request.order_id
                contract.consignee_name = request.consignee_name
                contract.consignee_address = request.consignee_address
                contract.destination = request.destination
            else:
                # Create new contract
                contract = PiContract(
                    pi_no=request.pi_no,
                    customer_code=request.customer_code,
                    sales_person=request.sales_person,
                    pi_date=request.pi_date,
                    is_ordered=request.is_ordered,
                    order_id=request.order_id,
                    consignee_name=request.consignee_name,
                    consignee_address=request.consignee_address,
                    destination=request.destination,
                )
                self.db.add(contract)
                self.db.flush()  # Get the ID

            pi_data_updated_count = 0
            seen_pi_data_codes: set = set()

            for item in request.items:
                pi_item = PiContractItem(
                    pi_contract_id=contract.id,
                    internal_code=item.internal_code,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total_amount=item.total_amount,
                    product_color=item.product_color,
                    hs_code=item.hs_code,
                    customs_name=item.customs_name,
                    customs_composition=item.customs_composition,
                    order_customs_name=item.order_customs_name,
                    notes=item.notes,
                )
                self.db.add(pi_item)

                # 批次内去重：同一 internal_code 只 upsert pi_data 一次
                if item.internal_code and item.internal_code not in seen_pi_data_codes:
                    updated = self._upsert_pi_data(item)
                    if updated:
                        pi_data_updated_count += 1
                        seen_pi_data_codes.add(item.internal_code)

            self.db.commit()
            return contract.id, len(request.items), pi_data_updated_count

        except Exception as e:
            self.db.rollback()
            raise e

    def _upsert_pi_data(self, item) -> bool:
        """
        Upsert a single item into pi_data.
        Returns True if a record was inserted or updated.
        Proforma 格式无 internal_code 时跳过。
        """
        if not item.internal_code:
            return False
        existing = self.db.query(PiData).filter_by(internal_code=item.internal_code).first()
        if existing:
            # Update fields if provided
            if item.hs_code:
                existing.hs_code = item.hs_code
            if item.customs_name:
                existing.customs_name = item.customs_name
            if item.customs_composition:
                existing.customs_composition = item.customs_composition
            if item.product_color:
                existing.product_color = item.product_color
            return True
        else:
            # Insert new
            pi_data = PiData(
                internal_code=item.internal_code,
                product_color=item.product_color,
                hs_code=item.hs_code,
                customs_name=item.customs_name,
                customs_composition=item.customs_composition,
            )
            self.db.add(pi_data)
            return True

    def query_contracts(
        self,
        pi_no: str | None = None,
        customer_code: str | None = None,
        internal_code: str | None = None,
    ) -> list[dict]:
        """Query pi_contracts with optional filters."""
        query = self.db.query(PiContract)

        if pi_no:
            query = query.filter(PiContract.pi_no == pi_no)
        if customer_code:
            query = query.filter(PiContract.customer_code == customer_code)

        contracts = query.all()
        results = []

        for c in contracts:
            contract_dict = {
                "id": c.id,
                "pi_no": c.pi_no,
                "customer_code": c.customer_code,
                "sales_person": c.sales_person,
                "pi_date": c.pi_date,
                "is_ordered": c.is_ordered,
                "items": [],
            }

            # Filter items by internal_code if provided
            items_query = self.db.query(PiContractItem).filter_by(pi_contract_id=c.id)
            if internal_code:
                items_query = items_query.filter(PiContractItem.internal_code == internal_code)

            for item in items_query.all():
                contract_dict["items"].append({
                    "internal_code": item.internal_code,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_amount": item.total_amount,
                    "product_color": item.product_color,
                    "hs_code": item.hs_code,
                    "customs_name": item.customs_name,
                    "customs_composition": item.customs_composition,
                    "order_customs_name": item.order_customs_name,
                    "notes": item.notes,
                })

            results.append(contract_dict)

        return results

    def get_customer_mapping(self, customer_code: str) -> dict | None:
        """Get stored column mapping for a customer (Phase 2 — stub for now)."""
        return None