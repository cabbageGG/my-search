# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.views.generic.base import View
from search.models import ArticleType, JobType, QuestionType
from django.http import HttpResponse
from elasticsearch import Elasticsearch
import json
from datetime import datetime
import redis

client = Elasticsearch(hosts=["127.0.0.1"])
redis_cli = redis.StrictRedis()

# Create your views here.

class IndexView(View):
    def get(self, request):
        return render(request, "index.html")

class SuggestView(View):
    def get(self, request):
        key_words = request.GET.get('s', '')
        s_type = request.GET.get('s_type', 'article')
        re_datas = []
        if s_type == "article":
            s = ArticleType.search()
        elif s_type == "question":
            s = QuestionType.search()
        elif s_type == "job":
            s = JobType.search()
        else:
            s = ArticleType.search()
        if key_words:
            s = s.suggest('my_suggest', key_words, completion={
                "field":"suggest",
                "fuzzy":{ "fuzziness":2 },
                "size":10
            })
            suggestions = s.execute_suggest()
            for match in suggestions.my_suggest[0].options:
                source = match._source
                re_datas.append(source["title"])
        return HttpResponse(json.dumps(re_datas), content_type="application/json")

class SearchView(View):
    def get(self, request):
        key_words = request.GET.get('q', '')
        s_type = request.GET.get('s_type', 'article')

        redis_cli.zincrby("search_keywords_set", key_words)

        topn_search = redis_cli.zrevrangebyscore("search_keywords_set", "+inf", "-inf", start=0, num=5)

        jobbole_count = redis_cli.get("jobbole_count")
        lagou_count = redis_cli.get("lagou_count")
        zhihu_count = redis_cli.get("zhihu_count")

        page = request.GET.get('p', '1')
        try:
            page = int(page)
        except:
            page = 1

        source = ""
        last_seconds = 0
        total_nums = 0
        hit_list = []
        page_nums = 0
        if s_type == "article":
            source = "伯乐在线"
            last_seconds,total_nums,hit_list,page_nums = self.get_jobbole(page, key_words)
        elif s_type == "question":
            source = "知乎"
            last_seconds, total_nums, hit_list,page_nums = self.get_zhihu(page, key_words)
        elif s_type == "job":
            source = "拉勾"
            last_seconds, total_nums, hit_list,page_nums = self.get_lagou(page, key_words)

        return render(request, "result.html", {"page": page,
                                               "all_hits": hit_list,
                                               "key_words": key_words,
                                               "total_nums": total_nums,
                                               "page_nums": page_nums,
                                               "last_seconds":last_seconds,
                                               "jobbole_count":jobbole_count,
                                               "lagou_count": lagou_count,
                                               "zhihu_count": zhihu_count,
                                               "topn_search":topn_search,
                                               "source":source})
    def get_jobbole(self, page, key_words):
        start_time = datetime.now()
        response = client.search(
            index="jobbole",
            body={
                "query": {
                    "multi_match": {
                        "query": key_words,
                        "fields": ["tags", "title", "content"]
                    }
                },
                "from": (page - 1) * 10,
                "size": 10,
                "highlight": {
                    "pre_tags": ['<span class="keyWord">'],
                    "post_tags": ['</span>'],
                    "fields":  {
                        "title": {},
                        "content": {},
                    }
                }
            }
        )
        end_time = datetime.now()
        last_seconds = (end_time - start_time).total_seconds()
        total_nums = response["hits"]["total"]
        if (page % 10) > 0:
            page_nums = int(total_nums / 10) + 1
        else:
            page_nums = int(total_nums / 10)
        hit_list = []
        for hit in response["hits"]["hits"]:
            hit_dict = {}
            if "title" in hit["highlight"]:
                hit_dict["title"] = "".join(hit["highlight"]["title"])
            else:
                hit_dict["title"] = hit["_source"]["title"]
            if "content" in hit["highlight"]:
                hit_dict["content"] = "".join(hit["highlight"]["content"])[:500]
            else:
                hit_dict["content"] = hit["_source"]["content"][:500]

            hit_dict["create_date"] = hit["_source"]["create_date"]
            hit_dict["url"] = hit["_source"]["url"]
            hit_dict["score"] = hit["_score"]

            hit_list.append(hit_dict)
        return last_seconds,total_nums,hit_list,page_nums

    def get_zhihu(self, page, key_words):
        start_time = datetime.now()
        response = client.search(
            index="zhihu",
            body={
                "query": {
                    "multi_match": {
                        "query": key_words,
                        "fields": [ "title", "content"]
                    }
                },
                "from": (page - 1) * 10,
                "size": 10,
                "highlight": {
                    "pre_tags": ['<span class="keyWord">'],
                    "post_tags": ['</span>'],
                    "fields":  {
                        "title": {},
                        "content": {},
                    }
                }
            }
        )
        end_time = datetime.now()
        last_seconds = (end_time - start_time).total_seconds()
        total_nums = response["hits"]["total"]
        if (page % 10) > 0:
            page_nums = int(total_nums / 10) + 1
        else:
            page_nums = int(total_nums / 10)
        hit_list = []
        for hit in response["hits"]["hits"]:
            hit_dict = {}
            if "title" in hit["highlight"]:
                hit_dict["title"] = "".join(hit["highlight"]["title"])
            else:
                hit_dict["title"] = hit["_source"]["title"]
            if "content" in hit["highlight"]:
                hit_dict["content"] = "".join(hit["highlight"]["content"])[:500]
            else:
                hit_dict["content"] = hit["_source"]["content"][:500]

            hit_dict["create_date"] = hit["_source"]["crawl_time"]
            hit_dict["url"] = hit["_source"]["url"]
            hit_dict["score"] = hit["_score"]

            hit_list.append(hit_dict)
        return last_seconds,total_nums,hit_list,page_nums

    def get_lagou(self, page, key_words):
        start_time = datetime.now()
        response = client.search(
            index="lagou",
            body={
                "query": {
                    "multi_match": {
                        "query": key_words,
                        "fields": ["tags", "title", "job_desc"]
                    }
                },
                "from": (page - 1) * 10,
                "size": 10,
                "highlight": {
                    "pre_tags": ['<span class="keyWord">'],
                    "post_tags": ['</span>'],
                    "fields":  {
                        "title": {},
                        "job_desc": {},
                    }
                }
            }
        )
        end_time = datetime.now()
        last_seconds = (end_time - start_time).total_seconds()
        total_nums = response["hits"]["total"]
        if (page % 10) > 0:
            page_nums = int(total_nums / 10) + 1
        else:
            page_nums = int(total_nums / 10)
        hit_list = []
        for hit in response["hits"]["hits"]:
            hit_dict = {}
            if "title" in hit["highlight"]:
                hit_dict["title"] = "".join(hit["highlight"]["title"])
            else:
                hit_dict["title"] = hit["_source"]["title"]
            if "content" in hit["highlight"]:
                hit_dict["content"] = "".join(hit["highlight"]["job_desc"])[:800]
            else:
                hit_dict["content"] = hit["_source"]["job_desc"][:800]

            hit_dict["create_date"] = hit["_source"]["publish_time"]
            hit_dict["url"] = hit["_source"]["url"]
            hit_dict["score"] = hit["_score"]

            hit_list.append(hit_dict)
        return last_seconds,total_nums,hit_list,page_nums