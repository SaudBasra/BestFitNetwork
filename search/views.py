import json
import requests

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Min, Max
from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse

from .models import Facility
from .serializers import FacilitySerializer
from bedupdates.models import BedAvailability  # Import BedData model
from .ollama_utils import ollama_chat
from bs4 import BeautifulSoup


# Template Views
def home(request):
    query = request.GET.get("q", "").strip()
    bed_count_filter = request.GET.get("bed_count", "").strip()
    selected_facility_types = request.GET.getlist("facility_type")
    sort_by = request.GET.get("sort_by", "name").strip()

    # Start with all facilities
    facilities = Facility.objects.all()

    # Apply search query first
    if query:
        facilities = facilities.filter(
            address__icontains=query
        )  # Replace with the fields you want to search

    # Apply filters only if a query is entered
    if query:
        # Filter by selected facility types
        if selected_facility_types:
            facilities = facilities.filter(endorsement__icontains=selected_facility_types[0])
            for facility_type in selected_facility_types[1:]:
                facilities = facilities | Facility.objects.filter(endorsement__icontains=facility_type)

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
    
    # Get bed data for each facility
    facilities_list = list(facilities)
    for facility in facilities_list:
        try:
            bed_data = BedAvailability.objects.filter(facility=facility).latest('updated_at')
            facility.bed_data = bed_data
        except BedAvailability.DoesNotExist:
            facility.bed_data = None
    
    # Pagination
    paginator = Paginator(facilities_list, 10)  # Show 10 facilities per page
    page = request.GET.get('page')
    
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # Get min and max bed counts for filter dropdown
    bed_counts = Facility.objects.values_list('bed_count', flat=True).distinct().order_by('bed_count')
    
    context = {
        'page_obj': page_obj,  
        'query': query,
        'selected_facility_types': selected_facility_types,
        'bed_count_filter': bed_count_filter,
        'sort_by': sort_by,
        'bed_counts': bed_counts,
    }
    
    return render(request, "search/home.html", context)

def facility_detail(request, facility_id):  # Template view
    facility = get_object_or_404(Facility, id=facility_id)
    
    # Get bed data if available
    try:
        bed_data = BedAvailability.objects.filter(facility=facility).latest('updated_at')
        facility.bed_data = bed_data
    except BedAvailability.DoesNotExist:
        facility.bed_data = None
        
    return render(request, "search/detail.html", {"facility": facility})
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
    bed_counts = Facility.objects.values_list("bed_count", flat=True).distinct().order_by("bed_count")

    return render(request, "search/home.html", {
        "page_obj": page_obj,
        "query": query,
        "bed_counts": bed_counts,
        "sort_by": sort_by,
        "bed_count_filter": bed_count_filter,
        "selected_facility_types": selected_facility_types,
    })


def searxnghome(request):
    query = request.GET.get("q", "").strip()
    bed_count_filter = request.GET.get("bed_count", "").strip()
    selected_facility_types = request.GET.getlist("facility_type")
    sort_by = request.GET.get("sort_by", "name").strip()

    # Start with all facilities
    facilities = Facility.objects.all()

    # Apply search query first
    if query:
        facilities = facilities.filter(
            address__icontains=query
        )

    if query:
        # Filter by selected facility types
        if selected_facility_types:
            facilities = facilities.filter(endorsement__icontains=selected_facility_types[0])
            for facility_type in selected_facility_types[1:]:
                facilities = facilities | Facility.objects.filter(endorsement__icontains=facility_type)

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
    bed_counts = Facility.objects.values_list("bed_count", flat=True).distinct().order_by("bed_count")

    return render(request, "search/searxng_home.html", {
        "page_obj": page_obj,
        "query": query,
        "bed_counts": bed_counts,
        "sort_by": sort_by,
        "bed_count_filter": bed_count_filter,
        "selected_facility_types": selected_facility_types,
    })
    

# Searxng facility detail view
#def searxngfacilitydetail(request, facility_id):
 #   facility = get_object_or_404(Facility, id=facility_id)
  #  return render(request, "search/detail_searxng.html", {"facility": facility})
# Import necessary modules
# Import necessary modules
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import logging
import random
from .models import Facility

# Set up logging
logger = logging.getLogger(__name__)

# Searxng facility detail view
def searxngfacilitydetail(request, facility_id):
    """
    View function to display the detail page for a specific facility
    """
    facility = get_object_or_404(Facility, id=facility_id)
    context = {
        "facility": facility,
        "request": request,  # Pass request to allow template to access GET parameters
    }
    return render(request, "search/detail_searxng.html", context)

# API for fetching insights - simple version for MVP
@require_http_methods(["GET"])
def facility_insights_api(request, facility_name):
    """
    API endpoint to fetch demo insights about a facility for MVP demo
    """
    # Sanitize the query
    query = facility_name.strip()
    if not query:
        return JsonResponse({"error": "Invalid facility name", "results": []})
    
    try:
        # Generate demo insights for the MVP
        results = generate_demo_insights(facility_name)
        return JsonResponse({"results": results})
    
    except Exception as e:
        logger.error(f"Error generating insights for {query}: {str(e)}")
        return JsonResponse({"error": str(e), "results": []})

def generate_demo_insights(facility_name):
    """
    Generate realistic-looking demo insights for the MVP with actual URLs
    """
    # Get facility name parts for use in generated content
    words = facility_name.split()
    name_part = words[0] if words else facility_name
    
    # Create search query string for URLs
    search_query = facility_name.replace(' ', '+')
    
    # List of possible care services for randomization
    care_services = [
        "Memory Care", "Assisted Living", "Skilled Nursing", 
        "Rehabilitation Services", "Long-term Care", "Respite Care",
        "24/7 Nursing Support", "Personal Care Services", "Medication Management"
    ]
    
    # List of possible amenities for randomization
    amenities = [
        "Private Rooms", "Semi-Private Rooms", "Dining Services", 
        "Activity Programs", "Transportation Services", "Therapy Services",
        "Garden Areas", "Community Spaces", "Family Visitation Areas"
    ]
    
    # Randomly select some services and amenities
    selected_services = random.sample(care_services, min(3, len(care_services)))
    selected_amenities = random.sample(amenities, min(3, len(amenities)))
    
    # Define templates for demo insights with realistic URLs
    templates = [
        {
            "title": f"{facility_name} - Care Home Overview",
            "url": f"https://www.google.com/search?q={search_query}+care+home",
            "snippet": f"{facility_name} provides quality care services in a comfortable environment. They specialize in {', '.join(selected_services[:2])} and other personalized care solutions for residents with varying needs."
        },
        {
            "title": f"About {name_part} Services and Programs",
            "url": f"https://www.medicare.gov/care-compare/?providerType=NursingHome&redirect=true#{search_query}",
            "snippet": f"{facility_name} offers comprehensive healthcare services including {', '.join(selected_services)}. Their professional staff is trained to provide excellent care and support to all residents."
        },
        {
            "title": f"{facility_name} Facilities and Amenities",
            "url": f"https://www.seniorliving.org/nursing-homes/search/?q={search_query}",
            "snippet": f"Residents at {facility_name} enjoy access to various amenities including {', '.join(selected_amenities)}. The facility is designed to create a comfortable and supportive environment for all residents."
        },
        {
            "title": f"Staff and Care at {name_part}",
            "url": f"https://www.caring.com/senior-living/assisted-living/search?q={search_query}",
            "snippet": f"{facility_name} employs qualified healthcare professionals dedicated to providing exceptional care. Their staff includes registered nurses, care assistants, and support personnel available 24/7."
        },
        {
            "title": f"Reviews of {facility_name}",
            "url": f"https://www.yelp.com/search?find_desc={search_query}+care+home",
            "snippet": f"Families of residents at {facility_name} have noted the quality of care provided. They particularly appreciate the {random.choice(selected_services).lower()} and the {random.choice(selected_amenities).lower()} available to residents."
        },
        {
            "title": f"{facility_name} Location and Accessibility",
            "url": f"https://maps.google.com/?q={search_query}+care+home",
            "snippet": f"Located in a convenient area, {facility_name} is easily accessible to visitors. The facility provides a safe and secure environment for residents while maintaining a welcoming atmosphere for family members."
        }
    ]
    
    # Return 3-4 random insights for variety
    num_results = random.randint(3, 4)
    random.shuffle(templates)
    return templates[:num_results]
#..............................................................................
def ollama_search(request):
    query = request.GET.get("q", "").strip()
    bed_count_filter = request.GET.get("bed_count", "").strip()
    selected_facility_types = request.GET.getlist("facility_type")
    sort_by = request.GET.get("sort_by", "name").strip()

    # Start with all facilities
    facilities = Facility.objects.all()
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

        # Generate AI summary if there are results
        if facilities.exists():
            # Prepare data for Ollama
            facility_data = []
            for facility in facilities[:15]:  # Limit to first 15 for summary
                facility_data.append({
                    'name': facility.name,
                    'type': facility.facility_type,
                    'endorsement': facility.endorsement,
                    'address': facility.address,
                    'bed_count': facility.bed_count,
                    'state': facility.state,
                    'county': facility.county,
                })
            
            # Get bed count range
            min_beds = facilities.aggregate(Min('bed_count'))['bed_count__min']
            max_beds = facilities.aggregate(Max('bed_count'))['bed_count__max']
            
            # Extract facility types for context
            facility_types = set()
            endorsements = set()
            for facility in facilities[:20]:  # Sample for variety
                if facility.facility_type:
                    facility_types.add(facility.facility_type)
                if facility.endorsement:
                    endorsements.update([e.strip() for e in facility.endorsement.split(',')])
            
            # Create an enhanced prompt for Ollama to generate a professional summary
            summary_prompt = f"""
            Analyze these healthcare facilities matching the search "{query}":
            {facility_data}

            User query context: "{query}"
            Total facilities found: {facilities.count()}
            Bed capacity range: {min_beds} to {max_beds}
            Facility types: {list(facility_types)}
            Endorsements/Specialties: {list(endorsements)}

            Create a personalized, insightful summary that:
            1. Directly addresses the query intent (e.g., if searching for "assisted living in Las Vegas," focus on Las Vegas options)
            2. Highlights the MOST RELEVANT facilities and WHY they match the query (e.g., specialized care, location)
            3. If multiple facility types are found, compare their offerings relevant to the query
            4. Mention specific locations if the query includes location terms
            5. Provide 1-2 specific facility recommendations with brief reasoning (e.g., "Mother's Love stands out for its 24/7 care and specialized Alzheimer's program")

            Rules:
            - Be specific and factual based ONLY on the data provided
            - If searching for multiple conditions (e.g., "Alzheimer's and disabled care"), specifically address facilities that offer BOTH
            - If searching for a location, emphasize facilities in that specific location
            - Be concise but informative (4-5 sentences)
            - Write in a professional healthcare advisor tone
            - Do NOT mention this being AI-generated or use disclaimers
            """
            
            try:
                # Get response from Ollama
                ai_summary = ollama_chat(summary_prompt)
                
                # Fallback if Ollama returns an error
                if ai_summary.startswith("Error") or ai_summary.startswith("Exception") or ai_summary.startswith("Could not connect"):
                    ai_summary = generate_fallback_summary(facilities, query, min_beds, max_beds)
            except Exception as e:
                # Simple fallback summary if Ollama fails
                ai_summary = generate_fallback_summary(facilities, query, min_beds, max_beds)
        else:
            # No results found - provide professional guidance
            try:
                no_results_prompt = f"""
                A user searched for healthcare facilities with: "{query}"
                No matching facilities were found in our database.
                
                Analyze the query to determine what type of facility or location they're looking for.
                
                Create a helpful, professional response that:
                1. Acknowledges the lack of results for their specific search
                2. Suggests 2-3 alternative search terms based on their query
                3. If the query includes multiple requirements, suggests searching for them separately
                4. If location is mentioned, suggests nearby areas or postal codes
                
                Format: 3-4 sentences total. Professional healthcare advisor tone.
                Be direct and helpful.
                """
                ai_summary = ollama_chat(no_results_prompt)
                
                # Fallback if Ollama returns an error
                if ai_summary.startswith("Error") or ai_summary.startswith("Exception") or ai_summary.startswith("Could not connect"):
                    ai_summary = generate_no_results_fallback(query)
            except Exception as e:
                # Simple fallback if Ollama fails
                ai_summary = generate_no_results_fallback(query)

        # Sorting
        sorting_options = {
            "name": "name",
            "bed_count": "bed_count",
            "-bed_count": "-bed_count",
            "relevance": "-relevance",  # If we're using the weighted search
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
    bed_counts = Facility.objects.values_list("bed_count", flat=True).distinct().order_by("bed_count")

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

def improved_search(queryset, query):
    """
    Perform an intelligent search that better handles location qualifiers
    and multiple facility type specifications
    """
    from django.db.models import Q, F, Value, IntegerField
    from django.db.models.functions import Greatest
    
    # Clean and normalize query
    query = query.strip()
    
    # Check for empty query
    if not query:
        return queryset.none()
    
    # Parse query to detect various components
    query_components = parse_query(query)
    
    # Extract components
    main_terms = query_components['main_terms']
    location_terms = query_components['location_terms']
    facility_types = query_components['facility_types']
    
    # Initialize empty Q objects for each category
    main_q = Q()
    location_q = Q()
    facility_type_q = Q()
    
    # Process main search terms (name, etc.)
    if main_terms:
        main_query = " ".join(main_terms)
        main_q = (
            Q(name__icontains=main_query) | 
            Q(endorsement__icontains=main_query)
        )
        
        # Also search individual words if multiple words are provided
        if len(main_terms) > 1:
            for term in main_terms:
                if len(term) > 2:  # Skip very short words
                    main_q |= (
                        Q(name__icontains=term) | 
                        Q(endorsement__icontains=term)
                    )
    
    # Process location terms (address, state, county, etc.)
    if location_terms:
        location_query = " ".join(location_terms)
        location_q = (
            Q(address__icontains=location_query) | 
            Q(state__icontains=location_query) | 
            Q(county__icontains=location_query)
        )
        
        # Also search for zip codes and individual location terms
        for term in location_terms:
            # If it looks like a zip code (5 digits)
            if term.isdigit() and len(term) == 5:
                location_q |= Q(address__icontains=term)
            elif len(term) > 2:  # Skip very short words
                location_q |= (
                    Q(address__icontains=term) | 
                    Q(state__icontains=term) | 
                    Q(county__icontains=term)
                )
    
    # Process facility type terms
    if facility_types:
        for facility_type in facility_types:
            facility_type_q |= (
                Q(facility_type__icontains=facility_type) | 
                Q(endorsement__icontains=facility_type)
            )
    
    # Combine queries based on what components were found
    combined_q = Q()
    
    # If we have all components, require matches for each category
    if main_terms and location_terms and facility_types:
        combined_q = main_q & location_q & facility_type_q
    # If we have main terms and location but no facility types
    elif main_terms and location_terms:
        combined_q = main_q & location_q
    # If we have main terms and facility types but no location
    elif main_terms and facility_types:
        combined_q = main_q & facility_type_q
    # If we have location and facility types but no main terms
    elif location_terms and facility_types:
        combined_q = location_q & facility_type_q
    # If we only have one component
    elif main_terms:
        combined_q = main_q
    elif location_terms:
        combined_q = location_q
    elif facility_types:
        combined_q = facility_type_q
    
    # Apply the combined query
    results = queryset.filter(combined_q)
    
    # If no results, try a more relaxed approach
    if not results.exists():
        # Relax the query by using OR instead of AND
        relaxed_q = Q()
        if main_terms:
            relaxed_q |= main_q
        if location_terms:
            relaxed_q |= location_q
        if facility_types:
            relaxed_q |= facility_type_q
        
        results = queryset.filter(relaxed_q)
    
    # Apply ranking to sort by relevance
    return apply_relevance_ranking(results, query_components)

def parse_query(query):
    """
    Parse the query string to detect main terms, location, and facility types
    """
    # Common location indicators
    location_indicators = ["in", "near", "at", "around", "by", "close to"]
    
    # Common facility type keywords
    facility_keywords = [
        "ALZHEIMER", "ASSISTED LIVING", "INTELLECTUAL DISABILIT", 
        "MENTAL ILLNESS", "ELDERLY", "DISABLED", "RESIDENTIAL", 
        "NURSING", "REHAB", "REHABILITATION", "CARE", "HOME", "CENTER"
    ]
    
    # Normalize query
    query = query.upper()  # Convert to uppercase for easier matching
    words = query.split()
    
    # Initialize components
    main_terms = []
    location_terms = []
    facility_types = []
    
    # Detect location part first
    i = 0
    while i < len(words):
        if words[i].lower() in location_indicators and i + 1 < len(words):
            # Collect all words after the location indicator
            j = i + 1
            while j < len(words):
                location_terms.append(words[j])
                j += 1
            i = j  # Skip to the end
        else:
            i += 1
    
    # If no location indicator found, try to detect ZIP codes
    if not location_terms:
        for word in words:
            if word.isdigit() and len(word) == 5:  # Likely a ZIP code
                location_terms.append(word)
    
    # Remove location terms from consideration for other categories
    remaining_words = [w for w in words if w.lower() not in location_indicators and w not in location_terms]
    
    # Detect facility types
    for word in remaining_words:
        for keyword in facility_keywords:
            if keyword in word:
                facility_types.append(word)
                break
    
    # Remaining words are main terms
    main_terms = [w for w in remaining_words if w not in facility_types]
    
    return {
        'main_terms': main_terms,
        'location_terms': location_terms,
        'facility_types': facility_types,
        'original_query': query
    }

def apply_relevance_ranking(queryset, query_components):
    """
    Apply relevance ranking to search results
    """
    from django.db.models import Case, When, Value, IntegerField, F
    
    # Extract components
    main_terms = query_components['main_terms']
    location_terms = query_components['location_terms']
    facility_types = query_components['facility_types']
    original_query = query_components['original_query']
    
    # Prepare annotation parameters
    annotation_params = {}
    
    # Name exact match gets highest score
    annotation_params['name_exact_match'] = Case(
        When(name__iexact=original_query, then=Value(100)),
        default=Value(0),
        output_field=IntegerField()
    )
    
    # Name contains full query
    annotation_params['name_contains'] = Case(
        When(name__icontains=original_query, then=Value(50)),
        default=Value(0),
        output_field=IntegerField()
    )
    
    # Location match
    if location_terms:
        location_query = " ".join(location_terms)
        annotation_params['location_match'] = Case(
            When(address__icontains=location_query, then=Value(40)),
            When(county__icontains=location_query, then=Value(30)),
            When(state__icontains=location_query, then=Value(20)),
            default=Value(0),
            output_field=IntegerField()
        )
    else:
        annotation_params['location_match'] = Value(0, output_field=IntegerField())
    
    # Facility type match
    if facility_types:
        facility_query = " ".join(facility_types)
        annotation_params['facility_match'] = Case(
            When(facility_type__icontains=facility_query, then=Value(40)),
            When(endorsement__icontains=facility_query, then=Value(35)),
            default=Value(0),
            output_field=IntegerField()
        )
    else:
        annotation_params['facility_match'] = Value(0, output_field=IntegerField())
    
    # Main terms match
    if main_terms:
        main_query = " ".join(main_terms)
        annotation_params['main_match'] = Case(
            When(name__icontains=main_query, then=Value(30)),
            When(endorsement__icontains=main_query, then=Value(25)),
            default=Value(0),
            output_field=IntegerField()
        )
    else:
        annotation_params['main_match'] = Value(0, output_field=IntegerField())
    
    # Apply annotations
    queryset = queryset.annotate(**annotation_params)
    
    # Calculate total relevance
    queryset = queryset.annotate(
        relevance=F('name_exact_match') + 
                 F('name_contains') + 
                 F('location_match') + 
                 F('facility_match') + 
                 F('main_match')
    )
    
    # Order by relevance
    return queryset.order_by('-relevance')

def generate_fallback_summary(facilities, query, min_beds, max_beds):
    """
    Generate a fallback summary when Ollama fails
    """
    count = facilities.count()
    
    # Extract query components
    query_components = parse_query(query)
    has_location = len(query_components['location_terms']) > 0
    has_facility_type = len(query_components['facility_types']) > 0
    
    # Basic summary
    summary = f"Found {count} facilities matching your search"
    
    # Add bed count info if available
    if min_beds is not None and max_beds is not None:
        if min_beds == max_beds:
            summary += f" with {min_beds} beds."
        else:
            summary += f" with bed counts ranging from {min_beds} to {max_beds}."
    else:
        summary += "."
    
    # Add location-specific info
    if has_location:
        location = " ".join(query_components['location_terms'])
        summary += f" Services are available in the {location} area."
    
    # Add facility type info
    if has_facility_type:
        facility_type = " ".join(query_components['facility_types'])
        summary += f" These facilities provide specialized {facility_type} services."
    
    # Add general recommendation
    summary += " Consider comparing facilities with similar services to find the best fit for your specific needs."
    
    return summary

def generate_no_results_fallback(query):
    """
    Generate a fallback message when no results are found
    """
    query_components = parse_query(query)
    
    main_terms = query_components['main_terms']
    location_terms = query_components['location_terms']
    facility_types = query_components['facility_types']
    
    # Basic message
    message = f"No facilities found matching '{query}'."
    
    # Suggest alternatives
    if location_terms and facility_types:
        message += f" Try searching for '{' '.join(facility_types)}' without specifying a location, or search for other facilities in '{' '.join(location_terms)}'."
    elif location_terms:
        message += f" Try searching for facilities in nearby areas or use a broader region than '{' '.join(location_terms)}'."
    elif facility_types:
        message += f" Try using more general terms for facility types instead of '{' '.join(facility_types)}'."
    else:
        message += " Try using more general terms or check for spelling errors."
    
    # Add final tip
    message += " You can also clear all filters and try a new search."
    
    return message

def ollama_chat(prompt):
    """
    Send a prompt to Ollama and get the response
    """
    import requests
    import json
    
    try:
        # Configure this to match your Ollama setup
        url = "http://localhost:11434/api/generate"
        
        payload = {
            "model": "mistral",  # Use your preferred model
            "prompt": prompt,
            "stream": False,
            "max_tokens": 500
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "")
        else:
            return f"Error: Received status code {response.status_code} from Ollama API"
            
    except Exception as e:
        return f"Exception when calling Ollama API: {str(e)}"