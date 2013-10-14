#views for order status
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from ast import literal_eval
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
import os
import logging

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

logger = logging.getLogger("default")

if not 'DEV' in os.environ:
    CORE_URL = 'https://core.stadi.us/'
else:
    CORE_URL = 'http://localhost:8001/'
CORE_ORDER_PATH = 'customer/api/customer/'

PRODUCT_KEYS = ['slug', 'price', 'tax', 'quantity', 'name']


def core_submit(request, order, cost, auth_check, *args, **kwargs):
    incoming_headers = request.META
    headers = {k[5:]:v for k,v in incoming_headers.items() if k.startswith('HTTP')}
    user_id = auth_check['user_id']
    logger.debug("core_submit user_id: %s" % user_id)
    post_url = "%s%s%s/order/" % (CORE_URL, CORE_ORDER_PATH, user_id)
    logger.debug("core_submit post_url: %s" % post_url)
    data = json.dumps(order)
    r = requests.post(post_url, data=data, headers={'ACCEPT': headers['ACCEPT'],
                                                    'Authorization': headers['AUTHORIZATION'],
                                                    'Content-Type': 'application/json'})
    logger.debug("core_submit status_code: %s" % r.status_code)
    return r


def check_auth(request):
    incoming_headers = request.META
    headers = {k[5:]:v for k,v in incoming_headers.items() if k.startswith('HTTP')}
    logger.debug("check_auth headers: %s" % headers)
    core = CORE_URL + "customer/api-token-auth/"
    logger.debug("check_auth core url: %s" % core)
    #r = requests.get(core, headers=headers)
    if not 'authorization' in [x.lower() for x in headers.keys()]:
        return "ERROR: Missing Authorization header"
    r = requests.get("https://core.stadi.us/customer/api-token-auth/", headers={"Authorization": headers['AUTHORIZATION']})
    logger.debug("check_auth request status: %s" % r.status_code)
    if "ERROR" in r.text:
        return r.text
    else:
        return r.text


@csrf_exempt
def submitted(request, *args, **kwargs):
    if request.method == "POST":
        check_result = check_auth(request)
        if 'ERROR' in check_result:
            print "Found ERROR condition"
            return HttpResponse(json.dumps({'ERROR': check_result}),
                content_type="application/json")

        products = json.loads(request.raw_post_data)
        product_list = products['products']
        gratuity = float(products['gratuity'])
        user = products['user']

        #print request.raw_post_data
        #print product_list

        cart = Cart()
        cart.save()

        product_data = []
        for p in product_list:
            product = Product.objects.get(pk=p['id'])
            cart.add(product, amount=p['qty'])
            d = model_to_dict(product)
            d['quantity'] = p['qty']

            product_data.append({k: v for k, v in d.items()
                                 if k in PRODUCT_KEYS})

        cost = cart.get_price_net(request)
        tax = cart.get_tax(request)

        cost = locale.currency((cost + tax + gratuity), grouping=True)

        auth_check = literal_eval(check_result)

        saved_order = {"cost": cost,
                       "tax": tax,
                       "gratuity": gratuity,
                       "items": product_data}

        order_handler = core_submit(request, saved_order,
                                    cost, auth_check=auth_check,
                                    user=user)

        logger.debug("order_handler status: %s" %
                     order_handler.status_code)

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
