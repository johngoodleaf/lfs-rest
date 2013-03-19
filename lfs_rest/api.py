# django imports
from django.contrib.auth.models import User

# tastypie imports
from tastypie import fields
from tastypie.authorization import Authorization
from tastypie.authentication import Authentication, BasicAuthentication
from tastypie.resources import ModelResource
from tastypie.resources import ALL
from tastypie.serializers import Serializer

# lfs imports
try:
    from lfs.addresses.models import Address
except ImportError:
    from lfs.customer.models import Address

from lfs.catalog.models import Category
from lfs.catalog.models import Product
from lfs.customer.models import Customer
from lfs.order.models import Order
from lfs.order.models import OrderItem
from django.forms.models import model_to_dict

from django.conf.urls import url
from tastypie.http import HttpGone, HttpMultipleChoices
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from tastypie.utils import trailing_slash
import pprint

class LFSSerializer(Serializer):
    def to_html(self, data, options=None):
        return self.to_json(data, options)


class ProductResource(ModelResource):
    categories = fields.ToManyField("lfs_rest.api.CategoryResource", "categories", null=True)

    class Meta:
        queryset = Product.objects.all()
        serializer = LFSSerializer()
        resource_name = 'product'
        authorization = Authorization()
        # authentication = BasicAuthentication()
        excludes = ["effective_price"]

        filtering = {
            "sku": ALL,
            "categories": ALL,
    }


class CategoryResource(ModelResource):
    parent = fields.ForeignKey("lfs_rest.api.CategoryResource", "parent", null=True)
    products = fields.ToManyField("lfs_rest.api.ProductResource", "products", null=True)
    #categories = fields.ToManyField('self', 'parent', full_list=True, null=True)
    subcategories = fields.ListField(null=True)
    class Meta:
        queryset = Category.objects.all()
        serializer = LFSSerializer()
        resource_name = 'category'
        authorization = Authorization()
        authentication = Authentication()
        excludes = ["level",
                    "uid",
                    "product_cols",
                    "product_rows",
                    "position",
                    "static_block",
                    "template",
                    "active_formats",
                    "category_cols",
                    "meta_description",
                    "meta_title",
                    "meta_keywords",
                    "show_all_products"
                    ]
        filtering = {
            "name": ALL,
        }


    def _strip_category_fields(self, datadictionary):
        c = CategoryResource()
        tempdict = {}
        fields = c.fields.keys()

        for key,val in datadictionary.items():
            if key in fields:
                tempdict.update({key:val})
        return tempdict

    def process_children(self, obj):
        pp = pprint.PrettyPrinter(indent=2)
        print "\n\n"
        print "=" * 60
        children = obj.get_children()
        subcategories = []
        if children:
            for child in children:
                #print "=" * 60
                #print "\tchild: %s\t parent: %s, subcats: %s" % (child, obj, subcategories)
                tempdict = self._strip_category_fields(model_to_dict(child))
                p = ProductResource()
                my_products = []
                for prod_pk in tempdict['products']:
                    product = Product.objects.get(pk=prod_pk)
                    prod_bundle = p.build_bundle(product)
                    prod_uri = p.get_resource_uri(prod_bundle)
                    my_products.append(prod_uri)
                tempdict['products'] = my_products
                print "\t\t%s" % tempdict
                subcategories.append(tempdict)
                #obj.subcategories.append(childresource.full_dehydrate())
                self.process_children(child)
        obj.subcategories = subcategories
        pp.pprint(obj.__dict__)
        print "+" * 60
        return obj

    def get_object_list(self, request):
        top_categories = Category.objects.filter(parent__isnull=True)
        return top_categories

    def dehydrate(self, bundle):
        self.process_children(bundle.obj)
        bundle.data['subcategories'] = bundle.obj.subcategories
        return bundle


class OrderResource(ModelResource):
    items = fields.ToManyField("lfs_rest.api.OrderItemResource", "items", null=True)

    class Meta:
        queryset = Order.objects.all()
        serializer = LFSSerializer()
        resource_name = 'order'

        filtering = {
            "created": ALL,
        }


class OrderItemResource(ModelResource):
    product = fields.ForeignKey("lfs_rest.api.ProductResource", "product", null=True)
    order = fields.ForeignKey("lfs_rest.api.OrderResource", "order")

    class Meta:
        queryset = OrderItem.objects.all()
        serializer = LFSSerializer()
        resource_name = 'order-item'

        filtering = {
            "created": ALL,
        }


class CustomerResource(ModelResource):
    addresses = fields.ToManyField("lfs_rest.api.AddressResource", "addresses", null=True)

    class Meta:
        queryset = Customer.objects.all()
        serializer = LFSSerializer()
        resource_name = 'customer'


class AddressResource(ModelResource):
    customer = fields.ForeignKey("lfs_rest.api.CustomerResource", "customer", null=True)

    class Meta:
        queryset = Address.objects.all()
        serializer = LFSSerializer()
        resource_name = 'address'
