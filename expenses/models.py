# expenses/models.py

from django.db import models


class Transaction(models.Model):

    TRANSACTION_TYPES = [
        ('Income', 'Income'),
        ('Expense', 'Expense'),
    ]

    CATEGORY_CHOICES = [
        ('Salary', 'Salary'),
        ('Business', 'Business'),
        ('Food', 'Food'),
        ('Travel', 'Travel'),
        ('Shopping', 'Shopping'),
        ('Bills', 'Bills'),
        ('Education', 'Education'),
        ('Health', 'Health'),
        ('Other', 'Other'),
    ]

    title = models.CharField(max_length=100)

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPES
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='Other'
    )

    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.title