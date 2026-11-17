from django.db import models
from decimal import Decimal

class Shop(models.Model):
    name = models.CharField(max_length=150, verbose_name="اسم الدكان / صاحب الدكان")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="رقم الهاتف")
    location = models.CharField(max_length=255, blank=True, null=True, verbose_name="الموقع / الحي")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def total_balance(self):
        """حساب إجمالي المديونية الحالية المتراكمة للدكان"""
        total_debt = sum(supply.remaining_amount for supply in self.supplies.all())
        total_paid_debts = sum(payment.amount for payment in self.payments.all())
        return total_debt - total_paid_debts

    class Meta:
        verbose_name = "دكان"
        verbose_name_plural = "الدكاكين"


class PriceConfig(models.Model):
    price_per_100 = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('47000.00'),
        verbose_name="سعر الـ 100 عيشة (جنيه)"
    )
    is_active = models.BooleanField(default=True, verbose_name="السعر الحالي النشط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ تفعيل السعر")

    def save(self, *args, **kwargs):
        if self.is_active:
            PriceConfig.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.price_per_100} SDG ({'نشط' if self.is_active else 'أرشيف'})"

    class Meta:
        verbose_name = "إعداد السعر"
        verbose_name_plural = "إعدادات الأسعار"


class DailySupply(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='supplies', verbose_name="الدكان")
    date = models.DateField(auto_now_add=True, verbose_name="التاريخ")
    quantity = models.PositiveIntegerField(verbose_name="عدد العيش (بالقطع)")
    unit_price_at_supply = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="سعر الـ 100 عيشة وقت التوريد"
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="المبلغ الكلي")
    paid_cash = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="المدفوع كاش")
    paid_bankak = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="المدفوع بنكك")
    remaining_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="المتبقي (آجل)")
    notes = models.CharField(max_length=255, blank=True, null=True, verbose_name="ملاحظات")

    def save(self, *args, **kwargs):
        if not self.unit_price_at_supply:
            active_price = PriceConfig.objects.filter(is_active=True).first()
            self.unit_price_at_supply = active_price.price_per_100 if active_price else Decimal('47000.00')

        self.total_amount = (Decimal(self.quantity) / Decimal('100.00')) * self.unit_price_at_supply
        total_paid = Decimal(self.paid_cash) + Decimal(self.paid_bankak)
        self.remaining_amount = self.total_amount - total_paid
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.shop.name} - {self.quantity} عيشة - {self.date}"

    class Meta:
        verbose_name = "توريد يومي"
        verbose_name_plural = "التوريدات اليومية"


class Payment(models.Model):
    PAYMENT_METHODS = (
        ('cash', 'كاش'),
        ('bankak', 'بنكك'),
    )
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='payments', verbose_name="الدكان")
    date = models.DateField(auto_now_add=True, verbose_name="تاريخ السداد")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="المبلغ المسدد")
    method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default='cash', verbose_name="طريقة السداد")
    notes = models.CharField(max_length=255, blank=True, null=True, verbose_name="ملاحظات")

    def __str__(self):
        return f"سداد: {self.shop.name} - {self.amount} جنيه"

    class Meta:
        verbose_name="دفعة سداد"
        verbose_name_plural="دفوعات السداد"