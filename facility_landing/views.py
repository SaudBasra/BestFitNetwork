# facility_landing/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator

from search.models import Facility
from .models import FacilityLandingPage, FacilityGallery, FacilityTestimonial, LandingPageView
from .forms import FacilityLandingPageForm, FacilityGalleryForm, TestimonialForm

import logging

logger = logging.getLogger(__name__)


def public_landing_page(request, facility_id):
    """Public landing page view for a facility"""
    
    # Get facility and ensure it's active
    facility = get_object_or_404(Facility, id=facility_id, status='active')
    
    # Get or create landing page
    landing_page, created = FacilityLandingPage.objects.get_or_create(
        facility=facility,
        defaults={
            'hero_tagline': f"Welcome to {facility.name}",
            'hero_description': f"Quality care and comfortable living at {facility.name}.",
            'mission_statement': "Our mission is to provide exceptional care and support to our residents in a warm, welcoming environment.",
            'services_description': f"At {facility.name}, we offer comprehensive care services tailored to meet the unique needs of each resident.",
            'is_published': True,
        }
    )
    
    # Check if landing page is published
    if not landing_page.is_published:
        messages.warning(request, "This facility's landing page is currently under construction.")
        return redirect('search:facility_detail', facility_id=facility_id)
    
    # Get gallery images organized by category
    gallery_images = FacilityGallery.objects.filter(facility=facility).order_by('display_order', '-uploaded_at')
    gallery_by_category = {}
    for image in gallery_images:
        if image.category not in gallery_by_category:
            gallery_by_category[image.category] = []
        gallery_by_category[image.category].append(image)
    
    # Get approved testimonials
    testimonials = FacilityTestimonial.objects.filter(
        facility=facility,
        is_approved=True
    ).order_by('-is_featured', '-created_at')[:6]  # Show up to 6 testimonials
    
    # Get bed availability data
    bed_data = None
    try:
        from bedupdates.models import BedAvailability
        bed_data = BedAvailability.objects.filter(facility=facility).latest('updated_at')
    except:
        pass
    
    # Track page view (simple analytics)
    try:
        client_ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        referer = request.META.get('HTTP_REFERER', '')
        
        LandingPageView.objects.create(
            facility=facility,
            ip_address=client_ip,
            user_agent=user_agent,
            referer=referer
        )
    except Exception as e:
        logger.warning(f"Could not track page view: {e}")
    
    context = {
        'facility': facility,
        'landing_page': landing_page,
        'gallery_images': gallery_images[:12],  # Limit for performance
        'gallery_by_category': gallery_by_category,
        'testimonials': testimonials,
        'bed_data': bed_data,
        'featured_images': gallery_images.filter(is_featured=True)[:4],
    }
    
    return render(request, 'facility_landing/public_page.html', context)


@login_required
def landing_page_dashboard(request):
    """Dashboard for facility staff to manage their landing page"""
    
    # Get user's facility
    try:
        user_profile = request.user.user_profile
        if user_profile.user_type != 'facility_staff':
            messages.error(request, "Access denied - facility staff access required.")
            return redirect('search:home')
        facility = user_profile.facility
    except AttributeError:
        messages.error(request, "User profile not found.")
        return redirect('search:home')
    
    if not facility:
        messages.error(request, "No facility associated with your account.")
        return redirect('search:home')
    
    # Get or create landing page
    landing_page, created = FacilityLandingPage.objects.get_or_create(
        facility=facility,
        defaults={
            'hero_tagline': f"Welcome to {facility.name}",
            'hero_description': f"Quality care and comfortable living at {facility.name}.",
            'mission_statement': "Our mission is to provide exceptional care and support to our residents in a warm, welcoming environment.",
            'services_description': f"At {facility.name}, we offer comprehensive care services tailored to meet the unique needs of each resident.",
            'is_published': True,
            'last_updated_by': request.user,
        }
    )
    
    # Get gallery statistics
    gallery_count = FacilityGallery.objects.filter(facility=facility).count()
    testimonial_count = FacilityTestimonial.objects.filter(facility=facility, is_approved=True).count()
    
    # Get recent page views (last 30 days)
    from datetime import timedelta
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_views = LandingPageView.objects.filter(
        facility=facility,
        viewed_at__gte=thirty_days_ago
    ).count()
    
    context = {
        'facility': facility,
        'landing_page': landing_page,
        'gallery_count': gallery_count,
        'testimonial_count': testimonial_count,
        'recent_views': recent_views,
    }
    
    return render(request, 'facility_landing/dashboard.html', context)


@login_required
def edit_landing_page(request, facility_id=None):
    """Edit facility landing page content"""
    
    # Get user's facility
    try:
        user_profile = request.user.user_profile
        if user_profile.user_type != 'facility_staff':
            messages.error(request, "Access denied - facility staff access required.")
            return redirect('search:home')
        facility = user_profile.facility
    except AttributeError:
        messages.error(request, "User profile not found.")
        return redirect('search:home')
    
    # Security check - ensure user can only edit their own facility
    if facility_id and int(facility_id) != facility.id:
        messages.error(request, "You can only edit your own facility's landing page.")
        return redirect('facility_landing:dashboard')
    
    # Get or create landing page
    landing_page, created = FacilityLandingPage.objects.get_or_create(
        facility=facility,
        defaults={
            'last_updated_by': request.user,
        }
    )
    
    if request.method == 'POST':
        form = FacilityLandingPageForm(request.POST, request.FILES, instance=landing_page)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    landing_page = form.save(commit=False)
                    landing_page.facility = facility
                    landing_page.last_updated_by = request.user
                    landing_page.save()
                    
                    logger.info(f"Landing page updated for {facility.name} by {request.user.username}")
                    messages.success(request, "Landing page updated successfully!")
                    
                    return redirect('facility_landing:dashboard')
            except Exception as e:
                logger.error(f"Error updating landing page: {e}")
                messages.error(request, "An error occurred while saving. Please try again.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = FacilityLandingPageForm(instance=landing_page)
    
    context = {
        'form': form,
        'facility': facility,
        'landing_page': landing_page,
        'is_editing': True,
    }
    
    return render(request, 'facility_landing/edit_page.html', context)


@login_required
def manage_gallery(request):
    """Manage facility gallery images"""
    
    # Get user's facility
    try:
        user_profile = request.user.user_profile
        facility = user_profile.facility
    except AttributeError:
        messages.error(request, "User profile not found.")
        return redirect('search:home')
    
    # Get gallery images
    images = FacilityGallery.objects.filter(facility=facility).order_by('display_order', '-uploaded_at')
    
    # Handle image upload
    if request.method == 'POST':
        form = FacilityGalleryForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                image = form.save(commit=False)
                image.facility = facility
                image.uploaded_by = request.user
                image.save()
                
                messages.success(request, "Image uploaded successfully!")
                return redirect('facility_landing:manage_gallery')
            except Exception as e:
                logger.error(f"Error uploading image: {e}")
                messages.error(request, "Error uploading image. Please try again.")
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = FacilityGalleryForm()
    
    context = {
        'facility': facility,
        'images': images,
        'form': form,
        'image_count': images.count(),
    }
    
    return render(request, 'facility_landing/manage_gallery.html', context)


@login_required
@require_http_methods(["POST"])
def delete_gallery_image(request, image_id):
    """Delete a gallery image"""
    
    try:
        user_profile = request.user.user_profile
        facility = user_profile.facility
        
        image = get_object_or_404(FacilityGallery, id=image_id, facility=facility)
        image.delete()
        
        messages.success(request, "Image deleted successfully!")
    except Exception as e:
        logger.error(f"Error deleting image: {e}")
        messages.error(request, "Error deleting image.")
    
    return redirect('facility_landing:manage_gallery')


@login_required
def manage_testimonials(request):
    """Manage facility testimonials"""
    
    # Get user's facility
    try:
        user_profile = request.user.user_profile
        facility = user_profile.facility
    except AttributeError:
        messages.error(request, "User profile not found.")
        return redirect('search:home')
    
    # Get testimonials
    testimonials = FacilityTestimonial.objects.filter(facility=facility).order_by('-created_at')
    
    # Handle testimonial submission
    if request.method == 'POST':
        form = TestimonialForm(request.POST)
        if form.is_valid():
            try:
                testimonial = form.save(commit=False)
                testimonial.facility = facility
                testimonial.is_approved = True  # Auto-approve for facility staff
                testimonial.approved_by = request.user
                testimonial.save()
                
                messages.success(request, "Testimonial added successfully!")
                return redirect('facility_landing:manage_testimonials')
            except Exception as e:
                logger.error(f"Error adding testimonial: {e}")
                messages.error(request, "Error adding testimonial. Please try again.")
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = TestimonialForm()
    
    context = {
        'facility': facility,
        'testimonials': testimonials,
        'form': form,
        'testimonial_count': testimonials.count(),
    }
    
    return render(request, 'facility_landing/manage_testimonials.html', context)


@login_required
@require_http_methods(["POST"])
def toggle_testimonial_featured(request, testimonial_id):
    """Toggle featured status of a testimonial"""
    
    try:
        user_profile = request.user.user_profile
        facility = user_profile.facility
        
        testimonial = get_object_or_404(FacilityTestimonial, id=testimonial_id, facility=facility)
        testimonial.is_featured = not testimonial.is_featured
        testimonial.save()
        
        status = "featured" if testimonial.is_featured else "unfeatured"
        messages.success(request, f"Testimonial {status} successfully!")
    except Exception as e:
        logger.error(f"Error toggling testimonial featured status: {e}")
        messages.error(request, "Error updating testimonial.")
    
    return redirect('facility_landing:manage_testimonials')


def preview_landing_page(request, facility_id):
    """Preview landing page (same as public but with preview notice)"""
    
    context = public_landing_page(request, facility_id).context_data
    context['is_preview'] = True
    
    return render(request, 'facility_landing/public_page.html', context)


# Utility functions
def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# API Views for AJAX calls
@login_required
@require_http_methods(["POST"])
def update_image_order(request):
    """Update gallery image display order via AJAX"""
    
    try:
        user_profile = request.user.user_profile
        facility = user_profile.facility
        
        import json
        data = json.loads(request.body)
        image_orders = data.get('image_orders', [])
        
        with transaction.atomic():
            for item in image_orders:
                image_id = item.get('id')
                order = item.get('order')
                
                FacilityGallery.objects.filter(
                    id=image_id,
                    facility=facility
                ).update(display_order=order)
        
        return JsonResponse({'success': True, 'message': 'Image order updated successfully!'})
    
    except Exception as e:
        logger.error(f"Error updating image order: {e}")
        return JsonResponse({'success': False, 'message': 'Error updating image order.'})


@login_required
def landing_page_analytics(request):
    """Basic analytics for landing page views"""
    
    try:
        user_profile = request.user.user_profile
        facility = user_profile.facility
    except AttributeError:
        messages.error(request, "User profile not found.")
        return redirect('search:home')
    
    # Get view statistics
    from datetime import timedelta, date
    from django.db.models import Count
    from django.db.models.functions import TruncDate
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    # Daily views for the last 30 days
    daily_views = LandingPageView.objects.filter(
        facility=facility,
        viewed_at__gte=thirty_days_ago
    ).annotate(
        date=TruncDate('viewed_at')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Total views
    total_views = LandingPageView.objects.filter(facility=facility).count()
    
    # Recent views
    recent_views = LandingPageView.objects.filter(facility=facility).order_by('-viewed_at')[:10]
    
    context = {
        'facility': facility,
        'daily_views': daily_views,
        'total_views': total_views,
        'recent_views': recent_views,
    }
    
    return render(request, 'facility_landing/analytics.html', context)



# facility_landing/views.py (add this temporarily)
from django.http import HttpResponse

def test_landing_page(request, facility_id):
    return HttpResponse(f"Landing page for facility {facility_id} works!")

# facility_landing/views.py - Additional functions to add to your existing views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator

from search.models import Facility
from .models import FacilityLandingPage, FacilityGallery, FacilityTestimonial, LandingPageView
from .forms import FacilityLandingPageForm, FacilityGalleryForm, TestimonialForm

import logging

logger = logging.getLogger(__name__)


# Add these missing functions to your existing views.py file:

@login_required
@require_http_methods(["POST"])
def delete_gallery_image(request, image_id):
    """Delete a gallery image"""
    
    try:
        user_profile = request.user.user_profile
        facility = user_profile.facility
        
        image = get_object_or_404(FacilityGallery, id=image_id, facility=facility)
        
        # Delete the image file from storage
        if image.image:
            image.image.delete(save=False)
        
        # Delete the database record
        image.delete()
        
        messages.success(request, "Image deleted successfully!")
        logger.info(f"Gallery image {image_id} deleted by {request.user.username}")
        
    except Exception as e:
        logger.error(f"Error deleting image: {e}")
        messages.error(request, "Error deleting image.")
    
    return redirect('facility_landing:manage_gallery')


@login_required
@require_http_methods(["POST"])
def toggle_testimonial_featured(request, testimonial_id):
    """Toggle featured status of a testimonial"""
    
    try:
        user_profile = request.user.user_profile
        facility = user_profile.facility
        
        testimonial = get_object_or_404(FacilityTestimonial, id=testimonial_id, facility=facility)
        testimonial.is_featured = not testimonial.is_featured
        testimonial.save()
        
        status = "featured" if testimonial.is_featured else "unfeatured"
        messages.success(request, f"Testimonial {status} successfully!")
        
    except Exception as e:
        logger.error(f"Error toggling testimonial featured status: {e}")
        messages.error(request, "Error updating testimonial.")
    
    return redirect('facility_landing:manage_testimonials')


@login_required
@require_http_methods(["POST"])
def update_image_order(request):
    """Update gallery image display order via AJAX"""
    
    try:
        user_profile = request.user.user_profile
        facility = user_profile.facility
        
        import json
        data = json.loads(request.body)
        image_orders = data.get('image_orders', [])
        
        with transaction.atomic():
            for item in image_orders:
                image_id = item.get('id')
                order = item.get('order')
                
                FacilityGallery.objects.filter(
                    id=image_id,
                    facility=facility
                ).update(display_order=order)
        
        return JsonResponse({'success': True, 'message': 'Image order updated successfully!'})
    
    except Exception as e:
        logger.error(f"Error updating image order: {e}")
        return JsonResponse({'success': False, 'message': 'Error updating image order.'})


@login_required
def landing_page_analytics(request):
    """Basic analytics for landing page views"""
    
    try:
        user_profile = request.user.user_profile
        facility = user_profile.facility
    except AttributeError:
        messages.error(request, "User profile not found.")
        return redirect('search:home')
    
    # Get view statistics
    from datetime import timedelta, date
    from django.db.models import Count
    from django.db.models.functions import TruncDate
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    # Daily views for the last 30 days
    daily_views = LandingPageView.objects.filter(
        facility=facility,
        viewed_at__gte=thirty_days_ago
    ).annotate(
        date=TruncDate('viewed_at')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Total views
    total_views = LandingPageView.objects.filter(facility=facility).count()
    
    # Recent views
    recent_views = LandingPageView.objects.filter(facility=facility).order_by('-viewed_at')[:10]
    
    context = {
        'facility': facility,
        'daily_views': daily_views,
        'total_views': total_views,
        'recent_views': recent_views,
    }
    
    return render(request, 'facility_landing/analytics.html', context)


def preview_landing_page(request, facility_id):
    """Preview landing page (same as public but with preview notice)"""
    
    # Get facility and ensure it exists
    facility = get_object_or_404(Facility, id=facility_id)
    
    # Get or create landing page
    landing_page, created = FacilityLandingPage.objects.get_or_create(
        facility=facility,
        defaults={
            'hero_tagline': f"Welcome to {facility.name}",
            'hero_description': f"Quality care and comfortable living at {facility.name}.",
            'mission_statement': "Our mission is to provide exceptional care and support to our residents in a warm, welcoming environment.",
            'services_description': f"At {facility.name}, we offer comprehensive care services tailored to meet the unique needs of each resident.",
            'is_published': True,
        }
    )
    
    # Get gallery images organized by category
    gallery_images = FacilityGallery.objects.filter(facility=facility).order_by('display_order', '-uploaded_at')
    gallery_by_category = {}
    for image in gallery_images:
        if image.category not in gallery_by_category:
            gallery_by_category[image.category] = []
        gallery_by_category[image.category].append(image)
    
    # Get approved testimonials
    testimonials = FacilityTestimonial.objects.filter(
        facility=facility,
        is_approved=True
    ).order_by('-is_featured', '-created_at')[:6]
    
    # Get bed availability data
    bed_data = None
    try:
        from bedupdates.models import BedAvailability
        bed_data = BedAvailability.objects.filter(facility=facility).latest('updated_at')
    except:
        pass
    
    context = {
        'facility': facility,
        'landing_page': landing_page,
        'gallery_images': gallery_images[:12],
        'gallery_by_category': gallery_by_category,
        'testimonials': testimonials,
        'bed_data': bed_data,
        'featured_images': gallery_images.filter(is_featured=True)[:4],
        'is_preview': True,  # This marks it as preview mode
    }
    
    return render(request, 'facility_landing/public_page.html', context)


@login_required
def quick_update_landing_page(request):
    """Quick update API endpoint for AJAX updates"""
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST method required'})
    
    try:
        user_profile = request.user.user_profile
        facility = user_profile.facility
        
        landing_page, created = FacilityLandingPage.objects.get_or_create(
            facility=facility,
            defaults={'last_updated_by': request.user}
        )
        
        import json
        data = json.loads(request.body)
        
        # Update specific fields
        if 'hero_tagline' in data:
            landing_page.hero_tagline = data['hero_tagline']
        if 'hero_description' in data:
            landing_page.hero_description = data['hero_description']
        if 'is_published' in data:
            landing_page.is_published = data['is_published']
        
        landing_page.last_updated_by = request.user
        landing_page.save()
        
        return JsonResponse({'success': True, 'message': 'Landing page updated successfully!'})
        
    except Exception as e:
        logger.error(f"Error in quick update: {e}")
        return JsonResponse({'success': False, 'message': 'Error updating landing page'})


@login_required
def bulk_gallery_upload(request):
    """Handle bulk gallery image uploads"""
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST method required'})
    
    try:
        user_profile = request.user.user_profile
        facility = user_profile.facility
        
        uploaded_files = request.FILES.getlist('images')
        category = request.POST.get('category', 'other')
        
        if not uploaded_files:
            return JsonResponse({'success': False, 'message': 'No files uploaded'})
        
        uploaded_count = 0
        
        with transaction.atomic():
            for file in uploaded_files[:10]:  # Limit to 10 files
                try:
                    gallery_item = FacilityGallery.objects.create(
                        facility=facility,
                        image=file,
                        title=f"Gallery Image {uploaded_count + 1}",
                        category=category,
                        uploaded_by=request.user
                    )
                    uploaded_count += 1
                except Exception as e:
                    logger.error(f"Error uploading file {file.name}: {e}")
                    continue
        
        return JsonResponse({
            'success': True, 
            'message': f'{uploaded_count} images uploaded successfully!',
            'uploaded_count': uploaded_count
        })
        
    except Exception as e:
        logger.error(f"Error in bulk upload: {e}")
        return JsonResponse({'success': False, 'message': 'Error uploading images'})


# Utility function to get client IP (add this if not already present)
def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# Simple test view (can be removed later)
def test_landing_page(request, facility_id):
    """Test endpoint to verify everything is working"""
    facility = get_object_or_404(Facility, id=facility_id)
    return JsonResponse({
        'message': f'Landing page for {facility.name} is working!',
        'facility_id': facility_id,
        'facility_name': facility.name
    })