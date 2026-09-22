from django.contrib import admin

from .models import (
    Expense,
    ExpenseCategory,
    Income,
    Invoice,
    InvoiceLine,
    InvoiceSequence,
    RecurringExpense,
)


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "colour", "position", "studio")
    list_filter = ("studio",)


@admin.register(RecurringExpense)
class RecurringExpenseAdmin(admin.ModelAdmin):
    list_display = ("name", "amount", "category", "interval", "is_active", "studio")
    list_filter = ("category", "interval", "is_active", "studio")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("date", "amount", "category", "supplier", "studio")
    list_filter = ("category", "date", "studio")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    inlines = [InvoiceLineInline]
    list_display = ("number", "client", "status", "issue_date", "total", "studio")
    list_filter = ("status", "studio")


@admin.register(InvoiceSequence)
class InvoiceSequenceAdmin(admin.ModelAdmin):
    list_display = ("year", "last_number", "studio")


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ("date", "amount", "method", "client", "studio")
    list_filter = ("method", "studio")
