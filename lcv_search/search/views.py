from django.shortcuts import render
from django.views.generic.base import View

# Create your views here.

class IndexView(View):
    def get(self, request):
        return render(request, "index.html")

class SuggestView(View):
    def get(self, request):
        return render(request, "index.html")

class SearchView(View):
    def get(self, request):
        return render(request, "result.html")