from django.shortcuts import render
from django.views.generic.base import View
from search.models import ArticleType
from django.http import HttpResponse
import json

# Create your views here.

class IndexView(View):
    def get(self, request):
        return render(request, "index.html")

class SuggestView(View):
    def get(self, request):
        key_words = request.GET.get('s', '')
        re_datas = []
        if key_words:
            s = ArticleType.search()
            s = s.suggest('my_suggest', key_words, completion={
                "field":"suggest", "fuzzy":{
                    "fuzziness":2
                },
                "size":10
            })
            suggestions = s.execute_suggest()
            for match in suggestions.my_suggest[0].options:
                source = match._source
                re_datas.append(source["title"])
        return HttpResponse(json.dumps(re_datas), content_type="application/json")

class SearchView(View):
    def get(self, request):
        return render(request, "result.html")