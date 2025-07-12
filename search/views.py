# search/views.py - Complete Refined version with natural summaries

import json
import requests
import logging
import time

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Min, Max
from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse
from .serializers import FacilitySerializer
from bedupdates.models import BedAvailability
from .ollama_utils import ollama_chat
from bs4 import BeautifulSoup

from .models import Facility

# Set up logging
logger = logging.getLogger(__name__)

# Speed-optimized Template Views
def home(request):
    """Speed-optimized home view with natural engaging summaries under 3 seconds"""
    query = request.GET.get("q", "").strip()
    bed_count_filter = request.GET.get("bed_count", "").strip()
    selected_facility_types = request.GET.getlist("facility_type")
    sort_by = request.GET.get("sort_by", "name").strip()

    # Start with only active facilities
    facilities = Facility.objects.filter(status='active')
    ai_summary = ""
    search_count = 0

    # Apply search query first
    if query:
        # Use the improved search function for better results
        facilities = improved_search(facilities, query)
        search_count = facilities.count()

        # Apply filters only if a query is entered
        # Filter by selected facility types
        if selected_facility_types:
            type_query = Q(endorsement__icontains=selected_facility_types[0])
            for facility_type in selected_facility_types[1:]:
                type_query |= Q(endorsement__icontains=facility_type)
            facilities = facilities.filter(type_query)

        # Filter by bed count
        if bed_count_filter.isdigit():
            facilities = facilities.filter(bed_count=int(bed_count_filter))

        # Generate FAST natural summary to hook users
        if facilities.exists():
            ai_summary = generate_natural_hook_summary(facilities, query)
        else:
            ai_summary = generate_natural_no_results_hook(query)

        # Sorting
        sorting_options = {
            "name": "name",
            "bed_count": "bed_count",
            "-bed_count": "-bed_count",
            "relevance": "-relevance",
        }
        if sort_by in sorting_options:
            facilities = facilities.order_by(sorting_options[sort_by])
    
    # Get bed data for each facility
    facilities_list = list(facilities)
    for facility in facilities_list:
        try:
            bed_data = BedAvailability.objects.filter(facility=facility).latest('updated_at')
            facility.bed_data = bed_data
        except BedAvailability.DoesNotExist:
            facility.bed_data = None
    
    # Pagination
    paginator = Paginator(facilities_list, 10)
    page = request.GET.get('page')
    
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # Get min and max bed counts for filter dropdown
    bed_counts = Facility.objects.filter(status='active').values_list('bed_count', flat=True).distinct().order_by('bed_count')
    
    context = {
        'page_obj': page_obj,  
        'query': query,
        'selected_facility_types': selected_facility_types,
        'bed_count_filter': bed_count_filter,
        'sort_by': sort_by,
        'bed_counts': bed_counts,
        'ai_summary': ai_summary,
        'search_count': search_count,
    }
    
    return render(request, "search/home.html", context)

def facility_detail(request, facility_id):
    """Enhanced facility detail view with quick insights"""
    facility = get_object_or_404(Facility, id=facility_id, status='active')
    
    # Get bed data if available
    try:
        bed_data = BedAvailability.objects.filter(facility=facility).latest('updated_at')
        facility.bed_data = bed_data
    except BedAvailability.DoesNotExist:
        facility.bed_data = None
    
    # Generate quick facility insight
    facility_insight = generate_facility_insight(facility)
    
    return render(request, "search/detail.html", {
        "facility": facility,
        "facility_insight": facility_insight
    })

def searxnghome(request):
    """Speed-optimized searxng home for backward compatibility"""
    query = request.GET.get("q", "").strip()
    bed_count_filter = request.GET.get("bed_count", "").strip()
    selected_facility_types = request.GET.getlist("facility_type")
    sort_by = request.GET.get("sort_by", "name").strip()

    # Start with only active facilities
    facilities = Facility.objects.filter(status='active')

    # Apply search query first
    if query:
        facilities = improved_search(facilities, query)

        # Filter by selected facility types
        if selected_facility_types:
            type_query = Q(endorsement__icontains=selected_facility_types[0])
            for facility_type in selected_facility_types[1:]:
                type_query |= Q(endorsement__icontains=facility_type)
            facilities = facilities.filter(type_query)

        # Filter by bed count
        if bed_count_filter.isdigit():
            facilities = facilities.filter(bed_count=int(bed_count_filter))

        # Sorting
        sorting_options = {
            "name": "name",
            "bed_count": "bed_count",
            "-bed_count": "-bed_count",
        }
        if sort_by in sorting_options:
            facilities = facilities.order_by(sorting_options[sort_by])

    # Pagination
    paginator = Paginator(facilities, 15)
    page_number = request.GET.get("page")
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Get distinct bed counts for the filter dropdown
    bed_counts = Facility.objects.filter(status='active').values_list("bed_count", flat=True).distinct().order_by("bed_count")

    return render(request, "search/searxng_home.html", {
        "page_obj": page_obj,
        "query": query,
        "bed_counts": bed_counts,
        "sort_by": sort_by,
        "bed_count_filter": bed_count_filter,
        "selected_facility_types": selected_facility_types,
    })

def searxngfacilitydetail(request, facility_id):
    """Searxng facility detail view"""
    facility = get_object_or_404(Facility, id=facility_id, status='active')
    context = {
        "facility": facility,
        "request": request,
    }
    return render(request, "search/detail_searxng.html", context)

def ollama_search(request):
    """Speed-optimized ollama search with natural summaries"""
    query = request.GET.get("q", "").strip()
    bed_count_filter = request.GET.get("bed_count", "").strip()
    selected_facility_types = request.GET.getlist("facility_type")
    sort_by = request.GET.get("sort_by", "name").strip()

    # Start with only active facilities
    facilities = Facility.objects.filter(status='active')
    ai_summary = ""
    search_count = 0

    # Apply search query first
    if query:
        # Use the improved search function for better results
        facilities = improved_search(facilities, query)
        search_count = facilities.count()

        # Apply filters only if a query is entered
        # Filter by selected facility types
        if selected_facility_types:
            type_query = Q(endorsement__icontains=selected_facility_types[0])
            for facility_type in selected_facility_types[1:]:
                type_query |= Q(endorsement__icontains=facility_type)
            facilities = facilities.filter(type_query)

        # Filter by bed count
        if bed_count_filter.isdigit():
            facilities = facilities.filter(bed_count=int(bed_count_filter))

        # Generate FAST natural summary to hook users
        if facilities.exists():
            ai_summary = generate_natural_hook_summary(facilities, query)
        else:
            ai_summary = generate_natural_no_results_hook(query)

        # Sorting
        sorting_options = {
            "name": "name",
            "bed_count": "bed_count",
            "-bed_count": "-bed_count",
            "relevance": "-relevance",
        }
        if sort_by in sorting_options:
            facilities = facilities.order_by(sorting_options[sort_by])

    # Pagination
    paginator = Paginator(facilities, 15)
    page_number = request.GET.get("page")
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Get distinct bed counts for the filter dropdown
    bed_counts = Facility.objects.filter(status='active').values_list("bed_count", flat=True).distinct().order_by("bed_count")

    return render(request, "search/ollama_search.html", {
        "page_obj": page_obj,
        "query": query,
        "bed_counts": bed_counts,
        "sort_by": sort_by,
        "bed_count_filter": bed_count_filter,
        "selected_facility_types": selected_facility_types,
        "ai_summary": ai_summary,
        "search_count": search_count,
    })

# NATURAL SUMMARY GENERATION FUNCTIONS

def generate_natural_hook_summary(facilities, query):
    """
    Generate natural, informative summary without specific recommendations
    """
    start_time = time.time()
    count = facilities.count()
    
    # Get analytics quickly
    min_beds = facilities.aggregate(Min('bed_count'))['bed_count__min']
    max_beds = facilities.aggregate(Max('bed_count'))['bed_count__max']
    
    # Extract locations and facility types
    cities = set()
    facility_types = set()
    specialties = set()
    
    for facility in facilities[:10]:  # Analyze first 10 for speed
        if facility.address:
            city = facility.address.split(',')[0].strip()
            if city:
                cities.add(city)
        if facility.facility_type:
            facility_types.add(facility.facility_type)
        if facility.endorsement:
            # Extract specialties
            facility_specialties = [s.strip() for s in facility.endorsement.split(',')[:3]]
            specialties.update(facility_specialties)
    
    # Try fast AI summary first (2-3 seconds max)
    ai_summary = try_natural_ai_summary(query, count, cities, facility_types, specialties, min_beds, max_beds)
    
    # If AI fails or takes too long, use smart instant summary
    elapsed = time.time() - start_time
    if not ai_summary or elapsed > 2.5 or ai_summary.startswith("Error"):
        ai_summary = generate_natural_instant_summary(query, count, cities, facility_types, specialties, min_beds, max_beds)
    
    logger.info(f"Summary generated in {time.time() - start_time:.2f} seconds for query: {query}")
    return ai_summary

def try_natural_ai_summary(query, count, cities, facility_types, specialties, min_beds, max_beds):
    """
    Attempt fast AI summary with natural language approach
    """
    try:
        # Extract key terms from query for natural reference
        query_terms = extract_key_terms(query)
        
        # Build context for AI
        context_data = {
            'search_type': determine_search_type(query),
            'count': count,
            'bed_range': f"{min_beds}-{max_beds}" if min_beds != max_beds else str(min_beds),
            'locations': list(cities)[:3],
            'facility_types': list(facility_types)[:3],
            'specialties': list(specialties)[:4]
        }

        # Natural prompt without exact query repetition
        prompt = f"""Create a natural summary for healthcare facility search results:

Search context: {query_terms['care_type']} in {query_terms['location']} area
Results: {count} facilities found
Bed capacity: {context_data['bed_range']} beds
Locations: {context_data['locations']}
Specialties: {context_data['specialties'][:3]}

Write 2-3 sentences that:
- Mention the number of facilities found
- Reference bed capacity range if meaningful
- Mention service areas if location was searched
- Note specializations if relevant to search
- End with encouraging users to compare facilities to find their best fit

Keep natural and informative without specific facility names."""

        response = requests.post(
            'http://my-ollama-llama31.h2ffbjbfh3fveffu.westus2.azurecontainer.io:11434/api/generate',
            json={
                'model': 'mistral:7b',
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.3,
                    'num_ctx': 512,
                    'num_predict': 100,
                }
            },
            timeout=3
        )
        
        if response.status_code == 200:
            return response.json()['response'].strip()
        else:
            return None
            
    except Exception as e:
        logger.warning(f"Natural AI summary failed: {str(e)}")
        return None

def generate_natural_instant_summary(query, count, cities, facility_types, specialties, min_beds, max_beds):
    """
    Generate natural instant summary without AI (under 0.5 seconds)
    """
    query_terms = extract_key_terms(query)
    
    # Start with count
    if count == 1:
        summary = f"{count} facility matches your search criteria"
    else:
        summary = f"{count} facilities match your search criteria"
    
    # Add bed capacity information
    if min_beds and max_beds:
        if min_beds == max_beds:
            summary += f", each offering {min_beds} beds"
        else:
            summary += f" with bed capacity ranging from {min_beds} to {max_beds}"
    
    # Add location information if location was in query
    if query_terms['location'] and cities:
        city_list = list(cities)
        if len(city_list) == 1:
            summary += f". Services are available in the {city_list[0]} area"
        elif len(city_list) <= 3:
            summary += f". Services are available across {', '.join(city_list[:2])}"
            if len(city_list) == 3:
                summary += f" and {city_list[2]}"
        else:
            summary += f". Services are available in {city_list[0]} and {len(city_list)-1} other locations"
    
    # Add specialty information if care type was in query
    if query_terms['care_type'] and specialties:
        relevant_specialties = [s for s in specialties if any(term in s.lower() for term in query_terms['care_type'].lower().split())][:2]
        if relevant_specialties:
            if len(relevant_specialties) == 1:
                summary += f". These facilities specialize in {relevant_specialties[0].lower()}"
            else:
                summary += f". These facilities specialize in {relevant_specialties[0].lower()} and {relevant_specialties[1].lower()}"
        elif specialties:
            specialty_list = list(specialties)[:2]
            summary += f". Available specialties include {specialty_list[0].lower()}"
            if len(specialty_list) > 1:
                summary += f" and {specialty_list[1].lower()}"
    
    # Natural ending encouraging comparison
    summary += ". Please compare the available facilities to find the best fit for your specific needs."
    
    return summary

def generate_natural_no_results_hook(query):
    """
    Generate natural no-results message
    """
    query_terms = extract_key_terms(query)
    
    summary = "No facilities found matching your specific search criteria"
    
    # Provide helpful suggestions based on query components
    suggestions = []
    
    if query_terms['location']:
        suggestions.append(f"try expanding your search to areas near {query_terms['location']}")
    
    if query_terms['care_type']:
        suggestions.append(f"search for {query_terms['care_type']} without location restrictions")
    
    if not suggestions:
        suggestions.append("try broader search terms")
        suggestions.append("search by location only")
    
    if suggestions:
        summary += ". Consider these alternatives: " + suggestions[0]
        if len(suggestions) > 1:
            summary += f" or {suggestions[1]}"
    
    summary += ". Complete the form below and our specialists will help you find suitable facilities in your preferred area."
    
    return summary

def extract_key_terms(query):
    """
    Extract key terms from query for natural language generation
    """
    query_lower = query.lower()
    
    # Identify care types
    care_types = {
        'assisted living': ['assisted living', 'assisted', 'independent living'],
        'memory care': ['alzheimer', 'memory care', 'dementia'],
        'nursing care': ['nursing home', 'skilled nursing', 'nursing'],
        'senior care': ['senior', 'elderly', 'elder care'],
        'rehabilitation': ['rehab', 'rehabilitation', 'physical therapy'],
        'respite care': ['respite', 'temporary care'],
        'hospice care': ['hospice', 'end of life'],
    }
    
    care_type = None
    for care_name, keywords in care_types.items():
        if any(keyword in query_lower for keyword in keywords):
            care_type = care_name
            break
    
    # Identify locations (simplified)
    location_indicators = ['in', 'near', 'around', 'at']
    location = None
    
    words = query.split()
    for i, word in enumerate(words):
        if word.lower() in location_indicators and i + 1 < len(words):
            location = ' '.join(words[i+1:])
            break
    
    # If no location indicator, check for common city names or zip codes
    if not location:
        for word in words:
            if word.isdigit() and len(word) == 5:  # ZIP code
                location = word
                break
            elif len(word) > 3 and word[0].isupper():  # Likely city name
                location = word
                break
    
    return {
        'care_type': care_type or 'healthcare services',
        'location': location or 'your area'
    }

def determine_search_type(query):
    """
    Determine the type of search for context
    """
    query_lower = query.lower()
    
    if any(term in query_lower for term in ['assisted living', 'assisted']):
        return 'assisted_living'
    elif any(term in query_lower for term in ['alzheimer', 'memory', 'dementia']):
        return 'memory_care'
    elif any(term in query_lower for term in ['nursing', 'skilled']):
        return 'nursing_care'
    elif any(term in query_lower for term in ['senior', 'elderly']):
        return 'senior_care'
    else:
        return 'general_care'

def generate_facility_insight(facility):
    """
    Generate quick facility insight for detail pages
    """
    insights = []
    
    # Capacity insight
    if facility.bed_count:
        if facility.bed_count <= 30:
            insights.append(f"Intimate community with {facility.bed_count} beds for personalized attention")
        elif facility.bed_count <= 80:
            insights.append(f"Mid-sized facility with {facility.bed_count} beds balancing personal care and comprehensive services")
        else:
            insights.append(f"Large facility with {facility.bed_count} beds offering extensive programs and specialized care")
    
    # Location insight
    if facility.address:
        city = facility.address.split(',')[0].strip()
        insights.append(f"Located in {city} for convenient family access")
    
    # Specialization insight
    if facility.endorsement:
        specialties = [s.strip() for s in facility.endorsement.split(',')[:2]]
        if len(specialties) == 1:
            insights.append(f"Specialized care includes {specialties[0].lower()}")
        else:
            insights.append(f"Specialized services include {specialties[0].lower()} and {specialties[1].lower()}")
    
    if insights:
        return ". ".join(insights) + ". Contact them directly to discuss your specific care requirements and available options."
    else:
        return f"This facility offers comprehensive care services. Contact them directly to learn more about their programs and how they can meet your specific needs."

# Helper functions (speed-optimized)

def improved_search(queryset, query):
    """
    Speed-optimized search function
    """
    from django.db.models import Q
    
    # Ensure we only search active facilities
    queryset = queryset.filter(status='active')
    
    # Clean and normalize query
    query = query.strip()
    
    # Check for empty query
    if not query:
        return queryset.none()
    
    # Split query into words for flexible searching
    words = [word for word in query.split() if len(word) > 1]
    
    if not words:
        return queryset.none()
    
    # Build search query
    search_q = Q()
    
    # Search across main fields
    for word in words:
        word_q = (
            Q(name__icontains=word) |
            Q(address__icontains=word) |
            Q(state__icontains=word) |
            Q(county__icontains=word) |
            Q(facility_type__icontains=word) |
            Q(endorsement__icontains=word)
        )
        
        if not search_q:
            search_q = word_q
        else:
            search_q &= word_q  # AND for multiple words
    
    # Apply search
    results = queryset.filter(search_q)
    
    # If no results with AND, try OR for broader results
    if not results.exists() and len(words) > 1:
        or_q = Q()
        for word in words:
            or_q |= (
                Q(name__icontains=word) |
                Q(address__icontains=word) |
                Q(state__icontains=word) |
                Q(county__icontains=word) |
                Q(facility_type__icontains=word) |
                Q(endorsement__icontains=word)
            )
        results = queryset.filter(or_q)
    
    return results

# API Views (simplified for speed)

@api_view(['GET'])
def facility_list(request):
    """
    Speed-optimized API endpoint to list facilities
    """
    query = request.GET.get('q', '')
    facilities = Facility.objects.filter(status='active')
    
    if query:
        facilities = improved_search(facilities, query)
    
    # Limit results for speed
    facilities = facilities[:50]
    
    serializer = FacilitySerializer(facilities, many=True)
    
    return Response({
        'results': serializer.data,
        'count': len(serializer.data),
    })

@api_view(['GET'])
def api_facility_detail(request, pk):
    """
    API endpoint for facility detail
    """
    try:
        facility = Facility.objects.get(pk=pk, status='active')
        
        # Add bed data if available
        try:
            bed_data = BedAvailability.objects.filter(facility=facility).latest('updated_at')
            facility.bed_data = bed_data
        except BedAvailability.DoesNotExist:
            facility.bed_data = None
            
        serializer = FacilitySerializer(facility)
        return Response(serializer.data)
    except Facility.DoesNotExist:
        return Response({'error': 'Facility not found'}, status=404)

def search_suggestions(request):
    """
    Fast search suggestions
    """
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    suggestions = []
    
    # Quick suggestions from facility names
    facilities = Facility.objects.filter(status='active', name__icontains=query)[:3]
    for facility in facilities:
        suggestions.append({
            'text': facility.name,
            'type': 'facility_name'
        })
    
    # Add common search suggestions
    common_searches = [
        'assisted living', 'memory care', 'nursing home', 
        'senior care', 'rehabilitation', 'respite care'
    ]
    for search_term in common_searches:
        if query.lower() in search_term.lower():
            suggestions.append({
                'text': search_term,
                'type': 'care_type'
            })
    
    return JsonResponse({'suggestions': suggestions[:5]})

def health_check(request):
    """
    Quick health check endpoint
    """
    try:
        facility_count = Facility.objects.filter(status='active').count()
        return JsonResponse({
            'status': 'healthy',
            'active_facilities': facility_count,
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=500)