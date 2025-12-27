from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from decimal import Decimal


class Product(models.Model):
    """
    Represents a cosmetic product in inventory.
    
    This is the SINGLE SOURCE OF TRUTH for:
    - Product identity (SKU, name, brand)
    - Current stock quantity
    - Pricing (cost and selling price)
    
    Key principle: Frontend displays this data, never modifies it directly.
    Only backend logic changes stock_quantity.
    """
    
    CATEGORY_CHOICES = [
        ('LIPS', 'Lips'),
        ('EYES', 'Eyes'),
        ('FACE', 'Face'),
        ('SKINCARE', 'Skincare'),
        ('ACCESSORIES', 'Accessories'),
    ]
    
    # Product Identity
    sku = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Stock Keeping Unit - unique product identifier"
    )
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=100)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        db_index=True
    )
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True,
        help_text="Product image for POS display"
    )
    
    # Pricing (Decimal for precision - NEVER Float for money!)
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="What we paid for this product (for profit calculation)"
    )
    selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="What customer pays (POS price)"
    )
    
    # Stock Management
    stock_quantity = models.PositiveIntegerField(
        default=0,
        help_text="Current available quantity"
    )
    restock_threshold = models.PositiveIntegerField(
        default=10,
        help_text="Alert when stock falls below this number"
    )
    
    # Metadata
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive products won't appear in POS"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        ordering = ['name']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
        ]
    
    def needs_restock(self):
        """
        Check if product stock is at or below threshold.
        Used for dashboard alerts.
        """
        return self.stock_quantity <= self.restock_threshold
    
    def profit_per_unit(self):
        """Calculate profit margin per unit"""
        return self.selling_price - self.cost_price
    
    def profit_percentage(self):
        """Calculate profit as percentage of cost"""
        if self.cost_price > 0:
            return (self.profit_per_unit() / self.cost_price) * 100
        return Decimal('0.00')
    
    def __str__(self):
        return f"{self.brand} - {self.name} (SKU: {self.sku})"


class StockReceipt(models.Model):
    """
    Records incoming inventory shipments.
    
    Why separate from Product?
    - Tracks WHO received stock and WHEN
    - Records cost_price at time of receipt (for historical tracking)
    - Provides audit trail for inventory changes
    - Shows recent receipts in "Receive Stock" screen
    
    Flow:
    1. Employee scans/selects product
    2. Enters quantity received
    3. StockReceipt is created
    4. Product.stock_quantity increases automatically
    """
    
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,  # Can't delete product if receipts exist
        related_name='stock_receipts'
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Number of units received"
    )
    cost_price_at_receipt = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Cost price at time of receiving (for records)"
    )
    
    # Supplier info (optional, for reference only)
    supplier_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Who supplied this stock (optional)"
    )
    supplier_notes = models.TextField(
        blank=True,
        help_text="Delivery notes, invoice number, etc."
    )
    
    # Tracking
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='received_stocks'
    )
    received_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stock_receipts'
        ordering = ['-received_at']  # Most recent first
        indexes = [
            models.Index(fields=['-received_at']),
            models.Index(fields=['product', '-received_at']),
        ]
    
    def __str__(self):
        return f"+{self.quantity} {self.product.name} on {self.received_at.strftime('%Y-%m-%d')}"