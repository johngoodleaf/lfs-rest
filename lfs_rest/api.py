# django imports
from django.contrib.auth.models import User

# tastypie imports
from tastypie import fields
from tastypie.authorization import Authorization
from tastypie.authentication import Authentication, BasicAuthentication
from tastypie.resources import ModelResource
from tastypie.resources import ALL, ALL_WITH_RELATIONS
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
from tastypie.bundle import Bundle

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
            "categories": ALL_WITH_RELATIONS,
            "slug": ALL,
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
            "slug": ALL_WITH_RELATIONS,
            "parent": ALL_WITH_RELATIONS,
        }

    def _strip_category_fields(self, datadictionary):
        c = CategoryResource()
        tempdict = {}
        fields = c.fields.keys()

        for key, val in datadictionary.items():
            if key in fields:
                tempdict.update({key: val})
        return tempdict

    def _get_product_uris(self, product_list):
        p = ProductResource()
        my_products = []
        for prod_pk in product_list:
            product = Product.objects.get(pk=prod_pk)
            prod_bundle = p.build_bundle(product)
            prod_uri = p.get_resource_uri(prod_bundle)
            my_products.append(prod_uri)
        return my_products

    def process_children(self, obj):
        subcategories = obj.get_children()
        if not subcategories:
            obj.subcategories = []
            #return obj
        else:
            obj.subcategories = []
            for category in subcategories:
                tempdict = self._strip_category_fields(model_to_dict(category))
                tempdict['products'] = self._get_product_uris(tempdict['products'])
                obj.subcategories.append(tempdict)
                self.process_children(category)
            #return obj

    # def get_object_list(self, request):
    #     top_categories = Category.objects.filter(parent__isnull=True)
    #     return top_categories

    def dehydrate(self, bundle):
        self.process_children(bundle.obj)
        bundle.data['subcategories'] = bundle.obj.subcategories
        return bundle

    def _get_id(self, uri_string):
        try:
            return int(uri_string.split('/')[3])
        except AttributeError:
            return None

    def _append_or_replace(self, blist, val):
        for b in blist:
            if isinstance(b, dict):
                blist.remove(b)
        if val in blist:
            blist.remove(val)
        blist.append(val)

    def search_bundle(self, obj_list):
        for o in obj_list:
            if isinstance(o, Bundle):
                subcats = o.data['subcategories']
                o.data['subcategories'] = self.strip_dicts(subcats)

    def strip_dicts(self, obj_list):
        return [thing for thing in obj_list if isinstance(thing, Bundle)]

    def alter_list_data_to_serialize(self, request, data):
        bundles = data['objects']
        bundle_dict = {}
        final_bundle = {}

        for bundle in bundles:
            bundle_dict[bundle.data['id']] = bundle

        with_parents = [v for v in bundle_dict.values() if v.data['parent']]
        without_parents = [v for v in bundle_dict.values() if not v in with_parents]

        for v in without_parents:
            final_bundle[v.data['id']] = v

        for v in with_parents:
            id_val = self._get_id(v.data['parent'])
            try:
                parent = final_bundle[id_val]
            except KeyError:
                parent = bundle_dict[id_val]
            self._append_or_replace(parent.data['subcategories'], v)

        # for k, v in final_bundle.data.items():
        #     if type(v) is "dict":
        #         del(final_bundle[k])
        #     elif type(v) is "Bundle" and v.data['subcategories']:
        #         del()
        data['objects'] = final_bundle.values()
        return data


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
