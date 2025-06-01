

@api_view(['GET'])
def search_suggestions(request):
    try:
        query = request.GET.get("query", "").strip()
        if not query:
            return JsonResponse({"locations": []})
        
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={'q': query, 'format': 'json', 'addressdetails': 1, 'limit': 5}
        )
        return JsonResponse({"locations": response.json()})
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
    


@api_view(['GET'])
def search_suggestions(request):
    try:
        query = request.GET.get("query", "").strip()
        if not query:
            return JsonResponse({"locations": []})
        
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={'q': query, 'format': 'json', 'addressdetails': 1, 'limit': 5}
        )
        return JsonResponse({"locations": response.json()})
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
    
    
    
  
    
    
    
# API Views
# views.py (Django)
@api_view(['GET'])
def facility_list(request):
    query = request.GET.get("q", "")
    bed_count = request.GET.get("bed_count", "")
    sort_by = request.GET.get("sort_by", "name")

    facilities = Facility.objects.all()

    # Filter by search query
    if query:
        facilities = facilities.filter(
            Q(address__icontains=query) |
            Q(county__icontains=query) |
            Q(state__icontains=query)
        )
    
    # Filter by bed count
    if bed_count.isdigit():
        facilities = facilities.filter(bed_count=int(bed_count))

    # Validate and apply sorting
    valid_sorts = ['name', 'bed_count', '-bed_count']
    if sort_by in valid_sorts:
        facilities = facilities.order_by(sort_by)

    # Pagination
    paginator = Paginator(facilities, 12)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    serializer = FacilitySerializer(page_obj, many=True)
    return Response({
        "results": serializer.data,
        "current_page": page_obj.number,
        "total_pages": paginator.num_pages
    })
    
@api_view(['GET'])
def api_facility_detail(request, pk):  # Renamed from facility_detail
    facility = get_object_or_404(Facility, pk=pk)
    serializer = FacilitySerializer(facility)
    return Response(serializer.data)

def searxng(request):
    # Dummy external search results
    external_results = [
        {'title': 'Care Facility A', 'url': 'https://example.com/a'},
        {'title': 'Care Facility B', 'url': 'https://example.com/b'},
    ]
    return render(request, 'search/searxng.html', {
        'external_results': external_results,
    })
def perplexica(request):
    external_results = [
        {'title': 'Facility Alpha', 'url': 'https://example.com/alpha', 'rating': '4.5'},
        {'title': 'Facility Beta', 'url': 'https://example.com/beta', 'rating': '4.2'},
    ]
    return render(request, 'search/perplexica.html', {
        'external_results': external_results,
    })
def combined(request):
    ai_summary = "Combined AI Summary: Comprehensive overview of facilities..."
    external_results = [
        {'title': 'Facility Combined A', 'url': 'https://example.com/ca'},
        {'title': 'Facility Combined B', 'url': 'https://example.com/cb'},
    ]
    return render(request, 'search/combined.html', {
        'ai_summary': ai_summary,
        'external_results': external_results,
    })


