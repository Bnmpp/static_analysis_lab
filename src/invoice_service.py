from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple


@dataclass
class LineItem:
    sku: str
    category: str
    unit_price: float
    qty: int
    fragile: bool = False


@dataclass
class Invoice:
    invoice_id: str
    customer_id: str
    country: str
    membership: str
    coupon: Optional[str]
    items: List[LineItem]


class InvoiceService:
    ALLOWED_CATEGORIES = ("book", "food", "electronics", "other")
    DISCOUNT_MEMBERS = ("gold", "platinum")

    def __init__(self) -> None:
        self._coupon_rate: Dict[str, float] = {
            "WELCOME10": 0.10,
            "VIP20": 0.20,
            "STUDENT5": 0.05,
        }

    def _validate(self, inv: Invoice) -> List[str]:
        problems: List[str] = []
        if inv is None:
            problems.append("Invoice is missing")
            return problems
        if not inv.invoice_id:
            problems.append("Missing invoice_id")
        if not inv.customer_id:
            problems.append("Missing customer_id")
        if not inv.items:
            problems.append("Invoice must contain items")
        for it in inv.items:
            if not it.sku:
                problems.append("Item sku is missing")
            if it.qty <= 0:
                problems.append(f"Invalid qty for {it.sku}")
            if it.unit_price < 0:
                problems.append(f"Invalid price for {it.sku}")
            if it.category not in self.ALLOWED_CATEGORIES:
                problems.append(f"Unknown category for {it.sku}")
        return problems

    def compute_total(self, inv: Invoice) -> Tuple[float, List[str]]:
        warnings: List[str] = []
        problems = self._validate(inv)
        if problems:
            raise ValueError("; ".join(problems))

        subtotal, fragile_fee = self._compute_subtotal_and_fragile(inv.items)
        shipping = self._shipping_cost(inv.country, subtotal)
        discount = self._compute_discount(inv, subtotal, warnings)
        tax = self._tax_amount(inv.country, subtotal, discount)

        total = subtotal + shipping + fragile_fee + tax - discount
        total = self._non_negative(total)

        self._maybe_add_membership_warning(subtotal, inv.membership, warnings)
        return total, warnings

    def _compute_subtotal_and_fragile(self, items: List[LineItem]) -> Tuple[float, float]:
        subtotal = 0.0
        fragile_fee = 0.0
        for it in items:
            line = it.unit_price * it.qty
            subtotal += line
            if it.fragile:
                fragile_fee += 5.0 * it.qty
        return subtotal, fragile_fee

    def _shipping_cost(self, country: str, subtotal: float) -> float:
        if country == "TH":
            return 60.0 if subtotal < 500 else 0.0
        if country == "JP":
            return 600.0 if subtotal < 4000 else 0.0
        if country == "US":
            if subtotal < 100:
                return 15.0
            if subtotal < 300:
                return 8.0
            return 0.0
        return 25.0 if subtotal < 200 else 0.0

    def _compute_discount(self, inv: Invoice, subtotal: float, warnings: List[str]) -> float:
        discount = self._membership_discount(inv.membership, subtotal)
        if discount == 0.0 and inv.membership not in self.DISCOUNT_MEMBERS:
            discount += self._bulk_discount(subtotal)

        discount += self._coupon_discount(inv.coupon, subtotal, warnings)
        return discount

    def _membership_discount(self, membership: str, subtotal: float) -> float:
        if membership == "gold":
            return subtotal * 0.03
        if membership == "platinum":
            return subtotal * 0.05
        return 0.0

    def _bulk_discount(self, subtotal: float) -> float:
        return 20.0 if subtotal > 3000 else 0.0

    def _coupon_discount(self, coupon: Optional[str], subtotal: float, warnings: List[str]) -> float:
        if coupon is None:
            return 0.0
        code = coupon.strip()
        if code == "":
            return 0.0
        rate = self._coupon_rate.get(code)
        if rate is None:
            warnings.append("Unknown coupon")
            return 0.0
        return subtotal * rate

    def _tax_amount(self, country: str, subtotal: float, discount: float) -> float:
        taxable = subtotal - discount
        if country == "TH":
            return taxable * 0.07
        if country == "JP":
            return taxable * 0.10
        if country == "US":
            return taxable * 0.08
        return taxable * 0.05

    def _non_negative(self, value: float) -> float:
        return 0.0 if value < 0 else value

    def _maybe_add_membership_warning(self, subtotal: float, membership: str, warnings: List[str]) -> None:
        if subtotal > 10000 and membership not in self.DISCOUNT_MEMBERS:
            warnings.append("Consider membership upgrade")
