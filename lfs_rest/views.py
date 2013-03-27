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
import pusher

@csrf_exempt
def submitted(request):
    if request.method == "POST":
        products = json.loads(request.raw_post_data)
        print request.raw_post_data

        print products
        p = pusher.Pusher(app_id='40239',
            key='1ebb3cc2881a1562cc37',
            secret='7296ddd9aede74695af1')

        p['order_channel'].trigger('order:pushed', {'products': products})
        return HttpResponse(json.dumps(products),
            content_type="application/json")
    else:
        return HttpResponse()
