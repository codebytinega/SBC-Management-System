from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model for CosmoShop.
    
    Extends Django's AbstractUser to add role-based permissions.
    
    Roles:
    - OWNER: Full access (reports, profits, employee management)
    - EMPLOYEE: Limited access (record sales, view stock)
    
    Why custom from day 1?
    - Django best practice: easier to modify later
    - We need role field immediately
    - Can't easily switch to custom user mid-project
    """
    
    ROLE_CHOICES = [
        ('OWNER', 'Owner'),
        ('EMPLOYEE', 'Employee'),
    ]
    
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='EMPLOYEE',
        help_text="User's access level in the system"
    )
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def is_owner(self):
        """Check if user has owner privileges"""
        return self.role == 'OWNER'
    
    def is_employee(self):
        """Check if user is an employee"""
        return self.role == 'EMPLOYEE'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"