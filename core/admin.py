from django.contrib import admin
from .models import Shop, PriceConfig, DailySupply, Payment

admin.site.register(Shop)
admin.site.register(PriceConfig)
admin.site.register(DailySupply)
admin.site.register(Payment)