
import scrapy.pipelines.files
from itemadapter import ItemAdapter

from sessionnet.utils import get_url_params


class HTMLFilterPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        for field in adapter.field_names():
            value = adapter.get(field)
            if value and isinstance(value, str):
                # remove non-breakable space
                value = value.replace(u"\xa0", " ")
            adapter[field] = value
        return item


class MyFilesPipeline(scrapy.pipelines.files.FilesPipeline):

    def file_path(self, request, response=None, info=None, *, item=None):
        file_id = get_url_params(request.url)["id"]
        ending = ItemAdapter(item).get("file_name").split(".")[-1]
        return f"{file_id}.{ending}"

