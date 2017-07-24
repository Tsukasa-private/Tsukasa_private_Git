from django.contrib import admin

from django.utils.html import format_html
from .models import Graph

# Register your models here.

class GraphAdmin(admin.ModelAdmin):
    def displayURL(self, obj):
        return format_html('<a href="{url}">View</a>', url="/dumpviewer/saved/{0}".format(obj.identifier))
    readonly_fields=("identifier", "displayURL")
    fields = ["identifier", "displayURL", "timestamp", "parameterString", "graphsString"]

admin.site.register(Graph, GraphAdmin)
