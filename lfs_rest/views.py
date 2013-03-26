#views for order status
from django.conf import settings
try:
    import json
except ImportError:
    from django.util import simplejson as json
from django.http import HttpResponse

from lfs.catalog.models import Product
import requests


def submitted(request):
    if request.POST:
        print request.POST
    else:
        return HttpResponse()
