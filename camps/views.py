"""Camp overview pages (SPEC §9.2)."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from camps.models import Camp


def camp_list(request: HttpRequest) -> HttpResponse:
    camps = Camp.objects.all()
    return render(request, "camps/camp_list.html", {"camps": camps})
