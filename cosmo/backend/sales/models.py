from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from decimal import Decimal
import uuid


class Sale(models.Model):
    """
    Represents a complete POS transaction.
    
    Think of this as the "receipt" - it holds:
    - Total amounts (subtotal, tax, final total)
    - Who made the sale
    - When it happened
    - Payment method
    - Calculated profit
    
    The actual products bought are in SaleItem (the cart).
    
    Relationship: 1 Sale has many SaleItems
    """
    
    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('UPI', 'UPI/QR'),
    ]
    
    # Unique order identifier (visible to customer)
    order_id = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Human-readable order ID (e.g., #ORD-2024-893)"
    )
    
    # Who processed this sale
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # Can't delete user who made sales
        related_name='sales'
    )
    
    # Financial totals (calculated by backend)
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Sum of all items before tax"
    )
    tax = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Tax amount (calculated by backend)"
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Final amount paid (subtotal + tax)"
    )
    profit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total profit from this sale (calculated)"
    )
    
    # Payment
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHODS
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True  # For fast date-range queries
    )
    notes = models.TextField(
        blank=True,
        help_text="Optional notes about the transaction"
    )
    
    class Meta:
        db_table = 'sales'
        ordering = ['-created_at']  # Newest first
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['cashier', '-created_at']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate order_id if not provided"""
        if not self.order_id:
            # Generate format: #ORD-2024-893
            self.order_id = f"#ORD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.order_id} - ${self.total} by {self.cashier.username}"


class SaleItem(models.Model):
    """
    Individual products within a sale (the shopping cart).
    
    Why separate from Sale?
    - A sale can have multiple products
    - Each product has its own quantity, price, profit
    - Makes it easy to show itemized receipts
    
    Example:
    Sale #ORD-2024-893:
      - SaleItem 1: 2x Velvet Lipstick @ $18.00 = $36.00
      - SaleItem 2: 1x Hydra Serum @ $45.00 = $45.00
      Total: $81.00
    
    Key principle: All prices/costs are snapshot at sale time.
    If product price changes tomorrow, this record stays accurate.
    """
    
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,  # Delete items if sale is deleted
        related_name='items'
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,  # Can't delete product with sale history
        related_name='sale_items'
    )
    
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    
    # Snapshot prices at time of sale (critical!)
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Selling price per unit at time of sale"
    )
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Cost price per unit at time of sale"
    )
    
    # Calculated fields (for performance)
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="unit_price × quantity"
    )
    profit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="(unit_price - unit_cost) × quantity"
    )
    
    class Meta:
        db_table = 'sale_items'
        ordering = ['id']
    
    def save(self, *args, **kwargs):
        """
        Auto-calculate subtotal and profit if not provided.
        This ensures data consistency.
        """
        if not self.subtotal:
            self.subtotal = self.unit_price * self.quantity
        if not self.profit:
            self.profit = (self.unit_price - self.unit_cost) * self.quantity
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name} in {self.sale.order_id}"