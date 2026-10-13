
# expenses/views.py

from datetime import date
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth

from .models import Transaction


def dashboard(request):
    # All transactions
    all_transactions = Transaction.objects.all()

    # Search by title
    search_query = request.GET.get('q', '').strip()
    transactions = all_transactions.order_by('-date', '-id')

    if search_query:
        transactions = transactions.filter(
            Q(title__icontains=search_query)
        )

    # Filter by Income or Expense
    selected_type = request.GET.get('type', '')

    if selected_type in ['Income', 'Expense']:
        transactions = transactions.filter(
            transaction_type=selected_type
        )
    else:
        selected_type = ''

    # Filter by category
    selected_category = request.GET.get('category', '')
    valid_categories = dict(Transaction.CATEGORY_CHOICES)

    if selected_category in valid_categories:
        transactions = transactions.filter(
            category=selected_category
        )
    else:
        selected_category = ''

    # Filter by month
    selected_month = request.GET.get('month', '')

    if selected_month:
        try:
            year_text, month_text = selected_month.split('-')
            year = int(year_text)
            month = int(month_text)

            if 1900 <= year <= 2100 and 1 <= month <= 12:
                transactions = transactions.filter(
                    date__year=year,
                    date__month=month
                )
            else:
                selected_month = ''

        except (ValueError, TypeError):
            selected_month = ''

    # Overall totals (not affected by filters)
    income = (
        all_transactions.filter(transaction_type='Income')
        .aggregate(total=Sum('amount'))['total']
        or Decimal('0.00')
    )

    expenses = (
        all_transactions.filter(transaction_type='Expense')
        .aggregate(total=Sum('amount'))['total']
        or Decimal('0.00')
    )

    balance = income - expenses

    # Group transactions by month and type
    monthly_totals = (
        all_transactions
        .annotate(month_start=TruncMonth('date'))
        .values('month_start', 'transaction_type')
        .annotate(total=Sum('amount'))
        .order_by('month_start')
    )

    totals_by_month = {}

    for row in monthly_totals:
        month_start = row['month_start']
        key = (month_start.year, month_start.month)

        if key not in totals_by_month:
            totals_by_month[key] = {
                'income': Decimal('0.00'),
                'expenses': Decimal('0.00'),
            }

        if row['transaction_type'] == 'Income':
            totals_by_month[key]['income'] = row['total']
        else:
            totals_by_month[key]['expenses'] = row['total']

    # Prepare the last 6 calendar months
    today = date.today()
    monthly_reports = []

    for offset in range(5, -1, -1):
        month_index = today.year * 12 + today.month - 1 - offset
        year = month_index // 12
        month = month_index % 12 + 1

        values = totals_by_month.get(
            (year, month),
            {
                'income': Decimal('0.00'),
                'expenses': Decimal('0.00'),
            }
        )

        month_income = values['income']
        month_expenses = values['expenses']

        monthly_reports.append({
            'label': date(year, month, 1).strftime('%b %Y'),
            'month_value': f'{year:04d}-{month:02d}',
            'income': month_income,
            'expenses': month_expenses,
            'balance': month_income - month_expenses,
        })

    # Data for Chart.js
    chart_labels = [row['label'] for row in monthly_reports]
    chart_income = [float(row['income']) for row in monthly_reports]
    chart_expenses = [float(row['expenses']) for row in monthly_reports]

    context = {
        'transactions': transactions,
        'income': income,
        'expenses': expenses,
        'balance': balance,
        'search_query': search_query,
        'selected_type': selected_type,
        'selected_category': selected_category,
        'selected_month': selected_month,
        'categories': Transaction.CATEGORY_CHOICES,
        'monthly_reports': monthly_reports,
        'chart_labels': chart_labels,
        'chart_income': chart_income,
        'chart_expenses': chart_expenses,
    }

    return render(
        request,
        'expenses/dashboard.html',
        context
    )


def add_transaction(request):
    return save_transaction(request)


def edit_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    return save_transaction(request, transaction)


def save_transaction(request, transaction=None):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        amount_text = request.POST.get('amount', '').strip()
        transaction_type = request.POST.get('transaction_type', '')
        category = request.POST.get('category', 'Other')

        error = None
        amount = None

        if not title:
            error = 'Please enter a transaction title.'

        elif len(title) > 100:
            error = 'Title must be 100 characters or fewer.'

        elif transaction_type not in ['Income', 'Expense']:
            error = 'Please select Income or Expense.'

        elif category not in dict(Transaction.CATEGORY_CHOICES):
            error = 'Please select a valid category.'

        try:
            amount = Decimal(amount_text)

            if not amount.is_finite() or amount <= 0:
                error = 'Amount must be greater than zero.'

            elif amount.as_tuple().exponent < -2:
                error = 'Amount can have at most 2 decimal places.'

            elif amount >= Decimal('1000000000'):
                error = 'Amount is too large.'

        except (InvalidOperation, ValueError):
            error = 'Please enter a valid amount.'

        if error is None:
            if transaction is not None:
                transaction.title = title
                transaction.amount = amount
                transaction.transaction_type = transaction_type
                transaction.category = category
                transaction.save()

            else:
                Transaction.objects.create(
                    title=title,
                    amount=amount,
                    transaction_type=transaction_type,
                    category=category,
                )

            return redirect('dashboard')

        return render(
            request,
            'expenses/add_transaction.html',
            {
                'transaction': transaction,
                'categories': Transaction.CATEGORY_CHOICES,
                'error': error,
                'form_title': title,
                'form_amount': amount_text,
                'form_type': transaction_type,
                'form_category': category,
            }
        )

    return render(
        request,
        'expenses/add_transaction.html',
        {
            'transaction': transaction,
            'categories': Transaction.CATEGORY_CHOICES,
        }
    )


def delete_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)

    if request.method == 'POST':
        transaction.delete()
        return redirect('dashboard')

    return render(
        request,
        'expenses/delete_transaction.html',
        {'transaction': transaction}
    )
