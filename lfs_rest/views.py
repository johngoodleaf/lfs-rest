#views for order status
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
try:
    import json
except ImportError:
    from django.util import simplejson as json
from django.http import HttpResponse

from lfs.catalog.models import Product
import requests

@csrf_exempt
def submitted(request):
    if request.method == "POST":
        products = request.POST.getlist('products')
        print request.raw_post_data
        print request.POST
        return HttpResponse(json.dumps(products),
            content_type="application/json")
    else:
        return HttpResponse()
