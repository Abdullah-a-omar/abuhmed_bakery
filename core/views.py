from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import Sum
from .models import Shop, DailySupply, Payment, PriceConfig
import urllib.parse
from decimal import Decimal

def dashboard(request):
    today = timezone.now().date()
    active_price = PriceConfig.objects.filter(is_active=True).first()
    
    # حسابات التوريدات والمبيعات اليومية
    today_supplies = DailySupply.objects.filter(date=today)
    today_payments = Payment.objects.filter(date=today)
    
    total_bread_today = today_supplies.aggregate(Sum('quantity'))['quantity__sum'] or 0
    total_sales_today = today_supplies.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # إجمالي التحصيرات اليومية (سواء دفعت مع التوريد أو عبر استلام دين مستقل)
    cash_from_supplies = today_supplies.aggregate(Sum('paid_cash'))['paid_cash__sum'] or 0
    cash_from_payments = today_payments.filter(method='cash').aggregate(Sum('amount'))['amount__sum'] or 0
    cash_today = cash_from_supplies + cash_from_payments
                 
    bankak_from_supplies = today_supplies.aggregate(Sum('paid_bankak'))['paid_bankak__sum'] or 0
    bankak_from_payments = today_payments.filter(method='bankak').aggregate(Sum('amount'))['amount__sum'] or 0
    bankak_today = bankak_from_supplies + bankak_from_payments
                   
    total_collected_today = cash_today + bankak_today
    
    # الديون الجديدة اليوم = إجمالي المبيعات مطروحاً منها كل ما تم تحصيله اليوم
    new_debt_today = total_sales_today - total_collected_today
    if new_debt_today < 0:
        new_debt_today = Decimal('0')
    
    # إجمالي ديون السوق التراكمية الكلية
    shops = Shop.objects.all()
    total_market_debt = sum(shop.total_balance for shop in shops)

    # تجهيز نص تقرير الواتساب لصاحب المخبز
    owner_report_text = f"""📊 *التقرير اليومي - مخبز أبو أحمد*
📅 *التاريخ:* {today.strftime('%Y/%m/%d')}
👤 *المدير المسؤول:* عبد الله
----------------------------------
🥖 *إجمالي العيش الموزع:* {total_bread_today:,} قطعة
💰 *إجمالي المبيعات:* {total_sales_today:,.2f} ج.س
----------------------------------
💵 *التحصيل الكاش:* {cash_today:,.2f} ج.س
📱 *التحصيل البنكي (بنكك):* {bankak_today:,.2f} ج.س
📥 *إجمالي السيولة الداخلة:* {total_collected_today:,.2f} ج.س
----------------------------------
📉 *ديون جديدة اليوم:* {new_debt_today:,.2f} ج.س
📚 *إجمالي ديون السوق الكلية:* {total_market_debt:,.2f} ج.س
----------------------------------
*تم استخراجه تلقائياً من تطبيق إدارة مخبز أبو أحمد*"""

    whatsapp_owner_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(owner_report_text)}"

    context = {
        'active_price': active_price,
        'total_bread_today': total_bread_today,
        'total_sales_today': total_sales_today,
        'cash_today': cash_today,
        'bankak_today': bankak_today,
        'new_debt_today': new_debt_today,
        'total_market_debt': total_market_debt,
        'whatsapp_owner_url': whatsapp_owner_url,
    }
    return render(request, 'core/dashboard.html', context)

def add_shop(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone', '')
        location = request.POST.get('location', '')
        notes = request.POST.get('notes', '')
        
        if name:
            Shop.objects.create(
                name=name,
                phone=phone,
                location=location,
                notes=notes
            )
            return redirect('shops_list')
            
    return render(request, 'core/add_shop.html')

def shops_list(request):
    query = request.GET.get('q', '')
    if query:
        shops = Shop.objects.filter(name__icontains=query)
    else:
        shops = Shop.objects.all()
    return render(request, 'core/shops_list.html', {'shops': shops, 'query': query})


def shop_detail(request, shop_id):
    shop = get_object_or_404(Shop, pk=shop_id)
    supplies = shop.supplies.all().order_by('-date', '-id')
    payments = shop.payments.all().order_by('-date', '-id')
    
    # رابط إرسال كشف الحساب عبر الواتساب للدكان
    statement_text = f"""مرحباً {shop.name} 👋
هذا ملخص كشف حسابك لدى *مخبز أبو أحمد*:
📌 *إجمالي المديونية المتبقية (الآجل القائم):* {shop.total_balance:,.2f} جنيه سوداني.
شاكرين ومقدرين تعاملكم معنا!
*إدارة مخبز أبو أحمد (عبد الله)*"""
    
    whatsapp_url = f"https://api.whatsapp.com/send?phone={shop.phone or ''}&text={urllib.parse.quote(statement_text)}"

    context = {
        'shop': shop,
        'supplies': supplies,
        'payments': payments,
        'whatsapp_url': whatsapp_url,
    }
    return render(request, 'core/shop_detail.html', context)


def edit_shop(request, shop_id):
    shop = get_object_or_404(Shop, pk=shop_id)
    if request.method == 'POST':
        shop.name = request.POST.get('name')
        shop.phone = request.POST.get('phone', '')
        shop.location = request.POST.get('location', '')
        shop.notes = request.POST.get('notes', '')
        shop.save()
        return redirect('shop_detail', shop_id=shop.id)
        
    return render(request, 'core/edit_shop.html', {'shop': shop})


def delete_shop(request, shop_id):
    shop = get_object_or_404(Shop, pk=shop_id)
    # حماية: منع الحذف إذا كان عليه مديونية
    if shop.total_balance <= 0:
        shop.delete()
        return redirect('shops_list')
    else:
        # يمكن تمرير رسالة خطأ أو العودة مع تنبيه
        return redirect('shop_detail', shop_id=shop.id)


def edit_supply(request, supply_id):
    supply = get_object_or_404(DailySupply, pk=supply_id)
    if request.method == 'POST':
        supply.quantity = int(request.POST.get('quantity', supply.quantity))
        supply.paid_cash = Decimal(request.POST.get('paid_cash') or '0')
        supply.paid_bankak = Decimal(request.POST.get('paid_bankak') or '0')
        supply.notes = request.POST.get('notes', '')
        supply.save() # نموذج السيف سيقوم بإعادة حساب الإجمالي والمتبقي آلياً
        return redirect('shop_detail', shop_id=supply.shop.id)
        
    return render(request, 'core/edit_supply.html', {'supply': supply})




def update_price(request):
    if request.method == 'POST':
        new_price = request.POST.get('price_per_100')
        if new_price:
            # إلغاء تفعيل الأسعار القديمة وتفعيل السعر الجديد
            PriceConfig.objects.filter(is_active=True).update(is_active=False)
            PriceConfig.objects.create(price_per_100=Decimal(new_price), is_active=True)
    return redirect('dashboard')


def new_supply(request):
    shops = Shop.objects.all()
    active_price = PriceConfig.objects.filter(is_active=True).first()
    price_value = active_price.price_per_100 if active_price else Decimal('47000.00')

    if request.method == 'POST':
        shop_id = request.POST.get('shop')
        quantity = int(request.POST.get('quantity', 0))
        paid_cash = Decimal(request.POST.get('paid_cash') or '0')
        paid_bankak = Decimal(request.POST.get('paid_bankak') or '0')
        notes = request.POST.get('notes', '')

        shop = Shop.objects.get(pk=shop_id)
        
        # إنشاء عملية التوريد (النموذج سيقوم بحساب الإجمالي والمتبقي آلياً)
        DailySupply.objects.create(
            shop=shop,
            quantity=quantity,
            unit_price_at_supply=price_value,
            paid_cash=paid_cash,
            paid_bankak=paid_bankak,
            notes=notes
        )
        return redirect('dashboard')

    context = {
        'shops': shops,
        'price_value': price_value,
    }
    return render(request, 'core/new_supply.html', context)


def new_payment(request):
    shops = Shop.objects.all()

    if request.method == 'POST':
        shop_id = request.POST.get('shop')
        amount = Decimal(request.POST.get('amount') or '0')
        method = request.POST.get('method')
        notes = request.POST.get('notes', '')

        shop = Shop.objects.get(pk=shop_id)
        
        Payment.objects.create(
            shop=shop,
            amount=amount,
            method=method,
            notes=notes
        )
        return redirect('dashboard')

    return render(request, 'core/new_payment.html', {'shops': shops})