#views for order status
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
try:
    import json
except ImportError:
    from django.util import simplejson as json
from django.http import HttpResponse

from lfs.catalog.models import Product
from lfs.cart.models import Cart, CartItem
from django.forms import model_to_dict
import requests
import pusher
import locale
locale.setlocale(locale.LC_ALL, '')

CORE_URL = 'http://localhost:8001/'
CORE_ORDER_PATH = 'customer/api/customer/'
def core_submit(request, order, *args, **kwargs):
    print request
    print order
    print args
    print kwargs
    #r = requests.post(CORE_URL + CORE_ORDER_PATH +)

@csrf_exempt
def submitted(request, *args, **kwargs):
    if request.method == "POST":
        products = json.loads(request.raw_post_data)
        product_list = products['products']
        gratuity = float(products['gratuity'])

        #print request.raw_post_data
        #print product_list

        cart = Cart()
        cart.save()

        product_data = []
        for p in product_list:
            product = Product.objects.get(pk=p['id'])
            cart.add(product, amount=p['quantity'])
            d = model_to_dict(product)
            d['quantity'] = p['quantity']
            product_data.append(d)

        cost = cart.get_price_net(request)
        tax = cart.get_tax(request)

        cost = locale.currency((cost + tax + gratuity), grouping=True)

        core_submit(request, product_data, cost)

        p = pusher.Pusher(app_id='40239',
            key='1ebb3cc2881a1562cc37',
            secret='7296ddd9aede74695af1')

        p['order_channel'].trigger('order:pushed',
            {'products': product_data,
             'cost': cost,
             'order': cart.id,
             })
        return HttpResponse(json.dumps(
            {'products': product_data, 'cost': cost}),
            content_type="application/json")
    else:
        return HttpResponse()
